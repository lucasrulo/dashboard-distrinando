"""
Publicidad MercadoLibre (Product Ads, API nueva) -> 3 CSV para el dashboard:

  meli_ads_campanias.csv  una fila por campaña: estado, estrategia, presupuesto, ACOS objetivo,
                          participación de impresiones y pérdida por presupuesto / por puja (30 días)
  meli_ads_diario.csv     una fila por campaña y día (últimos 90 días): impresiones, clics, inversión,
                          ventas directas/indirectas, unidades, orgánico
  meli_ads_items.csv      una fila por anuncio (publicación): métricas de 30 y 7 días

MeLi consolida las métricas una vez por día (10:00 hs): por eso trae hasta AYER.
Corre en el workflow diario (no hace falta cada 5 minutos).
"""
import os
import time
from datetime import datetime, timedelta

import pandas as pd

from extractor_meli import MeliCuenta, CUENTAS, ZONA_AR, API

SITE = "MLA"
BASE = f"/marketplace/advertising/{SITE}"
MET_CAMP = ("clicks,prints,ctr,cost,cpc,acos,cvr,roas,sov,direct_units_quantity,indirect_units_quantity,units_quantity,"
            "direct_amount,indirect_amount,total_amount,organic_units_quantity,organic_units_amount,"
            "direct_items_quantity,indirect_items_quantity,advertising_items_quantity,organic_items_quantity")
MET_IS = "impression_share,top_impression_share,lost_impression_share_by_budget,lost_impression_share_by_ad_rank,acos_benchmark"
MET_ADS = ("clicks,prints,cost,cpc,acos,direct_units_quantity,indirect_units_quantity,units_quantity,"
           "direct_amount,indirect_amount,total_amount,organic_units_quantity,organic_units_amount")
DIAS_HISTORIA = 89


def api_get(c, path, params=None, version="2"):
    """GET con el header de versión que pide la API de Product Ads (y reintentos)."""
    r = None
    for intento in range(5):
        h = {"Authorization": f"Bearer {c.tok['access_token']}", "api-version": version}
        r = c.s.get(f"{API}{path}", params=params, headers=h, timeout=40)
        if r.status_code == 401 and intento == 0:
            c.asegurar_token(forzar=True)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 * (intento + 1))
            continue
        return r
    return r


def metricas(obj):
    """Las métricas pueden venir en 'metrics', 'metrics_summary' o planas en el objeto."""
    m = obj.get("metrics") or obj.get("metrics_summary") or {}
    if not m:
        m = {k: v for k, v in obj.items() if isinstance(v, (int, float)) and k not in ("id", "campaign_id", "budget")}
    return m


def anunciantes(c):
    r = api_get(c, "/advertising/advertisers", {"product_id": "PADS"}, version="1")
    if r is None or r.status_code != 200:
        msg = getattr(r, "text", "")[:300]
        if r is not None and r.status_code in (401, 403):
            msg += " -> revisá que la app de MeLi tenga el permiso de 'Publicidad' (lectura)."
        print(f"   🚨 {c.marca}: advertisers HTTP {getattr(r, 'status_code', '?')} {msg}")
        return []
    advs = r.json().get("advertisers", [])
    return [a for a in advs if a.get("site_id", SITE) == SITE] or advs


def _rutas_campanias(adv):
    return [f"{BASE}/advertisers/{adv}/product_ads/campaigns/search",
            f"/advertising/advertisers/{adv}/product_ads/campaigns",
            f"{BASE}/advertisers/{adv}/product_ads/campaigns"]


def _rutas_detalle(cid):
    return [f"{BASE}/product_ads/campaigns/{cid}", f"/advertising/product_ads/campaigns/{cid}"]


RUTA_OK = {}  # recuerda qué variante de URL respondió bien, para no probar todas cada vez


def get_con_alternativas(c, clave, rutas, params):
    """Prueba las variantes de URL de la API de Product Ads hasta que una responda 200."""
    errores = []
    orden = [RUTA_OK[clave]] if clave in RUTA_OK else []
    orden += [i for i in range(len(rutas)) if i not in orden]
    for i in orden:
        r = api_get(c, rutas[i], params)
        if r is not None and r.status_code == 200:
            RUTA_OK[clave] = i
            return r
        errores.append(f"{rutas[i]} -> HTTP {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')[:150]}")
    return errores


def campanias(c, adv, desde, hasta):
    out, offset = [], 0
    while True:
        r = get_con_alternativas(c, "camp", _rutas_campanias(adv),
                                 {"limit": 50, "offset": offset, "date_from": desde, "date_to": hasta, "metrics": MET_CAMP})
        if isinstance(r, list):
            print(f"   🚨 {c.marca}: no pude listar campañas:")
            for e in r:
                print(f"        {e}")
            break
        d = r.json()
        res = d.get("results", []) if isinstance(d, dict) else d
        out.extend(res)
        offset += len(res)
        if not res or offset >= ((d.get("paging") or {}).get("total", 0) if isinstance(d, dict) else 0):
            break
    return out


def diario_campania(c, cid, desde, hasta):
    r = get_con_alternativas(c, "det", _rutas_detalle(cid),
                             {"date_from": desde, "date_to": hasta, "metrics": MET_CAMP, "aggregation_type": "DAILY"})
    if isinstance(r, list):
        if not getattr(diario_campania, "avisado", False):
            print(f"   ⚠️ {c.marca}: sin detalle diario de la campaña {cid}:")
            for e in r:
                print(f"        {e}")
            diario_campania.avisado = True
        return []
    d = r.json()
    filas = d if isinstance(d, list) else (d.get("results") or d.get("metrics") or d.get("daily") or [])
    out = []
    for f in filas if isinstance(filas, list) else []:
        fecha = f.get("date") or f.get("day")
        if fecha:
            out.append({"fecha": str(fecha)[:10], **metricas(f)})
    return out


def detalle_campania(c, cid, desde, hasta):
    """Datos de la campaña (nombre, estado, presupuesto...) + participación de impresiones."""
    r = get_con_alternativas(c, "det", _rutas_detalle(cid), {"date_from": desde, "date_to": hasta, "metrics": MET_IS})
    if isinstance(r, list):
        return {}
    d = r.json()
    return d if isinstance(d, dict) else {}


def fila_campania(marca, adv, cp, share):
    fila = {"marca": marca, "advertiser_id": adv, "campaign_id": cp.get("id") or cp.get("campaign_id"),
            "nombre": cp.get("name", ""), "estado": cp.get("status", ""), "estrategia": cp.get("strategy", ""),
            "presupuesto": cp.get("budget"), "acos_objetivo": cp.get("acos_target"),
            "presupuesto_automatico": cp.get("automatic_budget"),
            "creada": cp.get("date_created", ""), "actualizada": cp.get("last_updated", "")}
    fila.update({f"is_{k}": v for k, v in share.items()})
    return fila


def share_campania(c, cid, desde, hasta):
    r = get_con_alternativas(c, "det", _rutas_detalle(cid), {"date_from": desde, "date_to": hasta, "metrics": MET_IS})
    if isinstance(r, list):
        return {}
    return metricas(r.json())


def anuncios(c, adv, desde, hasta):
    out, offset = {}, 0
    rutas = [f"{BASE}/advertisers/{adv}/product_ads/ads/search", f"{BASE}/advertisers/{adv}/product_ads/ads"]
    ruta = rutas[0]
    while offset < 20000:
        params = {"limit": 50, "offset": offset, "date_from": desde, "date_to": hasta, "metrics": MET_ADS}
        r = api_get(c, ruta, params)
        if r is not None and r.status_code == 404 and ruta == rutas[0]:
            ruta = rutas[1]
            continue
        if r is None or r.status_code != 200:
            print(f"   🚨 {c.marca}: ads HTTP {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')[:300]}")
            break
        d = r.json()
        res = d.get("results", [])
        for a in res:
            out[a.get("item_id")] = a
        offset += len(res)
        if not res or offset >= (d.get("paging") or {}).get("total", 0):
            break
        time.sleep(0.1)
    return out


def sync():
    print(f"\n--- 📣 PUBLICIDAD MELI: {datetime.now(ZONA_AR):%d/%m %H:%M} ---")
    hoy = datetime.now(ZONA_AR).date()
    hasta = (hoy - timedelta(days=1)).isoformat()
    d90 = (hoy - timedelta(days=DIAS_HISTORIA)).isoformat()
    d30 = (hoy - timedelta(days=30)).isoformat()
    d7 = (hoy - timedelta(days=7)).isoformat()
    camp_rows, dia_rows, item_rows = [], [], []

    for marca, secret in CUENTAS.items():
        if not os.environ.get(secret):
            continue
        try:
            c = MeliCuenta(marca, secret)
            c.asegurar_token()
            for a in anunciantes(c):
                adv = a.get("advertiser_id")
                camps = campanias(c, adv, d30, hasta)
                for cp in camps:
                    cid = cp.get("id")
                    camp_rows.append(fila_campania(marca, adv, cp, share_campania(c, cid, d30, hasta)))
                    for dfila in diario_campania(c, cid, d90, hasta):
                        dia_rows.append({"marca": marca, "campaign_id": cid, **dfila})
                    time.sleep(0.1)
                a30 = anuncios(c, adv, d30, hasta)
                a7 = anuncios(c, adv, d7, hasta)
                # Si el listado de campañas falló, igual se trae el diario de las campañas que aparecen en los anuncios
                if not camps:
                    for cid in sorted({a.get("campaign_id") for a in a30.values() if a.get("campaign_id")}):
                        det = detalle_campania(c, cid, d30, hasta)
                        if det:
                            camp_rows.append(fila_campania(marca, adv, {"id": cid, **det}, metricas(det)))
                        for dfila in diario_campania(c, cid, d90, hasta):
                            dia_rows.append({"marca": marca, "campaign_id": cid, **dfila})
                        time.sleep(0.1)
                for iid, ad in a30.items():
                    fila = {"marca": marca, "item_id": iid, "campaign_id": ad.get("campaign_id"),
                            "titulo": ad.get("title", ""), "estado_ad": ad.get("status", ""), "precio": ad.get("price"),
                            "catalogo": ad.get("catalog_listing"), "buy_box_winner": ad.get("buy_box_winner"),
                            "nivel": ad.get("current_level", ""), "recomendado": ad.get("recommended"),
                            "con_descuento": ad.get("has_discount"), "logistica": ad.get("logistic_type", ""),
                            "thumbnail": ad.get("thumbnail", ""), "permalink": ad.get("permalink", "")}
                    fila.update({f"m30_{k}": v for k, v in metricas(ad).items()})
                    fila.update({f"m7_{k}": v for k, v in metricas(a7.get(iid, {})).items()})
                    item_rows.append(fila)
                print(f"   ✅ {marca}: {len(camps)} campañas, {len(a30)} anuncios")
        except Exception as e:
            print(f"   🚨 {marca}: {e}")

    ts = datetime.now(ZONA_AR).strftime("%Y-%m-%dT%H:%M:%S-03:00")
    for filas, nombre in [(camp_rows, "meli_ads_campanias.csv"), (dia_rows, "meli_ads_diario.csv"), (item_rows, "meli_ads_items.csv")]:
        if filas:
            df = pd.DataFrame(filas)
            df["actualizado"] = ts
            df.to_csv(nombre, index=False)
            print(f"🚀 {nombre}: {len(df):,} filas")


if __name__ == "__main__":
    try:
        sync()
    except Exception as e:
        print(f"🚨 Error crítico publicidad: {e}")
