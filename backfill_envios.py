"""
Backfill ÚNICO del estado detallado de envíos (pendiente, en camino, entregado, etc.).
Se corre una vez desde Actions -> "Backfill envíos". Después lo mantienen los extractores.
- Shopify: ventas del archivo vivo (90 días): baja id + fulfillments de cada pedido.
- MeLi: re-consulta cada envío de ventas_meli.csv (puede tardar ~30-40 min).
"""
import os
import time

import pandas as pd
import requests

from extractor import STORES, API_VERSION, envio_shopify
from extractor_meli import MeliCuenta, CUENTAS, ESTADO_FULFILL

COLS = ["envio_estado", "envio_detalle", "fecha_entrega", "transportista"]


def shopify():
    archivo = "ventas_hot_sale.csv"
    d = pd.read_csv(archivo, low_memory=False)
    desde = pd.to_datetime(d["fecha"], errors="coerce", format="mixed", utc=True).min()
    mapa = {}
    for marca, info in STORES.items():
        if not info["token"]:
            continue
        url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}/orders.json"
        params = {"limit": 250, "status": "any", "created_at_min": desde.isoformat(),
                  "fields": "id,name,cancelled_at,fulfillment_status,fulfillments"}
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
                mapa[(marca, int(o["id"]))] = {**envio_shopify(o), "nro_pedido": o.get("name", "")}
                n += 1
            url = r.links.get("next", {}).get("url")
            params = None
            if not url:
                break
            time.sleep(0.5)
        print(f"   ✅ Shopify {marca}: {n:,} pedidos")
    for c in COLS + ["nro_pedido"]:
        vals = [mapa.get((m, int(i)), {}).get(c) for m, i in zip(d["marca"], d["id_pedido"])]
        d[c] = vals if c not in d.columns else pd.Series(vals, index=d.index).where(pd.Series(vals, index=d.index).notna(), d[c])
    d.to_csv(archivo, index=False)
    print(f"   💾 {archivo}: {d['envio_estado'].notna().mean() * 100:.1f}% con estado de envío")


def meli():
    archivo = "ventas_meli.csv"
    if not os.path.exists(archivo):
        return
    d = pd.read_csv(archivo, low_memory=False)
    for c in COLS:
        if c not in d.columns:
            d[c] = None
    for marca, secret in CUENTAS.items():
        if not os.environ.get(secret):
            continue
        c = MeliCuenta(marca, secret)
        c.asegurar_token()
        sids = d.loc[(d["marca"] == marca) & d["shipping_id"].notna(), "shipping_id"].unique()
        for i, sid in enumerate(sids):
            env = c.envio(int(sid))
            if env:
                msk = (d["marca"] == marca) & (d["shipping_id"] == sid)
                d.loc[msk, "fulfillment_status"] = ESTADO_FULFILL.get(env["envio_estado"], "pending")
                for col in COLS + ["fecha_despacho"]:
                    d.loc[msk, col] = env.get(col)
            if i % 500 == 0:
                print(f"      {marca}: {i:,}/{len(sids):,}")
            time.sleep(0.05)
        print(f"   ✅ MeLi {marca}: {len(sids):,} envíos")
    if "nro_pedido" not in d.columns:
        d["nro_pedido"] = d["id_pedido"].astype(str)
    d.to_csv(archivo, index=False)
    print(f"   💾 {archivo}: {d['envio_estado'].notna().mean() * 100:.1f}% con estado de envío")


if __name__ == "__main__":
    shopify()
    meli()
