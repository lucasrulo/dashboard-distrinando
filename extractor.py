import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta, timezone

# ==============================================================================
# ⚙️ CONFIGURACIÓN COMERCIAL Y CONTROL DE BACKFILL
# ==============================================================================
# 🎯 True = Ignora el archivo local y descarga TODO el historial desde FECHA_INICIO.
# 🎯 False = Modo normal. Solo descarga las órdenes nuevas (incremental).
FORZAR_RECARGA_COMPLETA = False  

# Ajustá esta fecha al día más antiguo del que quieras traer datos (ej: 2025 o 2024)
FECHA_INICIO = "2026-01-01T00:00:00-03:00" 

FILENAME = "ventas_hot_sale.csv"
FILENAME_HISTORICO = "ventas_historico.csv"
# Días que se mantienen en el archivo "vivo" (el que lee el dashboard de Streamlit).
# Todo lo más viejo se mueve a FILENAME_HISTORICO para que el dashboard no se quede
# sin memoria cargando meses y meses de datos que ya nadie mira en el día a día.
DIAS_RETENCION_LIVE = 90
ZONA_AR = timezone(timedelta(hours=-3))

# Versión del Admin API REST. Shopify sostiene cada versión ~12 meses; hay que
# subirla cada 3-4 meses. Julio 2026: estables son 2025-10, 2026-01, 2026-04.
API_VERSION = "2025-10"


# 1. FUNCIÓN INTELIGENTE PARA LEER TOKENS
def obtener_token(nombre_secret):
    token_env = os.environ.get(nombre_secret)
    if token_env: return token_env
    try:
        from streamlit import secrets
        if nombre_secret in secrets: return secrets[nombre_secret]
    except Exception: pass
    return None

STORES = {
    "Reebok": {"url": "reebok-ar", "token": obtener_token("TOKEN_REEBOK")},
    "Columbia": {"url": "columbia-ar", "token": obtener_token("TOKEN_COLUMBIA")},
    "Crocs": {"url": "crocs-ar", "token": obtener_token("TOKEN_CROCS")},
    "Kappa": {"url": "kappa-ar", "token": obtener_token("TOKEN_KAPPA")},
    "Piccadilly": {"url": "piccadilly-ar", "token": obtener_token("TOKEN_PICCADILLY")}
}

class ShopifyManager:
    def __init__(self, name, info):
        self.name = name
        self.base_url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}"
        self.headers = {"X-Shopify-Access-Token": info['token']}
        self.store_url = f"https://{info['url']}.myshopify.com"
        self.catalog = {}

    def fetch_catalog(self):
        try:
            res = requests.get(f"{self.base_url}/products.json", headers=self.headers, params={"limit": 250, "fields": "id,handle,image"}, timeout=20)
            if res.status_code != 200:
                print(f"   🚨 {self.name} (catálogo): HTTP {res.status_code} - {res.text[:300]}")
                return
            for p in res.json().get('products', []):
                img = p.get('image', {}).get('src', '') if p.get('image') else ''
                self.catalog[p['id']] = {"img": img, "link": f"{self.store_url}/products/{p.get('handle')}"}
        except Exception as e:
            print(f"   🚨 {self.name} (catálogo): Excepción {e}")

    def extract_finances(self, order):
        tags = str(order.get('tags', '')).lower()
        notes = str(order.get('note_attributes', '')).lower()
        gateway = order.get('gateway', 'Desconocido').upper()
        content = tags + notes
        cuotas = "1 Cuota / Otro"
        if 'cuota' in content or 'quote' in content:
            for i in [18, 12, 9, 6, 3]:
                if f'{i} cuota' in content or f'{i}cuota' in content or f' {i} ' in content:
                    cuotas = f"{i} Cuotas"; break
        elif 'debit' in content or 'débito' in content: cuotas = "Débito"
        return gateway, cuotas, tags

    def get_orders_batch(self, params):
        rows = []
        try:
            res = requests.get(f"{self.base_url}/orders.json", headers=self.headers, params=params, timeout=30)
            if res.status_code == 429: time.sleep(5); return self.get_orders_batch(params)
            if res.status_code != 200:
                # 🚨 Antes esto se tragaba en silencio (devolvía [] como si fuera "no hay más datos").
                # Ahora devolvemos None para que el llamador sepa que fue un ERROR, no el fin real de la paginación.
                print(f"   🚨 {self.name}: HTTP {res.status_code} en /orders.json -> {res.text[:300]}")
                return None
            orders = res.json().get('orders', [])
            for o in orders:
                gateways = o.get('payment_gateway_names', [])
                medio_pago = gateways[0].upper() if gateways else 'DESCONOCIDO'
                discounts = o.get('discount_applications', [])
                descuento = discounts[0].get('title', 'Sin Descuento').upper() if discounts else 'Sin Descuento'
                gateway_legacy, cuotas, tags_raw = self.extract_finances(o)
                
                # Buscamos la palabra "reversso" (doble s) para clasificar la orden desde el origen
                es_reverso = 1 if 'reversso' in tags_raw else 0
                
                # Estandarización estricta ISO 8601 con offset local
                dt_utc = datetime.fromisoformat(o['created_at'].replace("Z", "+00:00"))
                dt_ar = dt_utc.astimezone(ZONA_AR)
                fecha_limpia = dt_ar.strftime("%Y-%m-%dT%H:%M:%S-03:00")
                hora_pico = dt_ar.hour
                
                provincia = o.get('shipping_address', {}).get('province', 'Buenos Aires') if o.get('shipping_address') else 'Buenos Aires'
                fulfillments = o.get('fulfillments', [])
                fecha_despacho = fulfillments[0].get('created_at') if fulfillments else None
                
                # 🚨 IMPORTANTE: algunos pedidos (cambios, devoluciones, ajustes) pueden no tener
                # line_items. Igual necesitamos "visitarlos" para no perder la cuenta de paginación,
                # aunque no generen ninguna fila en el CSV.
                items = o.get('line_items', [])
                if not items:
                    rows.append({
                        "id_pedido": o['id'], "fecha": fecha_limpia, "hora": hora_pico,
                        "total_pedido": float(o['total_price']), "marca": self.name, "es_reverso": es_reverso,
                        "cantidad": 0, "sku": "S/D", "modelo_color": "S/D",
                        "producto": "Sin ítems (ajuste/cambio)", "producto_base": "Sin ítems (ajuste/cambio)",
                        "fulfillment_status": o.get('fulfillment_status') or 'pending',
                        "img_url": "", "url_web": "#",
                        "subtotal_producto": 0.0, "medio_pago": medio_pago,
                        "cuotas": cuotas, "descuento": descuento, "tags": tags_raw,
                        "provincia": provincia, "fecha_despacho": fecha_despacho
                    })
                for item in items:
                    p_info = self.catalog.get(item.get('product_id'), {"img": "", "link": "#"})
                    cantidad = int(item.get('quantity', 1))
                    precio_unitario = float(item.get('price', 0))
                    sku_raw = item.get('sku', 'S/D')
                    modelo_color = sku_raw.rsplit('-', 1)[0] if '-' in sku_raw else sku_raw
                    nombre_raw = item.get('name', 'S/D')
                    producto_base = nombre_raw.split(' / ')[0]
                    
                    rows.append({
                        "id_pedido": o['id'], "fecha": fecha_limpia, "hora": hora_pico,
                        "total_pedido": float(o['total_price']), "marca": self.name, "es_reverso": es_reverso,
                        "cantidad": cantidad, "sku": sku_raw, "modelo_color": modelo_color,
                        "producto": nombre_raw, "producto_base": producto_base,
                        "fulfillment_status": o.get('fulfillment_status') or 'pending',
                        "img_url": p_info['img'], "url_web": p_info['link'],
                        "subtotal_producto": precio_unitario * cantidad, "medio_pago": medio_pago,
                        "cuotas": cuotas, "descuento": descuento, "tags": tags_raw,
                        "provincia": provincia, "fecha_despacho": fecha_despacho
                    })
        except Exception as e:
            print(f"   🚨 {self.name}: Excepción parseando lote de pedidos: {e}")
            return None
        # 🎯 FIX CRÍTICO: devolvemos también cuántos PEDIDOS trajo la página (no líneas)
        # y el id del último pedido, para que la paginación se corte por la cantidad real
        # de pedidos (que es lo que Shopify pagina con "limit"), no por cantidad de renglones.
        num_pedidos = len(orders)
        ultimo_id = orders[-1]['id'] if orders else None
        return rows, num_pedidos, ultimo_id

    def get_incremental_updates(self, last_id):
        self.fetch_catalog()
        all_rows = []
        curr_id = last_id
        while True:
            params = {"limit": 250, "status": "any", "order": "id asc"}
            if curr_id == 0: params["created_at_min"] = FECHA_INICIO
            else: params["since_id"] = curr_id
            resultado = self.get_orders_batch(params)
            if resultado is None:
                print(f"   ⚠️ {self.name}: paginación cortada por un error (arriba 👆). NO se asume que ya no hay más pedidos.")
                break
            batch, num_pedidos, ultimo_id = resultado
            if num_pedidos == 0: break  # página realmente vacía: ahí sí se terminaron los pedidos
            all_rows.extend(batch)
            curr_id = ultimo_id
            if num_pedidos < 250: break  # página parcial = última página (esto SÍ es por cantidad de PEDIDOS)
            
        ahora = datetime.now(ZONA_AR)
        inicio_hoy = ahora.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        params_update = {"limit": 250, "status": "any", "updated_at_min": inicio_hoy}
        resultado_update = self.get_orders_batch(params_update)
        if resultado_update:
            batch_updated, _, _ = resultado_update
            all_rows.extend(batch_updated)
        return all_rows

def sync():
    print(f"\n--- 🕒 SINCRO: {datetime.now(ZONA_AR).strftime('%H:%M:%S')} (ARG) ---")
    
    df_old = pd.read_csv(FILENAME) if os.path.exists(FILENAME) else pd.DataFrame()
    
    if FORZAR_RECARGA_COMPLETA:
        print("⚠️ ALERTA: Modo Recarga Completa activo. Extrayendo todo el historial viejo...")
        last_ids = {}
        df_old = pd.DataFrame() # Vaciamos memoria local para no duplicar datos viejos
    else:
        last_ids = df_old.groupby('marca')['id_pedido'].max().to_dict() if not df_old.empty else {}
    
    new_rows = []
    for name, info in STORES.items():
        if not info['token']: continue
        m = ShopifyManager(name, info)
        batch = m.get_incremental_updates(last_ids.get(name, 0))
        if batch:
            print(f"   ✅ {name}: +{len(batch)} líneas procesadas.")
            new_rows.extend(batch)
        else: print(f"   😴 {name}: Sin novedades.")

    if new_rows or not df_old.empty:
        df_final = pd.DataFrame(new_rows) if new_rows else pd.DataFrame()
        # Si no fue recarga completa, unificamos con lo que ya existía de forma segura
        if not df_old.empty:
            df_final = pd.concat([df_old, df_final], ignore_index=True) if not df_final.empty else df_old.copy()
            
        # Limpieza monolítica estricta por ID de pedido y SKU
        df_final = df_final.drop_duplicates(subset=['id_pedido', 'sku'], keep='last')

        # ======================================================================
        # 🗄️ ARCHIVADO: separamos lo reciente (vivo) de lo viejo (histórico)
        # ======================================================================
        df_final['fecha'] = pd.to_datetime(df_final['fecha'], errors='coerce')
        corte = datetime.now(ZONA_AR) - timedelta(days=DIAS_RETENCION_LIVE)
        es_reciente = df_final['fecha'] >= corte

        df_vivo = df_final[es_reciente].copy()
        df_para_archivar = df_final[~es_reciente].copy()

        if not df_para_archivar.empty:
            if os.path.exists(FILENAME_HISTORICO):
                df_hist_viejo = pd.read_csv(FILENAME_HISTORICO)
                df_para_archivar = pd.concat([df_hist_viejo, df_para_archivar], ignore_index=True)
            df_para_archivar = df_para_archivar.drop_duplicates(subset=['id_pedido', 'sku'], keep='last')
            df_para_archivar.to_csv(FILENAME_HISTORICO, index=False)
            print(f"   🗄️ {len(df_para_archivar):,} filas históricas archivadas en {FILENAME_HISTORICO}.")

        df_vivo.to_csv(FILENAME, index=False)
        print(f"🚀 Archivo vivo guardado. Total (últimos {DIAS_RETENCION_LIVE} días): {len(df_vivo):,} registros.")

if __name__ == "__main__":
    try: sync(); print("✅ Proceso finalizado.")
    except Exception as e: print(f"🚨 Error crítico: {e}")
