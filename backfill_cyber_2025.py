"""
Backfill ÚNICO: ventas del Cyber Monday 2025 (3/11/2025 00:00 → 9/11/2025 23:59) de Tienda Online (Shopify)
y MercadoLibre -> cyber_2025.csv. Sirve para comparar el Cyber 2026 hora a hora contra el del año pasado.
Se corre una sola vez desde Actions -> "Backfill Cyber 2025 (correr UNA vez)".

Una fila por línea de pedido: canal, marca, id_pedido, fecha, total_pedido, cantidad, sku, es_reverso.
"""
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

ZONA_AR = timezone(timedelta(hours=-3))
INI = datetime(2025, 11, 3, 0, 0, tzinfo=ZONA_AR)
FIN = datetime(2025, 11, 9, 23, 59, 59, tzinfo=ZONA_AR)
FILENAME = "cyber_2025.csv"


def shopify():
    from extractor import STORES, API_VERSION
    filas = []
    for marca, info in STORES.items():
        if not info["token"]:
            continue
        url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}/orders.json"
        params = {"limit": 250, "status": "any", "created_at_min": INI.isoformat(), "created_at_max": FIN.isoformat(),
                  "fields": "id,created_at,total_price,tags,cancelled_at,financial_status,line_items"}
        h = {"X-Shopify-Access-Token": info["token"]}
        n = 0
        for _ in range(500):
            r = requests.get(url, headers=h, params=params, timeout=40)
            if r.status_code == 429:
                time.sleep(3)
                continue
            if r.status_code != 200:
                print(f"   🚨 Shopify {marca}: HTTP {r.status_code} {r.text[:200]}")
                break
            for o in r.json().get("orders", []):
                tags = str(o.get("tags") or "").lower()
                pago = str(o.get("financial_status") or "").lower()
                if pago in ("expired", "voided"):
                    continue
                rev = 1 if ("reversso" in tags or o.get("cancelled_at") or pago == "refunded") else 0
                fecha = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).astimezone(ZONA_AR)
                for it in o.get("line_items") or []:
                    filas.append({"canal": "Tienda Online", "marca": marca, "id_pedido": o["id"],
                                  "fecha": fecha.strftime("%Y-%m-%dT%H:%M:%S-03:00"), "total_pedido": float(o.get("total_price") or 0),
                                  "cantidad": int(it.get("quantity") or 0), "sku": it.get("sku") or "", "es_reverso": rev})
                n += 1
            url = r.links.get("next", {}).get("url")
            params = None
            if not url:
                break
            time.sleep(0.5)
        print(f"   ✅ Shopify {marca}: {n:,} pedidos")
    return filas


def buscar(c, ruta, desde, hasta):
    """Órdenes por fecha. MeLi pasa las órdenes de más de ~12 meses a /orders/search/archived."""
    from extractor_meli import iso_ml
    out, offset = [], 0
    while offset < 9950:
        r = c.get(ruta, {"seller": c.user_id, "order.date_created.from": iso_ml(desde), "order.date_created.to": iso_ml(hasta),
                         "sort": "date_asc", "limit": 50, "offset": offset})
        if r is None or r.status_code != 200:
            return out, f"HTTP {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')[:150]}"
        d = r.json()
        res = d.get("results", [])
        out.extend(res)
        offset += len(res)
        if not res or offset >= (d.get("paging") or {}).get("total", 0):
            break
        time.sleep(0.2)
    return out, None


def meli():
    from extractor_meli import MeliCuenta, CUENTAS
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
        n = 0
        for ruta in ["/orders/search", "/orders/search/archived"]:
            ords_all, desde = [], INI
            while desde < FIN:
                hasta = min(desde + timedelta(hours=12), FIN)
                ords, err = buscar(c, ruta, desde, hasta)
                if err:
                    print(f"   ⚠️ MeLi {marca} {ruta}: {err}")
                    break
                ords_all.extend(ords)
                desde = hasta
            if ords_all:
                print(f"   · MeLi {marca}: {len(ords_all):,} órdenes desde {ruta}")
                break
        for o in ords_all:
            if True:
                pagos = o.get("payments") or []
                rev = 1 if (o.get("status") == "cancelled" or any(str((p or {}).get("status")) in ("refunded", "charged_back") for p in pagos)) else 0
                if o.get("status") not in ("paid", "cancelled", "partially_refunded"):
                    continue
                fecha = pd.Timestamp(o["date_created"]).tz_convert(ZONA_AR)
                pid = o.get("pack_id") or o["id"]
                for it in o.get("order_items") or []:
                    filas.append({"canal": "MercadoLibre", "marca": marca, "id_pedido": pid, "orden_meli": o["id"],
                                  "fecha": fecha.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
                                  "total_orden": float(o.get("total_amount") or 0), "cantidad": int(it.get("quantity") or 0),
                                  "sku": (it.get("item") or {}).get("seller_sku") or "", "es_reverso": rev})
                n += 1
        print(f"   ✅ MeLi {marca}: {n:,} órdenes")
    df = pd.DataFrame(filas)
    if df.empty:
        return []
    # total del pedido (pack) = suma de las órdenes del pack, como en el extractor de ventas
    tot = df.drop_duplicates("orden_meli").groupby("id_pedido")["total_orden"].sum()
    df["total_pedido"] = df["id_pedido"].map(tot)
    return df.drop(columns=["total_orden", "orden_meli"]).to_dict("records")


if __name__ == "__main__":
    print(f"--- Cyber Monday 2025: {INI:%d/%m/%Y %H:%M} → {FIN:%d/%m/%Y %H:%M} ---")
    filas = shopify() + meli()
    if filas:
        df = pd.DataFrame(filas)
        df.to_csv(FILENAME, index=False)
        ped = df.drop_duplicates(["canal", "marca", "id_pedido"])
        print(f"🚀 {FILENAME}: {len(df):,} líneas · {len(ped):,} pedidos")
        print(ped[ped["es_reverso"] == 0].groupby(["canal", "marca"])["total_pedido"].agg(["count", "sum"]).to_string())
    else:
        print("😴 No se encontraron ventas.")
