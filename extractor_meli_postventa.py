"""
Post-venta MercadoLibre -> 2 CSV para el dashboard (solo los ve dirección):

  meli_cancelaciones.csv  una fila por orden cancelada: quién la canceló (comprador / nosotros / MeLi),
                          motivo, monto y productos.
  meli_reclamos.csv       una fila por reclamo (mediación, devolución, cambio, cancelación...):
                          motivo, etapa, estado, a favor de quién se resolvió, si MeLi cubrió el dinero,
                          y si hubo devolución física: estado del envío de vuelta, dinero y revisión del producto.

Trae desde FECHA_INICIO (1/09) y se re-escribe entero en cada corrida (el volumen es chico).
Corre en el workflow diario. Si la API responde 401/403 hay que habilitar en la app de MeLi
el permiso de "Post venta / Reclamos" (lectura).
"""
import os
import time
from datetime import datetime, timedelta

import pandas as pd

from extractor_meli import MeliCuenta, CUENTAS, ZONA_AR, FECHA_INICIO, iso_ml

VENTANA_DIAS = 7

RUTAS_CLAIMS = ["/post-purchase/v1/claims/search", "/marketplace/v2/claims/search"]
RUTAS_REASON = ["/post-purchase/v1/claims/reasons/{id}", "/marketplace/v2/claims/reasons/{id}"]
RUTAS_RETURN = ["/post-purchase/v2/claims/{id}/returns", "/marketplace/v2/claims/{id}/returns"]

QUIEN = {"buyer": "Comprador", "seller": "Vendedor (nosotros)", "mediator": "MercadoLibre",
         "fraud": "MercadoLibre (fraude/seguridad)", "internal": "MercadoLibre", "shipment": "Envío",
         "shipping": "Envío", "payment": "Pago no acreditado", "mediations": "Por reclamo"}


def _ok(r):
    return r is not None and r.status_code == 200


def _err(r):
    return f"HTTP {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')[:200]}"


def _items(o):
    its = o.get("order_items") or []
    tit = " | ".join(str((x.get("item") or {}).get("title", "")) for x in its)[:300]
    skus = " | ".join(str((x.get("item") or {}).get("seller_sku") or (x.get("item") or {}).get("seller_custom_field") or "") for x in its)[:200]
    item_ids = " | ".join(str((x.get("item") or {}).get("id", "")) for x in its)[:200]
    unid = sum(int(x.get("quantity") or 0) for x in its)
    return tit, skus, item_ids, unid


# ============================================================================== CANCELACIONES
def cancelaciones(c, desde, hasta):
    filas = []
    ini = desde
    while ini < hasta:
        fin = min(ini + timedelta(days=VENTANA_DIAS), hasta)
        offset = 0
        while True:
            r = c.get("/orders/search", {"seller": c.user_id, "order.status": "cancelled",
                                         "order.date_created.from": iso_ml(ini), "order.date_created.to": iso_ml(fin),
                                         "sort": "date_asc", "limit": 50, "offset": offset})
            if not _ok(r):
                print(f"   🚨 {c.marca}: órdenes canceladas {_err(r)}")
                break
            d = r.json()
            res = d.get("results", [])
            for o in res:
                cd = o.get("cancel_detail") or {}
                tit, skus, iids, unid = _items(o)
                por = cd.get("requested_by") or cd.get("group") or ""
                pagos = o.get("payments") or []
                filas.append({
                    "marca": c.marca, "orden_meli": o.get("id"), "pack_id": o.get("pack_id") or "",
                    "fecha": o.get("date_created"), "fecha_cancelacion": cd.get("date") or o.get("date_closed") or o.get("last_updated"),
                    "monto": float(o.get("total_amount") or 0), "unidades": unid,
                    "cancel_por": por, "cancel_por_txt": QUIEN.get(str(por).lower(), str(por) or "Sin dato"),
                    "cancel_grupo": cd.get("group") or "", "cancel_codigo": cd.get("code") or "",
                    "cancel_motivo": cd.get("description") or "",
                    "pago_estado": (pagos[0] or {}).get("status", "") if pagos else "sin pago",
                    "pago_detalle": (pagos[0] or {}).get("status_detail", "") if pagos else "",
                    "tags": ",".join(o.get("tags") or []),
                    "titulos": tit, "skus": skus, "item_ids": iids,
                    "shipping_id": (o.get("shipping") or {}).get("id") or "",
                })
            offset += len(res)
            if not res or offset >= (d.get("paging") or {}).get("total", 0) or offset >= 9950:
                break
            time.sleep(0.2)
        ini = fin
    return filas


# ============================================================================== RECLAMOS
RUTA_OK = {}


def get_alt(c, clave, rutas, params=None, **fmt):
    errores = []
    orden = ([RUTA_OK[clave]] if clave in RUTA_OK else []) + [i for i in range(len(rutas)) if i != RUTA_OK.get(clave)]
    for i in orden:
        r = c.get(rutas[i].format(**fmt), params)
        if _ok(r):
            RUTA_OK[clave] = i
            return r, None
        errores.append(f"{rutas[i]} -> {_err(r)}")
        if r is not None and r.status_code == 404 and clave == "ret":
            continue
    return None, errores


def buscar_reclamos(c, desde):
    out, offset = [], 0
    base = {"player_role": "respondent", "player_user_id": c.user_id, "limit": 50}
    con_sort = True
    while offset < 5000:
        params = dict(base, offset=offset)
        if con_sort:
            params["sort"] = "date_created:desc"
        r, errs = get_alt(c, "claims", RUTAS_CLAIMS, params)
        if r is None and con_sort:
            con_sort = False          # algunas versiones no aceptan sort: se reintenta sin él
            continue
        if r is None:
            print(f"   🚨 {c.marca}: no pude buscar reclamos:")
            for e in errs or []:
                print(f"        {e}")
            if any(" 401 " in e or " 403 " in e for e in errs or []):
                print("        -> habilitá en la app de MeLi el permiso de 'Post venta / Reclamos' (lectura).")
            break
        d = r.json()
        res = d.get("data") or d.get("results") or []
        out.extend(res)
        offset += len(res)
        total = (d.get("paging") or {}).get("total", 0)
        if not res or offset >= total:
            break
        if con_sort:
            ult = pd.to_datetime(res[-1].get("date_created"), errors="coerce", utc=True)
            if pd.notna(ult) and ult < pd.Timestamp(desde).tz_convert("UTC"):
                break
        time.sleep(0.2)
    lim = pd.Timestamp(desde).tz_convert("UTC")
    return [x for x in out if pd.to_datetime(x.get("date_created"), errors="coerce", utc=True) >= lim]


_RAZONES = {}


def razon(c, rid):
    if not rid:
        return {}
    if rid not in _RAZONES:
        r, _ = get_alt(c, "reason", RUTAS_REASON, None, id=rid)
        d = r.json() if r is not None else {}
        _RAZONES[rid] = {"motivo": d.get("name") or "", "motivo_detalle": d.get("detail") or "",
                         "motivo_grupo": ((d.get("filter") or {}).get("group")) or ""}
    return _RAZONES[rid]


def devolucion(c, cid):
    r, _ = get_alt(c, "ret", RUTAS_RETURN, None, id=cid)
    if r is None:
        return {}
    d = r.json()
    if isinstance(d, list):
        d = d[0] if d else {}
    sh = d.get("shipping") or {}
    wr = d.get("warehouse_review") or {}
    sr = d.get("seller_review") or {}
    return {"dev_estado": d.get("status") or "", "dev_dinero": d.get("status_money") or "", "dev_subtipo": d.get("subtype") or "",
            "dev_reembolso_al": d.get("refund_at") or "", "dev_envio_estado": sh.get("status") or "",
            "dev_fecha": d.get("date_created") or "", "dev_fecha_cierre": d.get("date_closed") or "",
            "dev_condicion": wr.get("product_condition") or "", "dev_destino": wr.get("product_destination") or "",
            "dev_revision_vendedor": sr.get("status") or ""}


def orden_info(c, oid):
    if not oid:
        return {}
    r = c.get(f"/orders/{oid}")
    if not _ok(r):
        return {}
    o = r.json()
    tit, skus, iids, unid = _items(o)
    return {"monto": float(o.get("total_amount") or 0), "unidades": unid, "titulos": tit, "skus": skus, "item_ids": iids,
            "fecha_orden": o.get("date_created"), "pack_id": o.get("pack_id") or ""}


def reclamos(c, desde):
    filas = []
    for cl in buscar_reclamos(c, desde):
        cid = cl.get("id")
        res = cl.get("resolution") or {}
        rid = cl.get("reason_id") or ""
        fila = {"marca": c.marca, "claim_id": cid, "tipo": cl.get("type") or "", "etapa": cl.get("stage") or "",
                "estado": cl.get("status") or "", "recurso": cl.get("resource") or "", "orden_meli": cl.get("resource_id") or "",
                "reason_id": rid, "fecha": cl.get("date_created"), "actualizado_claim": cl.get("last_updated"),
                "res_motivo": res.get("reason") or "", "res_fecha": res.get("date_created") or "",
                "res_beneficiado": ",".join(res.get("benefited") or []) if isinstance(res.get("benefited"), list) else (res.get("benefited") or ""),
                "res_cerrado_por": res.get("closed_by") or "", "res_cobertura": res.get("applied_coverage")}
        fila.update(razon(c, rid))
        if fila["recurso"] in ("order", "purchase", "") and fila["orden_meli"]:
            fila.update(orden_info(c, fila["orden_meli"]))
        fila.update(devolucion(c, cid))
        filas.append(fila)
        time.sleep(0.1)
    return filas


def sync():
    print(f"\n--- 🔁 POST-VENTA MELI: {datetime.now(ZONA_AR):%d/%m %H:%M} ---")
    desde = pd.Timestamp(FECHA_INICIO).to_pydatetime()
    hasta = datetime.now(ZONA_AR)
    canc, recl = [], []
    for marca, secret in CUENTAS.items():
        if not os.environ.get(secret):
            continue
        try:
            c = MeliCuenta(marca, secret)
            c.asegurar_token()
            cf = cancelaciones(c, desde, hasta)
            rf = reclamos(c, desde)
            canc.extend(cf)
            recl.extend(rf)
            n_dev = sum(1 for x in rf if x.get("dev_estado"))
            print(f"   ✅ {marca}: {len(cf)} cancelaciones, {len(rf)} reclamos ({n_dev} con devolución)")
        except Exception as e:
            print(f"   🚨 {marca}: {e}")
    ts = datetime.now(ZONA_AR).strftime("%Y-%m-%dT%H:%M:%S-03:00")
    for filas, nombre in [(canc, "meli_cancelaciones.csv"), (recl, "meli_reclamos.csv")]:
        if filas:
            df = pd.DataFrame(filas)
            df = df.drop_duplicates(subset=["claim_id"] if "claim_id" in df.columns else ["orden_meli"], keep="last")
            df["actualizado"] = ts
            df.to_csv(nombre, index=False)
            print(f"🚀 {nombre}: {len(df):,} filas")


if __name__ == "__main__":
    try:
        sync()
    except Exception as e:
        print(f"🚨 Error crítico post-venta: {e}")
