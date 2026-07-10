import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta, timezone

# ==============================================================================
# ⚙️ CONFIGURACIÓN
# ==============================================================================
FILENAME_SESIONES = "sesiones_hot_sale.csv"

# Mismo criterio de arranque que ventas_hot_sale.csv, pero en formato YYYY-MM-DD
# (ShopifyQL usa fechas simples, no ISO con hora/offset)
FECHA_INICIO = "2026-01-01"

ZONA_AR = timezone(timedelta(hours=-3))

# shopifyqlQuery necesita una versión de API reciente (se liberó a fines de 2025).
# La fijamos independiente de la que usa extractor.py / extractor_catalogo.py.
API_VERSION_SHOPIFYQL = "2025-10"


# 1. FUNCIÓN INTELIGENTE PARA LEER TOKENS (idéntica a la de extractor.py)
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


def ejecutar_shopifyql(store_url, token, query, reintentos=3):
    """Ejecuta una query ShopifyQL contra la Admin GraphQL API de una tienda."""
    endpoint = f"https://{store_url}.myshopify.com/admin/api/{API_VERSION_SHOPIFYQL}/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    body = {
        "query": """
            query($ql: String!) {
              shopifyqlQuery(query: $ql) {
                tableData {
                  columns { name dataType displayName }
                  rows
                }
                parseErrors { code message }
              }
            }
        """,
        "variables": {"ql": query}
    }

    try:
        res = requests.post(endpoint, headers=headers, json=body, timeout=30)
    except Exception as e:
        print(f"   🚨 Error de red: {e}")
        return None

    if res.status_code == 429 and reintentos > 0:
        time.sleep(5)
        return ejecutar_shopifyql(store_url, token, query, reintentos - 1)

    if res.status_code != 200:
        print(f"   🚨 HTTP {res.status_code}: {res.text[:300]}")
        return None

    data = res.json()

    if 'errors' in data:
        print(f"   🚨 Error GraphQL: {data['errors']}")
        return None

    payload = (data.get('data') or {}).get('shopifyqlQuery') or {}

    if payload.get('parseErrors'):
        print(f"   🚨 Error de sintaxis ShopifyQL: {payload['parseErrors']}")
        return None

    return payload.get('tableData')


def extraer_sesiones_tienda(name, info):
    if not info['token']:
        print(f"   ⚠️ {name}: sin token configurado, se omite.")
        return []

    fecha_hoy = datetime.now(ZONA_AR).strftime("%Y-%m-%d")
    # "sessions", "orders" y "conversion_rate" son métricas dentro de la tabla "sales" en ShopifyQL.
    ql = f"FROM sales SHOW sessions, conversion_rate TIMESERIES day SINCE {FECHA_INICIO} UNTIL {fecha_hoy}"

    tabla = ejecutar_shopifyql(info['url'], info['token'], ql)
    if not tabla or not tabla.get('rows'):
        return []

    nombres_col = [c['name'] for c in tabla['columns']]
    filas = []
    for row in tabla['rows']:
        registro = dict(zip(nombres_col, row))
        # La columna de fecha en TIMESERIES day puede llamarse "day" o "date" según versión de API
        fecha_val = registro.get('day') or registro.get('date') or registro.get('Day')
        try:
            sesiones_val = int(float(registro.get('sessions', 0) or 0))
        except (TypeError, ValueError):
            sesiones_val = 0
        try:
            cr_shopify_val = float(registro.get('conversion_rate', 0) or 0)
        except (TypeError, ValueError):
            cr_shopify_val = 0.0

        filas.append({
            "marca": name,
            "fecha": fecha_val,
            "sesiones": sesiones_val,
            "conversion_rate_shopify": cr_shopify_val
        })
    return filas


def sync_sesiones():
    print(f"\n--- 📈 SINCRO SESIONES: {datetime.now(ZONA_AR).strftime('%H:%M:%S')} (ARG) ---")
    todas_filas = []

    for name, info in STORES.items():
        filas = extraer_sesiones_tienda(name, info)
        if filas:
            print(f"   ✅ {name}: {len(filas)} días de sesiones procesados.")
            todas_filas.extend(filas)
        else:
            print(f"   😴 {name}: sin datos de sesiones.")

    if todas_filas:
        df_nuevo = pd.DataFrame(todas_filas)
        df_nuevo['fecha'] = pd.to_datetime(df_nuevo['fecha'], errors='coerce')
        df_nuevo = df_nuevo.dropna(subset=['fecha'])
        df_nuevo = df_nuevo.drop_duplicates(subset=['marca', 'fecha'], keep='last')
        df_nuevo = df_nuevo.sort_values(['marca', 'fecha'])
        df_nuevo.to_csv(FILENAME_SESIONES, index=False)
        print(f"🚀 Sesiones guardadas con éxito. Total: {len(df_nuevo)} registros.")
    else:
        print("ℹ️ No se obtuvieron datos de sesiones en esta corrida.")


if __name__ == "__main__":
    try:
        sync_sesiones()
        print("✅ Proceso de sesiones finalizado.")
    except Exception as e:
        print(f"🚨 Error crítico: {e}")
