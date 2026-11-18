"""
Reputación de MercadoLibre -> CSVs para el dashboard (pestaña Post-venta MeLi · Reputación).

  meli_reputacion.csv          foto actual de cada cuenta: color/nivel, MercadoLíder, ventas del período y las 3 variables
                               (reclamos, cancelaciones, despachos demorados) con % y cantidad, y lo que MeLi excluyó.
  meli_reputacion_hist.csv     una foto por día y cuenta (para ver la evolución).
  meli_reclamos_reputacion.csv por reclamo de los últimos 60 días: si AFECTA la reputación, si todavía se puede resolver
                               para que no cuente (has_incentive) y hasta cuándo (due_date).
  meli_demoras.csv             por envío (últimos 60 días, sin Full): límite de despacho vs. despacho real,
                               horas de demora, y los que están en riesgo AHORA (sin despachar y con el límite vencido o por vencer).

Corre en el workflow diario, después de Post-venta (usa meli_reclamos.csv y ventas_meli.csv del repo).
Los envíos ya despachados se guardan y no se vuelven a consultar; hay un tope por corrida para no frenar al robot de ventas.
"""
import os
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from extractor_meli import MeliCuenta, CUENTAS, ZONA_AR

DIAS = 60
TOPE_ENVIOS_POR_CORRIDA = int(os.environ.get("MELI_TOPE_ENVIOS", "30000"))
ARCH_DEM = "meli_demoras.csv"
ARCH_HIST = "meli_reputacion_hist.csv"


def _ok(r):
    return r is not None and r.status_code == 200


def _m(met, k):
    return (met or {}).get(k)


# ============================================================================== FOTO DE REPUTACIÓN
def reputacion(c):
    r = c.get(f"/users/{c.user_id}")
    if not _ok(r):
        print(f"   🚨 {c.marca}: no pude leer la reputación (HTTP {getattr(r, 'status_code', '?')})")
        return None
    rep = (r.json().get("seller_reputation") or {})
    met = rep.get("metrics") or {}
    tr = rep.get("transactions") or {}
    f = {"marca": c.marca, "nivel": rep.get("level_id") or "", "mercadolider": rep.get("power_seller_status") or "",
         "nivel_real": rep.get("real_level") or "", "proteccion_hasta": rep.get("protection_end_date") or "",
         "ventas_periodo": _m(met.get("sales"), "completed"), "periodo": _m(met.get("sales"), "period"),
         "historico_total": tr.get("total"), "historico_canceladas": tr.get("canceled"),
         "calif_positivas": ((tr.get("ratings") or {}).get("positive")), "calif_negativas": ((tr.get("ratings") or {}).get("negative"))}
    for clave, nombre in [("claims", "reclamos"), ("cancellations", "cancelaciones"), ("delayed_handling_time", "demoras")]:
        m = met.get(clave) or {}
        exc = m.get("excluded") or {}
        f[f"{nombre}_tasa"] = m.get("rate")
        f[f"{nombre}_cant"] = m.get("value")
        f[f"{nombre}_real_tasa"] = exc.get("real_rate")
        f[f"{nombre}_real_cant"] = exc.get("real_value")
    return f


# ============================================================================== RECLAMOS QUE AFECTAN
def reclamos_reputacion(c, rec):
    filas = []
    for _, x in rec.iterrows():
        r = c.get(f"/post-purchase/v1/claims/{x['claim_id']}/affects-reputation")
        d = r.json() if _ok(r) else {}
        filas.append({"marca": c.marca, "claim_id": x["claim_id"], "orden_meli": x.get("orden_meli"),
                      "afecta": d.get("affects_reputation") or ("sin dato" if not _ok(r) else ""),
                      "se_puede_resolver": d.get("has_incentive"), "resolver_hasta": d.get("due_date")})
        time.sleep(0.1)
    return filas


# ============================================================================== DEMORAS DE DESPACHO
# Fuente: la propia API de envíos de MeLi
#   /shipments/{id}/delays    -> MeLi marca 'handling_delayed' cuando el despacho fue tarde (lo que cuenta en la reputación)
#   /shipments/{id}/lead_time -> estimated_handling_limit.date = fecha límite para despachar
import requests
from concurrent.futures import ThreadPoolExecutor

API = "https://api.mercadolibre.com"
HILOS = 8
VERSION_DEM = 2      # si cambia la forma de calcular, se vuelve a consultar todo


def _get_json(tok, path):
    for intento in range(4):
        try:
            r = requests.get(f"{API}{path}", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        except Exception:
            time.sleep(1 + intento)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 * (intento + 1))
            continue
        return r.json() if r.status_code == 200 else None
    return None


def consultar_envio(tok, sid, pendiente):
    d = _get_json(tok, f"/shipments/{sid}/delays")
    dels = (d or {}).get("delays") or []
    hd = [x for x in dels if "handling" in str(x.get("type", ""))]
    out = {"meli_demora": (bool(hd) if d is not None else None), "tipo_demora": ",".join(sorted({str(x.get("type")) for x in dels})),
           "fecha_demora": (hd[0].get("date") if hd else None), "consultado": True, "version": VERSION_DEM}
    lt = _get_json(tok, f"/shipments/{sid}/lead_time") or {}
    out["limite_despacho"] = ((lt.get("estimated_handling_limit") or {}).get("date"))
    return out


def demoras(cuentas_ok):
    if not os.path.exists("ventas_meli.csv"):
        print("   ⚠️ No está ventas_meli.csv: no puedo calcular demoras.")
        return
    v = pd.read_csv("ventas_meli.csv", low_memory=False,
                    usecols=lambda c_: c_ in {"marca", "orden_meli", "nro_pedido", "shipping_id", "fecha", "logistica", "total_orden_meli",
                                               "producto", "fecha_despacho", "envio_estado", "envio_detalle", "provincia"})
    v["f"] = pd.to_datetime(v["fecha"], errors="coerce", format="mixed", utc=True)
    v = v[(v["f"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=DIAS)) & v["shipping_id"].notna() & (v["logistica"].astype(str) != "Full")]
    v["shipping_id"] = pd.to_numeric(v["shipping_id"], errors="coerce").astype("Int64").astype(str)
    prod = v.groupby(["marca", "shipping_id"])["producto"].agg(lambda x: " | ".join(dict.fromkeys(map(str, x)))[:200])
    v = v.sort_values("f", ascending=False).drop_duplicates(["marca", "shipping_id"])
    v["producto"] = [prod.get((m, s_), "") for m, s_ in zip(v["marca"], v["shipping_id"])]

    viejo = pd.read_csv(ARCH_DEM, dtype={"shipping_id": str}) if os.path.exists(ARCH_DEM) else pd.DataFrame()
    cache = {}
    if len(viejo) and "version" in viejo.columns:
        viejo = viejo[pd.to_numeric(viejo["version"], errors="coerce") == VERSION_DEM]
        cache = {(m, s_): r for m, s_, r in zip(viejo["marca"], viejo["shipping_id"], viejo.to_dict("records"))}

    pend_est = {"Pendiente", "Listo para despachar", ""}
    v["pendiente"] = v["fecha_despacho"].isna() & v["envio_estado"].fillna("").isin(pend_est)
    # qué consultar: pendientes (siempre) + despachados que todavía no están en el cache; los más recientes primero
    tareas = []
    for _, x in v.iterrows():
        k = (x["marca"], x["shipping_id"])
        if x["marca"] not in cuentas_ok:
            continue
        if x["pendiente"] or k not in cache or str(cache[k].get("meli_demora")).lower() not in ("true", "false"):
            tareas.append((k, x["pendiente"]))
    tareas = tareas[:TOPE_ENVIOS_POR_CORRIDA]
    print(f"   🔎 Demoras: {len(tareas):,} envíos a consultar ({HILOS} en paralelo)…")
    t0 = time.time()

    def _job(t):
        (m, s_), pend = t
        return (m, s_), consultar_envio(cuentas_ok[m].tok["access_token"], s_, pend)

    nuevos = {}
    with ThreadPoolExecutor(HILOS) as ex:
        for k, r in ex.map(_job, tareas):
            nuevos[k] = r
    print(f"   ⏱️ {len(nuevos):,} envíos consultados en {time.time() - t0:.0f}s")

    filas = []
    for _, x in v.iterrows():
        k = (x["marca"], x["shipping_id"])
        info = nuevos.get(k) or cache.get(k)
        if info is None:
            continue
        filas.append({"marca": x["marca"], "orden_meli": x["orden_meli"], "nro_pedido": x["nro_pedido"], "shipping_id": x["shipping_id"],
                      "fecha_venta": x["fecha"], "logistica": x["logistica"], "monto": x["total_orden_meli"], "producto": x["producto"],
                      "provincia": x.get("provincia"), "estado_envio": x["envio_estado"], "fecha_despacho": x["fecha_despacho"],
                      "limite_despacho": info.get("limite_despacho"), "meli_demora": info.get("meli_demora"),
                      "tipo_demora": info.get("tipo_demora"), "fecha_demora": info.get("fecha_demora"), "version": VERSION_DEM})
    df = pd.DataFrame(filas)
    if df.empty:
        return
    ahora = pd.Timestamp.now(tz="UTC")
    # MeLi: del límite solo vale la FECHA (la hora es de relleno) -> se toma el fin de ese día
    lim = (pd.to_datetime(df["limite_despacho"], errors="coerce", utc=True).dt.tz_convert(ZONA_AR).dt.normalize()
           + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).dt.tz_convert("UTC")
    des = pd.to_datetime(df["fecha_despacho"], errors="coerce", format="mixed", utc=True)
    df["demora_horas"] = ((des - lim).dt.total_seconds() / 3600).round(1)
    md = df["meli_demora"].astype(str).str.lower()
    # Lo que dice MeLi manda; si MeLi no respondió, se calcula con límite vs. despacho
    df["demorado"] = md.eq("true") | (~md.isin(["true", "false"]) & (df["demora_horas"] > 0))
    df["fuente_demora"] = np.where(md.isin(["true", "false"]), "MeLi", "Calculada")
    sin = des.isna() & df["estado_envio"].fillna("").isin(pend_est)
    df["en_riesgo"] = sin & lim.notna() & (lim <= ahora + pd.Timedelta(hours=24))
    df["vencido_sin_despachar"] = sin & lim.notna() & (lim < ahora)
    df.to_csv(ARCH_DEM, index=False)
    print(f"🚀 {ARCH_DEM}: {len(df):,} envíos · {int(df['demorado'].sum()):,} con demora según MeLi · "
          f"{int(df['vencido_sin_despachar'].sum()):,} vencidos sin despachar · {int(df['en_riesgo'].sum()):,} en riesgo")
    print("   " + " · ".join(f"{m}: {int(g['demorado'].sum())}/{len(g)}" for m, g in df.groupby("marca")))
    falta = len(v) - len(df)
    if falta > 0:
        print(f"   ⏳ Faltan {falta:,} envíos por revisar: se completan en la próxima corrida.")


def sync():
    ahora = datetime.now(ZONA_AR)
    print(f"\n--- ⭐ REPUTACIÓN MELI: {ahora:%d/%m %H:%M} ---")
    rec = pd.read_csv("meli_reclamos.csv") if os.path.exists("meli_reclamos.csv") else pd.DataFrame()
    if len(rec):
        rec = rec[pd.to_datetime(rec["fecha"], errors="coerce", utc=True) >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=DIAS)]
    fotos, rr, cuentas_ok = [], [], {}
    for marca, secret in CUENTAS.items():
        if not os.environ.get(secret):
            continue
        try:
            c = MeliCuenta(marca, secret)
            c.asegurar_token()
            cuentas_ok[marca] = c
            f = reputacion(c)
            if f:
                fotos.append(f)
                print(f"   ✅ {marca}: {f['nivel']} {f['mercadolider'] or ''} · reclamos {f['reclamos_tasa']} · "
                      f"cancelaciones {f['cancelaciones_tasa']} · demoras {f['demoras_tasa']} ({f['ventas_periodo']} ventas)")
            if len(rec):
                rr.extend(reclamos_reputacion(c, rec[rec["marca"] == marca]))
        except Exception as e:
            print(f"   🚨 {marca}: {e}")
    ts = ahora.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    if fotos:
        df = pd.DataFrame(fotos)
        df["actualizado"] = ts
        df.to_csv("meli_reputacion.csv", index=False)
        h = pd.read_csv(ARCH_HIST) if os.path.exists(ARCH_HIST) else pd.DataFrame()
        df["fecha"] = ahora.strftime("%Y-%m-%d")
        h = pd.concat([h, df], ignore_index=True).drop_duplicates(["marca", "fecha"], keep="last")
        h.to_csv(ARCH_HIST, index=False)
        print(f"🚀 meli_reputacion.csv: {len(df)} cuentas")
    if rr:
        d = pd.DataFrame(rr)
        d["actualizado"] = ts
        d.to_csv("meli_reclamos_reputacion.csv", index=False)
        print(f"🚀 meli_reclamos_reputacion.csv: {len(d):,} reclamos · {int((d['afecta'] == 'affected').sum())} afectan la reputación")
    try:
        demoras(cuentas_ok)
    except Exception as e:
        print(f"   ⚠️ Demoras: {e}")


if __name__ == "__main__":
    try:
        sync()
    except Exception as e:
        print(f"🚨 Error crítico reputación: {e}")
