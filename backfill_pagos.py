"""
Backfill ÚNICO: agrega la columna 'estado_pago' (financial_status de Shopify) a las ventas de la
Tienda Online que ya están en el repo. Se corre una sola vez desde Actions -> "Backfill pagos".
Después la mantiene extractor.py (pedidos nuevos + re-consulta de pagos pendientes).

Valores de Shopify: paid, pending, authorized, partially_paid, partially_refunded, refunded, voided, expired.
"""
import os
import time

import pandas as pd
import requests

from extractor import STORES, API_VERSION, FECHA_INICIO


def mapa_pagos():
    mapa = {}
    for marca, info in STORES.items():
        if not info["token"]:
            continue
        url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}/orders.json"
        params = {"limit": 250, "status": "any", "created_at_min": FECHA_INICIO, "fields": "id,financial_status,cancelled_at"}
        h = {"X-Shopify-Access-Token": info["token"]}
        n = 0
        for _ in range(3000):
            r = requests.get(url, headers=h, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(3)
                continue
            if r.status_code != 200:
                print(f"   🚨 {marca}: HTTP {r.status_code} {r.text[:200]}")
                break
            for o in r.json().get("orders", []):
                mapa[(marca, int(o["id"]))] = (o.get("financial_status") or "", bool(o.get("cancelled_at")))
                n += 1
            url = r.links.get("next", {}).get("url")
            params = None
            if not url:
                break
            time.sleep(0.5)
        print(f"   ✅ {marca}: {n:,} pedidos")
    return mapa


def completar(archivo, mapa):
    if not os.path.exists(archivo):
        return
    d = pd.read_csv(archivo, low_memory=False)
    claves = list(zip(d["marca"], d["id_pedido"].astype("int64")))
    d["estado_pago"] = [mapa.get(k, ("", False))[0] for k in claves]
    cancel = pd.Series([mapa.get(k, ("", False))[1] for k in claves], index=d.index)
    if "envio_estado" in d.columns:
        d.loc[cancel, "envio_estado"] = "Cancelado"
    d.to_csv(archivo, index=False)
    print(f"   💾 {archivo}: {int((d['estado_pago'] != '').sum()):,} de {len(d):,} líneas con estado de pago")
    print(d.drop_duplicates(["marca", "id_pedido"])["estado_pago"].value_counts().to_string())


if __name__ == "__main__":
    m = mapa_pagos()
    for a in ["ventas_hot_sale.csv", "ventas_historico.csv"]:
        completar(a, m)
