import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta, timezone

# Versión Segura: Lee las contraseñas desde la caja fuerte de GitHub
STORES = {
    "Reebok": {"url": "reebok-ar", "token": os.environ.get("TOKEN_REEBOK")},
    "Columbia": {"url": "columbia-ar", "token": os.environ.get("TOKEN_COLUMBIA")},
    "Crocs": {"url": "crocs-ar", "token": os.environ.get("TOKEN_CROCS")},
    "Kappa": {"url": "kappa-ar", "token": os.environ.get("TOKEN_KAPPA")},
    "Piccadilly": {"url": "piccadilly-ar", "token": os.environ.get("TOKEN_PICCADILLY")}
}

FILENAME = "ventas_hot_sale.csv"
FECHA_INICIO = "2026-01-01T00:00:00-03:00"

# HUSO HORARIO LOCAL ARGENTINA
ZONA_AR = timezone(timedelta(hours=-3))

class ShopifyManager:
    def __init__(self, name, info):
        self.name = name
        self.base_url = f"https://{info['url']}.myshopify.com/admin/api/2024-04"
        self.headers = {"X-Shopify-Access-Token": info['token']}
        self.store_url = f"https://{info['url']}.myshopify.com"
        self.catalog = {}

    def fetch_catalog(self):
        try:
            res = requests.get(f"{self.base_url}/products.json", headers=self.headers, params={"limit": 250, "fields": "id,handle,image"}, timeout=20)
            for p in res.json().get('products', []):
                img = p.get('image', {}).get('src', '') if p.get('image') else ''
                self.catalog[p['id']] = {"img": img, "link": f"{self.store_url}/products/{p.get('handle')}"}
        except: pass

    def extract_finances(self, order):
        tags = str(order.get('tags', '')).lower()
        notes = str(order.get('note_attributes', '')).lower()
        gateway = order.get('gateway', 'Desconocido').upper()
        
        content = tags + notes
        cuotas = "1 Cuota / Otro"
        if 'cuota' in content or 'quote' in content:
            for i in [18, 12, 9, 6, 3]:
                if f'{i} cuota' in content or f'{i}cuota' in content or f' {i} ' in content:
                    cuotas = f"{i} Cuotas"
                    break
        elif 'debit' in content or 'débito' in content:
            cuotas = "Débito"
            
        return gateway, cuotas, tags

    def get_orders_batch(self, params):
        rows = []
        try:
            res = requests.get(f"{self.base_url}/orders.json", headers=self.headers, params=params, timeout=30)
            if res.status_code == 429: 
                time.sleep(5)
                return self.get_orders_batch(params)
            orders = res.json().get('orders', [])
            for o in orders:
                gateways = o.get('payment_gateway_names', [])
                medio_pago = gateways[0].upper() if gateways else 'DESCONOCIDO'
                
                discounts = o.get('discount_applications', [])
                descuento = discounts[0].get('title', 'Sin Descuento').upper() if discounts else 'Sin Descuento'

                gateway_legacy, cuotas, tags_raw = self.extract_finances(o)
                es_reverso = 1 if 'reverso' in tags_raw else 0
                
                # Convertir fechas a hora local de Argentina para evitar desfasajes
                dt_utc = datetime.fromisoformat(o['created_at'].replace("Z", "+00:00"))
                dt_ar = dt_utc.astimezone(ZONA_AR)
                hora_pico = dt_ar.hour
                
                provincia = o.get('shipping_address', {}).get('province', 'Buenos Aires') if o.get('shipping_address') else 'Buenos Aires'
                
                # Extraer fecha de despacho si existe en los fulfillments
                fulfillments = o.get('fulfillments', [])
                fecha_despacho = fulfillments[0].get('created_at') if fulfillments else None
                
                for item in o.get('line_items', []):
                    p_info = self.catalog.get(item.get('product_id'), {"img": "", "link": "#"})
                    cantidad = int(item.get('quantity', 1))
                    precio_unitario = float(item.get('price', 0))
                    
                    sku_raw = item.get('sku', 'S/D')
                    modelo_color = sku_raw.rsplit('-', 1)[0] if '-' in sku_raw else sku_raw
                    nombre_raw = item.get('name', 'S/D')
                    producto_base = nombre_raw.split(' / ')[0]
                    
                    rows.append({
                        "id_pedido": o['id'], 
                        "fecha": dt_ar.strftime("%Y-%m-%d %H:%M:%S"), 
                        "hora": hora_pico,
                        "total_pedido": float(o['total_price']),
                        "marca": self.name, 
                        "es_reverso": es_reverso,
                        "cantidad": cantidad, 
                        "sku": sku_raw,
                        "modelo_color": modelo_color,
                        "producto": nombre_raw, 
                        "producto_base": producto_base,
                        "fulfillment_status": o.get('fulfillment_status') or 'pending',
                        "img_url": p_info['img'], 
                        "url_web": p_info['link'],
                        "subtotal_producto": precio_unitario * cantidad,
                        "medio_pago": medio_pago,
                        "cuotas": cuotas,
                        "descuento": descuento,
                        "tags": tags_raw,
                        "provincia": provincia,
                        "fecha_despacho": fecha_despacho
                    })
        except Exception as e: 
            print(f"Error parseando lote: {e}")
        return rows

    def get_incremental_updates(self, last_id):
        self.fetch_catalog()
        all_rows = []
        
        # 1. BUSCAR PEDIDOS NUEVOS (Desde el último ID)
        curr_id = last_id
        while True:
            params = {"limit": 250, "status": "any", "order": "id asc"}
            if curr_id == 0: 
                params["created_at_min"] = FECHA_INICIO
            else: 
                params["since_id"] = curr_id
                
            batch = self.get_orders_batch(params)
            if not batch: break
            all_rows.extend(batch)
            curr_id = batch[-1]['id_pedido']
            if len(batch) < 250: break
            
        # 2. BUSCAR ACTUALIZACIONES DE HOY (Pedidos viejos que cambiaron de estado hoy)
        ahora = datetime.now(ZONA_AR)
        inicio_hoy = ahora.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        params_update = {"limit": 250, "status": "any", "updated_at_min": inicio_hoy}
        batch_updated = self.get_orders_batch(params_update)
        all_rows.extend(batch_updated)
        
        return all_rows

def sync():
    print(f"\n--- 🕒 ACTUALIZANDO: {datetime.now(ZONA_AR).strftime('%H:%M:%S')} (ARG) ---")
    df_old = pd.read_csv(FILENAME) if os.path.exists(FILENAME) else pd.DataFrame()
    last_ids = df_old.groupby('marca')['id_pedido'].max().to_dict() if not df_old.empty else {}
    
    new_rows = []
    for name, info in STORES.items():
        if not info['token']: continue
        m = ShopifyManager(name, info)
        batch = m.get_incremental_updates(last_ids.get(name, 0))
        if batch:
            print(f"   ✅ {name}: +{len(batch)} líneas extraídas/actualizadas.")
            new_rows.extend(batch)
        else: 
            print(f"   😴 {name}: Al día.")

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        if not df_old.empty:
            # Concatenamos y al eliminar duplicados nos quedamos con la versión MÁS RECIENTE ('last')
            # Esto plancha los cambios logísticos sobre los pedidos viejos
            df_final = pd.concat([df_old, df_new], ignore_index=True)
            df_final = df_final.drop_duplicates(subset=['id_pedido', 'sku'], keep='last')
        else:
            df_final = df_new
            
        df_final.to_csv(FILENAME, index=False)
        print(f"🚀 Sincronizado. Total en base: {len(df_final)} registros.")

if __name__ == "__main__":
    try: 
        sync()
        print("✅ Extracción finalizada con éxito.")
    except Exception as e: 
        print(f"🚨 Error: {e}")
