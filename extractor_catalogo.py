import requests
import pandas as pd
import os
import time
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
MAX_PAGINAS = 200  # válvula de seguridad (200 x 250 = 50.000 productos)


def sync_catalogo():
    print(f"--- 📦 INICIANDO SINCRONIZACIÓN DE CATÁLOGO: {datetime.now()} ---")
    all_products = []

    for name, info in STORES.items():
        if not info['token']: continue
        print(f"-> Extrayendo {name}...")
        headers = {"X-Shopify-Access-Token": info['token']}
        url = f"https://{info['url']}.myshopify.com/admin/api/{API_VERSION}/products.json"
        params = {"limit": 250, "status": "active", "fields": "id,title,handle,variants"}
        store_url = f"https://{info['url']}.myshopify.com"
        n_prod, pagina = 0, 0
        try:
            # 🎯 FIX: antes se leía solo la primera página (250 productos por marca).
            # Ahora se sigue el header "Link: rel=next" hasta traer todo el catálogo activo.
            while url and pagina < MAX_PAGINAS:
                pagina += 1
                res = requests.get(url, headers=headers, params=params, timeout=30)
                if res.status_code == 429:
                    time.sleep(3)
                    continue
                if res.status_code != 200:
                    print(f"🚨 {name}: HTTP {res.status_code} -> {res.text[:300]}")
                    break
                products = res.json().get('products', [])
                n_prod += len(products)
                for p in products:
                    for variant in p.get('variants', []):
                        sku = str(variant.get('sku') or '').strip()
                        if sku == '': continue
                        all_products.append({
                            "marca": name,
                            "modelo_color": sku.rsplit('-', 1)[0] if '-' in sku else sku,
                            "sku": sku,
                            "stock": variant.get('inventory_quantity', 0),
                            "precio": variant.get('price', 0),
                            "titulo": p.get('title', 'S/D'),
                            "url_web": f"{store_url}/products/{p.get('handle')}",
                        })
                # La página siguiente ya trae sus parámetros en la URL (page_info)
                url = res.links.get("next", {}).get("url")
                params = None
                time.sleep(0.5)
            print(f"   ✅ {name}: {n_prod} productos activos en {pagina} páginas")
        except Exception as e:
            print(f"🚨 Error en {name}: {e}")

    if all_products:
        df = pd.DataFrame(all_products).drop_duplicates(subset=["marca", "sku"], keep="last")
        df.to_csv(FILENAME_CATALOGO, index=False)
        print(f"✅ Catálogo guardado. {len(df)} variantes procesadas.")


if __name__ == "__main__":
    sync_catalogo()
