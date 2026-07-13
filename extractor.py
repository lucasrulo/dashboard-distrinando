import requests
import pandas as pd
import os
from datetime import datetime

# Función para leer tokens
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

FILENAME_CATALOGO = "catalogo_stock.csv"
# Misma versión que extractor.py — mantenerlas sincronizadas al hacer el bump trimestral.
API_VERSION = "2025-10"

def sync_catalogo():
    print(f"--- 📦 INICIANDO SINCRONIZACIÓN DE CATÁLOGO: {datetime.now()} ---")
    all_products = []
    
    for name, info in STORES.items():
        if not info['token']: continue
        print(f"-> Extrayendo {name}...")
        
        base_url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}/products.json"
        headers = {"X-Shopify-Access-Token": info['token']}
        
        # Shopify limita a 250 por página
        params = {"limit": 250, "status": "active"}
        
        try:
            res = requests.get(base_url, headers=headers, params=params, timeout=30)
            if res.status_code != 200:
                # Antes esto se tragaba en silencio. Ahora se ve en el log si el token
                # o la versión de API tienen algún problema.
                print(f"🚨 {name}: HTTP {res.status_code} -> {res.text[:300]}")
                continue
            products = res.json().get('products', [])
            
            for p in products:
                for variant in p.get('variants', []):
                    # El SKU es la clave para cruzar con tus ventas
                    sku = str(variant.get('sku', '')).strip()
                    if sku == '': continue
                    
                    all_products.append({
                        "marca": name,
                        "modelo_color": sku.rsplit('-', 1)[0] if '-' in sku else sku,
                        "sku": sku,
                        "stock": variant.get('inventory_quantity', 0),
                        "precio": variant.get('price', 0),
                        "titulo": p.get('title', 'S/D')
                    })
        except Exception as e:
            print(f"🚨 Error en {name}: {e}")
            
    if all_products:
        df = pd.DataFrame(all_products)
        df.to_csv(FILENAME_CATALOGO, index=False)
        print(f"✅ Catálogo guardado. {len(df)} variantes procesadas.")

if __name__ == "__main__":
    sync_catalogo()
