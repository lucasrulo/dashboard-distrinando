"""
Extractor de ventas de MercadoLibre -> ventas_meli.csv
Mismo esquema de columnas que ventas_hot_sale.csv (Shopify) + columnas propias de MeLi,
para que el dashboard las una con una columna 'canal'.

Secrets necesarios en GitHub Actions:
  MELI_APP_ID, MELI_CLIENT_SECRET          -> de tu app en developers.mercadolibre.com.ar
  MELI_<MARCA> (uno por cuenta)            -> JSON generado por meli_autorizar.py
  GH_PAT_SECRETS                           -> PAT fine-grained con "Secrets: Read and write"
                                              sobre este repo (para rotar el refresh_token)
"""
import os
import json
import time
import hashlib
import subprocess
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd

# ==============================================================================
# ⚙️ CONFIGURACIÓN
# ==============================================================================
REPO = "lucasrulo/dashboard-distrinando"
API = "https://api.mercadolibre.com"
FILENAME = "ventas_meli.csv"
FILENAME_HISTORICO = "ventas_meli_historico.csv"
FECHA_INICIO = os.environ.get("MELI_FECHA_INICIO") or "2026-09-01T00:00:00.000-03:00"   # backfill inicial: desde el 1/09
DIAS_RETENCION_LIVE = 90
DIAS_REVISION_ENVIOS = 15      # re-consulta envíos todavía no despachados de los últimos N días
VENTANA_BACKFILL_DIAS = 2      # el search de órdenes no pagina más allá de ~10k offset: vamos por ventanas
ZONA_AR = timezone(timedelta(hours=-3))

# 🎯 AJUSTAR: marca del dashboard -> nombre del secret con los tokens de esa cuenta de MeLi
CUENTAS = {
    "Reebok": "MELI_REEBOK",
    "Crocs": "MELI_CROCS",
    "Kappa": "MELI_KAPPA",
    "Columbia": "MELI_COLUMBIA",
}

CLIENTES_SALT = os.environ.get("CLIENTES_SALT", "")


def hash_cliente(valor):
    """Comprador seudonimizado (el repo es público: nunca se guarda el id real)."""
    v = str(valor or "").strip().lower()
    if not v or v in ("none", "nan"):
        return ""
    return hashlib.sha256((CLIENTES_SALT + v).encode()).hexdigest()[:16]


APP_ID = os.environ.get("MELI_APP_ID")
CLIENT_SECRET = os.environ.get("MELI_CLIENT_SECRET")

# 🚚 Estado detallado del envío (mismas etiquetas que Shopify, para comparar canales)
FALLA_ENTREGA = {"receiver_absent", "not_visited", "delivery_failed", "bad_address", "not_localized",
                 "unvisited_address", "dangerous_area", "contact_with_carrier", "rescheduled_by_meli"}


def estado_envio_meli(status, sub):
    status, sub = (status or "").lower(), (sub or "").lower()
    if status in ("", "pending", "handling"):
        return "Pendiente"
    if status == "ready_to_ship":
        return "Despachado" if sub in ("dropped_off", "in_hub", "picked_up", "in_packing_list", "at_the_door") else "Listo para despachar"
    if status == "shipped":
        if sub == "out_for_delivery":
            return "En reparto"
        if sub in ("waiting_for_withdrawal", "ready_to_pickup"):
            return "Listo para retirar"
        if sub in FALLA_ENTREGA:
            return "Intento fallido"
        return "En camino"
    if status == "delivered":
        return "Entregado"
    if status == "not_delivered":
        return "Devolución" if "return" in sub else "No entregado"
    if status == "cancelled":
        return "Cancelado"
    return "Pendiente"


# envio_estado -> fulfillment_status estilo Shopify (lo usan otras partes del dashboard)
ESTADO_FULFILL = {"Pendiente": "pending", "Listo para despachar": "pending", "Despachado": "fulfilled",
                  "En camino": "fulfilled", "En reparto": "fulfilled", "Listo para retirar": "fulfilled",
                  "Intento fallido": "fulfilled", "Entregado": "fulfilled", "No entregado": "restocked",
                  "Devolución": "restocked", "Cancelado": "unfulfilled"}
EN_CURSO = {"Despachado", "En camino", "En reparto", "Listo para retirar", "Intento fallido"}
# Envíos en camino -> entregados: se re-consultan cada ~2 hs (no en cada corrida, para no gastar llamadas).
# Se activa por variable, o solo en la primera corrida de cada hora par (sirve con cron-job.org cada 10 min).
_ahora_ar = datetime.now(ZONA_AR)
REFRESCAR_ENTREGAS = (os.environ.get("MELI_REFRESCAR_ENTREGAS") == "1"
                      or (_ahora_ar.hour % 2 == 0 and _ahora_ar.minute < 10))


def a_iso_ar(v):
    return pd.Timestamp(v).tz_convert(ZONA_AR).strftime("%Y-%m-%dT%H:%M:%S-03:00") if v else None
LOGISTICA = {"fulfillment": "Full", "self_service": "Flex", "cross_docking": "Colecta",
             "xd_drop_off": "Drop-off", "drop_off": "Drop-off", "custom": "Acordar"}


def iso_ml(dt):
    """Formato que espera el search de órdenes: 2026-10-13T00:00:00.000-03:00"""
    return dt.astimezone(ZONA_AR).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")


def guardar_secret(nombre, valor):
    pat = os.environ.get("GH_PAT_SECRETS")
    if not pat:
        raise RuntimeError("Falta GH_PAT_SECRETS: no puedo guardar el refresh_token nuevo")
    for intento in range(3):
        r = subprocess.run(["gh", "secret", "set", nombre, "--repo", REPO, "--body", valor],
                           env={**os.environ, "GH_TOKEN": pat}, capture_output=True, text=True)
        if r.returncode == 0:
            return
        time.sleep(3)
    raise RuntimeError(f"No se pudo guardar {nombre}: {r.stderr[:300]}")


class MeliCuenta:
    def __init__(self, marca, secret_name):
        self.marca = marca
        self.secret_name = secret_name
        raw = os.environ.get(secret_name)
        if not raw:
            raise RuntimeError(f"Secret {secret_name} vacío")
        self.tok = json.loads(raw)
        self.s = requests.Session()

    @property
    def user_id(self):
        return self.tok["user_id"]

    # ---------- OAuth ----------
    def asegurar_token(self, forzar=False):
        # El access_token dura 6 hs. Solo refrescamos si le quedan < 30 min:
        # así el refresh_token (que es de UN SOLO USO) rota pocas veces por día.
        if not forzar and self.tok.get("expires_at", 0) - time.time() > 1800:
            return
        r = requests.post(f"{API}/oauth/token", timeout=30,
                          headers={"accept": "application/json",
                                   "content-type": "application/x-www-form-urlencoded"},
                          data={"grant_type": "refresh_token", "client_id": APP_ID,
                                "client_secret": CLIENT_SECRET,
                                "refresh_token": self.tok["refresh_token"]})
        if r.status_code != 200:
            raise RuntimeError(f"{self.marca}: refresh falló HTTP {r.status_code} {r.text[:300]} "
                               f"-> volver a correr meli_autorizar.py para esta cuenta")
        d = r.json()
        nuevo = {"access_token": d["access_token"],
                 "refresh_token": d.get("refresh_token", self.tok["refresh_token"]),
                 "expires_at": int(time.time()) + int(d.get("expires_in", 21600)),
                 "user_id": d.get("user_id", self.tok.get("user_id"))}
        print(f"::add-mask::{nuevo['access_token']}")
        print(f"::add-mask::{nuevo['refresh_token']}")
        # 🚨 Primero se guarda, después se usa: si el guardado falla, el refresh viejo ya no sirve
        guardar_secret(self.secret_name, json.dumps(nuevo))
        self.tok = nuevo
        print(f"   🔑 {self.marca}: token renovado y guardado")

    def get(self, path, params=None):
        r = None
        for intento in range(5):
            r = self.s.get(f"{API}{path}", params=params, timeout=30,
                           headers={"Authorization": f"Bearer {self.tok['access_token']}"})
            if r.status_code == 401 and intento == 0:
                self.asegurar_token(forzar=True)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 * (intento + 1))
                continue
            return r
        return r

    # ---------- Órdenes ----------
    def buscar_ordenes(self, campo, desde, hasta=None):
        """campo: 'order.date_created' o 'order.date_last_updated'"""
        ordenes, offset = [], 0
        while True:
            params = {"seller": self.user_id, f"{campo}.from": iso_ml(desde),
                      "sort": "date_asc", "limit": 50, "offset": offset}
            if hasta:
                params[f"{campo}.to"] = iso_ml(hasta)
            r = self.get("/orders/search", params)
            if r is None or r.status_code != 200:
                print(f"   🚨 {self.marca}: /orders/search HTTP {getattr(r, 'status_code', '?')} "
                      f"{getattr(r, 'text', '')[:300]}")
                return None
            d = r.json()
            res = d.get("results", [])
            ordenes.extend(res)
            offset += len(res)
            total = d.get("paging", {}).get("total", 0)
            if not res or offset >= total:
                break
            if offset >= 9950:
                print(f"   ⚠️ {self.marca}: ventana con >10k órdenes, achicar VENTANA_BACKFILL_DIAS")
                break
            time.sleep(0.2)
        return ordenes

    # ---------- Envíos ----------
    def envio(self, shipping_id):
        if not shipping_id:
            return {}
        r = self.get(f"/shipments/{shipping_id}")
        if r is None or r.status_code != 200:
            return {}
        s = r.json()
        # Tolerante a formato viejo y nuevo de /shipments
        recv = s.get("receiver_address") or \
            ((s.get("destination") or {}).get("shipping_address")) or {}
        hist = s.get("status_history") or {}
        logistic = s.get("logistic_type") or (s.get("logistic") or {}).get("type") or ""
        status, sub = s.get("status", ""), s.get("substatus") or ""
        envio = estado_envio_meli(status, sub)
        return {
            "estado_envio": status,
            "envio_estado": envio,
            "envio_detalle": f"{status}/{sub}" if sub else status,
            "provincia": ((recv.get("state") or {}).get("name")) or "Buenos Aires",
            "fecha_despacho": a_iso_ar(hist.get("date_shipped")),
            "fecha_entrega": a_iso_ar(hist.get("date_delivered")),
            "transportista": "Mercado Envíos",
            "logistica": LOGISTICA.get(logistic, logistic or "S/D"),
        }

    # ---------- Orden -> filas ----------
    def a_filas(self, o, envio):
        pagos = o.get("payments") or [{}]
        p0 = pagos[0] or {}
        tipo = str(p0.get("payment_type") or "desconocido").upper()
        cuotas_n = int(p0.get("installments") or 1)
        cuotas = "Débito" if "DEBIT" in tipo else (f"{cuotas_n} Cuotas" if cuotas_n > 1 else "1 Cuota / Otro")
        reembolsado = any(str(p.get("status")) in ("refunded", "charged_back") for p in pagos if p)
        es_reverso = 1 if (o.get("status") == "cancelled" or reembolsado) else 0

        fecha = pd.Timestamp(o["date_created"]).tz_convert(ZONA_AR)
        envio_estado = envio.get("envio_estado", "Pendiente")
        filas = []
        for oi in o.get("order_items", []):
            item = oi.get("item", {})
            item_id = str(item.get("id", ""))
            sku = item.get("seller_sku") or item.get("seller_custom_field") or item_id or "S/D"
            sku = str(sku).strip()
            talle = next((a.get("value_name") for a in (item.get("variation_attributes") or [])
                          if a.get("id") == "SIZE" or "talle" in str(a.get("name", "")).lower()), None)
            titulo = item.get("title", "S/D")
            cant = int(oi.get("quantity", 1))
            precio = float(oi.get("unit_price", 0) or 0)
            filas.append({
                "id_pedido": o.get("pack_id") or o["id"],   # carrito (pack) = "pedido", igual que Shopify
                "fecha": fecha.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
                "hora": fecha.hour,
                "total_pedido": 0.0,                        # se recalcula por pack al final
                "marca": self.marca,
                "es_reverso": es_reverso,
                "cantidad": cant,
                "sku": sku,
                "modelo_color": sku.rsplit("-", 1)[0] if "-" in sku else sku,
                "producto": f"{titulo} / {talle}" if talle else titulo,
                "producto_base": titulo,
                "fulfillment_status": ESTADO_FULFILL.get(envio_estado, "pending"),
                "img_url": "",
                "url_web": f"https://articulo.mercadolibre.com.ar/{item_id[:3]}-{item_id[3:]}" if item_id else "#",
                "subtotal_producto": precio * cant,
                "medio_pago": f"MERCADO PAGO MELI - {tipo}",
                "cuotas": cuotas,
                "descuento": "SIN DESCUENTO",
                "tags": ",".join(o.get("tags") or []),
                "provincia": envio.get("provincia", "Buenos Aires"),
                "fecha_despacho": envio.get("fecha_despacho"),
                # --- columnas propias de MeLi ---
                "orden_meli": o["id"],
                "item_id": item_id,
                "cliente": hash_cliente(f"meli:{(o.get('buyer') or {}).get('id', '')}"),
                "total_orden_meli": float(o.get("total_amount", 0) or 0),
                "comision_meli": float(oi.get("sale_fee", 0) or 0) * cant,
                "logistica": envio.get("logistica", "S/D"),
                "envio_estado": envio_estado,
                "envio_detalle": envio.get("envio_detalle", ""),
                "fecha_entrega": envio.get("fecha_entrega"),
                "transportista": envio.get("transportista", "Mercado Envíos"),
                "nro_pedido": str(o.get("pack_id") or o["id"]),
                "shipping_id": (o.get("shipping") or {}).get("id"),
                "estado_orden": o.get("status", ""),
                "ultima_actualizacion": o.get("date_last_updated") or o.get("date_created"),
            })
        return filas

    def procesar(self, ordenes):
        filas = []
        for o in ordenes:
            env = self.envio((o.get("shipping") or {}).get("id"))
            filas.extend(self.a_filas(o, env))
            time.sleep(0.05)
        return filas


def refrescar_envios(cuenta, df_marca):
    """Re-consulta envíos que todavía pueden cambiar de estado.
    - Pendientes / listos para despachar de los últimos 15 días: en cada corrida.
    - Despachados y en camino de los últimos 30 días: cada 2 hs (MELI_REFRESCAR_ENTREGAS=1)."""
    ahora = datetime.now(ZONA_AR)
    f = pd.to_datetime(df_marca["fecha"], errors="coerce", format="mixed", utc=True).dt.tz_convert(ZONA_AR)
    if "envio_estado" in df_marca.columns:
        est = df_marca["envio_estado"].fillna("")
        pend = est.isin(["Pendiente", "Listo para despachar", ""]) & (f >= ahora - timedelta(days=DIAS_REVISION_ENVIOS))
        curso = est.isin(EN_CURSO) & (f >= ahora - timedelta(days=30)) if REFRESCAR_ENTREGAS else False
        msk = pend | curso
    else:
        msk = (df_marca["fulfillment_status"] == "pending") & (f >= ahora - timedelta(days=DIAS_REVISION_ENVIOS))
    sel = df_marca[msk & df_marca["shipping_id"].notna()]
    cambios = {}
    for sid in sel["shipping_id"].unique():
        env = cuenta.envio(int(sid))
        if env:
            cambios[sid] = env
        time.sleep(0.05)
    return cambios


def sync():
    print(f"\n--- 🟡 SINCRO MELI: {datetime.now(ZONA_AR).strftime('%H:%M:%S')} (ARG) ---")
    if not APP_ID or not CLIENT_SECRET:
        print("🚨 Faltan MELI_APP_ID / MELI_CLIENT_SECRET")
        return
    df_old = pd.read_csv(FILENAME) if os.path.exists(FILENAME) else pd.DataFrame()
    ahora = datetime.now(ZONA_AR)
    nuevas = []

    for marca, secret_name in CUENTAS.items():
        if not os.environ.get(secret_name):
            print(f"   ⏭️ {marca}: sin secret {secret_name}, salteo")
            continue
        try:
            c = MeliCuenta(marca, secret_name)
            c.asegurar_token()
            df_m = df_old[df_old["marca"] == marca] if not df_old.empty else pd.DataFrame()

            if df_m.empty:
                # Backfill por ventanas de fecha de creación
                print(f"   📥 {marca}: backfill desde {FECHA_INICIO}")
                desde = pd.Timestamp(FECHA_INICIO).to_pydatetime()
                ordenes = []
                while desde < ahora:
                    hasta = min(desde + timedelta(days=VENTANA_BACKFILL_DIAS), ahora)
                    lote = c.buscar_ordenes("order.date_created", desde, hasta)
                    if lote is None:
                        break
                    ordenes.extend(lote)
                    desde = hasta
            else:
                # Incremental: todo lo actualizado desde la última corrida (con 15 min de margen)
                ult = pd.to_datetime(df_m["ultima_actualizacion"], errors="coerce", utc=True).max()
                desde = (ult.to_pydatetime() - timedelta(minutes=15)) if pd.notna(ult) else ahora - timedelta(days=1)
                ordenes = c.buscar_ordenes("order.date_last_updated", desde) or []

            filas = c.procesar(ordenes)
            print(f"   ✅ {marca}: {len(ordenes)} órdenes nuevas/actualizadas -> {len(filas)} líneas")
            nuevas.extend(filas)

            # Envíos pendientes que pudieron despacharse sin que cambie la orden
            if not df_m.empty and "shipping_id" in df_m.columns:
                cambios = refrescar_envios(c, df_m)
                for c_ in ["envio_estado", "envio_detalle", "fecha_entrega", "transportista"]:
                    if c_ not in df_old.columns:
                        df_old[c_] = None
                for sid, env in cambios.items():
                    msk = (df_old["marca"] == marca) & (df_old["shipping_id"] == sid)
                    df_old.loc[msk, "fulfillment_status"] = ESTADO_FULFILL.get(env["envio_estado"], "pending")
                    for c_ in ["fecha_despacho", "logistica", "envio_estado", "envio_detalle", "fecha_entrega", "transportista"]:
                        df_old.loc[msk, c_] = env.get(c_)
                if cambios:
                    print(f"   🚚 {marca}: {len(cambios)} envíos re-consultados")
        except Exception as e:
            print(f"   🚨 {marca}: {e}")

    if not nuevas and df_old.empty:
        print("😴 Sin datos.")
        return

    df = pd.concat([df_old, pd.DataFrame(nuevas)], ignore_index=True) if nuevas else df_old.copy()
    df = df.drop_duplicates(subset=["orden_meli", "sku"], keep="last")

    # total_pedido = suma de total_amount de todas las órdenes del pack (carrito)
    # (sin contar órdenes canceladas del pack; si el pack entero se canceló, queda el total bruto)
    ords = df.drop_duplicates("orden_meli")
    tot_ok = ords[ords["es_reverso"] == 0].groupby("id_pedido")["total_orden_meli"].sum()
    tot_all = ords.groupby("id_pedido")["total_orden_meli"].sum()
    df["total_pedido"] = df["id_pedido"].map(tot_ok).fillna(df["id_pedido"].map(tot_all)).astype(float)

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", format="mixed")
    corte = datetime.now(ZONA_AR) - timedelta(days=DIAS_RETENCION_LIVE)
    vivo, viejo = df[df["fecha"] >= corte].copy(), df[df["fecha"] < corte].copy()

    if not viejo.empty:
        if os.path.exists(FILENAME_HISTORICO):
            viejo = pd.concat([pd.read_csv(FILENAME_HISTORICO), viejo], ignore_index=True)
        viejo.drop_duplicates(subset=["orden_meli", "sku"], keep="last").to_csv(FILENAME_HISTORICO, index=False)

    vivo.to_csv(FILENAME, index=False)
    print(f"🚀 {FILENAME}: {len(vivo):,} líneas / {vivo['id_pedido'].nunique():,} pedidos")


if __name__ == "__main__":
    try:
        sync()
        print("✅ MeLi OK")
    except Exception as e:
        print(f"🚨 Error crítico MeLi: {e}")
