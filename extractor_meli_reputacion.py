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

import pandas as pd

from extractor_meli import MeliCuenta, CUENTAS, ZONA_AR

DIAS = 60
TOPE_ENVIOS_POR_CORRIDA = int(os.environ.get("MELI_TOPE_ENVIOS", "4000"))
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
def _limite(s):
    for ruta in (("lead_time", "estimated_handling_limit", "date"), ("shipping_option", "estimated_handling_limit", "date")):
        d = s
        for k in ruta:
            d = (d or {}).get(k) if isinstance(d, dict) else None
        if d:
            return d
    return None


def envio_demora(c, sid):
    r = c.get(f"/shipments/{sid}")
    if not _ok(r):
        return None
    s = r.json()
    h = s.get("status_history") or {}
    return {"limite_despacho": _limite(s), "fecha_despacho": h.get("date_shipped") or h.get("date_handling_completed"),
            "estado": s.get("status") or "", "subestado": s.get("substatus") or ""}


def demoras(cuentas_ok):
    if not os.path.exists("ventas_meli.csv"):
        print("   ⚠️ No está ventas_meli.csv: no puedo calcular demoras.")
        return
    v = pd.read_csv("ventas_meli.csv", usecols=lambda c_: c_ in {"marca", "orden_meli", "nro_pedido", "shipping_id", "fecha", "logistica", "total_orden_meli", "producto"},
                    low_memory=False)
    v["f"] = pd.to_datetime(v["fecha"], errors="coerce", format="mixed", utc=True)
    v = v[(v["f"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=DIAS)) & v["shipping_id"].notna() & (v["logistica"].astype(str) != "Full")]
    v["shipping_id"] = pd.to_numeric(v["shipping_id"], errors="coerce").astype("Int64").astype(str)
    v = v.sort_values("f", ascending=False).drop_duplicates(["marca", "shipping_id"])
    viejo = pd.read_csv(ARCH_DEM, dtype={"shipping_id": str}) if os.path.exists(ARCH_DEM) else pd.DataFrame(columns=["marca", "shipping_id"])
    cache = {(m, s): r for m, s, r in zip(viejo["marca"], viejo["shipping_id"], viejo.to_dict("records"))}
    ahora = pd.Timestamp.now(tz="UTC")
    filas, consultas = [], 0
    for _, x in v.iterrows():
        k = (x["marca"], x["shipping_id"])
        prev = cache.get(k)
        terminado = prev is not None and (pd.notna(prev.get("fecha_despacho")) and str(prev.get("fecha_despacho")) != "" or
                                          str(prev.get("estado")) in ("cancelled", "not_delivered"))
        base = {"marca": x["marca"], "orden_meli": x.get("orden_meli"), "nro_pedido": x.get("nro_pedido"), "shipping_id": x["shipping_id"],
                "fecha_venta": x["fecha"], "logistica": x.get("logistica"), "monto": x.get("total_orden_meli"), "producto": str(x.get("producto", ""))[:120]}
        if terminado or x["marca"] not in cuentas_ok or consultas >= TOPE_ENVIOS_POR_CORRIDA:
            if prev is not None:
                filas.append({**prev, **base})
            continue
        e = envio_demora(cuentas_ok[x["marca"]], x["shipping_id"])
        consultas += 1
        if e is None:
            if prev is not None:
                filas.append({**prev, **base})
            continue
        filas.append({**base, **e})
        time.sleep(0.05)
    df = pd.DataFrame(filas)
    if df.empty:
        return
    lim = pd.to_datetime(df["limite_despacho"], errors="coerce", utc=True)
    des = pd.to_datetime(df["fecha_despacho"], errors="coerce", utc=True)
    df["demora_horas"] = ((des - lim).dt.total_seconds() / 3600).round(1)
    df["demorado"] = (df["demora_horas"] > 0)
    sin = des.isna() & ~df["estado"].astype(str).isin(["cancelled", "not_delivered", "delivered"])
    df["en_riesgo"] = sin & lim.notna() & (lim <= ahora + pd.Timedelta(hours=24))
    df["vencido_sin_despachar"] = sin & lim.notna() & (lim < ahora)
    df.to_csv(ARCH_DEM, index=False)
    print(f"🚀 {ARCH_DEM}: {len(df):,} envíos ({consultas:,} consultados en esta corrida) · "
          f"{int(df['demorado'].sum()):,} despachados tarde · {int(df['vencido_sin_despachar'].sum()):,} vencidos sin despachar · "
          f"{int(df['en_riesgo'].sum()):,} en riesgo")
    pend = len(v) - len(df)
    if pend > 0:
        print(f"   ⏳ Faltan {pend:,} envíos por revisar: se completan en las próximas corridas.")


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
