"""
Backfill ÚNICO: agrega la columna 'cliente' (seudonimizada) a las ventas que ya están en el repo.
Se corre una sola vez desde Actions -> "Backfill clientes". Después lo mantienen los extractores.

- Shopify: baja solo id + email/cliente de cada pedido desde FECHA_INICIO (liviano).
- MeLi: baja las órdenes (sin envíos) desde el 1/09 y toma el comprador.
"""
import os
import re
import time
from datetime import timedelta

import pandas as pd
import requests

from extractor import STORES, API_VERSION, FECHA_INICIO, cliente_de_orden
from extractor_meli import MeliCuenta, CUENTAS, hash_cliente, ZONA_AR

FECHA_INICIO_MELI = "2026-09-01T00:00:00.000-03:00"


def mapa_shopify():
    mapa = {}
    for marca, info in STORES.items():
        if not info["token"]:
            continue
        url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}/orders.json"
        params = {"limit": 250, "status": "any", "created_at_min": FECHA_INICIO, "fields": "id,email,contact_email,customer"}
        h = {"X-Shopify-Access-Token": info["token"]}
        n = 0
        for _ in range(2000):
            r = requests.get(url, headers=h, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(3)
                continue
            if r.status_code != 200:
                print(f"   🚨 {marca}: HTTP {r.status_code} {r.text[:200]}")
                break
            for o in r.json().get("orders", []):
                mapa[(marca, int(o["id"]))] = cliente_de_orden(o)
                n += 1
            url = r.links.get("next", {}).get("url")
            params = None
            if not url:
                break
            time.sleep(0.5)
        print(f"   ✅ Shopify {marca}: {n:,} pedidos")
    return mapa


def mapa_meli():
    mapa = {}
    ahora = pd.Timestamp.now(tz=ZONA_AR).to_pydatetime()
    for marca, secret in CUENTAS.items():
        if not os.environ.get(secret):
            continue
        c = MeliCuenta(marca, secret)
        c.asegurar_token()
        desde = pd.Timestamp(FECHA_INICIO_MELI).to_pydatetime()
        n = 0
        while desde < ahora:
            hasta = min(desde + timedelta(days=2), ahora)
            for o in c.buscar_ordenes("order.date_created", desde, hasta) or []:
                mapa[int(o["id"])] = hash_cliente(f"meli:{(o.get('buyer') or {}).get('id', '')}")
                n += 1
            desde = hasta
        print(f"   ✅ MeLi {marca}: {n:,} órdenes")
    return mapa


def completar(archivo, fn):
    if not os.path.exists(archivo):
        return
    d = pd.read_csv(archivo, low_memory=False)
    if "cliente" not in d.columns:
        d["cliente"] = ""
    d["cliente"] = d["cliente"].fillna("").astype(str)
    falta = d["cliente"] == ""
    d.loc[falta, "cliente"] = d[falta].apply(fn, axis=1)
    d.to_csv(archivo, index=False)
    print(f"   💾 {archivo}: {int((d['cliente'] != '').sum()):,} de {len(d):,} líneas con cliente")


def main():
    ms = mapa_shopify()
    for a in ["ventas_hot_sale.csv", "ventas_historico.csv"]:
        completar(a, lambda r: ms.get((r["marca"], int(r["id_pedido"])), ""))

    mm = mapa_meli()
    for a in ["ventas_meli.csv", "ventas_meli_historico.csv"]:
        if not os.path.exists(a):
            continue
        completar(a, lambda r: mm.get(int(r["orden_meli"]), ""))
        d = pd.read_csv(a, low_memory=False)
        if "item_id" not in d.columns or d["item_id"].isna().any():
            ids = d["url_web"].astype(str).str.extract(r"(MLA)-?(\d+)").fillna("").agg("".join, axis=1)
            d["item_id"] = d["item_id"].fillna(ids) if "item_id" in d.columns else ids
            d.to_csv(a, index=False)


if __name__ == "__main__":
    main()
