"""
Google Analytics 4 -> CSVs para el dashboard (pestaña "Tráfico web").

  ga4_canales_diario.csv     por marca, día y canal (Orgánico, Pago, Directo, Social, Email...):
                             sesiones, usuarios, nuevos, sesiones con interacción, carritos, checkouts, compras e ingresos.
  ga4_embudo_diario.csv      por marca y día: vistas de producto, agregados al carrito, inicios de checkout, compras.
  ga4_dispositivo_diario.csv por marca, día y dispositivo (mobile / desktop / tablet).
  ga4_landing.csv            páginas de entrada de los últimos 30 días (top 300 por marca).
  ga4_fuente.csv             fuente / medio de los últimos 30 días (top 150 por marca).
  ga4_region.csv             provincia de los últimos 30 días.

Usa la API de datos de GA4 (REST) con el mismo OAuth que Google Ads (el refresh token tiene que incluir
el permiso analytics.readonly). Secretos: GADS_CLIENT_ID, GADS_CLIENT_SECRET, GADS_REFRESH_TOKEN y
GA4_PROPIEDADES = {"Reebok": "333721081", ...}  (marca -> ID numérico de la propiedad).
"""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

ZONA_AR = timezone(timedelta(hours=-3))
DIAS = 90
URL = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"


def access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GADS_CLIENT_ID"], "client_secret": os.environ["GADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GADS_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"No pude renovar el token de Google ({r.status_code}): {r.text[:300]}")
    d = r.json()
    if "analytics" not in d.get("scope", ""):
        print("   ⚠️ El refresh token NO tiene el permiso de Analytics (analytics.readonly). "
              "Generalo de nuevo en el OAuth Playground con los dos permisos y actualizá GADS_REFRESH_TOKEN.")
    return d["access_token"]


def reporte(tok, pid, dims, mets, desde, hasta="today", filtro=None, orden=None, limite=100000):
    body = {"dateRanges": [{"startDate": desde, "endDate": hasta}],
            "dimensions": [{"name": d} for d in dims], "metrics": [{"name": m} for m in mets], "limit": limite}
    if filtro:
        body["dimensionFilter"] = filtro
    if orden:
        body["orderBys"] = [{"metric": {"metricName": orden}, "desc": True}]
    filas, offset = [], 0
    while True:
        body["offset"] = offset
        for intento in range(3):
            r = requests.post(URL.format(pid=pid), headers={"Authorization": f"Bearer {tok}"}, json=body, timeout=120)
            if r.status_code in (429, 500, 503):
                time.sleep(5 * (intento + 1))
                continue
            break
        if r.status_code != 200:
            try:
                msg = r.json().get("error", {}).get("message", r.text[:300])
            except Exception:
                msg = r.text[:300]
            raise RuntimeError(f"HTTP {r.status_code}: {msg}")
        d = r.json()
        for row in d.get("rows", []):
            f = {dims[i]: v.get("value") for i, v in enumerate(row.get("dimensionValues", []))}
            for i, v in enumerate(row.get("metricValues", [])):
                try:
                    f[mets[i]] = float(v.get("value") or 0)
                except ValueError:
                    f[mets[i]] = 0.0
            filas.append(f)
        total = int(d.get("rowCount") or 0)
        offset += limite
        if offset >= total or limite < 100000:
            break
    return pd.DataFrame(filas)


def _fecha(df):
    if "date" in df.columns:
        df["fecha"] = pd.to_datetime(df["date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
        df = df.drop(columns="date")
    return df


RENOMBRE = {"sessions": "sesiones", "totalUsers": "usuarios", "newUsers": "nuevos", "engagedSessions": "sesiones_interaccion",
            "addToCarts": "carritos", "checkouts": "checkouts", "ecommercePurchases": "compras", "purchaseRevenue": "ingresos",
            "sessionDefaultChannelGroup": "canal", "deviceCategory": "dispositivo", "landingPage": "landing",
            "sessionSourceMedium": "fuente_medio", "region": "region", "eventName": "evento", "eventCount": "cantidad"}

TRAD_CANAL = {"Organic Search": "Búsqueda orgánica", "Paid Search": "Búsqueda paga", "Direct": "Directo", "Organic Social": "Social orgánico",
              "Paid Social": "Social pago", "Email": "Email", "Referral": "Referidos", "Cross-network": "Google Ads (PMax/Demand Gen)",
              "Paid Shopping": "Shopping pago", "Organic Shopping": "Shopping orgánico", "Paid Video": "Video pago",
              "Organic Video": "Video orgánico", "Display": "Display", "Paid Other": "Otros pagos", "Unassigned": "Sin asignar",
              "Affiliates": "Afiliados", "SMS": "SMS", "Mobile Push Notifications": "Notificaciones", "Audio": "Audio"}
TRAD_DISP = {"mobile": "Celular", "desktop": "Computadora", "tablet": "Tablet", "smart tv": "Smart TV"}


def sync():
    ahora = datetime.now(ZONA_AR)
    print(f"\n--- 📈 GOOGLE ANALYTICS 4: {ahora:%d/%m %H:%M} ---")
    props = json.loads(os.environ.get("GA4_PROPIEDADES") or "{}")
    if not props:
        print("🚨 Falta el secreto GA4_PROPIEDADES, por ejemplo {\"Reebok\": \"333721081\"}")
        return
    tok = access_token()
    desde = f"{DIAS}daysAgo"
    salida = {k: [] for k in ["canales", "embudo", "dispositivo", "landing", "fuente", "region"]}
    for marca, pid in props.items():
        pid = re.sub(r"\D", "", str(pid))
        try:
            c = reporte(tok, pid, ["date", "sessionDefaultChannelGroup"],
                        ["sessions", "totalUsers", "newUsers", "engagedSessions", "addToCarts", "checkouts", "ecommercePurchases", "purchaseRevenue"], desde)
        except Exception as e:
            print(f"   🚨 {marca} ({pid}): {e}")
            if "403" in str(e):
                print("        -> el mail del token no tiene acceso a esta propiedad, o la propiedad no es la correcta.")
            continue
        c = _fecha(c).rename(columns=RENOMBRE)
        c["canal"] = c["canal"].map(TRAD_CANAL).fillna(c["canal"])
        c.insert(0, "marca", marca)
        salida["canales"].append(c)
        u7 = c[pd.to_datetime(c["fecha"]) >= pd.Timestamp(ahora.date() - timedelta(days=7))]
        print(f"   ✅ {marca} ({pid}): últimos 7 días {u7['sesiones'].sum():,.0f} sesiones · {u7['compras'].sum():,.0f} compras · "
              f"$ {u7['ingresos'].sum():,.0f}")
        pasos = [
            ("embudo", ["date", "eventName"], ["eventCount"], desde,
             {"filter": {"fieldName": "eventName", "inListFilter": {"values": ["view_item", "add_to_cart", "begin_checkout", "add_payment_info", "purchase"]}}}, None, 100000),
            ("dispositivo", ["date", "deviceCategory"], ["sessions", "addToCarts", "ecommercePurchases", "purchaseRevenue"], desde, None, None, 100000),
            ("landing", ["landingPage"], ["sessions", "engagedSessions", "addToCarts", "ecommercePurchases", "purchaseRevenue"], "30daysAgo", None, "sessions", 300),
            ("fuente", ["sessionSourceMedium"], ["sessions", "engagedSessions", "ecommercePurchases", "purchaseRevenue"], "30daysAgo", None, "sessions", 150),
            ("region", ["region"], ["sessions", "ecommercePurchases", "purchaseRevenue"], "30daysAgo", None, "sessions", 100),
        ]
        for nombre, dims, mets, d0, filtro, orden, lim in pasos:
            try:
                df = _fecha(reporte(tok, pid, dims, mets, d0, filtro=filtro, orden=orden, limite=lim)).rename(columns=RENOMBRE)
                if "dispositivo" in df.columns:
                    df["dispositivo"] = df["dispositivo"].map(TRAD_DISP).fillna(df["dispositivo"])
                df.insert(0, "marca", marca)
                salida[nombre].append(df)
            except Exception as e:
                print(f"   ⚠️ {marca} {nombre}: {e}")

    ts = ahora.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    for nombre, archivo in [("canales", "ga4_canales_diario.csv"), ("embudo", "ga4_embudo_diario.csv"), ("dispositivo", "ga4_dispositivo_diario.csv"),
                            ("landing", "ga4_landing.csv"), ("fuente", "ga4_fuente.csv"), ("region", "ga4_region.csv")]:
        if salida[nombre]:
            df = pd.concat(salida[nombre], ignore_index=True)
            for c_ in df.columns:
                if df[c_].dtype == float:
                    df[c_] = df[c_].round(2)
            df["actualizado"] = ts
            df.to_csv(archivo, index=False)
            print(f"🚀 {archivo}: {len(df):,} filas")


if __name__ == "__main__":
    try:
        sync()
    except Exception as e:
        print(f"🚨 Error crítico GA4: {e}")
