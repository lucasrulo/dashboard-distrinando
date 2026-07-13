import requests
import os
import json

# Diagnóstico mínimo — SOLO Reebok, SOLO una llamada, SIN ninguna lógica del extractor.
# El objetivo es ver la respuesta CRUDA de Shopify para saber si el problema es un
# bloqueo de acceso (protected customer data / 60 días) o algo en nuestro script.

def obtener_token(nombre_secret):
    token_env = os.environ.get(nombre_secret)
    if token_env: return token_env
    try:
        from streamlit import secrets
        if nombre_secret in secrets: return secrets[nombre_secret]
    except Exception: pass
    return None

TOKEN = obtener_token("TOKEN_REEBOK")
API_VERSION = "2025-10"
STORE = "reebok-ar"
ULTIMO_ID_CONOCIDO = 12474622247284  # el id más alto que tenemos, fechado 2026-07-09 23:29:32

url = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/orders.json"
headers = {"X-Shopify-Access-Token": TOKEN}

print("=" * 70)
print("PRUEBA 1: since_id (lo que usa nuestro extractor)")
print("=" * 70)
params_1 = {"limit": 5, "status": "any", "order": "id asc", "since_id": ULTIMO_ID_CONOCIDO}
res_1 = requests.get(url, headers=headers, params=params_1, timeout=30)
print("STATUS:", res_1.status_code)
print("BODY (primeros 2000 chars):")
print(res_1.text[:2000])

print()
print("=" * 70)
print("PRUEBA 2: created_at_min = hoy (sin since_id, para descartar el bug ahí)")
print("=" * 70)
from datetime import datetime, timedelta, timezone
ZONA_AR = timezone(timedelta(hours=-3))
hace_3_dias = (datetime.now(ZONA_AR) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S-03:00")
params_2 = {"limit": 5, "status": "any", "order": "id asc", "created_at_min": hace_3_dias}
res_2 = requests.get(url, headers=headers, params=params_2, timeout=30)
print("STATUS:", res_2.status_code)
print("BODY (primeros 2000 chars):")
print(res_2.text[:2000])

print()
print("=" * 70)
print("PRUEBA 3: sin ningún filtro de fecha/id, solo status=any (la más simple posible)")
print("=" * 70)
params_3 = {"limit": 5, "status": "any"}
res_3 = requests.get(url, headers=headers, params=params_3, timeout=30)
print("STATUS:", res_3.status_code)
print("BODY (primeros 2000 chars):")
print(res_3.text[:2000])
