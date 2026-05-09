import requests
import pandas as pd
import time
import os
from datetime import datetime

# Versión Segura: Lee las contraseñas desde la caja fuerte de GitHub
STORES = {
    "Reebok": {"url": "reebok-ar", "token": os.environ.get("TOKEN_REEBOK")},
    "Columbia": {"url": "columbia-ar", "token": os.environ.get("TOKEN_COLUMBIA")},
    "Crocs": {"url": "crocs-ar", "token": os.environ.get("TOKEN_CROCS")},
    "Kappa": {"url": "kappa-ar", "token": os.environ.get("TOKEN_KAPPA")},
    "Piccadilly": {"url": "piccadilly-ar", "token": os.environ.get("TOKEN_PICCADILLY")}
}
# ... (el resto del código sigue exactamente igual)
FILENAME = "ventas_hot_sale.csv"
FECHA_INICIO = "2026-01-01T00:00:00-03:00"

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

    def get_new_orders(self, last_id):
        self.fetch_catalog()
        rows = []
        curr_id = last_id
        while True:
            params = {"limit": 250, "status": "any", "order": "id asc"}
            if curr_id == 0: params["created_at_min"] = FECHA_INICIO
            else: params["since_id"] = curr_id
            try:
                res = requests.get(f"{self.base_url}/orders.json", headers=self.headers, params=params, timeout=30)
                if res.status_code == 429: time.sleep(5); continue
                orders = res.json().get('orders', [])
                if not orders: break
                for o in orders:
                    gateways = o.get('payment_gateway_names', [])
                    medio_pago = gateways[0].upper() if gateways else 'DESCONOCIDO'
                    
                    discounts = o.get('discount_applications', [])
                    descuento = discounts[0].get('title', 'Sin Descuento').upper() if discounts else 'Sin Descuento'

                    gateway_legacy, cuotas, tags_raw = self.extract_finances(o)
                    es_reverso = 1 if 'reverso' in tags_raw else 0
                    hora_pico = datetime.fromisoformat(o['created_at']).hour
                    
                    for item in o.get('line_items', []):
                        p_info = self.catalog.get(item.get('product_id'), {"img": "", "link": "#"})
                        cantidad = int(item.get('quantity', 1))
                        precio_unitario = float(item.get('price', 0))
                        
                        # LOGICA DE EXTRACCIÓN MODELO/COLOR
                        sku_raw = item.get('sku', 'S/D')
                        # Corta el SKU en el último guion (Ej: 12345-BLK-40 -> 12345-BLK)
                        modelo_color = sku_raw.rsplit('-', 1)[0] if '-' in sku_raw else sku_raw
                        
                        nombre_raw = item.get('name', 'S/D')
                        # Corta el nombre antes del talle (Ej: Campera / M -> Campera)
                        producto_base = nombre_raw.split(' / ')[0]
                        
                        rows.append({
                            "id_pedido": o['id'], 
                            "fecha": o['created_at'], 
                            "hora": hora_pico,
                            "total_pedido": float(o['total_price']),
                            "marca": self.name, 
                            "es_reverso": es_reverso,
                            "cantidad": cantidad, 
                            "sku": sku_raw,
                            "modelo_color": modelo_color,
                            "producto": nombre_raw, 
                            "producto_base": producto_base,
                            "fulfillment_status": o.get('fulfillment_status', 'pending'),
                            "img_url": p_info['img'], 
                            "url_web": p_info['link'],
                            "subtotal_producto": precio_unitario * cantidad,
                            "medio_pago": medio_pago,
                            "cuotas": cuotas,
                            "descuento": descuento,
                            "tags": tags_raw
                        })
                curr_id = orders[-1]['id']
                if len(orders) < 250: break
            except Exception as e: 
                print(f"Error parseando orden: {e}")
                break
        return rows

def sync():
    print(f"\n--- 🕒 ACTUALIZANDO: {datetime.now().strftime('%H:%M:%S')} ---")
    df_old = pd.read_csv(FILENAME) if os.path.exists(FILENAME) else pd.DataFrame()
    last_ids = df_old.groupby('marca')['id_pedido'].max().to_dict() if not df_old.empty else {}
    
    new_rows = []
    for name, info in STORES.items():
        m = ShopifyManager(name, info)
        batch = m.get_new_orders(last_ids.get(name, 0))
        if batch:
            print(f"   ✅ {name}: +{len(batch)} items nuevos.")
            new_rows.extend(batch)
        else: print(f"   😴 {name}: Al día.")

    if new_rows:
        df_final = pd.concat([df_old, pd.DataFrame(new_rows)], ignore_index=True).drop_duplicates(subset=['id_pedido', 'sku'], keep='last')
        df_final.to_csv(FILENAME, index=False)
        print(f"🚀 Sincronizado. Total en base: {len(df_final)} registros.")

if __name__ == "__main__":
    try: 
        sync()
        print("✅ Extracción finalizada con éxito.")
    except Exception as e: 
        print(f"🚨 Error: {e}")