"""
Backfill de ventas de un período pasado (Tienda Online + MercadoLibre) -> ventas_<desde>_<hasta>.csv
Sirve para comparar meses del año anterior (ej. noviembre y diciembre de 2025) y armar objetivos.

Una fila por pedido: canal, marca, id_pedido, fecha, total_pedido, unidades, es_reverso.
Al final imprime en el log el resumen por mes, canal y marca, y el crecimiento de un mes al otro.

Fechas por variables de entorno (las carga el workflow): BACKFILL_DESDE=2025-11-01  BACKFILL_HASTA=2025-12-31
"""
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

ZONA_AR = timezone(timedelta(hours=-3))
DESDE = datetime.fromisoformat(os.environ.get("BACKFILL_DESDE") or "2025-11-01").replace(tzinfo=ZONA_AR)
HASTA = datetime.fromisoformat(os.environ.get("BACKFILL_HASTA") or "2025-12-31").replace(hour=23, minute=59, second=59, tzinfo=ZONA_AR)
ARCHIVO = f"ventas_{DESDE:%Y%m%d}_{HASTA:%Y%m%d}.csv"


def shopify():
    from extractor import STORES, API_VERSION
    filas = []
    for marca, info in STORES.items():
        if not info["token"]:
            continue
        url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}/orders.json"
        params = {"limit": 250, "status": "any", "created_at_min": DESDE.isoformat(), "created_at_max": HASTA.isoformat(),
                  "fields": "id,created_at,total_price,tags,cancelled_at,financial_status,payment_gateway_names,line_items"}
        h = {"X-Shopify-Access-Token": info["token"]}
        n = 0
        for _ in range(2000):
            r = requests.get(url, headers=h, params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(3)
                continue
            if r.status_code != 200:
                print(f"   🚨 Shopify {marca}: HTTP {r.status_code} {r.text[:200]}")
                if r.status_code == 403:
                    print("      -> el token no puede leer pedidos de más de 60 días: hace falta el permiso 'read_all_orders' en la app de Shopify.")
                break
            for o in r.json().get("orders", []):
                pago = str(o.get("financial_status") or "").lower()
                if pago in ("expired", "voided"):
                    continue
                tags = str(o.get("tags") or "").lower()
                gw = " ".join(o.get("payment_gateway_names") or []).lower()
                rev = 1 if ("reversso" in tags or "reversso" in gw or o.get("cancelled_at") or pago == "refunded") else 0
                fecha = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).astimezone(ZONA_AR)
                filas.append({"canal": "Tienda Online", "marca": marca, "id_pedido": o["id"], "fecha": fecha.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
                              "total_pedido": float(o.get("total_price") or 0),
                              "unidades": sum(int(i.get("quantity") or 0) for i in (o.get("line_items") or [])), "es_reverso": rev})
                n += 1
            url = r.links.get("next", {}).get("url")
            params = None
            if not url:
                break
            time.sleep(0.5)
        print(f"   ✅ Shopify {marca}: {n:,} pedidos")
    return filas


def meli():
    from extractor_meli import MeliCuenta, CUENTAS, iso_ml
    filas = []
    for marca, secret in CUENTAS.items():
        if not os.environ.get(secret):
            continue
        try:
            c = MeliCuenta(marca, secret)
            c.asegurar_token()
        except Exception as e:
            print(f"   🚨 MeLi {marca}: {e}")
            continue
        ords = {}
        for ruta in ["/orders/search", "/orders/search/archived"]:
            desde = DESDE
            errores = 0
            while desde < HASTA:
                hasta = min(desde + timedelta(hours=12), HASTA)
                offset = 0
                while offset < 9950:
                    r = c.get(ruta, {"seller": c.user_id, "order.date_created.from": iso_ml(desde), "order.date_created.to": iso_ml(hasta),
                                     "sort": "date_asc", "limit": 50, "offset": offset})
                    if r is None or r.status_code != 200:
                        errores += 1
                        if errores <= 2:
                            print(f"   ⚠️ MeLi {marca} {ruta}: HTTP {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')[:150]}")
                        break
                    d = r.json()
                    res = d.get("results", [])
                    for o in res:
                        ords[o["id"]] = o
                    offset += len(res)
                    if not res or offset >= (d.get("paging") or {}).get("total", 0):
                        break
                    time.sleep(0.15)
                desde = hasta
            print(f"   · MeLi {marca}: {len(ords):,} órdenes acumuladas tras {ruta}")
        n = 0
        for o in ords.values():
            if o.get("status") not in ("paid", "cancelled", "partially_refunded", "partially_paid"):
                continue
            pagos = o.get("payments") or []
            rev = 1 if (o.get("status") == "cancelled" or any(str((p or {}).get("status")) in ("refunded", "charged_back") for p in pagos)) else 0
            fecha = pd.Timestamp(o["date_created"]).tz_convert(ZONA_AR)
            filas.append({"canal": "MercadoLibre", "marca": marca, "id_pedido": o.get("pack_id") or o["id"], "orden_meli": o["id"],
                          "fecha": fecha.strftime("%Y-%m-%dT%H:%M:%S-03:00"), "total_pedido": float(o.get("total_amount") or 0),
                          "unidades": sum(int(i.get("quantity") or 0) for i in (o.get("order_items") or [])), "es_reverso": rev})
            n += 1
        print(f"   ✅ MeLi {marca}: {n:,} órdenes")
    return filas


def resumen(df):
    d = df[df["es_reverso"] == 0].copy()
    d["mes"] = pd.to_datetime(d["fecha"]).dt.strftime("%Y-%m")
    # MeLi: un pack (carrito) = un pedido; se suman las órdenes del pack
    p = d.groupby(["canal", "marca", "mes", "id_pedido"], as_index=False).agg(total=("total_pedido", "sum"), unidades=("unidades", "sum"))
    t = p.groupby(["mes", "canal", "marca"]).agg(facturacion=("total", "sum"), pedidos=("id_pedido", "nunique"), unidades=("unidades", "sum"))
    print("\n📊 VENTA NETA POR MES (sin devoluciones/cancelaciones):")
    print(t.assign(facturacion=(t["facturacion"] / 1e6).round(1)).rename(columns={"facturacion": "fact_M$"}).to_string())
    tot = p.groupby(["mes", "canal"])["total"].sum().unstack().fillna(0)
    tot["Total"] = tot.sum(axis=1)
    print("\n💰 TOTAL POR MES Y CANAL (millones):")
    print((tot / 1e6).round(1).to_string())
    meses = sorted(p["mes"].unique())
    if len(meses) >= 2:
        a, b = meses[0], meses[-1]
        fm = p.groupby(["mes", "canal", "marca"])["total"].sum().unstack("mes").fillna(0)
        fm["crec_%"] = ((fm[b] / fm[a].where(fm[a] > 0) - 1) * 100).round(1)
        print(f"\n📈 CRECIMIENTO {b} vs {a} por canal y marca:")
        print(fm[["crec_%"]].to_string())
        tt = tot["Total"]
        print(f"\n➡️ Total grupo: {(tt[b] / tt[a] - 1) * 100:.1f}%")


if __name__ == "__main__":
    print(f"--- Backfill {DESDE:%d/%m/%Y} → {HASTA:%d/%m/%Y} ---")
    filas = shopify() + meli()
    if filas:
        df = pd.DataFrame(filas)
        df.to_csv(ARCHIVO, index=False)
        print(f"🚀 {ARCHIVO}: {len(df):,} filas")
        resumen(df)
    else:
        print("😴 No se encontraron ventas.")
