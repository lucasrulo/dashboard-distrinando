"""
Google Ads -> CSVs para el dashboard (pestaña "Google Ads").

  gads_campanias_diario.csv   una fila por campaña y día (últimos 90 días, incluye HOY parcial):
                              inversión, impresiones, clics, conversiones, valor, % impresiones perdidas.
  gads_productos.csv          productos de Shopping / Performance Max (últimos 7 y 30 días) + SKU y stock de Shopify.
  gads_terminos.csv           búsquedas que activaron los anuncios (30 días, las 500 con más gasto por cuenta).
  gads_recomendaciones.csv    recomendaciones de Google con su impacto estimado.

Usa la API REST de Google Ads (sin librería) con OAuth. Secretos:
  GADS_CLIENT_ID, GADS_CLIENT_SECRET, GADS_REFRESH_TOKEN
  GADS_LOGIN_CUSTOMER_ID   (solo si las cuentas cuelgan de una cuenta administradora; sin guiones)
  GADS_CUENTAS             JSON {"Reebok": "1234567890", "Columbia": ["111", "222"]}  (marca -> cuenta o lista de cuentas)
"""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

ZONA_AR = timezone(timedelta(hours=-3))
VERSIONES = ["v25", "v24", "v23", "v22", "v21"]   # se usa la primera que responda
DIAS_HISTORIA = 90
VERSION_OK = None


def _limpio(x):
    return re.sub(r"\D", "", str(x or ""))


def access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GADS_CLIENT_ID"], "client_secret": os.environ["GADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GADS_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"No pude renovar el token de Google ({r.status_code}): {r.text[:300]}")
    return r.json()["access_token"]


LOGIN_OK = {}        # cuenta -> login-customer-id que funcionó ("" = sin login)
CANDIDATOS_LOGIN = []


def _headers(tok, login):
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    if login:
        h["login-customer-id"] = login
    if os.environ.get("GADS_DEVELOPER_TOKEN"):        # opcional desde sept/2026
        h["developer-token"] = os.environ["GADS_DEVELOPER_TOKEN"]
    return h


def _msg(r):
    try:
        d = r.json()
        d = d[0] if isinstance(d, list) else d
        errs = (((d.get("error") or {}).get("details") or [{}])[0].get("errors") or [])
        if errs:
            return f"{list(errs[0].get('errorCode', {}).values())[0]}: {errs[0].get('message', '')[:200]}"
        return (d.get("error") or {}).get("message", r.text[:300])
    except Exception:
        return r.text[:300]


def _post(tok, cid, query, login):
    global VERSION_OK
    versiones = [VERSION_OK] if VERSION_OK else VERSIONES
    r = None
    for v in versiones:
        for intento in range(3):
            r = requests.post(f"https://googleads.googleapis.com/{v}/customers/{cid}/googleAds:searchStream",
                              headers=_headers(tok, login), json={"query": query}, timeout=120)
            if r.status_code in (429, 500, 503):
                time.sleep(5 * (intento + 1))
                continue
            break
        if r.status_code == 404 and not VERSION_OK:
            continue
        if r.status_code == 200:
            VERSION_OK = v
        return r
    return r


def gaql(tok, cid, query):
    """Corre una consulta GAQL con searchStream. Si la cuenta da 'sin permiso', prueba con cada cuenta
    administradora accesible como login-customer-id (y sin login) y recuerda la que funcionó."""
    if cid in LOGIN_OK:
        orden = [LOGIN_OK[cid]]
    else:
        orden = []
        for x in [_limpio(os.environ.get("GADS_LOGIN_CUSTOMER_ID"))] + CANDIDATOS_LOGIN + [""]:
            if x not in orden and x != cid:
                orden.append(x)
        orden.append(cid)     # la cuenta como su propio login
    errores = []
    for login in orden:
        r = _post(tok, cid, query, login)
        if r is not None and r.status_code == 200:
            LOGIN_OK[cid] = login
            filas = []
            for bloque in r.json():
                filas.extend(bloque.get("results", []))
            return filas
        errores.append(f"login={login or 'ninguno'} -> HTTP {getattr(r, 'status_code', '?')} {_msg(r) if r is not None else ''}")
        if r is not None and r.status_code not in (401, 403):
            break
    raise RuntimeError(" | ".join(errores))


def diagnostico(tok):
    """Lista las cuentas a las que tiene acceso el usuario que generó el refresh token."""
    global VERSION_OK
    ids = []
    for v in ([VERSION_OK] if VERSION_OK else VERSIONES):
        r = requests.get(f"https://googleads.googleapis.com/{v}/customers:listAccessibleCustomers",
                         headers=_headers(tok, ""), timeout=60)
        if r.status_code == 404:
            continue
        if r.status_code != 200:
            print(f"   ⚠️ No pude listar las cuentas accesibles: HTTP {r.status_code} {_msg(r)}")
            return
        VERSION_OK = v
        ids = [x.split("/")[-1] for x in r.json().get("resourceNames", [])]
        break
    print(f"   👤 El usuario del token accede directo a {len(ids)} cuenta(s) (API {VERSION_OK}):")
    for i in ids:
        try:
            r = _post(tok, i, "SELECT customer.id, customer.descriptive_name, customer.manager FROM customer", i)
            d = (r.json()[0].get("results") or [{}])[0].get("customer", {}) if r.status_code == 200 else {}
            es_mcc = bool(d.get("manager"))
            print(f"      · {i}  {d.get('descriptiveName', '(sin nombre)')}  {'[ADMINISTRADORA]' if es_mcc else ''}")
            if es_mcc and i not in CANDIDATOS_LOGIN:
                CANDIDATOS_LOGIN.append(i)
        except Exception as e:
            print(f"      · {i}  (no pude leer el nombre: {e})")


def _g(d, ruta, default=None):
    for k in ruta.split("."):
        if not isinstance(d, dict):
            return default
        d = d.get(k)
    return default if d is None else d


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _pct(x):
    """Las métricas de % vienen como fracción (0.23). Devuelve 23.0 o None."""
    try:
        return round(float(x) * 100, 1)
    except (TypeError, ValueError):
        return None


# ============================================================================== CONSULTAS
def campanias_diario(tok, marca, cid, desde, hasta):
    q = f"""
        SELECT segments.date, campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type,
               campaign.bidding_strategy_type, campaign_budget.amount_micros,
               metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value,
               metrics.search_impression_share, metrics.search_budget_lost_impression_share,
               metrics.search_rank_lost_impression_share
        FROM campaign
        WHERE segments.date BETWEEN '{desde}' AND '{hasta}' AND campaign.status != 'REMOVED'"""
    out = []
    for r in gaql(tok, cid, q):
        m = r.get("metrics", {})
        out.append({"marca": marca, "cuenta": cid, "fecha": _g(r, "segments.date"),
                    "campaign_id": _g(r, "campaign.id"), "campania": _g(r, "campaign.name", ""),
                    "estado": _g(r, "campaign.status", ""), "tipo": _g(r, "campaign.advertisingChannelType", ""),
                    "puja": _g(r, "campaign.biddingStrategyType", ""),
                    "presupuesto_diario": _num(_g(r, "campaignBudget.amountMicros")) / 1e6,
                    "inversion": _num(m.get("costMicros")) / 1e6, "impresiones": _num(m.get("impressions")),
                    "clics": _num(m.get("clicks")), "conversiones": _num(m.get("conversions")),
                    "valor_conv": _num(m.get("conversionsValue")),
                    "is_impresiones": _pct(m.get("searchImpressionShare")),
                    "is_perdida_presupuesto": _pct(m.get("searchBudgetLostImpressionShare")),
                    "is_perdida_ranking": _pct(m.get("searchRankLostImpressionShare"))})
    return out


def productos(tok, marca, cid, periodo):
    q = f"""
        SELECT segments.product_item_id, segments.product_title, campaign.id, campaign.name,
               metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value
        FROM shopping_performance_view
        WHERE segments.date DURING {periodo}"""
    out = []
    for r in gaql(tok, cid, q):
        m = r.get("metrics", {})
        out.append({"marca": marca, "item_id": str(_g(r, "segments.productItemId", "")),
                    "titulo": _g(r, "segments.productTitle", ""), "campania": _g(r, "campaign.name", ""),
                    "inversion": _num(m.get("costMicros")) / 1e6, "impresiones": _num(m.get("impressions")),
                    "clics": _num(m.get("clicks")), "conversiones": _num(m.get("conversions")),
                    "valor_conv": _num(m.get("conversionsValue"))})
    return out


def terminos(tok, marca, cid):
    q = """
        SELECT search_term_view.search_term, campaign.name, ad_group.name,
               metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value
        FROM search_term_view
        WHERE segments.date DURING LAST_30_DAYS AND metrics.cost_micros > 0
        ORDER BY metrics.cost_micros DESC
        LIMIT 500"""
    out = []
    for r in gaql(tok, cid, q):
        m = r.get("metrics", {})
        out.append({"marca": marca, "termino": _g(r, "searchTermView.searchTerm", ""),
                    "campania": _g(r, "campaign.name", ""), "grupo": _g(r, "adGroup.name", ""),
                    "inversion": _num(m.get("costMicros")) / 1e6, "impresiones": _num(m.get("impressions")),
                    "clics": _num(m.get("clicks")), "conversiones": _num(m.get("conversions")),
                    "valor_conv": _num(m.get("conversionsValue"))})
    return out


def recomendaciones(tok, marca, cid):
    q = "SELECT recommendation.type, recommendation.campaign FROM recommendation"
    out = []
    for r in gaql(tok, cid, q):
        rec = r.get("recommendation", {})
        out.append({"marca": marca, "tipo": rec.get("type", ""), "campaign_id": str(rec.get("campaign", "")).split("/")[-1]})
    return out


# ============================================================================== SHOPIFY: id de variante -> SKU y stock
def variantes_shopify():
    """El feed de Shopify publica cada producto como shopify_AR_<producto>_<variante>.
    Se baja de cada tienda el SKU y el stock de cada variante para cruzarlos."""
    try:
        from extractor import STORES, API_VERSION
    except Exception as e:
        print(f"   ⚠️ No pude leer las tiendas de Shopify: {e}")
        return {}
    mapa = {}
    for marca, info in STORES.items():
        if not info.get("token"):
            continue
        url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}/products.json"
        params = {"limit": 250, "fields": "id,status,variants"}
        h = {"X-Shopify-Access-Token": info["token"]}
        for _ in range(200):
            r = requests.get(url, headers=h, params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(3)
                continue
            if r.status_code != 200:
                print(f"   ⚠️ Shopify {marca}: HTTP {r.status_code}")
                break
            for p in r.json().get("products", []):
                for v in p.get("variants") or []:
                    mapa[str(v.get("id"))] = {"sku": v.get("sku") or "", "stock": v.get("inventory_quantity"),
                                              "estado_producto": p.get("status", "")}
            url = r.links.get("next", {}).get("url")
            params = None
            if not url:
                break
            time.sleep(0.5)
    print(f"   🛍️ Shopify: {len(mapa):,} variantes para cruzar con Google")
    return mapa


def cruzar_productos(df, mapa):
    if df.empty:
        return df
    var = df["item_id"].str.extract(r"_(\d+)$")[0]
    df["variant_id"] = var.fillna("")
    df["sku"] = [mapa.get(v, {}).get("sku", "") for v in df["variant_id"]]
    df["stock"] = [mapa.get(v, {}).get("stock") for v in df["variant_id"]]
    df["estado_producto"] = [mapa.get(v, {}).get("estado_producto", "") for v in df["variant_id"]]
    # Si el feed usa el SKU como id, se usa directo
    sin = df["sku"] == ""
    df.loc[sin, "sku"] = df.loc[sin, "item_id"].where(~df.loc[sin, "item_id"].str.startswith("shopify_"), "")
    return df


# ============================================================================== MAIN
def sync():
    ahora = datetime.now(ZONA_AR)
    print(f"\n--- 🔎 GOOGLE ADS: {ahora:%d/%m %H:%M} ---")
    cuentas = json.loads(os.environ.get("GADS_CUENTAS") or "{}")
    if not cuentas:
        print("🚨 Falta el secreto GADS_CUENTAS, por ejemplo {\"Reebok\": \"1234567890\"}")
        return
    tok = access_token()
    diagnostico(tok)
    hoy = ahora.date()
    desde = (hoy - timedelta(days=DIAS_HISTORIA)).isoformat()
    camp, prods, terms, recs = [], [], [], []
    pares = [(m, _limpio(c)) for m, v in cuentas.items() for c in (v if isinstance(v, list) else [v])]
    for marca, cid in pares:   # una marca puede tener varias cuentas: se suman
        try:
            c = campanias_diario(tok, marca, cid, desde, hoy.isoformat())
            camp.extend(c)
            print(f"   ✅ {marca} ({cid}): {len(c):,} filas campaña-día · API {VERSION_OK}")
        except Exception as e:
            print(f"   🚨 {marca} campañas: {e}")
            continue
        for periodo, sufijo in [("LAST_30_DAYS", "30d"), ("LAST_7_DAYS", "7d")]:
            try:
                p = productos(tok, marca, cid, periodo)
                for x in p:
                    x["periodo"] = sufijo
                prods.extend(p)
            except Exception as e:
                print(f"   ⚠️ {marca} productos {sufijo}: {e}")
        try:
            terms.extend(terminos(tok, marca, cid))
        except Exception as e:
            print(f"   ⚠️ {marca} búsquedas: {e}")
        try:
            recs.extend(recomendaciones(tok, marca, cid))
        except Exception as e:
            print(f"   ⚠️ {marca} recomendaciones: {e}")

    ts = ahora.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    dp = pd.DataFrame(prods)
    if not dp.empty:
        dp = dp[dp["item_id"].astype(str) != ""]
        info = dp.groupby(["marca", "item_id"], as_index=False).agg(titulo=("titulo", "first"),
                                                                    campania=("campania", lambda x: " | ".join(sorted(set(map(str, x))))[:150]))
        met = ["inversion", "impresiones", "clics", "conversiones", "valor_conv"]
        pv = dp.groupby(["marca", "item_id", "periodo"])[met].sum().unstack("periodo").fillna(0)
        pv.columns = [f"{m}_{per}" for m, per in pv.columns]
        dp = info.merge(pv.reset_index(), on=["marca", "item_id"], how="left").fillna(0)
        for c_ in [f"{m}_{per}" for m in met for per in ("7d", "30d")]:
            if c_ not in dp.columns:
                dp[c_] = 0.0
        dp = dp[(dp["inversion_30d"] > 0) | (dp["valor_conv_30d"] > 0)]
        dp = cruzar_productos(dp, variantes_shopify())
        for c_ in dp.columns:
            if c_.startswith(("inversion", "valor_conv", "conversiones")):
                dp[c_] = dp[c_].round(2)
    for filas, nombre in [(pd.DataFrame(camp), "gads_campanias_diario.csv"), (dp, "gads_productos.csv"),
                          (pd.DataFrame(terms), "gads_terminos.csv"), (pd.DataFrame(recs), "gads_recomendaciones.csv")]:
        if len(filas):
            filas["actualizado"] = ts
            filas.to_csv(nombre, index=False)
            print(f"🚀 {nombre}: {len(filas):,} filas")


if __name__ == "__main__":
    sync()
