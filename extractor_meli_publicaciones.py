"""
Publicaciones de MercadoLibre -> meli_publicaciones.csv (una fila por publicación)

Trae, por cada cuenta:
  - estado (activa / pausada), stock, precio, vendidos, SKU (modelo_color)
  - visitas de los últimos 30 días (para calcular conversión con las ventas)
  - si es de catálogo: estado de competencia y "precio para ganar"

Corre 2 veces por día (workflow diario.yml), no cada 5 min: estos datos cambian lento
y así no gastamos llamadas a la API.
"""
import os
import time
from datetime import datetime, timedelta

import pandas as pd

from extractor_meli import MeliCuenta, CUENTAS, ZONA_AR

FILENAME = "meli_publicaciones.csv"
DIAS_VISITAS = 30
LOTE = 20  # multiget de ítems: máximo 20 ids por llamada


def sku_de_item(it):
    """SKU del vendedor: atributo SELLER_SKU, seller_custom_field, o el de la 1ª variación."""
    for a in it.get("attributes") or []:
        if a.get("id") == "SELLER_SKU" and a.get("value_name"):
            return str(a["value_name"]).strip()
    if it.get("seller_custom_field"):
        return str(it["seller_custom_field"]).strip()
    for v in it.get("variations") or []:
        for a in v.get("attributes") or []:
            if a.get("id") == "SELLER_SKU" and a.get("value_name"):
                return str(a["value_name"]).strip()
        if v.get("seller_custom_field"):
            return str(v["seller_custom_field"]).strip()
    return ""


def ids_publicaciones(c, status):
    """Lista de ids con search_type=scan (sin el límite de 1000 del offset)."""
    ids, scroll = [], None
    for _ in range(500):
        params = {"search_type": "scan", "limit": 100, "status": status}
        if scroll:
            params["scroll_id"] = scroll
        r = c.get(f"/users/{c.user_id}/items/search", params)
        if r is None or r.status_code != 200:
            print(f"   ⚠️ {c.marca}: items/search {status} HTTP {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')[:200]}")
            break
        d = r.json()
        res = d.get("results", [])
        if not res:
            break
        ids.extend(res)
        scroll = d.get("scroll_id")
        if not scroll:
            break
        time.sleep(0.1)
    return ids


def detalle_items(c, ids):
    out = []
    for i in range(0, len(ids), LOTE):
        r = c.get("/items", {"ids": ",".join(ids[i:i + LOTE]), "include_attributes": "all"})
        if r is None or r.status_code != 200:
            continue
        for e in r.json():
            if e.get("code") == 200 and e.get("body"):
                out.append(e["body"])
        time.sleep(0.1)
    return out


def visitas_30d(c, ids):
    hasta = datetime.now(ZONA_AR).date()
    desde = hasta - timedelta(days=DIAS_VISITAS)
    vis = {}
    for i in range(0, len(ids), LOTE):
        lote = ids[i:i + LOTE]
        r = c.get("/items/visits", {"ids": ",".join(lote), "date_from": desde.isoformat(), "date_to": hasta.isoformat()})
        if r is not None and r.status_code == 200:
            d = r.json()
            filas = d if isinstance(d, list) else [d]
            for f in filas:
                if isinstance(f, dict) and f.get("item_id"):
                    vis[f["item_id"]] = int(f.get("total_visits", 0) or 0)
        else:
            # Plan B: una llamada por ítem
            for iid in lote:
                r2 = c.get(f"/items/{iid}/visits/time_window", {"last": DIAS_VISITAS, "unit": "day"})
                if r2 is not None and r2.status_code == 200:
                    vis[iid] = int(r2.json().get("total_visits", 0) or 0)
        time.sleep(0.1)
    return vis


def precio_para_ganar(c, iid):
    r = c.get(f"/items/{iid}/price_to_win", {"version": "v2"})
    if r is None or r.status_code != 200:
        return {}
    d = r.json()
    return {"catalogo_estado": d.get("status", ""),
            "precio_para_ganar": d.get("price_to_win"),
            "precio_ganador": (d.get("winner") or {}).get("price")}


def sync():
    print(f"\n--- 🏷️ PUBLICACIONES MELI: {datetime.now(ZONA_AR):%d/%m %H:%M} ---")
    filas = []
    for marca, secret_name in CUENTAS.items():
        if not os.environ.get(secret_name):
            continue
        try:
            c = MeliCuenta(marca, secret_name)
            c.asegurar_token()
            ids = ids_publicaciones(c, "active") + ids_publicaciones(c, "paused")
            ids = list(dict.fromkeys(ids))
            items = detalle_items(c, ids)
            vis = visitas_30d(c, [it["id"] for it in items if it.get("status") == "active"])
            n_cat = 0
            for it in items:
                sku = sku_de_item(it)
                fila = {
                    "marca": marca, "item_id": it["id"], "titulo": it.get("title", ""),
                    "sku": sku, "modelo_color": sku.rsplit("-", 1)[0] if "-" in sku else sku,
                    "estado": it.get("status", ""), "sub_estado": ",".join(it.get("sub_status") or []),
                    "precio": it.get("price"), "stock": int(it.get("available_quantity") or 0),
                    "vendidos_total": int(it.get("sold_quantity") or 0),
                    "variaciones": len(it.get("variations") or []),
                    "tipo": it.get("listing_type_id", ""), "catalogo": bool(it.get("catalog_listing")),
                    "visitas_30d": vis.get(it["id"], 0), "permalink": it.get("permalink", ""),
                    "catalogo_estado": "", "precio_para_ganar": None, "precio_ganador": None,
                }
                if fila["catalogo"] and fila["estado"] == "active":
                    fila.update(precio_para_ganar(c, it["id"]))
                    n_cat += 1
                    time.sleep(0.1)
                filas.append(fila)
            print(f"   ✅ {marca}: {len(items)} publicaciones ({n_cat} de catálogo)")
        except Exception as e:
            print(f"   🚨 {marca}: {e}")

    if filas:
        df = pd.DataFrame(filas)
        df["actualizado"] = datetime.now(ZONA_AR).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        df.to_csv(FILENAME, index=False)
        print(f"🚀 {FILENAME}: {len(df):,} publicaciones")


if __name__ == "__main__":
    try:
        sync()
    except Exception as e:
        print(f"🚨 Error crítico publicaciones: {e}")
