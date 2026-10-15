import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import os
import io
import re
import json
import base64
import hashlib
import hmac
import time
import requests
from collections import Counter
from itertools import combinations
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh

# ==============================================================================
# 1. CONFIGURACIÓN
# ==============================================================================
st.set_page_config(page_title="Distrinando | Centro de Comando", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

REPO_DATOS = "lucasrulo/dashboard-distrinando"
WORKFLOW_ID = "actualizador.yml"
OBJ_ARCHIVO_REPO = "objetivos.json"
ZONA_AR = timezone(timedelta(hours=-3))

CANALES = ["Tienda Online", "MercadoLibre"]
CORTO = {"Tienda Online": "Tienda", "MercadoLibre": "MeLi"}
COLOR_CANAL = {"Tienda Online": "#22D3EE", "MercadoLibre": "#FFE600"}
COLOR_SCOPE = {"General": "#A78BFA", "Tienda Online": "#22D3EE", "MercadoLibre": "#FFE600"}
OPC_CANAL = ["Consolidado", "Tienda Online", "MercadoLibre"]
PALETA_MARCAS = {"Reebok": "#38BDF8", "Columbia": "#818CF8", "Crocs": "#34D399",
                 "Kappa": "#F472B6", "Piccadilly": "#FBBF24"}
MARCAS_BASE = ["Reebok", "Columbia", "Crocs", "Kappa", "Piccadilly"]
DOMINIOS_OFICIALES = {
    "Reebok": "https://www.reebok.com.ar", "Columbia": "https://www.columbiasportswear.com.ar",
    "Crocs": "https://www.crocs.com.ar", "Kappa": "https://www.kappastore.com.ar",
    "Piccadilly": "https://www.piccadilly.com.ar",
}
ESTADO_MAPA = {"fulfilled": "Enviado", "null": "Pendiente", "pending": "En preparación",
               "restocked": "Devuelto", "unfulfilled": "No enviado", "partial": "Envío parcial"}
COLOR_ESTADO = {"Enviado": "#34D399", "En preparación": "#FBBF24", "Pendiente": "#94A3B8",
                "Devuelto": "#F87171", "No enviado": "#F472B6", "Envío parcial": "#A78BFA"}
PROVINCIAS_MAPA = {
    'caba': 'CABA', 'ciudad autónoma de buenos aires': 'CABA', 'ciudad autonoma de buenos aires': 'CABA',
    'capital federal': 'CABA', 'distrito federal': 'CABA',
    'buenos aires': 'Buenos Aires', 'pba': 'Buenos Aires', 'provincia de buenos aires': 'Buenos Aires', 'bs as': 'Buenos Aires',
    'catamarca': 'Catamarca', 'chaco': 'Chaco', 'chubut': 'Chubut', 'córdoba': 'Córdoba', 'cordoba': 'Córdoba',
    'corrientes': 'Corrientes', 'entre ríos': 'Entre Ríos', 'entre rios': 'Entre Ríos', 'formosa': 'Formosa',
    'jujuy': 'Jujuy', 'la pampa': 'La Pampa', 'la rioja': 'La Rioja', 'mendoza': 'Mendoza', 'misiones': 'Misiones',
    'neuquén': 'Neuquén', 'neuquen': 'Neuquén', 'río negro': 'Río Negro', 'rio negro': 'Río Negro',
    'salta': 'Salta', 'san juan': 'San Juan', 'san luis': 'San Luis', 'santa cruz': 'Santa Cruz',
    'santa fe': 'Santa Fe', 'santiago del estero': 'Santiago del Estero',
    'tierra del fuego': 'Tierra del Fuego', 'tdf': 'Tierra del Fuego', 'tucumán': 'Tucumán', 'tucuman': 'Tucumán'
}
ORDEN_ENVIO = ["Pendiente", "Listo para despachar", "Despachado", "En camino", "En reparto", "Listo para retirar",
               "Intento fallido", "Entregado", "No entregado", "Devolución", "Cancelado"]
COLOR_ENVIO = {"Pendiente": "#F87171", "Listo para despachar": "#FBBF24", "Despachado": "#38BDF8", "En camino": "#22D3EE",
               "En reparto": "#A78BFA", "Listo para retirar": "#818CF8", "Intento fallido": "#F472B6", "Entregado": "#34D399",
               "No entregado": "#EF4444", "Devolución": "#FB923C", "Cancelado": "#64748B"}
ENV_PEND = {"Pendiente", "Listo para despachar"}
ENV_CURSO = {"Despachado", "En camino", "En reparto", "Listo para retirar", "Intento fallido"}
ENV_DESP = ENV_CURSO | {"Entregado", "No entregado", "Devolución"}
ENV_PROB = {"Intento fallido", "No entregado", "Devolución"}
ORDEN_CUOTAS = ["1 pago", "Débito", "2 cuotas", "3 cuotas", "4 cuotas", "6 cuotas", "9 cuotas", "12 cuotas", "18 cuotas"]
SIN_DESCUENTO = {"SIN DESCUENTO", "", "NAN", "NONE"}

# ==============================================================================
# 2. ESTILO
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --card: rgba(15,23,42,.62); --border: rgba(148,163,184,.13); --muted: #8B95A7; --text: #E5E7EB; }
.stApp {
  background:
    radial-gradient(1100px 520px at 0% -10%, rgba(34,211,238,.10), transparent 60%),
    radial-gradient(900px 480px at 100% -5%, rgba(167,139,250,.11), transparent 60%),
    radial-gradient(700px 400px at 60% 110%, rgba(255,230,0,.05), transparent 60%),
    #060A13;
}
html, body, .stApp, .stMarkdown, p, label, input, textarea, button { font-family: 'Inter', sans-serif !important; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1640px; }
section[data-testid="stSidebar"] { background: rgba(6,10,19,.94); border-right: 1px solid var(--border); }

/* HERO */
.hero { display:flex; justify-content:space-between; align-items:flex-end; gap:16px; flex-wrap:wrap;
  padding: 24px 28px; border-radius: 22px; margin-bottom: 18px; border:1px solid var(--border);
  background: linear-gradient(120deg, rgba(34,211,238,.12), rgba(167,139,250,.09) 55%, rgba(255,230,0,.07)); }
.hero-eyebrow { font-size:11px; letter-spacing:3px; text-transform:uppercase; color:var(--muted); font-weight:700; }
.hero-title { font-family:'Space Grotesk', sans-serif; font-size:38px; font-weight:700; line-height:1.05; margin:6px 0 6px;
  background: linear-gradient(90deg,#F8FAFC 10%,#A5F3FC 55%,#FDE68A); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.hero-sub { color:#A3ADBF; font-size:13px; }
.hero-sub b { color:#E5E7EB; font-weight:600; }
.live { display:inline-flex; align-items:center; gap:8px; padding:7px 14px; border-radius:999px; font-size:12px; font-weight:700;
  background:rgba(52,211,153,.10); border:1px solid rgba(52,211,153,.35); color:#6EE7B7; letter-spacing:.5px; }
.live-dot { width:8px; height:8px; border-radius:50%; background:#34D399; animation:pulse 1.8s infinite; }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(52,211,153,.6)} 70%{box-shadow:0 0 0 10px rgba(52,211,153,0)} 100%{box-shadow:0 0 0 0 rgba(52,211,153,0)} }

/* SECCIONES */
.sec { margin: 30px 0 12px; }
.sec-eyebrow { font-size:10.5px; letter-spacing:2.5px; text-transform:uppercase; color:#22D3EE; font-weight:800; }
.sec-title { font-family:'Space Grotesk', sans-serif; font-size:23px; font-weight:700; color:#F8FAFC; margin-top:2px; }
.sec-desc { color:var(--muted); font-size:12.5px; margin-top:3px; }

/* KPI */
.kpi { background:var(--card); border:1px solid var(--border); border-radius:18px; padding:18px 18px 14px; position:relative;
  overflow:hidden; backdrop-filter: blur(10px); height:100%; transition: border-color .2s, transform .2s; }
.kpi:hover { border-color: rgba(34,211,238,.45); transform: translateY(-2px); }
.kpi::before { content:""; position:absolute; left:0; right:0; top:0; height:3px; background: var(--kpi-accent, #22D3EE); }
.kpi::after { content:""; position:absolute; right:-40px; top:-40px; width:120px; height:120px; border-radius:50%;
  background: var(--kpi-accent, #22D3EE); opacity:.07; filter: blur(4px); }
.kpi-label { font-size:11px; text-transform:uppercase; letter-spacing:1.4px; color:var(--muted); font-weight:700; }
.kpi-value { font-family:'Space Grotesk', sans-serif; font-size:clamp(22px, 1.9vw, 30px); font-weight:700; color:#F8FAFC; margin:6px 0 8px; letter-spacing:-.5px; white-space:nowrap; }
.kpi.sm .kpi-value { font-size:clamp(19px, 1.6vw, 24px); }
.delta { display:inline-block; font-size:11.5px; font-weight:700; padding:2px 9px; border-radius:999px; }
.delta.up { color:#34D399; background:rgba(52,211,153,.13); }
.delta.down { color:#F87171; background:rgba(248,113,113,.13); }
.delta.flat { color:var(--muted); background:rgba(148,163,184,.10); }
.delta-cap { font-size:10.5px; color:var(--muted); margin-left:6px; }
.split { display:flex; height:6px; border-radius:999px; overflow:hidden; background:rgba(148,163,184,.12); margin-top:12px; gap:2px; }
.split div { height:100%; border-radius:999px; }
.split-legend { display:flex; justify-content:space-between; font-size:11px; color:#A3ADBF; margin-top:6px; }
.dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:5px; vertical-align:middle; }

/* MARCAS */
.brand { background:var(--card); border:1px solid var(--border); border-radius:18px; padding:16px 16px 14px; height:100%; position:relative; overflow:hidden; }
.brand::before { content:""; position:absolute; left:0; right:0; top:0; height:3px; background: var(--b-accent); }
.brand-name { font-family:'Space Grotesk', sans-serif; font-size:17px; font-weight:700; }
.brand-big { font-family:'Space Grotesk', sans-serif; font-size:25px; font-weight:700; color:#F8FAFC; margin:4px 0 6px; }
.row { display:flex; justify-content:space-between; font-size:12.5px; color:var(--muted); margin:5px 0; }
.row b { color:#E5E7EB; font-weight:600; }
.sep { border-top:1px solid var(--border); margin:9px 0; }

/* PRODUCTOS */
.pgrid { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:14px; }
.prod { background:var(--card); border:1px solid var(--border); border-radius:18px; padding:12px; position:relative; transition: all .2s; display:flex; flex-direction:column; }
.prod:hover { border-color: rgba(34,211,238,.5); transform: translateY(-3px); }
.prod-rank { position:absolute; top:10px; left:10px; z-index:2; font-family:'Space Grotesk', sans-serif; font-weight:700; font-size:12px; padding:2px 9px; border-radius:999px; background:rgba(6,10,19,.85); color:#F8FAFC; border:1px solid var(--border); }
.prod img { width:100%; height:150px; object-fit:contain; background:#fff; border-radius:12px; padding:6px; }
.prod-name { font-size:12px; font-weight:600; color:#E5E7EB; line-height:1.3; height:32px; overflow:hidden; margin:10px 0 8px; }
.prod-stats { display:flex; justify-content:space-between; border-top:1px solid var(--border); padding-top:8px; }
.prod-stats div { font-size:9.5px; color:var(--muted); text-transform:uppercase; font-weight:700; letter-spacing:.6px; }
.prod-stats b { display:block; font-family:'Space Grotesk', sans-serif; font-size:15px; color:#22D3EE; letter-spacing:0; text-transform:none; }
.chips { display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }
.chip { font-size:10.5px; padding:2px 8px; border-radius:999px; background:rgba(148,163,184,.10); color:#CBD5E1; border:1px solid var(--border); }
.prod a { text-decoration:none; }

/* COMBOS */
.combo { display:flex; align-items:center; gap:12px; background:var(--card); border:1px solid var(--border); border-radius:16px; padding:10px 14px; margin-bottom:10px; }
.combo-n { font-family:'Space Grotesk', sans-serif; font-weight:700; color:#22D3EE; font-size:18px; width:34px; text-align:center; }
.combo img { width:62px; height:62px; object-fit:contain; background:#fff; border-radius:10px; padding:3px; }
.combo-plus { color:var(--muted); font-size:20px; font-weight:700; }
.combo-txt { flex:1; font-size:13px; color:#E5E7EB; font-weight:600; line-height:1.45; }
.combo-txt span { color:var(--muted); font-size:11px; font-weight:500; }
.combo-f { text-align:right; font-family:'Space Grotesk', sans-serif; color:#34D399; font-size:19px; font-weight:700; }
.combo-f span { display:block; font-family:'Inter', sans-serif; color:var(--muted); font-size:9.5px; text-transform:uppercase; letter-spacing:.8px; }

/* TABLAS */
.tbl-wrap { background:var(--card); border:1px solid var(--border); border-radius:18px; overflow-x:auto; }
.ftable { width:100%; border-collapse:collapse; font-size:13px; }
.ftable th { color:var(--muted); padding:12px 12px; font-weight:700; font-size:10.5px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid var(--border); text-align:right; white-space:nowrap; }
.ftable th:first-child, .ftable td:first-child { text-align:left; }
.ftable td { padding:11px 12px; border-bottom:1px solid rgba(148,163,184,.07); color:#E5E7EB; text-align:right; white-space:nowrap; }
.ftable tr:last-child td { border-bottom:none; }
.ftable tr:hover td { background:rgba(34,211,238,.05); }
.ftable td.strong { font-weight:700; color:#F8FAFC; }
.ftable tr.total td { font-weight:800; color:#F8FAFC; background:rgba(148,163,184,.06); }
.pill { display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px; font-weight:700; }
.pill.ok { background:rgba(52,211,153,.14); color:#34D399; }
.pill.warn { background:rgba(251,191,36,.14); color:#FBBF24; }
.pill.bad { background:rgba(248,113,113,.14); color:#F87171; }

/* TABS (selectores por rol: funcionan en versiones nuevas y viejas de Streamlit) */
.stTabs [role="tablist"] { gap:6px; background:rgba(15,23,42,.7); padding:6px; border-radius:16px; border:1px solid var(--border); flex-wrap:wrap; }
.stTabs [role="tab"] { height:42px; padding:0 18px; border-radius:11px; color:var(--muted); font-weight:600; background:transparent; display:flex; align-items:center; border:none !important; }
.stTabs [role="tab"] p { font-weight:600; font-size:14px; }
.stTabs [role="tab"]:hover { color:#E5E7EB; background:rgba(148,163,184,.08); }
.stTabs [role="tab"][aria-selected="true"] { background:linear-gradient(135deg, rgba(34,211,238,.24), rgba(167,139,250,.24)) !important; color:#F8FAFC !important; box-shadow: inset 0 0 0 1px rgba(34,211,238,.35); }
.stTabs [role="tab"][aria-selected="true"] p { color:#F8FAFC; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }
.stTabs [role="tabpanel"] { padding-top: 6px; }

/* TAGS DEL MULTISELECT */
[data-testid="stMultiSelectTagsContainer"] [data-tag], span[data-baseweb="tag"] {
  background: rgba(34,211,238,.14) !important; color:#A5F3FC !important; border:1px solid rgba(34,211,238,.35) !important; border-radius:8px !important; }

/* GRÁFICOS COMO CARDS */
div[data-testid="stPlotlyChart"] { background:var(--card); border:1px solid var(--border); border-radius:18px; padding:6px 4px 2px; }
div[data-testid="stExpander"] details { background:var(--card); border:1px solid var(--border); border-radius:16px; }
.scope-head { display:flex; align-items:center; gap:8px; font-family:'Space Grotesk', sans-serif; font-weight:700; font-size:16px; color:#F8FAFC; margin:6px 0 8px; }

@media (max-width: 900px) {
  .pgrid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .hero-title { font-size:28px; }
  .kpi-value { font-size:24px; }
  .block-container { padding-left:.8rem; padding-right:.8rem; }
}
</style>
""", unsafe_allow_html=True)

pio.templates["distri"] = go.layout.Template(layout=dict(
    font=dict(family="Inter, sans-serif", color="#A3ADBF", size=12),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", separators=",.",
    colorway=["#22D3EE", "#FFE600", "#A78BFA", "#34D399", "#F472B6", "#FBBF24", "#38BDF8", "#F87171"],
    xaxis=dict(gridcolor="rgba(148,163,184,.08)", zerolinecolor="rgba(148,163,184,.15)", linecolor="rgba(148,163,184,.15)"),
    yaxis=dict(gridcolor="rgba(148,163,184,.08)", zerolinecolor="rgba(148,163,184,.15)", linecolor="rgba(148,163,184,.15)"),
    legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="center", x=0.5, bgcolor="rgba(0,0,0,0)", title_text=""),
    hoverlabel=dict(bgcolor="#0F172A", bordercolor="#334155", font=dict(color="#E5E7EB", family="Inter")),
    title=dict(font=dict(family="Space Grotesk, sans-serif", size=15, color="#E5E7EB"), x=0.02, y=0.96),
    margin=dict(l=12, r=12, t=52, b=12),
))


def estilo(fig, h=360):
    fig.update_layout(template="distri", height=h, legend_title_text="", uniformtext_minsize=9, uniformtext_mode="hide")
    return fig


# ==============================================================================
# 3. FORMATO Y COMPONENTES
# ==============================================================================
def fmt_ars(v):
    return "$" + f"{v:,.0f}".replace(",", ".")


def fmt_kpi(v):
    """Montos de tarjetas: completos hasta 999 M; desde mil millones, en millones."""
    return fmt_ars(v) if abs(v) < 1e9 else "$" + fmt_num(v / 1e6) + " M"


def fmt_num(v):
    return f"{v:,.0f}".replace(",", ".")


def fmt_dec(v, n=1):
    return f"{v:.{n}f}".replace(".", ",")


def fmt_compact(v, moneda=True):
    p = "$" if moneda else ""
    a = abs(v)
    if a >= 1e9:
        return p + fmt_dec(v / 1e9, 2) + " MM"
    if a >= 1e6:
        return p + fmt_dec(v / 1e6, 1) + " M"
    if a >= 1e4:
        return p + fmt_num(v / 1e3) + " K"
    return p + fmt_num(v)


def delta_html(cur, prev, invert=False, pp=False, cap="vs período anterior"):
    if prev is None or (not pp and prev <= 0):
        return "<span class='delta flat'>sin comparación</span>"
    d = (cur - prev) if pp else (cur - prev) / prev * 100
    bueno = d <= 0 if invert else d >= 0
    cls = "flat" if abs(d) < 0.05 else ("up" if bueno else "down")
    flecha = "▲" if d > 0 else ("▼" if d < 0 else "•")
    return f"<span class='delta {cls}'>{flecha} {fmt_dec(abs(d))}{' pp' if pp else '%'}</span><span class='delta-cap'>{cap}</span>"


def split_html(vals):
    tot = sum(v for v in vals.values() if v > 0)
    if tot <= 0:
        return ""
    segs = "".join(f"<div style='width:{v / tot * 100:.2f}%;background:{COLOR_CANAL[c]}'></div>"
                   for c, v in vals.items() if v > 0)
    leg = "".join(f"<span><span class='dot' style='background:{COLOR_CANAL[c]}'></span>{CORTO[c]} {v / tot * 100:.0f}%</span>"
                  for c, v in vals.items())
    return f"<div class='split'>{segs}</div><div class='split-legend'>{leg}</div>"


def kpi_card(label, valor, delta="", split="", accent="#22D3EE", sm=False):
    return (f"<div class='kpi{' sm' if sm else ''}' style='--kpi-accent:{accent}'><div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{valor}</div><div>{delta}</div>{split}</div>")


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def seccion(eyebrow, titulo, desc=""):
    d = f"<div class='sec-desc'>{desc}</div>" if desc else ""
    html(f"<div class='sec'><div class='sec-eyebrow'>{eyebrow}</div><div class='sec-title'>{titulo}</div>{d}</div>")


def selector_canal(key, label="Canal"):
    v = st.segmented_control(label, OPC_CANAL, default="Consolidado", key=key)
    return v or "Consolidado"


def por_canal(d, sel):
    return d if sel == "Consolidado" else d[d["canal"] == sel]


def img_azure(marca, modelo_color):
    mc = str(modelo_color).strip().upper()
    if mc in ("", "NAN", "NONE", "S/D"):
        return "https://via.placeholder.com/150"
    return f"https://distriecomm.blob.core.windows.net/catalogo/{str(marca).strip()}/{mc}-1.jpg"


def primer_link(serie):
    urls = [u for u in serie.astype(str) if u.startswith("http") and not u.endswith("/#")]
    propias = [u for u in urls if "mercadolibre" not in u]
    return (propias or urls or ["#"])[0]


def a_str(d):
    d = d.copy()
    for c in d.columns:
        if isinstance(d[c].dtype, pd.CategoricalDtype):
            d[c] = d[c].astype(str)
    return d


# ==============================================================================
# 4. DATOS
# ==============================================================================
def _gh_token():
    try:
        return st.secrets["GH_TOKEN"]
    except Exception:
        return None


def leer_csv_repo(nombre):
    url = f"https://raw.githubusercontent.com/{REPO_DATOS}/main/{nombre}?t={int(time.time() // 60)}"
    tok = _gh_token()
    r = requests.get(url, headers={"Authorization": f"token {tok}"} if tok else {}, timeout=60)
    if r.status_code != 200 and tok:
        r = requests.get(url, timeout=60)
    if r.status_code != 200:
        return pd.DataFrame()
    return pd.read_csv(io.BytesIO(r.content), low_memory=False)


def norm_medio(v):
    s = str(v).lower()
    if "meli" in s:
        if "credit" in s:
            return "MeLi · Tarjeta de crédito"
        if "debit" in s:
            return "MeLi · Débito"
        if "account_money" in s:
            return "MeLi · Dinero en cuenta"
        if "ticket" in s or "atm" in s:
            return "MeLi · Efectivo"
        if "digital_currency" in s:
            return "MeLi · Mercado Crédito"
        if "transfer" in s:
            return "MeLi · Transferencia"
        return "MeLi · Otros"
    if "reversso" in s:
        return "Reversso"
    if "mercado pago" in s or "mercadopago" in s:
        return "Mercado Pago"
    if "mobbex" in s:
        return "Mobbex"
    if "transfer" in s:
        return "Transferencia"
    return "Otros"


def norm_cuotas(v):
    s = str(v).lower()
    if "déb" in s or "deb" in s:
        return "Débito"
    m = re.search(r"(\d+)\s*cuota", s)
    if m:
        n = int(m.group(1))
        return "1 pago" if n <= 1 else f"{n} cuotas"
    return "1 pago"


@st.cache_data(ttl=60, show_spinner="Cargando ventas…")
def load_data():
    partes = []
    for nombre, canal in [("ventas_hot_sale.csv", "Tienda Online"), ("ventas_meli.csv", "MercadoLibre")]:
        try:
            d = leer_csv_repo(nombre)
        except Exception:
            d = pd.DataFrame()
        if not d.empty:
            d["canal"] = canal
            partes.append(d)
    if not partes:
        return pd.DataFrame()
    df = pd.concat(partes, ignore_index=True)

    if "total_orden" in df.columns and "total_pedido" not in df.columns:
        df = df.rename(columns={"total_orden": "total_pedido"})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", format="mixed", utc=True).dt.tz_convert(ZONA_AR)
    df = df.dropna(subset=["fecha"])

    for c in ["total_pedido", "subtotal_producto", "comision_meli", "cantidad", "es_reverso"]:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    if df["subtotal_producto"].sum() == 0:
        df["subtotal_producto"] = df["total_pedido"] / df.groupby("id_pedido")["id_pedido"].transform("count")

    textos = {"medio_pago": "DESCONOCIDO", "cuotas": "1 Cuota / Otro", "descuento": "SIN DESCUENTO",
              "provincia": "Buenos Aires", "tags": "", "url_web": "#", "fulfillment_status": "pending",
              "sku": "S/D", "producto": "S/D", "cliente": "", "envio_detalle": "", "transportista": "", "nro_pedido": ""}
    for c, default in textos.items():
        if c not in df.columns:
            df[c] = default
        df[c] = df[c].fillna(default).astype(str)
    if "producto_base" not in df.columns:
        df["producto_base"] = df["producto"].str.split(" / ").str[0]
    if "modelo_color" not in df.columns:
        df["modelo_color"] = df["sku"].str.rsplit("-", n=1).str[0]
    ids_url = df["url_web"].str.extract(r"(MLA)-?(\d+)").fillna("").agg("".join, axis=1)
    if "item_id" not in df.columns:
        df["item_id"] = ids_url
    else:
        df["item_id"] = df["item_id"].fillna("").astype(str)
        df.loc[df["item_id"] == "", "item_id"] = ids_url
    df["producto_base"] = df["producto_base"].fillna("S/D").astype(str)
    df["modelo_color"] = df["modelo_color"].fillna("S/D").astype(str)

    df["es_reverso"] = (df["es_reverso"].astype(bool)
                        | df["tags"].str.lower().str.contains("reversso", na=False)
                        | df["medio_pago"].str.lower().str.contains("reversso", na=False)).astype("int8")

    fd = df["fecha_despacho"] if "fecha_despacho" in df.columns else pd.Series(pd.NaT, index=df.index)
    df["fecha_despacho"] = pd.to_datetime(fd, errors="coerce", format="mixed", utc=True).dt.tz_convert(ZONA_AR)

    prov = df["provincia"].str.strip()
    df["provincia"] = prov.str.lower().map(PROVINCIAS_MAPA).fillna(prov.str.title())
    df["descuento"] = df["descuento"].str.strip().str.upper()
    df["medio_grupo"] = df["medio_pago"].map({v: norm_medio(v) for v in df["medio_pago"].unique()})
    df["cuotas_grupo"] = df["cuotas"].map({v: norm_cuotas(v) for v in df["cuotas"].unique()})
    df["estado"] = df["fulfillment_status"].str.lower().map(ESTADO_MAPA).fillna("Pendiente")
    # Estado detallado del envío (si el extractor todavía no lo trae, se deduce del fulfillment)
    deducido = df["fulfillment_status"].str.lower().map({"fulfilled": "Despachado", "partial": "Despachado",
                                                         "restocked": "Devolución"}).fillna("Pendiente")
    deducido = deducido.where(~((df["canal"] == "MercadoLibre") & (df["fulfillment_status"] == "unfulfilled")), "Cancelado")
    if "envio_estado" in df.columns:
        df["envio_estado"] = df["envio_estado"].fillna(deducido).replace("", np.nan).fillna(deducido)
    else:
        df["envio_estado"] = deducido
    fe = df["fecha_entrega"] if "fecha_entrega" in df.columns else pd.Series(pd.NaT, index=df.index)
    df["fecha_entrega"] = pd.to_datetime(fe, errors="coerce", format="mixed", utc=True).dt.tz_convert(ZONA_AR)
    df["nro_pedido"] = df["nro_pedido"].where(df["nro_pedido"] != "", df["id_pedido"].astype(str))
    df["dia"] = df["fecha"].dt.date
    df["cantidad"] = df["cantidad"].astype("int32")

    for c in ["marca", "canal", "medio_pago", "medio_grupo", "cuotas", "cuotas_grupo", "descuento", "provincia", "estado",
              "envio_estado", "transportista"]:
        df[c] = df[c].astype("category")
    return df


@st.cache_data(ttl=240, show_spinner=False)
def estado_robot():
    """Mira la última corrida del robot de ventas. GitHub no garantiza el cron de 5 min (a veces pasa horas
    sin correr), así que si la última corrida tiene más de 10 min y no hay otra en curso, la dispara.
    Está cacheado 4 min y compartido entre todos los usuarios: a lo sumo un disparo cada 4 min."""
    tok = _gh_token()
    if not tok:
        return None
    h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    base = f"https://api.github.com/repos/{REPO_DATOS}/actions/workflows/{WORKFLOW_ID}"
    try:
        runs = requests.get(f"{base}/runs", params={"per_page": 5}, headers=h, timeout=10).json().get("workflow_runs", [])
        if not runs:
            return None
        activo = any(x.get("status") in ("queued", "in_progress", "waiting", "pending", "requested") for x in runs)
        ok = [x for x in runs if x.get("conclusion") == "success"]
        ult_ok = pd.Timestamp(ok[0]["updated_at"]).tz_convert(ZONA_AR) if ok else None
        disparado = False
        if not activo and (pd.Timestamp.now(tz="UTC") - pd.Timestamp(runs[0]["created_at"])).total_seconds() > 600:
            disparado = requests.post(f"{base}/dispatches", headers=h, json={"ref": "main"}, timeout=10).status_code == 204
        return {"ult_ok": ult_ok, "activo": activo or disparado}
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def load_aux(nombre):
    """CSVs secundarios (catálogo, publicaciones, clientes). Si no existen todavía, vuelve vacío."""
    try:
        return leer_csv_repo(nombre)
    except Exception:
        return pd.DataFrame()


COLS_PED = ["canal", "marca", "id_pedido", "fecha", "dia", "total_pedido", "es_reverso", "unidades", "medio_grupo",
            "cuotas_grupo", "provincia", "estado", "fecha_despacho", "comision", "cliente", "envio_estado", "envio_detalle",
            "fecha_entrega", "transportista", "nro_pedido"]


def a_pedidos(d):
    """Una fila por pedido (canal + marca + id)."""
    if d.empty:
        return pd.DataFrame(columns=COLS_PED)
    return d.groupby(["canal", "marca", "id_pedido"], observed=True, sort=False).agg(
        fecha=("fecha", "first"), dia=("dia", "first"), total_pedido=("total_pedido", "first"),
        es_reverso=("es_reverso", "max"), unidades=("cantidad", "sum"), medio_grupo=("medio_grupo", "first"),
        cuotas_grupo=("cuotas_grupo", "first"), provincia=("provincia", "first"), estado=("estado", "first"),
        fecha_despacho=("fecha_despacho", "first"), comision=("comision_meli", "sum"), cliente=("cliente", "first"),
        envio_estado=("envio_estado", "first"), envio_detalle=("envio_detalle", "first"), fecha_entrega=("fecha_entrega", "first"),
        transportista=("transportista", "first"), nro_pedido=("nro_pedido", "first"),
    ).reset_index()


def resumen(Pd):
    fact = float(Pd["total_pedido"].sum()) if len(Pd) else 0.0
    ords = int(len(Pd))
    un = int(Pd["unidades"].sum()) if len(Pd) else 0
    return {"fact": fact, "ords": ords, "un": un, "tkt": fact / ords if ords else 0.0}


def por_canal_vals(Pd, campo):
    if Pd.empty:
        return {c: 0 for c in CANALES}
    s = Pd.groupby("canal", observed=True).size() if campo == "ords" else Pd.groupby("canal", observed=True)[campo].sum()
    return {c: float(s.get(c, 0)) for c in CANALES}


# ==============================================================================
# 5. OBJETIVOS (se guardan en el repo de datos → no se pierden al reiniciar la app)
# ==============================================================================
def normalizar_obj(o):
    o = o or {}
    base = {c: o.get(c, {}) for c in CANALES} if any(k in o for k in CANALES) else {"Tienda Online": o, "MercadoLibre": {}}
    return {c: {m: {"unidades": int((v or {}).get("unidades", 0) or 0), "facturacion": int((v or {}).get("facturacion", 0) or 0)}
                for m, v in (base.get(c) or {}).items()} for c in CANALES}


def _gh_headers():
    h = {"Accept": "application/vnd.github+json"}
    tok = _gh_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


@st.cache_data(ttl=120, show_spinner=False)
def load_objetivos():
    try:
        r = requests.get(f"https://api.github.com/repos/{REPO_DATOS}/contents/{OBJ_ARCHIVO_REPO}",
                         headers=_gh_headers(), timeout=20)
        if r.status_code == 200:
            return normalizar_obj(json.loads(base64.b64decode(r.json()["content"]))), "repo"
    except Exception:
        pass
    if os.path.exists("objetivos_hot_sale.json"):
        try:
            with open("objetivos_hot_sale.json", "r") as f:
                return normalizar_obj(json.load(f)), "local"
        except Exception:
            pass
    return normalizar_obj({}), "vacío"


def guardar_objetivos(data):
    if not _gh_token():
        return False, "Falta GH_TOKEN en los secrets de Streamlit."
    url = f"https://api.github.com/repos/{REPO_DATOS}/contents/{OBJ_ARCHIVO_REPO}"
    try:
        sha = None
        r = requests.get(url, headers=_gh_headers(), timeout=20)
        if r.status_code == 200:
            sha = r.json().get("sha")
        body = {"message": "🎯 Metas actualizadas desde el dashboard",
                "content": base64.b64encode(json.dumps(data, indent=2, ensure_ascii=False).encode()).decode(),
                "branch": "main"}
        if sha:
            body["sha"] = sha
        r = requests.put(url, headers=_gh_headers(), json=body, timeout=20)
        if r.status_code in (200, 201):
            return True, "ok"
        return False, f"GitHub {r.status_code}: {r.json().get('message', '')}"
    except Exception as e:
        return False, str(e)


def meta(obj, scope, marcas, campo):
    canales = CANALES if scope == "General" else [scope]
    return sum(obj.get(c, {}).get(m, {}).get(campo, 0) for c in canales for m in marcas)


def gauge(valor, objetivo, titulo, color, moneda=False):
    pct = valor / objetivo * 100 if objetivo > 0 else 0
    col_pct = "#34D399" if pct >= 90 else ("#FBBF24" if pct >= 50 else "#F87171")
    sub = (f"<span style='font-size:12px;color:{col_pct}'>{fmt_dec(pct)}% de {fmt_compact(objetivo, moneda)}</span>"
           if objetivo > 0 else "<span style='font-size:12px;color:#8B95A7'>Sin meta cargada</span>")
    tope = max(objetivo * 1.2, valor * 1.05, 1)
    fig = go.Figure(go.Indicator(
        mode="gauge", value=valor, domain=dict(x=[0, 1], y=[0.12, 1]),
        title=dict(text=f"{titulo}<br>{sub}", font=dict(size=13, color="#CBD5E1")),
        gauge=dict(shape="angular", axis=dict(range=[0, tope], visible=False),
                   bar=dict(color=color, thickness=0.3), bgcolor="rgba(148,163,184,.10)", borderwidth=0,
                   threshold=dict(line=dict(color="#F8FAFC", width=3 if objetivo > 0 else 0), thickness=0.95,
                                  value=objetivo if objetivo > 0 else 0)),
    ))
    txt = fmt_kpi(valor) if moneda else f"{fmt_num(valor)} un."
    fig.add_annotation(x=0.5, y=0.08, xref="paper", yref="paper", showarrow=False, text=f"<b>{txt}</b>",
                       font=dict(size=22, family="Space Grotesk, sans-serif", color="#F8FAFC"))
    fig.update_layout(height=235, margin=dict(l=24, r=24, t=62, b=6), paper_bgcolor="rgba(0,0,0,0)",
                      separators=",.", font=dict(family="Inter"))
    return fig


# ==============================================================================
# 6. LOGIN (usuarios y contraseñas cifradas en los secrets de Streamlit)
# ==============================================================================
def _usuarios():
    try:
        return {k.lower(): dict(v) for k, v in st.secrets["usuarios"].items()}
    except Exception:
        return {}


def _hash(usuario, clave):
    return hashlib.pbkdf2_hmac("sha256", clave.encode(), ("distrinando:" + usuario.lower()).encode(), 200_000).hex()


def pantalla_login():
    html("""<style>
      section[data-testid="stSidebar"], header[data-testid="stHeader"] { display:none; }
      .block-container { max-width: 460px !important; padding-top: 9vh !important; }
      div[data-testid="stForm"] { background: rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.16);
        border-radius:22px; padding: 26px 26px 18px; backdrop-filter: blur(10px); }
    </style>""")
    html("<div style='text-align:center;margin-bottom:22px'>"
         "<div style='font-family:Space Grotesk, sans-serif;font-size:30px;font-weight:700;letter-spacing:2px;color:#F8FAFC'>DISTRINANDO</div>"
         "<div style='font-size:11px;color:#8B95A7;letter-spacing:3px;text-transform:uppercase;margin-top:4px'>E-commerce · Centro de Comando</div></div>")
    usuarios = _usuarios()
    bloqueado_hasta = st.session_state.get("login_bloqueo", 0)
    with st.form("login", clear_on_submit=False):
        u = st.text_input("Usuario", placeholder="Tu usuario")
        c = st.text_input("Contraseña", type="password", placeholder="••••••••")
        ok = st.form_submit_button("Ingresar", type="primary", width="stretch", icon=":material/login:")
    if not usuarios:
        st.error("No hay usuarios configurados (falta la sección [usuarios] en los secrets de Streamlit).")
        return
    if ok:
        if time.time() < bloqueado_hasta:
            st.error(f"Demasiados intentos. Esperá {int(bloqueado_hasta - time.time())} segundos.")
            return
        datos = usuarios.get(u.strip().lower())
        if datos and hmac.compare_digest(_hash(u.strip(), c), str(datos.get("hash", ""))):
            st.session_state["auth"] = {"usuario": u.strip().lower(), "nombre": datos.get("nombre", u),
                                        "rol": datos.get("rol", "usuario")}
            st.session_state.pop("login_fallos", None)
            st.rerun()
        else:
            fallos = st.session_state.get("login_fallos", 0) + 1
            st.session_state["login_fallos"] = fallos
            if fallos >= 5:
                st.session_state["login_bloqueo"] = time.time() + 60
                st.session_state["login_fallos"] = 0
            st.error("Usuario o contraseña incorrectos.")


if "auth" not in st.session_state:
    pantalla_login()
    st.stop()

AUTH = st.session_state["auth"]
ES_ADMIN = AUTH["rol"] == "admin"
st_autorefresh(interval=300000, limit=None, key="auto_refresh")


# ==============================================================================
# 7. APP
# ==============================================================================
try:
    df_raw = load_data()
except Exception as e:
    st.error(f"No se pudieron cargar los datos: {e}")
    st.stop()
if df_raw.empty:
    st.warning("⚠️ No se encontró la base de datos.")
    st.stop()

ahora = datetime.now(ZONA_AR)
hoy = ahora.date()
f_min = df_raw["dia"].min()

# ---------------- SIDEBAR ----------------
with st.sidebar:
    html("<div style='font-family:Space Grotesk, sans-serif;font-size:22px;font-weight:700;color:#F8FAFC;letter-spacing:1px'>DISTRINANDO</div>"
         "<div style='font-size:11px;color:#8B95A7;letter-spacing:2px;text-transform:uppercase;margin-bottom:14px'>E-commerce · Analytics</div>")
    marcas_disp = sorted(map(str, df_raw["marca"].unique()))
    marcas_sel = st.multiselect("Marcas", marcas_disp, default=marcas_disp) or marcas_disp

    periodo = st.segmented_control("Período", ["Hoy", "7D", "30D", "Todo", "Rango"], default="30D", key="periodo") or "30D"
    if periodo == "Hoy":
        d0, d1 = hoy, hoy
    elif periodo == "7D":
        d0, d1 = hoy - timedelta(days=6), hoy
    elif periodo == "30D":
        d0, d1 = hoy - timedelta(days=29), hoy
    elif periodo == "Rango":
        r = st.date_input("Desde / Hasta", [max(f_min, hoy - timedelta(days=29)), hoy],
                          min_value=f_min, max_value=hoy, key="rango_custom")
        d0, d1 = (r[0], r[1]) if len(r) == 2 else (r[0], r[0])
    else:
        d0, d1 = f_min, hoy
    d0 = max(d0, f_min)

    st.divider()
    rol_txt = "Super admin" if ES_ADMIN else "Usuario"
    html(f"<div class='row' style='margin-bottom:6px'><span>👤 <b style='color:#F8FAFC'>{AUTH['nombre']}</b></span>"
         f"<span class='chip'>{rol_txt}</span></div>")
    if st.button("Cerrar sesión", width="stretch", icon=":material/logout:"):
        st.session_state.pop("auth", None)
        st.rerun()
    st.divider()
    html("<div class='kpi-label' style='margin-bottom:8px'>Última venta registrada</div>")
    for c in CANALES:
        sub = df_raw[df_raw["canal"] == c]
        txt = sub["fecha"].max().strftime("%d/%m %H:%M") + " hs" if not sub.empty else "sin datos"
        html(f"<div class='row'><span><span class='dot' style='background:{COLOR_CANAL[c]}'></span>{c}</span><b>{txt}</b></div>")

    rb = estado_robot()
    if rb and rb.get("ult_ok") is not None:
        mins = int((ahora - rb["ult_ok"]).total_seconds() // 60)
        hace = f"hace {mins} min" if mins < 120 else f"hace {mins // 60} h"
        estado_txt = "<span class='chip' style='color:#FBBF24'>actualizando…</span>" if rb["activo"] else ""
        html(f"<div class='row' style='margin-top:8px'><span>🔄 Datos actualizados {hace}</span>{estado_txt}</div>")
    st.write("")
    if st.button("Actualizar datos ahora", type="primary", width="stretch", icon=":material/sync:"):
        tok = _gh_token()
        if not tok:
            st.error("Falta GH_TOKEN en los secrets.")
        else:
            res = requests.post(f"https://api.github.com/repos/{REPO_DATOS}/actions/workflows/{WORKFLOW_ID}/dispatches",
                                headers={"Authorization": f"token {tok}", "Accept": "application/vnd.github.v3+json"},
                                json={"ref": "main"}, timeout=20)
            if res.status_code == 204:
                st.cache_data.clear()
                st.toast("Extracción lanzada. Los datos nuevos aparecen en ~2 minutos.", icon="⏳")
            else:
                st.error(f"Error GitHub ({res.status_code})")

# ---------------- BASES ----------------
base_m = df_raw[df_raw["marca"].isin(marcas_sel)]
base_net = base_m[base_m["es_reverso"] == 0]
en_rango = base_m[(base_m["dia"] >= d0) & (base_m["dia"] <= d1)]
df_f = en_rango[en_rango["es_reverso"] == 0]
P_all = a_pedidos(en_rango)
P = P_all[P_all["es_reverso"] == 0]

n_dias = (d1 - d0).days + 1
p0, p1 = d0 - timedelta(days=n_dias), d0 - timedelta(days=1)
P_prev_all = a_pedidos(base_m[(base_m["dia"] >= p0) & (base_m["dia"] <= p1)])
P_prev = P_prev_all[P_prev_all["es_reverso"] == 0]
hay_prev = (not P_prev.empty) and p0 >= f_min

# ---------------- HERO ----------------
rango_txt = f"{d0:%d/%m}" if d0 == d1 else f"{d0:%d/%m} → {d1:%d/%m/%Y}"
canales_con_datos = [c for c in CANALES if (df_raw["canal"] == c).any()]
html("<div class='hero'><div><div class='hero-eyebrow'>Distrinando · E-commerce</div>"
     "<div class='hero-title'>Centro de Comando</div>"
     f"<div class='hero-sub'>Venta neta consolidada · <b>{' + '.join(canales_con_datos)}</b> · <b>{len(marcas_sel)}</b> marcas · <b>{rango_txt}</b></div></div>"
     f"<div class='live'><span class='live-dot'></span>EN VIVO · {ahora:%H:%M} hs</div></div>")

if P.empty:
    st.info("No hay ventas para los filtros seleccionados.")
    st.stop()

_tabs = [":material/space_dashboard: Resumen", ":material/flag: Metas & Forecast", ":material/local_mall: Productos",
         ":material/inventory_2: Stock & Publicaciones", ":material/payments: Comercial", ":material/campaign: Publicidad MeLi",
         ":material/group: Clientes"]
if ES_ADMIN:  # Operaciones (logística) solo para super admins
    _tabs.append(":material/local_shipping: Operaciones")
_t = st.tabs(_tabs)
tab_res, tab_metas, tab_prod, tab_stock, tab_com, tab_ads, tab_cli = _t[:7]
tab_ops = _t[7] if ES_ADMIN else None

# ==============================================================================
# TAB 1 · RESUMEN
# ==============================================================================
with tab_res:
    # ---------- HOY ----------
    P_hoy_all = a_pedidos(base_m[base_m["dia"] == hoy])
    P_hoy = P_hoy_all[P_hoy_all["es_reverso"] == 0]
    P_ayer = a_pedidos(base_net[(base_net["dia"] == hoy - timedelta(days=1)) & (base_net["fecha"] <= ahora - timedelta(days=1))])
    seccion("En vivo", f"Actividad de hoy · {hoy:%d/%m/%Y}", "Comparado contra ayer hasta la misma hora.")
    if P_hoy.empty:
        st.info("Todavía no hay ventas netas hoy para las marcas seleccionadas.")
    else:
        h = resumen(P_hoy)
        a = resumen(P_ayer) if not P_ayer.empty else None
        av = (lambda key: a[key]) if a else (lambda key: None)
        pico = int(P_hoy["fecha"].dt.hour.value_counts().idxmax())
        cols = st.columns(5)
        cols[0].markdown(kpi_card("Facturación hoy", fmt_kpi(h["fact"]), delta_html(h["fact"], av("fact"), cap="vs ayer"),
                                  split_html(por_canal_vals(P_hoy, "total_pedido")), "#22D3EE", sm=True), unsafe_allow_html=True)
        cols[1].markdown(kpi_card("Órdenes", fmt_num(h["ords"]), delta_html(h["ords"], av("ords"), cap="vs ayer"),
                                  split_html(por_canal_vals(P_hoy, "ords")), "#A78BFA", sm=True), unsafe_allow_html=True)
        cols[2].markdown(kpi_card("Unidades", fmt_num(h["un"]), delta_html(h["un"], av("un"), cap="vs ayer"),
                                  split_html(por_canal_vals(P_hoy, "unidades")), "#34D399", sm=True), unsafe_allow_html=True)
        cols[3].markdown(kpi_card("Ticket promedio", fmt_ars(h["tkt"]), delta_html(h["tkt"], av("tkt"), cap="vs ayer"),
                                  "", "#FBBF24", sm=True), unsafe_allow_html=True)
        cols[4].markdown(kpi_card("Hora pico", f"{pico:02d}:00 hs", "<span class='delta flat'>más órdenes del día</span>", "",
                                  "#F472B6", sm=True), unsafe_allow_html=True)

    # ---------- KPIs PERÍODO ----------
    seccion("Consolidado", "Indicadores del período",
            f"Tienda Online + MercadoLibre · {rango_txt} · comparado con los {n_dias} días anteriores.")
    k, kp = resumen(P), resumen(P_prev)
    dev = P_all["es_reverso"].mean() * 100 if len(P_all) else 0
    dev_prev = P_prev_all["es_reverso"].mean() * 100 if (hay_prev and len(P_prev_all)) else None
    pv = (lambda key: kp[key]) if hay_prev else (lambda key: None)
    cols = st.columns(5)
    cols[0].markdown(kpi_card("Facturación neta", fmt_kpi(k["fact"]), delta_html(k["fact"], pv("fact")),
                              split_html(por_canal_vals(P, "total_pedido")), "#22D3EE"), unsafe_allow_html=True)
    cols[1].markdown(kpi_card("Órdenes netas", fmt_num(k["ords"]), delta_html(k["ords"], pv("ords")),
                              split_html(por_canal_vals(P, "ords")), "#A78BFA"), unsafe_allow_html=True)
    cols[2].markdown(kpi_card("Unidades netas", fmt_num(k["un"]), delta_html(k["un"], pv("un")),
                              split_html(por_canal_vals(P, "unidades")), "#34D399"), unsafe_allow_html=True)
    fv, ov = por_canal_vals(P, "total_pedido"), por_canal_vals(P, "ords")
    tk_txt = "".join(f"<span><span class='dot' style='background:{COLOR_CANAL[c]}'></span>{CORTO[c]} {fmt_compact(fv[c] / ov[c]) if ov[c] else '—'}</span>"
                     for c in CANALES)
    cols[3].markdown(kpi_card("Ticket promedio", fmt_ars(k["tkt"]), delta_html(k["tkt"], pv("tkt")),
                              f"<div class='split-legend' style='margin-top:14px'>{tk_txt}</div>", "#FBBF24"), unsafe_allow_html=True)
    cols[4].markdown(kpi_card("Tasa de devolución", f"{fmt_dec(dev, 2)}%", delta_html(dev, dev_prev, invert=True, pp=True),
                              "", "#F87171"), unsafe_allow_html=True)

    # ---------- CANALES ----------
    seccion("Canales", "Tienda Online vs. MercadoLibre", "Participación, facturación por marca y costo de comisiones de MeLi.")
    c1, c2, c3 = st.columns([1, 1.7, 1.1])
    with c1:
        sh = a_str(P.groupby("canal", observed=True)["total_pedido"].sum().reset_index())
        fig = px.pie(sh, values="total_pedido", names="canal", hole=0.68, color="canal", color_discrete_map=COLOR_CANAL,
                     title="Share de facturación")
        fig.update_traces(textinfo="percent", textfont=dict(size=14, family="Space Grotesk", color="#060A13"),
                          marker=dict(line=dict(color="#060A13", width=3)), hovertemplate="%{label}<br>$%{value:,.0f}<extra></extra>")
        fig.add_annotation(text=f"<b>{fmt_compact(k['fact'])}</b><br><span style='font-size:11px;color:#8B95A7'>total</span>",
                           showarrow=False, font=dict(size=18, family="Space Grotesk", color="#F8FAFC"))
        st.plotly_chart(estilo(fig, 340), width="stretch")
    with c2:
        mc = a_str(P.groupby(["marca", "canal"], observed=True)["total_pedido"].sum().reset_index())
        mc["txt"] = mc["total_pedido"].map(fmt_compact)
        fig = px.bar(mc, x="marca", y="total_pedido", color="canal", barmode="group", color_discrete_map=COLOR_CANAL,
                     title="Facturación por marca y canal", text="txt")
        fig.update_traces(marker_line_width=0, textfont_size=11, hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>")
        fig.update_layout(xaxis_title="", yaxis_title="", bargap=0.25)
        st.plotly_chart(estilo(fig, 340), width="stretch")
    with c3:
        Pm = P[P["canal"] == "MercadoLibre"]
        if Pm.empty:
            html(kpi_card("Comisiones MeLi", "—", "<span class='delta flat'>sin ventas MeLi en el período</span>", "", "#FFE600"))
        else:
            com, fm = Pm["comision"].sum(), Pm["total_pedido"].sum()
            html(kpi_card("Comisiones MeLi", fmt_kpi(com),
                          f"<span class='delta down'>{fmt_dec(com / fm * 100 if fm else 0)}% de la venta</span>",
                          f"<div class='split-legend' style='margin-top:12px'><span>Neto MeLi</span><b style='color:#34D399'>{fmt_ars(fm - com)}</b></div>",
                          "#FFE600", sm=True))
            cm = Pm.groupby("marca", observed=True)[["comision", "total_pedido"]].sum()
            cm = a_str((cm["comision"] / cm["total_pedido"] * 100).round(1).rename("pct").reset_index().dropna())
            fig = px.bar(cm, y="marca", x="pct", orientation="h", text_auto=".1f", color="marca", color_discrete_map=PALETA_MARCAS,
                         title="Comisión MeLi s/ venta (%)")
            fig.update_traces(marker_line_width=0, hovertemplate="%{y}: %{x:.1f}%<extra></extra>")
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="", margin=dict(t=46))
            st.plotly_chart(estilo(fig, 214), width="stretch")

    # ---------- MARCAS ----------
    seccion("Unidades de negocio", "Rendimiento por marca", "Venta neta del período y de hoy. Elegí General o un canal.")
    vista_m = st.segmented_control("Canal", ["General", "Tienda Online", "MercadoLibre"], default="General",
                                   key="marcas_canal") or "General"
    marcas_orden = [m for m in marcas_sel if m in set(P["marca"].astype(str))]

    def _filtro(d):
        return d if (vista_m == "General" or d.empty) else d[d["canal"] == vista_m]

    Pv, Pv_prev = _filtro(P), _filtro(P_prev)
    Pv_hoy = _filtro(P_hoy) if not P_hoy.empty else P_hoy
    for i in range(0, len(marcas_orden), 5):
        cols = st.columns(5)
        for j, m in enumerate(marcas_orden[i:i + 5]):
            acc = PALETA_MARCAS.get(m, "#94A3B8")
            Pm_ = Pv[Pv["marca"] == m]
            if Pm_.empty:
                cols[j].markdown(
                    f"<div class='brand' style='--b-accent:{acc}'><div class='brand-name' style='color:{acc}'>{m}</div>"
                    f"<div class='brand-big' style='color:#8B95A7'>$0</div><span class='delta flat'>sin ventas en {vista_m}</span></div>",
                    unsafe_allow_html=True)
                continue
            r = resumen(Pm_)
            rp = resumen(Pv_prev[Pv_prev["marca"] == m]) if hay_prev else None
            hoy_m = Pv_hoy[Pv_hoy["marca"] == m]["total_pedido"].sum() if not Pv_hoy.empty else 0
            upt = r["un"] / r["ords"] if r["ords"] else 0
            asp = r["fact"] / r["un"] if r["un"] else 0
            if vista_m == "General":
                pie = split_html(por_canal_vals(Pm_, "total_pedido"))
                extra = ""
            else:
                tot_m = P[P["marca"] == m]["total_pedido"].sum()
                sh = r["fact"] / tot_m * 100 if tot_m else 0
                col_c = COLOR_CANAL[vista_m]
                pie = (f"<div class='split'><div style='width:{sh:.2f}%;background:{col_c}'></div></div>"
                       f"<div class='split-legend'><span><span class='dot' style='background:{col_c}'></span>"
                       f"{fmt_dec(sh, 0)}% de la venta de {m}</span></div>")
                extra = ""
                if vista_m == "MercadoLibre":
                    com = Pm_["comision"].sum()
                    extra = (f"<div class='row' title='Comisión cobrada por MercadoLibre'><span>Comisión</span>"
                             f"<b style='color:#F87171'>{fmt_dec(com / r['fact'] * 100 if r['fact'] else 0)}%</b></div>")
            cols[j].markdown(
                f"<div class='brand' style='--b-accent:{acc}'><div class='brand-name' style='color:{acc}'>{m}</div>"
                f"<div class='brand-big'>{fmt_kpi(r['fact'])}</div>{delta_html(r['fact'], rp['fact'] if rp else None, cap='vs ant.')}"
                f"<div class='sep'></div>"
                f"<div class='row'><span>Hoy</span><b style='color:#22D3EE'>{fmt_ars(hoy_m)}</b></div>"
                f"<div class='row'><span>Órdenes</span><b>{fmt_num(r['ords'])}</b></div>"
                f"<div class='row'><span>Unidades</span><b>{fmt_num(r['un'])}</b></div>"
                f"<div class='sep'></div>"
                f"<div class='row' title='Average Order Value'><span>AOV</span><b>{fmt_ars(r['tkt'])}</b></div>"
                f"<div class='row' title='Units per Transaction'><span>UPT</span><b>{fmt_dec(upt, 2)}</b></div>"
                f"<div class='row' title='Average Selling Price'><span>ASP</span><b>{fmt_ars(asp)}</b></div>"
                f"{extra}{pie}</div>", unsafe_allow_html=True)

    # ---------- TENDENCIA ----------
    seccion("Evolución", "Tendencia de ventas", "Por día, o por hora si el período es un solo día.")
    t1, t2, _ = st.columns([1, 1.3, 2])
    with t1:
        vista = st.segmented_control("Apertura", ["Por canal", "Por marca"], default="Por canal", key="tend_vista") or "Por canal"
    with t2:
        metrica = st.segmented_control("Métrica", ["Facturación", "Pedidos", "Unidades"], default="Facturación", key="tend_met") or "Facturación"
    Pt = P.copy()
    Pt["eje"] = Pt["fecha"].dt.hour if d0 == d1 else pd.to_datetime(Pt["dia"])
    dim = "canal" if vista == "Por canal" else "marca"
    if metrica == "Facturación":
        vt = Pt.groupby(["eje", dim], observed=True)["total_pedido"].sum()
    elif metrica == "Pedidos":
        vt = Pt.groupby(["eje", dim], observed=True).size()
    else:
        vt = Pt.groupby(["eje", dim], observed=True)["unidades"].sum()
    vt = a_str(vt.rename("valor").reset_index()).sort_values("eje")
    if dim == "canal":
        fig = px.area(vt, x="eje", y="valor", color=dim, color_discrete_map=COLOR_CANAL, line_shape="spline")
        fig.update_traces(line_width=2)
    else:
        fig = px.line(vt, x="eje", y="valor", color=dim, color_discrete_map=PALETA_MARCAS, line_shape="spline", markers=True)
    fig.update_layout(xaxis_title="Hora" if d0 == d1 else "", yaxis_title=metrica, hovermode="x unified",
                      title=f"{metrica} {'por hora' if d0 == d1 else 'diaria'} · {vista.lower()}")
    st.plotly_chart(estilo(fig, 380), width="stretch")

    # ---------- RESUMEN OPERATIVO ----------
    seccion("Tabla", "Resumen por marca y canal")
    g = P.groupby(["marca", "canal"], observed=True).agg(fact=("total_pedido", "sum"), ords=("id_pedido", "count"),
                                                          un=("unidades", "sum")).reset_index()
    filas = ""
    for m in marcas_orden:
        gm = g[g["marca"] == m]
        ft = {str(kk): vv for kk, vv in gm.set_index("canal")["fact"].items()}
        tot, ords, un = gm["fact"].sum(), gm["ords"].sum(), gm["un"].sum()
        share_ml = ft.get("MercadoLibre", 0) / tot * 100 if tot else 0
        filas += (f"<tr><td class='strong'><span class='dot' style='background:{PALETA_MARCAS.get(m, '#94A3B8')}'></span>{m}</td>"
                  f"<td>{fmt_ars(ft.get('Tienda Online', 0))}</td><td>{fmt_ars(ft.get('MercadoLibre', 0))}</td>"
                  f"<td class='strong'>{fmt_ars(tot)}</td><td>{share_ml:.0f}%</td><td>{fmt_num(ords)}</td><td>{fmt_num(un)}</td>"
                  f"<td>{fmt_ars(tot / ords if ords else 0)}</td></tr>")
    ftt = {str(kk): vv for kk, vv in g.groupby("canal", observed=True)["fact"].sum().items()}
    tt, to, tu = g["fact"].sum(), g["ords"].sum(), g["un"].sum()
    filas += (f"<tr class='total'><td>Total</td><td>{fmt_ars(ftt.get('Tienda Online', 0))}</td><td>{fmt_ars(ftt.get('MercadoLibre', 0))}</td>"
              f"<td>{fmt_ars(tt)}</td><td>{(ftt.get('MercadoLibre', 0) / tt * 100 if tt else 0):.0f}%</td><td>{fmt_num(to)}</td>"
              f"<td>{fmt_num(tu)}</td><td>{fmt_ars(tt / to if to else 0)}</td></tr>")
    html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Marca</th><th>Tienda Online</th><th>MercadoLibre</th>"
         "<th>Total</th><th>% MeLi</th><th>Órdenes</th><th>Unidades</th><th>Ticket</th></tr></thead><tbody>" + filas + "</tbody></table></div>")

# ==============================================================================
# TAB 2 · METAS & FORECAST
# ==============================================================================
with tab_metas:
    objetivos, origen_obj = load_objetivos()

    seccion("Objetivos", "Cumplimiento de metas · Real vs. Objetivo",
            f"Venta neta del período ({rango_txt}) contra la meta. La línea blanca marca el objetivo.")
    alc = st.segmented_control("Alcance", ["Todas las marcas"] + marcas_sel, default="Todas las marcas", key="meta_alc") or "Todas las marcas"
    marcas_alc = marcas_sel if alc == "Todas las marcas" else [alc]
    Pa = P[P["marca"].isin(marcas_alc)]
    cols = st.columns(3)
    for col, scope in zip(cols, ["General", "Tienda Online", "MercadoLibre"]):
        Ps = Pa if scope == "General" else Pa[Pa["canal"] == scope]
        with col:
            html(f"<div class='scope-head'><span class='dot' style='background:{COLOR_SCOPE[scope]};width:10px;height:10px'></span>{scope}</div>")
            st.plotly_chart(gauge(Ps["total_pedido"].sum(), meta(objetivos, scope, marcas_alc, "facturacion"), "Facturación",
                                  COLOR_SCOPE[scope], moneda=True), width="stretch", key=f"g_fc_{scope}")
            st.plotly_chart(gauge(Ps["unidades"].sum(), meta(objetivos, scope, marcas_alc, "unidades"), "Unidades",
                                  COLOR_SCOPE[scope]), width="stretch", key=f"g_un_{scope}")

    if ES_ADMIN:  # solo super admins editan metas
        with st.expander("Editar metas por marca y canal", icon=":material/edit:"):
            st.caption("General = Tienda Online + MercadoLibre. Las metas se guardan en el repo de datos y no se pierden al reiniciar la app."
                       + (" ⚠️ Todavía se están leyendo del archivo local: guardalas una vez para pasarlas al repo." if origen_obj != "repo" else ""))
            marcas_ed = sorted(set(MARCAS_BASE) | set(marcas_disp))
            ed = pd.DataFrame([{"Marca": m, "Canal": c,
                                "Unidades": objetivos.get(c, {}).get(m, {}).get("unidades", 0),
                                "Facturación ($)": objetivos.get(c, {}).get(m, {}).get("facturacion", 0)}
                               for c in CANALES for m in marcas_ed])
            ed_out = st.data_editor(ed, hide_index=True, width="stretch", key="editor_metas", column_config={
                "Marca": st.column_config.TextColumn(disabled=True),
                "Canal": st.column_config.TextColumn(disabled=True),
                "Unidades": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
                "Facturación ($)": st.column_config.NumberColumn(min_value=0, step=100000, format="$%d")})
            if st.button("Guardar metas", type="primary", icon=":material/save:"):
                nuevo = {c: {} for c in CANALES}
                for _, row in ed_out.iterrows():
                    nuevo[row["Canal"]][row["Marca"]] = {"unidades": int(row["Unidades"] or 0),
                                                         "facturacion": int(row["Facturación ($)"] or 0)}
                ok, msg = guardar_objetivos(nuevo)
                if ok:
                    load_objetivos.clear()
                    st.toast("Metas guardadas", icon="✅")
                    st.rerun()
                else:
                    st.error(f"No se pudieron guardar: {msg}")

    # ---------- FORECAST ----------
    seccion("Proyección", "Forecast y análisis de brecha",
            "Run rate lineal según el tiempo transcurrido del período elegido. General = suma de ambos canales.")
    f1, f2 = st.columns([1.4, 1])
    with f1:
        sc_f = st.segmented_control("Canal", ["General", "Tienda Online", "MercadoLibre"], default="General", key="fc_canal") or "General"
    with f2:
        rf = st.date_input("Período del forecast", [hoy, hoy + timedelta(days=6)], key="fore_date")
    if len(rf) == 2:
        f_start = datetime.combine(rf[0], datetime.min.time(), tzinfo=ZONA_AR)
        f_end = datetime.combine(rf[1], datetime.max.time(), tzinfo=ZONA_AR)
        dias_tot = (f_end - f_start).total_seconds() / 86400.0
        if ahora < f_start:
            dias_trans = 0.001
        elif ahora > f_end:
            dias_trans = dias_tot
        else:
            dias_trans = (ahora - f_start).total_seconds() / 86400.0
        dias_rest = max(0.0, dias_tot - dias_trans)
        contra = 0 < dias_rest < 1
        div_r = dias_rest * 24.0 if contra else dias_rest
        etq = "hora" if contra else "día"

        base_sc = base_net if sc_f == "General" else base_net[base_net["canal"] == sc_f]
        Psem = a_pedidos(base_sc[(base_sc["fecha"] >= f_start) & (base_sc["fecha"] <= f_end)])
        filas, tot_v, tot_o, tot_f = "", 0, 0, 0
        for m in marcas_sel:
            Pm_ = Psem[Psem["marca"] == m]
            venta = Pm_["total_pedido"].sum()
            uni = Pm_["unidades"].sum()
            obj = meta(objetivos, sc_f, [m], "facturacion")
            fc = venta / dias_trans * dias_tot if dias_trans > 0 else 0
            gap = obj - venta
            tot_v, tot_o, tot_f = tot_v + venta, tot_o + obj, tot_f + fc
            rr, ur = 0, 0
            if obj <= 0:
                estado = "<span class='pill warn'>Sin meta</span>"
            elif gap <= 0:
                estado = "<span class='pill ok'>✓ Meta cumplida</span>"
            elif dias_rest > 0:
                rr = gap / div_r
                asp = venta / uni if uni else 0
                if asp == 0:
                    hp = a_pedidos(base_sc[base_sc["marca"] == m])
                    asp = hp["total_pedido"].sum() / hp["unidades"].sum() if len(hp) and hp["unidades"].sum() else 50000
                ur = int(np.ceil(rr / asp))
                cls = "ok" if fc >= obj else ("warn" if fc >= obj * 0.8 else "bad")
                estado = f"<span class='pill {cls}'>Faltan {fmt_compact(gap)}</span>"
            else:
                estado = "<span class='pill bad'>Período cerrado</span>"
            pct = venta / obj * 100 if obj else 0
            filas += (f"<tr><td class='strong'><span class='dot' style='background:{PALETA_MARCAS.get(m, '#94A3B8')}'></span>{m}</td>"
                      f"<td>{fmt_ars(venta)}</td><td>{fmt_ars(obj)}</td><td>{pct:.0f}%</td>"
                      f"<td style='color:#22D3EE;font-weight:700'>{fmt_ars(fc)}</td><td>{estado}</td>"
                      f"<td style='color:#FBBF24;font-weight:700'>{fmt_ars(rr) if rr > 0 else '—'}</td>"
                      f"<td style='color:#F472B6;font-weight:700'>{(fmt_num(ur) + ' un.') if ur > 0 else '—'}</td></tr>")
        filas += (f"<tr class='total'><td>Total</td><td>{fmt_ars(tot_v)}</td><td>{fmt_ars(tot_o)}</td>"
                  f"<td>{(tot_v / tot_o * 100 if tot_o else 0):.0f}%</td><td>{fmt_ars(tot_f)}</td><td></td><td></td><td></td></tr>")
        html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Marca</th><th>Venta acum.</th><th>Objetivo</th><th>Avance</th>"
             f"<th>Proyección</th><th>Brecha</th><th>Necesario $/{etq}</th><th>Necesario un./{etq}</th></tr></thead><tbody>"
             + filas + "</tbody></table></div>")
        st.write("")
        cf = st.columns(3)
        div_g = dias_trans * 24.0 if contra else dias_trans
        cf[0].markdown(kpi_card("Tiempo consumido", f"{fmt_dec(dias_trans)} de {dias_tot:.0f} días", "", "", "#A78BFA", sm=True),
                       unsafe_allow_html=True)
        cf[1].markdown(kpi_card("Tiempo restante", f"{fmt_dec(dias_rest)} días" if dias_rest >= 1 else f"{fmt_dec(dias_rest * 24)} horas",
                                "", "", "#FBBF24", sm=True), unsafe_allow_html=True)
        cf[2].markdown(kpi_card(f"Ritmo neto actual (/{etq})", fmt_ars(tot_v / div_g if dias_trans > 0 else 0), "", "",
                                COLOR_SCOPE[sc_f], sm=True), unsafe_allow_html=True)
    else:
        st.info("Elegí fecha de inicio y fin para activar el forecast.")

# ==============================================================================
# TAB 3 · PRODUCTOS
# ==============================================================================
with tab_prod:
    seccion("Ranking", "TOP 10 productos", "El mismo artículo suma Tienda Online + MercadoLibre (agrupa por código).")
    p1c, p2c = st.columns([1.4, 1])
    with p1c:
        sel_top = selector_canal("top_canal")
    with p2c:
        agr = st.segmented_control("Nivel", ["Modelo/Color", "Talle (SKU)"], default="Modelo/Color", key="top_agr") or "Modelo/Color"
    dtop = por_canal(df_f, sel_top)
    dtop = dtop[dtop["cantidad"] > 0]
    marcas_top = [m for m in marcas_sel if (dtop["marca"] == m).any()]
    if not marcas_top:
        st.info("Sin ventas para este canal.")
    else:
        clave = "modelo_color" if agr == "Modelo/Color" else "sku"
        col_nom = "producto_base" if agr == "Modelo/Color" else "producto"
        for tab_m, m in zip(st.tabs([m.upper() for m in marcas_top]), marcas_top):
            with tab_m:
                dp = dtop[(dtop["marca"] == m) & (dtop[clave] != "S/D")]
                top = dp.groupby(clave, observed=True).agg(
                    nombre=(col_nom, "first"), url=("url_web", primer_link), mc=("modelo_color", "first"),
                    cantidad=("cantidad", "sum"), fc=("subtotal_producto", "sum")).nlargest(10, "cantidad")
                uc = dp[dp[clave].isin(top.index)].groupby([clave, "canal"], observed=True)["cantidad"].sum().unstack(fill_value=0)
                uc.columns = [str(c) for c in uc.columns]
                cards = ""
                for i, (k_, it) in enumerate(top.iterrows(), 1):
                    link = it["url"] if str(it["url"]).startswith("http") else f"{DOMINIOS_OFICIALES.get(m, '')}/search?q={it['mc']}"
                    chips = ""
                    if sel_top == "Consolidado" and k_ in uc.index:
                        chips = "<div class='chips'>" + "".join(
                            f"<span class='chip'><span class='dot' style='background:{COLOR_CANAL[c]}'></span>{CORTO[c]} {int(uc.loc[k_, c])}</span>"
                            for c in CANALES if c in uc.columns and uc.loc[k_, c] > 0) + "</div>"
                    nombre = str(it["nombre"]).replace("<", "").replace(">", "").replace("'", "")
                    cards += (f"<div class='prod'><span class='prod-rank'>#{i}</span><a href='{link}' target='_blank'>"
                              f"<img src='{img_azure(m, it['mc'])}' loading='lazy'></a><div class='prod-name' title='{nombre}'>{nombre}</div>"
                              f"<div class='prod-stats'><div>Unidades<b>{fmt_num(it['cantidad'])}</b></div>"
                              f"<div style='text-align:right'>Facturación<b>{fmt_compact(it['fc'])}</b></div></div>{chips}</div>")
                html(f"<div class='pgrid'>{cards}</div>")

    # ---------- CROSS-SELLING ----------
    seccion("Afinidad de carrito", "Análisis de cross-selling", "Pares de productos que se compran juntos en el mismo pedido / carrito.")
    x1, x2, x3 = st.columns([1.4, 1, 1])
    with x1:
        sel_x = selector_canal("cross_canal")
    with x2:
        marca_x = st.selectbox("Marca", marcas_sel, key="cross_marca")
    with x3:
        rx = st.date_input("Período", [d0, d1], min_value=f_min, max_value=hoy, key="cross_fecha")
    if len(rx) == 2 and marca_x:
        dx = por_canal(base_net, sel_x)
        dx = dx[(dx["marca"] == marca_x) & (dx["dia"] >= rx[0]) & (dx["dia"] <= rx[1]) & (dx["modelo_color"] != "S/D")]
        nombres = dx.drop_duplicates("modelo_color").set_index("modelo_color")["producto_base"].to_dict()
        links = dx.groupby("modelo_color")["url_web"].agg(primer_link).to_dict() if not dx.empty else {}
        items = dx.groupby(["canal", "id_pedido"], observed=True)["modelo_color"].agg(lambda s: sorted(set(s))) if not dx.empty else pd.Series(dtype=object)
        items = items[items.apply(len) > 1] if len(items) else items
        cnt = Counter(c for it in items for c in combinations(it, 2))
        if not cnt:
            st.info("No hay pedidos con más de un producto para esta selección.")
        else:
            df_csv = pd.DataFrame([(a, nombres.get(a, a), b, nombres.get(b, b), n) for (a, b), n in cnt.most_common()],
                                  columns=["Modelo/Color 1", "Producto 1", "Modelo/Color 2", "Producto 2 (Cross-selling)", "Carritos"])
            st.download_button("Descargar ranking completo (CSV)", df_csv.to_csv(index=False).encode("utf-8"),
                               file_name=f"cross_selling_{marca_x}.csv", mime="text/csv", icon=":material/download:")
            out = ""
            for i, ((a, b), n) in enumerate(cnt.most_common(10), 1):
                la, lb = links.get(a, "#"), links.get(b, "#")
                la = la if la.startswith("http") else f"{DOMINIOS_OFICIALES.get(marca_x, '')}/search?q={a}"
                lb = lb if lb.startswith("http") else f"{DOMINIOS_OFICIALES.get(marca_x, '')}/search?q={b}"
                out += (f"<div class='combo'><div class='combo-n'>#{i}</div>"
                        f"<a href='{la}' target='_blank'><img src='{img_azure(marca_x, a)}' loading='lazy'></a><div class='combo-plus'>+</div>"
                        f"<a href='{lb}' target='_blank'><img src='{img_azure(marca_x, b)}' loading='lazy'></a>"
                        f"<div class='combo-txt'>{nombres.get(a, a)} <span>({a})</span><br>{nombres.get(b, b)} <span>({b})</span></div>"
                        f"<div class='combo-f'>{n}<span>carritos</span></div></div>")
            html(out)

# ==============================================================================
# TAB · STOCK & PUBLICACIONES
# ==============================================================================
with tab_stock:
    cat = load_aux("catalogo_stock.csv")
    pub = load_aux("meli_publicaciones.csv")

    # ---------- REPOSICIÓN UNIFICADA ----------
    seccion("Reposición", "Stock y demanda unificada",
            "Velocidad de venta = Tienda Online + MercadoLibre. Stock = depósito (inventario de Shopify).")
    s1, s2, s3 = st.columns([1.2, 1, 1.1])
    with s1:
        nivel_s = st.segmented_control("Nivel", ["Modelo/Color", "Talle (SKU)"], default="Modelo/Color", key="stk_nivel") or "Modelo/Color"
    with s2:
        dias_v = int((st.segmented_control("Ventas de los últimos", ["15", "30", "60"], default="30", key="stk_dias") or "30"))
    with s3:
        umbral = int((st.segmented_control("Alerta si cubre menos de (días)", ["15", "30", "45"], default="30", key="stk_umbral") or "30"))
    clave_s = "modelo_color" if nivel_s == "Modelo/Color" else "sku"
    nom_s = "producto_base" if nivel_s == "Modelo/Color" else "producto"
    vent = base_net[(base_net["dia"] > hoy - timedelta(days=dias_v)) & (base_net[clave_s] != "S/D") & (base_net["cantidad"] > 0)]
    if vent.empty or cat.empty:
        st.info("Faltan datos de ventas o de catálogo para calcular la reposición.")
    else:
        vu = vent.groupby(["marca", clave_s, "canal"], observed=True)["cantidad"].sum().unstack(fill_value=0)
        vu.columns = [str(c) for c in vu.columns]
        for c in CANALES:
            if c not in vu.columns:
                vu[c] = 0
        vu["total"] = vu[CANALES].sum(axis=1)
        vu.index = vu.index.set_levels([lv.astype(str) for lv in vu.index.levels])
        nombres_s = vent.groupby(["marca", clave_s], observed=True)[nom_s].first()
        nombres_s.index = nombres_s.index.set_levels([lv.astype(str) for lv in nombres_s.index.levels])
        cat_m = cat[cat["marca"].isin(marcas_sel)].copy()
        cat_m["stock"] = pd.to_numeric(cat_m["stock"], errors="coerce").fillna(0).clip(lower=0)
        stk = cat_m.groupby(["marca", clave_s])["stock"].sum()
        R = vu.join(stk, how="left").join(nombres_s.rename("nombre"), how="left").reset_index()
        R["vel"] = R["total"] / dias_v
        R["cobertura"] = np.where(R["vel"] > 0, R["stock"] / R["vel"], np.inf)
        R["reponer"] = np.maximum(0, np.ceil(R["vel"] * 60 - R["stock"].fillna(0)))
        mc_key = "modelo_color" if clave_s == "modelo_color" else None
        R["mc"] = R[clave_s] if mc_key else R[clave_s].str.rsplit("-", n=1).str[0]
        if not pub.empty:
            est = pub.groupby(["marca", "modelo_color"])["estado"].agg(lambda s: "Activa" if (s == "active").any() else ("Pausada" if (s == "paused").any() else "—"))
            R = R.merge(est.rename("meli").reset_index().rename(columns={"modelo_color": "mc"}), on=["marca", "mc"], how="left")
        else:
            R["meli"] = "s/d"
        R["meli"] = R["meli"].fillna("—")

        con_stock = R[R["stock"].notna()]
        riesgo = con_stock[(con_stock["cobertura"] < umbral)].sort_values("vel", ascending=False)
        agotados = con_stock[(con_stock["stock"] <= 0)]
        u_t, u_m = R["Tienda Online"].sum(), R["MercadoLibre"].sum()
        k = st.columns(4)
        k[0].markdown(kpi_card(f"En riesgo (< {umbral} días)", fmt_num(len(riesgo)), "<span class='delta flat'>con ventas en el período</span>", "", "#F87171", sm=True), unsafe_allow_html=True)
        k[1].markdown(kpi_card("Agotados con demanda", fmt_num(len(agotados)), "<span class='delta down'>stock 0 y ventas recientes</span>", "", "#FBBF24", sm=True), unsafe_allow_html=True)
        k[2].markdown(kpi_card("Demanda que aporta MeLi", f"{fmt_dec(u_m / (u_t + u_m) * 100 if (u_t + u_m) else 0)}%",
                               f"<span class='delta up'>+{fmt_dec(u_m / u_t * 100 if u_t else 0)}% vs. mirar solo Shopify</span>",
                               split_html({"Tienda Online": u_t, "MercadoLibre": u_m}), "#FFE600", sm=True), unsafe_allow_html=True)
        k[3].markdown(kpi_card("Unidades en depósito", fmt_num(cat_m["stock"].sum()),
                               f"<span class='delta flat'>{fmt_num(cat_m[clave_s].nunique())} {'modelos' if clave_s == 'modelo_color' else 'SKUs'} activos</span>", "", "#22D3EE", sm=True),
                      unsafe_allow_html=True)
        st.write("")
        ver = st.segmented_control("Mostrar", ["En riesgo", "Agotados", "Todos los que venden"], default="En riesgo", key="stk_ver") or "En riesgo"
        T = riesgo if ver == "En riesgo" else (agotados.sort_values("vel", ascending=False) if ver == "Agotados" else R.sort_values("vel", ascending=False))
        filas = ""
        for _, r in T.head(25).iterrows():
            cob = r["cobertura"]
            cls = "bad" if cob < umbral / 2 else ("warn" if cob < umbral else "ok")
            cob_txt = "∞" if not np.isfinite(cob) else f"{cob:.0f} días"
            pill_meli = {"Activa": "ok", "Pausada": "warn"}.get(r["meli"], "")
            meli_html = f"<span class='pill {pill_meli}'>{r['meli']}</span>" if pill_meli else str(r["meli"])
            filas += (f"<tr><td><img src='{img_azure(r['marca'], r['mc'])}' style='width:38px;height:38px;object-fit:contain;background:#fff;border-radius:8px;vertical-align:middle;margin-right:8px'>"
                      f"<span class='dot' style='background:{PALETA_MARCAS.get(r['marca'], '#94A3B8')}'></span>{r['marca']}</td>"
                      f"<td style='text-align:left;max-width:280px;overflow:hidden;text-overflow:ellipsis'>{str(r['nombre'])[:60]}</td><td>{r[clave_s]}</td>"
                      f"<td>{fmt_num(r['Tienda Online'])}</td><td>{fmt_num(r['MercadoLibre'])}</td><td class='strong'>{fmt_dec(r['vel'], 1)}</td>"
                      f"<td>{fmt_num(r['stock']) if pd.notna(r['stock']) else '—'}</td><td><span class='pill {cls}'>{cob_txt}</span></td>"
                      f"<td style='color:#22D3EE;font-weight:700'>{fmt_num(r['reponer'])}</td>"
                      f"<td>{meli_html}</td></tr>")
        if filas:
            html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Marca</th><th style='text-align:left'>Producto</th><th>Código</th>"
                 f"<th>Vend. Tienda</th><th>Vend. MeLi</th><th>Un./día</th><th>Stock</th><th>Cobertura</th><th>Reponer (60 d)</th><th>MeLi</th></tr></thead><tbody>{filas}</tbody></table></div>")
            st.caption(f"Mostrando hasta 25 filas ordenadas por velocidad de venta. 'Reponer' = unidades para cubrir 60 días a la velocidad actual.")
        else:
            st.success("No hay productos en esta situación. 🎉")
        st.download_button("Descargar reposición completa (CSV)",
                           R.drop(columns=["mc"]).rename(columns={"vel": "unid_por_dia", "nombre": "producto"}).to_csv(index=False).encode("utf-8"),
                           file_name="reposicion_unificada.csv", mime="text/csv", icon=":material/download:")
        if R["stock"].isna().any():
            st.caption(f"ℹ️ {int(R['stock'].isna().sum())} códigos vendidos no están en el catálogo activo de Shopify (stock sin dato).")

    # ---------- PUBLICACIONES MELI ----------
    seccion("MercadoLibre", "Publicaciones: visitas, conversión y problemas",
            "Se actualiza 2 veces por día. Conversión = pedidos / visitas de los últimos 30 días.")
    if pub.empty:
        st.info("Todavía no hay datos de publicaciones. Se generan con el workflow diario (Publicaciones MeLi + Clientes).")
    else:
        pm = pub[pub["marca"].isin(marcas_sel)].copy()
        v30 = base_net[(base_net["canal"] == "MercadoLibre") & (base_net["dia"] > hoy - timedelta(days=30)) & (base_net["item_id"] != "")]
        vi = v30.groupby("item_id").agg(unidades=("cantidad", "sum"), pedidos=("id_pedido", "nunique"))
        pm = pm.merge(vi, left_on="item_id", right_index=True, how="left").fillna({"unidades": 0, "pedidos": 0})
        pm["visitas_30d"] = pd.to_numeric(pm["visitas_30d"], errors="coerce").fillna(0)
        pm["conv"] = np.where(pm["visitas_30d"] > 0, pm["pedidos"] / pm["visitas_30d"] * 100, np.nan)
        # Stock en depósito: por SKU exacto (hay marcas con una publicación por talle); si la publicación
        # agrupa talles (SKU = modelo/color), se compara contra el total del modelo.
        if not cat.empty:
            cat_s = cat.copy()
            cat_s["stock"] = pd.to_numeric(cat_s["stock"], errors="coerce").fillna(0).clip(lower=0)
            por_sku = cat_s.groupby(["marca", "sku"])["stock"].sum()
            por_mod = cat_s.groupby(["marca", "modelo_color"])["stock"].sum()
            k_sku = list(zip(pm["marca"], pm["sku"].astype(str)))
            k_mod = list(zip(pm["marca"], pm["modelo_color"].astype(str)))
            pm["stock_deposito"] = [por_sku.get(a, por_mod.get(b, np.nan)) for a, b in zip(k_sku, k_mod)]
        else:
            pm["stock_deposito"] = np.nan
        act = pm[pm["estado"] == "active"]
        vis_tot, ped_tot = act["visitas_30d"].sum(), act["pedidos"].sum()
        k = st.columns(4)
        k[0].markdown(kpi_card("Publicaciones activas", fmt_num(len(act)), f"<span class='delta flat'>{fmt_num((pm['estado'] == 'paused').sum())} pausadas</span>", "", "#FFE600", sm=True), unsafe_allow_html=True)
        k[1].markdown(kpi_card("Visitas (30 días)", fmt_num(vis_tot), "", "", "#22D3EE", sm=True), unsafe_allow_html=True)
        k[2].markdown(kpi_card("Conversión promedio", f"{fmt_dec(ped_tot / vis_tot * 100 if vis_tot else 0, 2)}%", "", "", "#34D399", sm=True), unsafe_allow_html=True)
        k[3].markdown(kpi_card("Activas sin ventas (30 d)", fmt_num(((act["pedidos"] == 0) & (act["visitas_30d"] > 0)).sum()),
                               "<span class='delta down'>con visitas pero 0 pedidos</span>", "", "#F87171", sm=True), unsafe_allow_html=True)
        st.write("")
        g1, g2 = st.columns([1.3, 1])
        with g1:
            sc = a_str(act[act["visitas_30d"] > 0])
            fig = px.scatter(sc, x="visitas_30d", y="unidades", color="marca", color_discrete_map=PALETA_MARCAS, log_x=True,
                             hover_name="titulo", hover_data={"conv": ":.2f", "precio": ":,.0f"}, title="Visitas vs. unidades vendidas (30 días)")
            fig.update_traces(marker=dict(size=8, opacity=0.75, line=dict(width=0)))
            fig.update_layout(xaxis_title="Visitas (escala log)", yaxis_title="Unidades vendidas")
            st.plotly_chart(estilo(fig, 420), width="stretch")
        with g2:
            con_vis = act[act["visitas_30d"] > 0]
            umbral_vis = con_vis["visitas_30d"].quantile(0.75) if len(con_vis) else 0
            conv_med = (ped_tot / vis_tot * 100) if vis_tot else 0  # conversión promedio de la cuenta
            opp = con_vis[(con_vis["visitas_30d"] >= umbral_vis) & (con_vis["conv"].fillna(0) < conv_med / 2)].sort_values("visitas_30d", ascending=False).head(12)
            filas = "".join(
                f"<tr><td style='max-width:230px;overflow:hidden;text-overflow:ellipsis'><a href='{r['permalink']}' target='_blank' style='color:#E5E7EB;text-decoration:none'>{str(r['titulo'])[:45]}</a></td>"
                f"<td>{fmt_num(r['visitas_30d'])}</td><td>{fmt_num(r['pedidos'])}</td><td><span class='pill bad'>{fmt_dec(r['conv'] if pd.notna(r['conv']) else 0, 2)}%</span></td>"
                f"<td>{fmt_ars(r['precio'] or 0)}</td></tr>" for _, r in opp.iterrows())
            html("<div class='scope-head'>🔎 Muchas visitas, poca conversión</div>")
            if filas:
                html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Publicación</th><th>Visitas</th><th>Pedidos</th><th>Conv.</th><th>Precio</th></tr></thead>"
                     f"<tbody>{filas}</tbody></table></div>")
                st.caption(f"Top 25% en visitas y menos de la mitad de la conversión promedio ({fmt_dec(conv_med or 0, 2)}%). Revisar precio, fotos y ficha.")
            else:
                st.success("No hay publicaciones con ese problema.")

        # Problemas de stock entre MeLi y depósito
        p1, p2 = st.columns(2)
        pausadas_stock = pm[(pm["estado"] == "paused") & (pm["stock_deposito"].fillna(0) > 0)].sort_values("stock_deposito", ascending=False)
        activas_sin = pm[(pm["estado"] == "active") & (pm["stock_deposito"].fillna(-1) == 0)].sort_values("pedidos", ascending=False)
        for col, titulo, dfp, cls, nota in [
            (p1, f"⏸️ Pausadas con stock en depósito ({len(pausadas_stock)})", pausadas_stock, "warn", "Oportunidad: se podrían reactivar."),
            (p2, f"⚠️ Activas sin stock en depósito ({len(activas_sin)})", activas_sin, "bad", "Riesgo de vender algo que no hay."),
        ]:
            with col:
                html(f"<div class='scope-head'>{titulo}</div>")
                if dfp.empty:
                    st.success("Nada para revisar.")
                else:
                    motivo = {"out_of_stock": "sin stock", "paused_by_seller": "pausada a mano"}
                    filas = "".join(
                        f"<tr><td style='max-width:220px;overflow:hidden;text-overflow:ellipsis'><a href='{r['permalink']}' target='_blank' style='color:#E5E7EB;text-decoration:none'>{str(r['titulo'])[:38]}</a></td>"
                        f"<td>{r['sku']}</td><td>{', '.join(motivo.get(x, x) for x in str(r.get('sub_estado') or '').split(',') if x and x != 'nan') or '—'}</td>"
                        f"<td><span class='pill {cls}'>{fmt_num(r['stock_deposito'] if pd.notna(r['stock_deposito']) else 0)}</span></td></tr>"
                        for _, r in dfp.head(12).iterrows())
                    html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Publicación</th><th>SKU</th><th>Motivo</th><th>Depósito</th></tr></thead>"
                         f"<tbody>{filas}</tbody></table></div>")
                    st.caption(nota)

        # Catálogo: precio para ganar
        cat_pub = pm[(pm["catalogo"].astype(str).str.lower() == "true") & (pm["estado"] == "active")].copy()
        if not cat_pub.empty and cat_pub["catalogo_estado"].notna().any():
            seccion("Catálogo MeLi", "Competencia en publicaciones de catálogo", "Quién se queda con la compra cuando hay varios vendedores del mismo producto.")
            est = cat_pub["catalogo_estado"].fillna("sin dato").astype(str)
            n_win = int(est.isin(["winning", "sharing_first_place"]).sum())
            n_comp = int((est == "competing").sum())
            k = st.columns(3)
            k[0].markdown(kpi_card("Ganando", fmt_num(n_win), "", "", "#34D399", sm=True), unsafe_allow_html=True)
            k[1].markdown(kpi_card("Perdiendo", fmt_num(n_comp), "", "", "#F87171", sm=True), unsafe_allow_html=True)
            k[2].markdown(kpi_card("Publicaciones de catálogo", fmt_num(len(cat_pub)), "", "", "#FFE600", sm=True), unsafe_allow_html=True)
            comp = cat_pub[est == "competing"].copy()
            if not comp.empty:
                comp["dif"] = (pd.to_numeric(comp["precio"], errors="coerce") / pd.to_numeric(comp["precio_para_ganar"], errors="coerce") - 1) * 100
                filas = "".join(
                    f"<tr><td style='max-width:280px;overflow:hidden;text-overflow:ellipsis'><a href='{r['permalink']}' target='_blank' style='color:#E5E7EB;text-decoration:none'>{str(r['titulo'])[:50]}</a></td>"
                    f"<td>{r['marca']}</td><td>{fmt_ars(r['precio'] or 0)}</td><td style='color:#34D399;font-weight:700'>{fmt_ars(r['precio_para_ganar']) if pd.notna(r['precio_para_ganar']) else '—'}</td>"
                    f"<td><span class='pill bad'>{fmt_dec(r['dif'], 1) + '%' if pd.notna(r['dif']) else '—'}</span></td><td>{fmt_num(r['visitas_30d'])}</td></tr>"
                    for _, r in comp.sort_values("visitas_30d", ascending=False).head(20).iterrows())
                html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Publicación</th><th>Marca</th><th>Precio actual</th><th>Precio para ganar</th><th>Diferencia</th><th>Visitas</th></tr></thead>"
                     f"<tbody>{filas}</tbody></table></div>")

# ==============================================================================
# TAB 4 · COMERCIAL
# ==============================================================================
with tab_com:
    sel_c = selector_canal("com_canal")
    dcom = por_canal(df_f, sel_c)
    Pc = por_canal(P, sel_c)

    # ---------- PROMOS ----------
    seccion("Campañas", "Análisis de promociones", "Impacto de cada código de descuento (venta neta, sin reversos).")
    dpr = dcom[~dcom["descuento"].astype(str).isin(SIN_DESCUENTO)]
    if sel_c == "MercadoLibre":
        st.info("MercadoLibre no informa cupones por API: las promociones de MeLi se ven como descuentos en el precio de la publicación.")
    elif dpr.empty:
        st.info("No hay ventas con códigos de descuento en el período.")
    else:
        rank = dpr.groupby("descuento", observed=True)["subtotal_producto"].sum().sort_values(ascending=False)
        opciones = [str(x) for x in rank.index]
        codigos = st.multiselect("Códigos", opciones, default=opciones[:6], key="promo_cod")
        dsel = dpr[dpr["descuento"].astype(str).isin(codigos)]
        if dsel.empty:
            st.info("Elegí al menos un código.")
        else:
            ped_cod = dsel.drop_duplicates(["canal", "marca", "id_pedido"]).shape[0]
            cp = st.columns(3)
            cp[0].markdown(kpi_card("Facturación con código", fmt_kpi(dsel["subtotal_producto"].sum()), "", "", "#22D3EE", sm=True),
                           unsafe_allow_html=True)
            cp[1].markdown(kpi_card("Pedidos con código", fmt_num(ped_cod),
                                    f"<span class='delta flat'>{fmt_dec(ped_cod / max(len(Pc), 1) * 100)}% del total</span>", "", "#A78BFA", sm=True),
                           unsafe_allow_html=True)
            cp[2].markdown(kpi_card("Unidades con código", fmt_num(dsel["cantidad"].sum()), "", "", "#34D399", sm=True),
                           unsafe_allow_html=True)
            st.write("")
            dim_p = "canal" if sel_c == "Consolidado" else "marca"
            cm_p = COLOR_CANAL if dim_p == "canal" else PALETA_MARCAS
            g1, g2 = st.columns(2)
            with g1:
                d_ = a_str(dsel.groupby(["descuento", dim_p], observed=True)["subtotal_producto"].sum().reset_index())
                d_["txt"] = d_["subtotal_producto"].map(fmt_compact)
                fig = px.bar(d_, x="subtotal_producto", y="descuento", color=dim_p, orientation="h", color_discrete_map=cm_p,
                             title="Facturación por código", text="txt")
                fig.update_layout(xaxis_title="", yaxis_title="", yaxis=dict(categoryorder="total ascending"))
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(estilo(fig, 380), width="stretch")
            with g2:
                d_ = a_str(dsel.groupby(["descuento", dim_p], observed=True)["cantidad"].sum().reset_index())
                d_["txt"] = d_["cantidad"].map(fmt_num)
                fig = px.bar(d_, x="cantidad", y="descuento", color=dim_p, orientation="h", color_discrete_map=cm_p,
                             title="Unidades por código", text="txt")
                fig.update_layout(xaxis_title="", yaxis_title="", yaxis=dict(categoryorder="total ascending"))
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(estilo(fig, 380), width="stretch")

    # ---------- FINANZAS ----------
    seccion("Cobros", "Finanzas", "Medios de pago y financiación en cuotas, abierto por canal.")
    if Pc.empty:
        st.info("Sin ventas para este canal.")
    else:
        COLOR_MEDIO = {"Mercado Pago": "#009EE3", "Mobbex": "#A78BFA", "Reversso": "#F472B6", "Transferencia": "#34D399",
                       "Otros": "#64748B", "MeLi · Tarjeta de crédito": "#FFE600", "MeLi · Débito": "#FDE68A",
                       "MeLi · Dinero en cuenta": "#FBBF24", "MeLi · Mercado Crédito": "#F59E0B", "MeLi · Efectivo": "#D97706",
                       "MeLi · Transferencia": "#CA8A04", "MeLi · Otros": "#A16207"}
        canales_fin = [c for c in CANALES if (Pc["canal"] == c).any()]
        cols_fin = st.columns(len(canales_fin))
        for col, c in zip(cols_fin, canales_fin):
            Pcc = Pc[Pc["canal"] == c]
            mp = a_str(Pcc.groupby("medio_grupo", observed=True)["total_pedido"].sum().reset_index())
            fig = px.pie(mp, values="total_pedido", names="medio_grupo", hole=0.62, color="medio_grupo",
                         color_discrete_map=COLOR_MEDIO, title=f"{c} · facturación por medio de pago")
            fig.update_traces(textinfo="percent", textposition="inside", marker=dict(line=dict(color="#060A13", width=2)),
                              hovertemplate="%{label}<br>$%{value:,.0f}<extra></extra>")
            fig.add_annotation(text=f"<b>{fmt_compact(Pcc['total_pedido'].sum())}</b>", showarrow=False,
                               font=dict(size=17, family="Space Grotesk, sans-serif", color=COLOR_CANAL[c]))
            with col:
                st.plotly_chart(estilo(fig, 400), width="stretch", key=f"fin_medio_{c}")

        # Cuotas: solo canales que informan financiación (Shopify hoy no la trae en el pedido)
        cu = Pc.groupby(["cuotas_grupo", "canal"], observed=True).size().rename("ped").reset_index()
        cu["canal"] = cu["canal"].astype(str)
        con_cuotas = [c for c in canales_fin if set(cu.loc[cu["canal"] == c, "cuotas_grupo"].astype(str)) - {"1 pago"}]
        sin_cuotas = [c for c in canales_fin if c not in con_cuotas]
        cu = cu[cu["canal"].isin(con_cuotas)]
        if cu.empty:
            st.info("Este canal no informa la cantidad de cuotas de cada pedido.")
        else:
            cu["pct"] = cu["ped"] / cu.groupby("canal")["ped"].transform("sum") * 100
            tk = Pc[Pc["canal"].astype(str).isin(con_cuotas)].groupby(["cuotas_grupo", "canal"], observed=True)["total_pedido"].mean()
            tk = a_str(tk.rename("ticket").reset_index())
            cu = a_str(cu).merge(tk, on=["cuotas_grupo", "canal"], how="left")
            orden = [c for c in ORDEN_CUOTAS if c in set(cu["cuotas_grupo"])] + sorted(set(cu["cuotas_grupo"]) - set(ORDEN_CUOTAS))
            g1, g2 = st.columns(2)
            with g1:
                fig = px.bar(cu, x="cuotas_grupo", y="pct", color="canal", barmode="group", color_discrete_map=COLOR_CANAL,
                             category_orders={"cuotas_grupo": orden}, title="Pedidos por financiación (% de pedidos del canal)",
                             text=cu["pct"].map(lambda v: fmt_dec(v, 0) + "%"), custom_data=["ped"])
                fig.update_traces(marker_line_width=0, hovertemplate="%{x}<br>%{y:.1f}% · %{customdata[0]} pedidos<extra></extra>")
                fig.update_layout(xaxis_title="", yaxis_title="% de pedidos", bargap=0.25)
                st.plotly_chart(estilo(fig, 380), width="stretch")
            with g2:
                fig = px.bar(cu, x="cuotas_grupo", y="ticket", color="canal", barmode="group", color_discrete_map=COLOR_CANAL,
                             category_orders={"cuotas_grupo": orden}, title="Ticket promedio según financiación",
                             text=cu["ticket"].map(fmt_compact))
                fig.update_traces(marker_line_width=0, hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>")
                fig.update_layout(xaxis_title="", yaxis_title="Ticket ($)", bargap=0.25)
                st.plotly_chart(estilo(fig, 380), width="stretch")
            if sin_cuotas:
                st.caption(f"ℹ️ {', '.join(sin_cuotas)}: el pedido no trae la cantidad de cuotas, por eso no aparece en estos gráficos.")

# ==============================================================================
# TAB · PUBLICIDAD MELI (Product Ads)
# ==============================================================================
def _pct_norm(s):
    """Las participaciones pueden venir 0-1 o 0-100: se normaliza a 0-100."""
    s = pd.to_numeric(s, errors="coerce")
    return s * 100 if s.dropna().le(1).all() else s


def _ads_kpis(d):
    t = {k: float(pd.to_numeric(d.get(k, pd.Series(dtype=float)), errors="coerce").sum()) for k in
         ["cost", "prints", "clicks", "total_amount", "direct_amount", "indirect_amount", "units_quantity",
          "direct_units_quantity", "indirect_units_quantity", "organic_units_quantity", "organic_units_amount"]}
    t["roas"] = t["total_amount"] / t["cost"] if t["cost"] else 0
    t["acos"] = t["cost"] / t["total_amount"] * 100 if t["total_amount"] else 0
    t["ctr"] = t["clicks"] / t["prints"] * 100 if t["prints"] else 0
    t["cpc"] = t["cost"] / t["clicks"] if t["clicks"] else 0
    t["cpm"] = t["cost"] / t["prints"] * 1000 if t["prints"] else 0
    t["cvr"] = t["units_quantity"] / t["clicks"] * 100 if t["clicks"] else 0
    return t


with tab_ads:
    a_camp = load_aux("meli_ads_campanias.csv")
    a_dia = load_aux("meli_ads_diario.csv")
    a_items = load_aux("meli_ads_items.csv")
    if a_dia.empty and a_items.empty:
        st.info("Todavía no hay datos de publicidad. Se generan con el workflow diario (Publicidad de MercadoLibre). "
                "Si el log muestra error 403, hay que habilitar el permiso de 'Publicidad' en la app de MeLi.")
    else:
        a_dia = a_dia[a_dia["marca"].isin(marcas_sel)].copy()
        a_dia["dia"] = pd.to_datetime(a_dia["fecha"]).dt.date
        a_camp = a_camp[a_camp["marca"].isin(marcas_sel)].copy() if not a_camp.empty else a_camp
        nombres_c = dict(zip(a_camp["campaign_id"], a_camp["nombre"])) if not a_camp.empty else {}
        f_ads_min, f_ads_max = a_dia["dia"].min(), a_dia["dia"].max()
        a0, a1 = max(d0, f_ads_min), min(d1, f_ads_max)
        if a0 > a1:
            a0, a1 = max(f_ads_min, f_ads_max - timedelta(days=29)), f_ads_max
        nd = (a1 - a0).days + 1
        pa0, pa1 = a0 - timedelta(days=nd), a0 - timedelta(days=1)

        c1, c2 = st.columns([2.2, 1])
        with c1:
            camp_opts = sorted(a_dia["campaign_id"].unique(), key=lambda x: str(nombres_c.get(x, x)))
            camp_sel = st.multiselect("Campañas", camp_opts, default=camp_opts, key="ads_camps",
                                      format_func=lambda x: str(nombres_c.get(x, x))) or camp_opts
        with c2:
            html(f"<div class='hero-sub' style='margin-top:30px'>📅 <b>{a0:%d/%m} → {a1:%d/%m/%Y}</b> · "
                 f"MeLi consolida la publicidad 1 vez por día (datos hasta {f_ads_max:%d/%m}).</div>")
        dsel = a_dia[a_dia["campaign_id"].isin(camp_sel)]
        cur = dsel[(dsel["dia"] >= a0) & (dsel["dia"] <= a1)]
        prv = dsel[(dsel["dia"] >= pa0) & (dsel["dia"] <= pa1)]
        k, kp = _ads_kpis(cur), _ads_kpis(prv)
        hay_prev_ads = (not prv.empty) and pa0 >= f_ads_min
        pv = (lambda x: kp[x]) if hay_prev_ads else (lambda x: None)
        # Venta total MeLi del período (para TACOS y % atribuido a publicidad)
        def _venta_meli(x0, x1):
            b = base_net[(base_net["canal"] == "MercadoLibre") & (base_net["dia"] >= x0) & (base_net["dia"] <= x1)]
            pp = a_pedidos(b)
            return float(pp["total_pedido"].sum()) if len(pp) else 0.0, float(pp["unidades"].sum()) if len(pp) else 0.0
        vm, um = _venta_meli(a0, a1)
        vm_p, _ = _venta_meli(pa0, pa1) if hay_prev_ads else (0, 0)
        tacos = k["cost"] / vm * 100 if vm else 0
        tacos_p = kp["cost"] / vm_p * 100 if vm_p else None

        # ---------- KPIs ----------
        seccion("Mercado Ads", "Rendimiento de la inversión", f"Product Ads de MercadoLibre · comparado con los {nd} días anteriores.")
        cc = st.columns(6)
        cc[0].markdown(kpi_card("Inversión", fmt_kpi(k["cost"]), delta_html(k["cost"], pv("cost")), "", "#F472B6", sm=True), unsafe_allow_html=True)
        cc[1].markdown(kpi_card("Ventas por publicidad", fmt_kpi(k["total_amount"]), delta_html(k["total_amount"], pv("total_amount")),
                                f"<div class='split-legend' style='margin-top:10px'><span>Directas {fmt_compact(k['direct_amount'])}</span><span>Indirectas {fmt_compact(k['indirect_amount'])}</span></div>",
                                "#34D399", sm=True), unsafe_allow_html=True)
        cc[2].markdown(kpi_card("ROAS", f"{fmt_dec(k['roas'], 1)}x", delta_html(k["roas"], pv("roas")), "<div class='split-legend' style='margin-top:10px'><span>$ vendidos por $1 invertido</span></div>", "#22D3EE", sm=True), unsafe_allow_html=True)
        cc[3].markdown(kpi_card("ACOS", f"{fmt_dec(k['acos'])}%", delta_html(k["acos"], pv("acos"), invert=True, pp=True), "<div class='split-legend' style='margin-top:10px'><span>inversión / ventas por ads</span></div>", "#FBBF24", sm=True), unsafe_allow_html=True)
        cc[4].markdown(kpi_card("TACOS", f"{fmt_dec(tacos)}%", delta_html(tacos, tacos_p, invert=True, pp=True), "<div class='split-legend' style='margin-top:10px'><span>inversión / venta total MeLi</span></div>", "#A78BFA", sm=True), unsafe_allow_html=True)
        cc[5].markdown(kpi_card("Venta MeLi por ads", f"{fmt_dec(k['total_amount'] / vm * 100 if vm else 0)}%", "", "<div class='split-legend' style='margin-top:10px'><span>del total vendido en MeLi</span></div>", "#FFE600", sm=True), unsafe_allow_html=True)
        st.write("")
        cc = st.columns(6)
        cc[0].markdown(kpi_card("Impresiones", fmt_compact(k["prints"], False), delta_html(k["prints"], pv("prints")), "", "#38BDF8", sm=True), unsafe_allow_html=True)
        cc[1].markdown(kpi_card("Clics", fmt_num(k["clicks"]), delta_html(k["clicks"], pv("clicks")), "", "#38BDF8", sm=True), unsafe_allow_html=True)
        cc[2].markdown(kpi_card("CTR", f"{fmt_dec(k['ctr'], 2)}%", delta_html(k["ctr"], pv("ctr"), pp=True), "", "#38BDF8", sm=True), unsafe_allow_html=True)
        cc[3].markdown(kpi_card("CPC", fmt_ars(k["cpc"]), delta_html(k["cpc"], pv("cpc"), invert=True), "", "#38BDF8", sm=True), unsafe_allow_html=True)
        cc[4].markdown(kpi_card("Conversión (CVR)", f"{fmt_dec(k['cvr'], 2)}%", delta_html(k["cvr"], pv("cvr"), pp=True), "<div class='split-legend' style='margin-top:10px'><span>unidades / clics</span></div>", "#38BDF8", sm=True), unsafe_allow_html=True)
        cc[5].markdown(kpi_card("Unidades por ads", fmt_num(k["units_quantity"]), delta_html(k["units_quantity"], pv("units_quantity")),
                                f"<div class='split-legend' style='margin-top:10px'><span>CPM {fmt_ars(k['cpm'])}</span><span>orgánicas {fmt_num(k['organic_units_quantity'])}</span></div>", "#38BDF8", sm=True), unsafe_allow_html=True)

        # ---------- TENDENCIA + EMBUDO ----------
        from plotly.subplots import make_subplots
        g1, g2 = st.columns([1.7, 1])
        with g1:
            td = cur.groupby("dia")[["cost", "total_amount"]].sum().reset_index()
            td["acos"] = np.where(td["total_amount"] > 0, td["cost"] / td["total_amount"] * 100, np.nan)
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=td["dia"], y=td["cost"], name="Inversión", marker_color="#F472B6", opacity=0.85)
            fig.add_scatter(x=td["dia"], y=td["total_amount"], name="Ventas por ads", line=dict(color="#34D399", width=2.5, shape="spline"))
            fig.add_scatter(x=td["dia"], y=td["acos"], name="ACOS %", line=dict(color="#FBBF24", width=2, dash="dot"), secondary_y=True)
            fig.update_layout(title="Inversión, ventas y ACOS por día", hovermode="x unified", bargap=0.3)
            fig.update_yaxes(title_text="$", secondary_y=False)
            fig.update_yaxes(title_text="ACOS", secondary_y=True, showgrid=False, ticksuffix="%", tickformat=".1f", rangemode="tozero")
            st.plotly_chart(estilo(fig, 400), width="stretch")
        with g2:
            fig = go.Figure(go.Funnel(y=["Impresiones", "Clics", "Unidades vendidas"],
                                      x=[k["prints"], k["clicks"], k["units_quantity"]], textinfo="text+percent previous",
                                      text=[fmt_compact(k["prints"], moneda=False), fmt_num(k["clicks"]), fmt_num(k["units_quantity"])],
                                      marker=dict(color=["#38BDF8", "#A78BFA", "#34D399"]),
                                      connector=dict(line=dict(color="rgba(148,163,184,.25)"))))
            fig.update_layout(title="Embudo publicitario")
            st.plotly_chart(estilo(fig, 400), width="stretch")

        # ---------- POR MARCA ----------
        bm = cur.groupby("marca")[["cost", "total_amount", "direct_amount", "indirect_amount", "clicks", "prints", "units_quantity"]].sum()
        bm["acos"] = np.where(bm["total_amount"] > 0, bm["cost"] / bm["total_amount"] * 100, 0)
        vm_marca = a_pedidos(base_net[(base_net["canal"] == "MercadoLibre") & (base_net["dia"] >= a0) & (base_net["dia"] <= a1)])
        vm_marca = vm_marca.groupby("marca", observed=True)["total_pedido"].sum() if len(vm_marca) else pd.Series(dtype=float)
        vm_marca.index = vm_marca.index.astype(str)
        bm["tacos"] = [bm.loc[m, "cost"] / vm_marca.get(m, 0) * 100 if vm_marca.get(m, 0) else 0 for m in bm.index]
        bm = bm.reset_index()
        g1, g2 = st.columns(2)
        with g1:
            mm = bm.melt(id_vars="marca", value_vars=["cost", "direct_amount", "indirect_amount"], var_name="tipo", value_name="monto")
            mm["tipo"] = mm["tipo"].map({"cost": "Inversión", "direct_amount": "Venta directa", "indirect_amount": "Venta indirecta"})
            mm["txt"] = mm["monto"].map(fmt_compact)
            fig = px.bar(mm, x="marca", y="monto", color="tipo", barmode="group", text="txt", title="Inversión vs. ventas por marca",
                         color_discrete_map={"Inversión": "#F472B6", "Venta directa": "#34D399", "Venta indirecta": "#22D3EE"})
            fig.update_traces(marker_line_width=0)
            fig.update_layout(xaxis_title="", yaxis_title="", bargap=0.25)
            st.plotly_chart(estilo(fig, 380), width="stretch")
        with g2:
            ml = bm.melt(id_vars="marca", value_vars=["acos", "tacos"], var_name="m", value_name="pct")
            ml["m"] = ml["m"].str.upper()
            fig = px.bar(ml, x="marca", y="pct", color="m", barmode="group", text=ml["pct"].map(lambda v: fmt_dec(v) + "%"),
                         color_discrete_map={"ACOS": "#FBBF24", "TACOS": "#A78BFA"}, title="ACOS y TACOS por marca")
            fig.update_traces(marker_line_width=0)
            fig.update_layout(xaxis_title="", yaxis_title="%", bargap=0.3)
            st.plotly_chart(estilo(fig, 380), width="stretch")

        # ---------- CAMPAÑAS ----------
        seccion("Campañas", "Rendimiento y salud de cada campaña",
                "Participación de impresiones y pérdidas son de los últimos 30 días. La recomendación cruza ACOS real vs. objetivo y por qué se pierden impresiones.")
        cm = cur.groupby("campaign_id")[["cost", "total_amount", "clicks", "prints", "units_quantity"]].sum()
        if not a_camp.empty:
            cm = a_camp.set_index("campaign_id").join(cm, how="left").fillna({"cost": 0, "total_amount": 0, "clicks": 0, "prints": 0, "units_quantity": 0})
            cm = cm[cm.index.isin(camp_sel)]
            for c_ in ["is_impression_share", "is_top_impression_share", "is_lost_impression_share_by_budget", "is_lost_impression_share_by_ad_rank"]:
                cm[c_] = _pct_norm(cm[c_]) if c_ in cm.columns else np.nan
            cm = cm.sort_values("cost", ascending=False)
            filas = ""
            for cid, r in cm.iterrows():
                acos_r = r["cost"] / r["total_amount"] * 100 if r["total_amount"] else np.nan
                obj = pd.to_numeric(r.get("acos_objetivo"), errors="coerce")
                lb, lr = r.get("is_lost_impression_share_by_budget"), r.get("is_lost_impression_share_by_ad_rank")
                if str(r.get("estado")) != "active":
                    rec, cls = "Pausada", "warn"
                elif pd.notna(acos_r) and pd.notna(obj) and acos_r > obj * 1.2:
                    rec, cls = "🔻 ACOS sobre objetivo: revisar anuncios que gastan sin vender", "bad"
                elif pd.notna(lb) and lb >= 20 and (pd.isna(obj) or pd.isna(acos_r) or acos_r <= obj):
                    rec, cls = f"⬆️ Subir presupuesto: pierde {fmt_dec(lb, 0)}% de impresiones con ACOS sano", "ok"
                elif pd.notna(lr) and lr >= 30:
                    rec, cls = f"🎯 Pierde {fmt_dec(lr, 0)}% por ranking: mejorar precio/publicación o subir ACOS objetivo", "warn"
                elif r["cost"] > 0 and r["total_amount"] == 0:
                    rec, cls = "⚪ Gasta sin ventas", "bad"
                else:
                    rec, cls = "✅ Mantener", "ok"
                est_cls = "ok" if r.get("estado") == "active" else "warn"
                fpct = lambda v: f"{fmt_dec(v, 0)}%" if pd.notna(v) else "—"
                filas += (f"<tr><td class='strong' style='text-align:left'><span class='dot' style='background:{PALETA_MARCAS.get(r['marca'], '#94A3B8')}'></span>{r['nombre']}</td>"
                          f"<td style='text-align:left;white-space:normal;min-width:230px'><span class='pill {cls}'>{rec}</span></td>"
                          f"<td><span class='pill {est_cls}'>{r.get('estado', '')}</span></td><td>{str(r.get('estrategia', '')).title()}</td>"
                          f"<td>{fmt_ars(pd.to_numeric(r.get('presupuesto'), errors='coerce') or 0)}</td>"
                          f"<td>{fpct(obj)}</td><td class='strong'>{fpct(acos_r)}</td>"
                          f"<td>{fmt_dec(r['total_amount'] / r['cost'], 1) + 'x' if r['cost'] else '—'}</td>"
                          f"<td>{fmt_ars(r['cost'])}</td><td>{fmt_ars(r['total_amount'])}</td>"
                          f"<td>{fmt_dec(r['clicks'] / r['prints'] * 100, 2) + '%' if r['prints'] else '—'}</td>"
                          f"<td>{fmt_ars(r['cost'] / r['clicks']) if r['clicks'] else '—'}</td>"
                          f"<td>{fmt_dec(r['units_quantity'] / r['clicks'] * 100, 2) + '%' if r['clicks'] else '—'}</td>"
                          f"<td>{fpct(r.get('is_impression_share'))}</td><td>{fpct(lb)}</td><td>{fpct(lr)}</td></tr>")
            html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Campaña</th><th style='text-align:left'>Recomendación</th><th>Estado</th><th>Estrategia</th>"
                 "<th>Presup./día</th><th>ACOS obj.</th><th>ACOS real</th><th>ROAS</th><th>Inversión</th><th>Ventas</th><th>CTR</th><th>CPC</th><th>CVR</th>"
                 "<th>Impr. share</th><th>Pérdida x presup.</th><th>Pérdida x ranking</th></tr></thead>"
                 f"<tbody>{filas}</tbody></table></div>")

        # ---------- PRODUCTOS EN CAMPAÑA + STOCK ----------
        seccion("Productos", "Productos en campaña vs. stock",
                "Cruza cada anuncio con el stock en MeLi, el depósito y la velocidad de venta (Tienda + MeLi, 30 días). Métricas del anuncio: últimos 30 días.")
        if a_items.empty:
            st.info("Sin datos de anuncios.")
        else:
            it = a_items[a_items["marca"].isin(marcas_sel) & a_items["campaign_id"].isin(camp_sel)].copy()
            for c_ in ["m30_cost", "m30_clicks", "m30_prints", "m30_units_quantity", "m30_total_amount", "m7_cost"]:
                it[c_] = pd.to_numeric(it[c_], errors="coerce").fillna(0) if c_ in it.columns else 0.0
            pub_a = load_aux("meli_publicaciones.csv")
            cat_a = load_aux("catalogo_stock.csv")
            if not pub_a.empty:
                it = it.merge(pub_a[["item_id", "sku", "modelo_color", "stock", "estado"]].rename(columns={"stock": "stock_meli", "estado": "estado_pub"}),
                              on="item_id", how="left")
            else:
                it["sku"], it["modelo_color"], it["stock_meli"], it["estado_pub"] = "", "", np.nan, ""
            if not cat_a.empty:
                cat_a["stock"] = pd.to_numeric(cat_a["stock"], errors="coerce").fillna(0).clip(lower=0)
                ps, pmod = cat_a.groupby(["marca", "sku"])["stock"].sum(), cat_a.groupby(["marca", "modelo_color"])["stock"].sum()
                it["stock_dep"] = [ps.get((m, str(s)), pmod.get((m, str(mc)), np.nan)) for m, s, mc in zip(it["marca"], it["sku"], it["modelo_color"])]
            else:
                it["stock_dep"] = np.nan
            v30 = base_net[(base_net["dia"] > hoy - timedelta(days=30)) & (base_net["cantidad"] > 0)]
            vel_sku = v30.groupby("sku")["cantidad"].sum() / 30
            vel_mod = v30.groupby("modelo_color")["cantidad"].sum() / 30
            it["vel"] = [vel_sku.get(str(s), np.nan) if str(s) in vel_sku.index else vel_mod.get(str(mc), 0) for s, mc in zip(it["sku"], it["modelo_color"])]
            it["vel"] = pd.to_numeric(it["vel"], errors="coerce").fillna(0)
            it["stock_ref"] = it[["stock_meli", "stock_dep"]].min(axis=1, skipna=True)
            it["cobertura"] = np.where(it["vel"] > 0, it["stock_ref"] / it["vel"], np.inf)
            it["acos30"] = np.where(it["m30_total_amount"] > 0, it["m30_cost"] / it["m30_total_amount"] * 100, np.nan)
            it["cvr30"] = np.where(it["m30_clicks"] > 0, it["m30_units_quantity"] / it["m30_clicks"] * 100, np.nan)
            obj_c = dict(zip(a_camp["campaign_id"], pd.to_numeric(a_camp["acos_objetivo"], errors="coerce"))) if not a_camp.empty else {}
            it["acos_obj"] = it["campaign_id"].map(obj_c)
            gasto_ref = it.loc[it["m30_cost"] > 0, "m30_cost"].quantile(0.75) if (it["m30_cost"] > 0).any() else 0

            def accion(r):
                activo = str(r["estado_ad"]) == "active"
                sin_stock = (pd.notna(r["stock_meli"]) and r["stock_meli"] <= 0) or (pd.notna(r["stock_dep"]) and r["stock_dep"] <= 0)
                if activo and sin_stock:
                    return "🔴 Pausar: sin stock"
                if activo and r["vel"] > 0 and r["cobertura"] < 15:
                    return "🟠 Reponer: stock crítico"
                if activo and r["m30_cost"] >= gasto_ref and r["m30_units_quantity"] == 0 and r["m30_cost"] > 0:
                    return "⚪ Revisar: gasta sin vender"
                obj = r["acos_obj"] if pd.notna(r["acos_obj"]) else 20
                if activo and pd.notna(r["acos30"]) and r["acos30"] > obj * 1.5:
                    return "🔻 ACOS alto"
                if activo and pd.notna(r["acos30"]) and r["acos30"] <= obj and r["cobertura"] >= 30:
                    return "🟢 Escalar"
                if not activo and not sin_stock and pd.notna(r["stock_ref"]) and r["stock_ref"] > 0 and r["vel"] > 0:
                    return "🟣 Reactivar anuncio"
                return "Mantener"
            it["accion"] = it.apply(accion, axis=1)

            desperdicio7 = it.loc[it["accion"] == "🔴 Pausar: sin stock", "m7_cost"].sum()
            desperdicio30 = it.loc[it["accion"] == "🔴 Pausar: sin stock", "m30_cost"].sum()
            cnt = it["accion"].value_counts()
            k6 = st.columns(6)
            k6[0].markdown(kpi_card("Anuncios activos", fmt_num((it["estado_ad"] == "active").sum()), f"<span class='delta flat'>{fmt_num(len(it))} en campañas</span>", "", "#22D3EE", sm=True), unsafe_allow_html=True)
            k6[1].markdown(kpi_card("🔴 Sin stock y con anuncio", fmt_num(cnt.get("🔴 Pausar: sin stock", 0)), f"<span class='delta down'>gastaron {fmt_compact(desperdicio7)} en 7 días</span>", "", "#EF4444", sm=True), unsafe_allow_html=True)
            k6[2].markdown(kpi_card("🟠 Para reponer", fmt_num(cnt.get("🟠 Reponer: stock crítico", 0)), "<span class='delta flat'>&lt; 15 días de stock</span>", "", "#FB923C", sm=True), unsafe_allow_html=True)
            k6[3].markdown(kpi_card("⚪ Gastan sin vender", fmt_num(cnt.get("⚪ Revisar: gasta sin vender", 0)), "", "", "#94A3B8", sm=True), unsafe_allow_html=True)
            k6[4].markdown(kpi_card("🔻 ACOS alto", fmt_num(cnt.get("🔻 ACOS alto", 0)), "<span class='delta flat'>&gt; 1,5x el objetivo</span>", "", "#FBBF24", sm=True), unsafe_allow_html=True)
            k6[5].markdown(kpi_card("🟢 Para escalar", fmt_num(cnt.get("🟢 Escalar", 0)), "<span class='delta up'>ACOS sano y stock &gt; 30 días</span>", "", "#34D399", sm=True), unsafe_allow_html=True)
            if desperdicio30 > 0:
                st.caption(f"💸 Inversión en anuncios de productos sin stock en los últimos 30 días: **{fmt_ars(desperdicio30)}**.")
            opciones_acc = ["Todas"] + [a for a in ["🔴 Pausar: sin stock", "🟠 Reponer: stock crítico", "⚪ Revisar: gasta sin vender",
                                                    "🔻 ACOS alto", "🟢 Escalar", "🟣 Reactivar anuncio", "Mantener"] if cnt.get(a, 0)]
            ver_acc = st.segmented_control("Acción", opciones_acc, default="Todas", key="ads_accion") or "Todas"
            T = it if ver_acc == "Todas" else it[it["accion"] == ver_acc]
            _prio = {"🔴 Pausar: sin stock": 0, "🟠 Reponer: stock crítico": 1, "⚪ Revisar: gasta sin vender": 2, "🔻 ACOS alto": 3,
                     "🟣 Reactivar anuncio": 4, "🟢 Escalar": 5, "Mantener": 6}
            T = T.assign(_p=T["accion"].map(_prio)).sort_values(["_p", "m30_cost"], ascending=[True, False])
            pill = {"🔴": "bad", "🟠": "warn", "⚪": "warn", "🔻": "bad", "🟢": "ok", "🟣": "warn"}
            filas = ""
            for _, r in T.head(40).iterrows():
                cls = pill.get(r["accion"][:1], "")
                img = r["thumbnail"] if str(r.get("thumbnail", "")).startswith("http") else img_azure(r["marca"], r.get("modelo_color", ""))
                cob = "∞" if not np.isfinite(r["cobertura"]) else f"{r['cobertura']:.0f} d"
                filas += (f"<tr><td style='text-align:left;max-width:300px;overflow:hidden;text-overflow:ellipsis'>"
                          f"<img src='{img}' style='width:34px;height:34px;object-fit:contain;background:#fff;border-radius:6px;vertical-align:middle;margin-right:8px'>"
                          f"<a href='{r['permalink']}' target='_blank' style='color:#E5E7EB;text-decoration:none'>{str(r['titulo'])[:48]}</a></td>"
                          f"<td style='text-align:left;white-space:nowrap'><span class='pill {cls}'>{r['accion']}</span></td><td>{r['marca']}</td><td style='max-width:160px;overflow:hidden;text-overflow:ellipsis'>{nombres_c.get(r['campaign_id'], r['campaign_id'])}</td>"
                          f"<td>{r['estado_ad']}</td><td>{fmt_ars(r['m30_cost'])}</td><td>{fmt_ars(r['m30_total_amount'])}</td>"
                          f"<td>{fmt_dec(r['acos30'], 0) + '%' if pd.notna(r['acos30']) else '—'}</td><td>{fmt_num(r['m30_clicks'])}</td>"
                          f"<td>{fmt_dec(r['cvr30'], 1) + '%' if pd.notna(r['cvr30']) else '—'}</td>"
                          f"<td>{fmt_num(r['stock_meli']) if pd.notna(r['stock_meli']) else '—'}</td><td>{fmt_num(r['stock_dep']) if pd.notna(r['stock_dep']) else '—'}</td>"
                          f"<td>{cob}</td></tr>")
            if filas:
                html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Publicación</th><th style='text-align:left'>Acción sugerida</th><th>Marca</th><th>Campaña</th><th>Anuncio</th>"
                     "<th>Inversión 30d</th><th>Ventas ads 30d</th><th>ACOS</th><th>Clics</th><th>CVR</th><th>Stock MeLi</th><th>Depósito</th><th>Cobertura</th>"
                     f"</tr></thead><tbody>{filas}</tbody></table></div>")
                st.caption(f"Mostrando hasta 40 de {fmt_num(len(T))}, ordenados por urgencia de la acción y luego por inversión. Cobertura = días de stock a la velocidad de venta actual.")
            exp = T[["marca", "item_id", "titulo", "sku", "campaign_id", "estado_ad", "m30_cost", "m30_total_amount", "acos30", "m30_clicks",
                     "m30_units_quantity", "cvr30", "stock_meli", "stock_dep", "vel", "cobertura", "accion", "permalink"]].copy()
            exp["campaign_id"] = exp["campaign_id"].map(lambda x: nombres_c.get(x, x))
            st.download_button("Descargar productos en campaña (CSV)", exp.to_csv(index=False).encode("utf-8"),
                               file_name="productos_en_campania.csv", mime="text/csv", icon=":material/download:")

            # ---------- OPORTUNIDADES: STOCK SIN PUBLICIDAD ----------
            if not pub_a.empty:
                seccion("Oportunidades", "Stock sin publicidad",
                        "Publicaciones activas con stock en depósito que no están en ninguna campaña: candidatas a sumar a Product Ads.")
                fuera = pub_a[pub_a["marca"].isin(marcas_sel) & (pub_a["estado"] == "active") & ~pub_a["item_id"].isin(a_items["item_id"])].copy()
                if not cat_a.empty and not fuera.empty:
                    fuera["stock_dep"] = [ps.get((m, str(s)), pmod.get((m, str(mc)), 0)) for m, s, mc in zip(fuera["marca"], fuera["sku"], fuera["modelo_color"])]
                    fuera["visitas_30d"] = pd.to_numeric(fuera["visitas_30d"], errors="coerce").fillna(0)
                    fuera = fuera[fuera["stock_dep"] > 0].sort_values(["stock_dep", "visitas_30d"], ascending=False)
                    filas = "".join(
                        f"<tr><td style='text-align:left;max-width:340px;overflow:hidden;text-overflow:ellipsis'><a href='{r['permalink']}' target='_blank' style='color:#E5E7EB;text-decoration:none'>{str(r['titulo'])[:55]}</a></td>"
                        f"<td>{r['marca']}</td><td>{r['sku']}</td><td class='strong'>{fmt_num(r['stock_dep'])}</td><td>{fmt_num(r['stock'])}</td><td>{fmt_num(r['visitas_30d'])}</td><td>{fmt_ars(r['precio'] or 0)}</td></tr>"
                        for _, r in fuera.head(20).iterrows())
                    if filas:
                        html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Publicación</th><th>Marca</th><th>SKU</th>"
                             f"<th>Stock depósito</th><th>Stock MeLi</th><th>Visitas 30d</th><th>Precio</th></tr></thead><tbody>{filas}</tbody></table></div>")
                        st.caption(f"{fmt_num(len(fuera))} publicaciones activas con stock y sin anuncio. Ordenadas por stock en depósito.")
                    else:
                        st.success("Todas las publicaciones con stock están en alguna campaña.")

# ==============================================================================
# TAB · CLIENTES
# ==============================================================================
with tab_cli:
    res_c = load_aux("clientes_resumen.csv")
    coh_c = load_aux("clientes_cohortes.csv")
    sel_cl = selector_canal("cli_canal")
    Pcl = por_canal(P, sel_cl)
    Pcl = Pcl[Pcl["cliente"].astype(str).str.len() > 0]
    if res_c.empty or Pcl.empty:
        st.info("Todavía no hay datos de clientes. Se habilitan después de correr una vez el workflow 'Backfill clientes'.")
    else:
        st.caption("Los clientes se identifican por canal: MercadoLibre no comparte el email, así que un mismo cliente en "
                   "Tienda y MeLi se cuenta dos veces en Consolidado. 'Nuevo' = primera compra desde que hay datos.")
        res_c["canal"] = res_c["canal"].astype(str)
        prim = dict(zip(zip(res_c["canal"], res_c["cliente"].astype(str)), res_c["primera_compra"].astype(str)))
        Pcl = Pcl.copy()
        Pcl["canal"] = Pcl["canal"].astype(str)
        Pcl["es_nuevo"] = [prim.get((c, str(cl)), "") == str(d) for c, cl, d in zip(Pcl["canal"], Pcl["cliente"], Pcl["dia"])]
        cli_u = Pcl.groupby(["canal", "cliente"]).agg(nuevo=("es_nuevo", "max"), fact=("total_pedido", "sum"), ped=("id_pedido", "count"))

        # ---------- KPIs ----------
        seccion("Clientes", "Nuevos vs. recurrentes", f"Clientes que compraron en el período ({rango_txt}).")
        n_cli, n_new = len(cli_u), int(cli_u["nuevo"].sum())
        fact_rec = cli_u.loc[~cli_u["nuevo"], "fact"].sum()
        tk_new = Pcl.loc[Pcl["es_nuevo"], "total_pedido"].mean() if Pcl["es_nuevo"].any() else 0
        tk_rec = Pcl.loc[~Pcl["es_nuevo"], "total_pedido"].mean() if (~Pcl["es_nuevo"]).any() else 0
        k = st.columns(5)
        k[0].markdown(kpi_card("Clientes únicos", fmt_num(n_cli), "", split_html(cli_u.groupby(level=0).size().to_dict() | {c: 0 for c in CANALES if c not in cli_u.index.get_level_values(0)}), "#22D3EE", sm=True), unsafe_allow_html=True)
        k[1].markdown(kpi_card("Clientes nuevos", f"{fmt_dec(n_new / n_cli * 100 if n_cli else 0)}%", f"<span class='delta flat'>{fmt_num(n_new)} clientes</span>", "", "#34D399", sm=True), unsafe_allow_html=True)
        k[2].markdown(kpi_card("Venta de recurrentes", f"{fmt_dec(fact_rec / cli_u['fact'].sum() * 100 if cli_u['fact'].sum() else 0)}%", "<span class='delta flat'>de la facturación</span>", "", "#A78BFA", sm=True), unsafe_allow_html=True)
        k[3].markdown(kpi_card("Pedidos por cliente", fmt_dec(cli_u["ped"].mean(), 2), "", "", "#FBBF24", sm=True), unsafe_allow_html=True)
        k[4].markdown(kpi_card("Ticket nuevo vs. recurrente", f"{fmt_compact(tk_new)} / {fmt_compact(tk_rec)}", "", "", "#F472B6", sm=True), unsafe_allow_html=True)
        st.write("")
        g1, g2 = st.columns([1.4, 1])
        with g1:
            Pcl["semana"] = pd.to_datetime(Pcl["dia"]).dt.to_period("W-SUN").dt.start_time
            sem = Pcl.groupby(["semana", "es_nuevo"])["cliente"].nunique().rename("clientes").reset_index()
            sem["tipo"] = np.where(sem["es_nuevo"], "Nuevos", "Recurrentes")
            fig = px.bar(sem, x="semana", y="clientes", color="tipo", color_discrete_map={"Nuevos": "#34D399", "Recurrentes": "#A78BFA"},
                         title="Clientes por semana")
            fig.update_traces(marker_line_width=0)
            fig.update_layout(xaxis_title="", yaxis_title="Clientes", bargap=0.2)
            st.plotly_chart(estilo(fig, 380), width="stretch")

        # ---------- FRECUENCIA Y VALOR (histórico) ----------
        rc = res_c if sel_cl == "Consolidado" else res_c[res_c["canal"] == sel_cl]
        rc = rc[rc["marcas"].astype(str).apply(lambda s: any(m in s.split("|") for m in marcas_sel))]
        with g2:
            rc_ = rc.copy()
            rc_["compras"] = pd.cut(rc_["pedidos"], [0, 1, 2, 3, 4, 10**9], labels=["1", "2", "3", "4", "5+"])
            fr = rc_.groupby(["canal", "compras"], observed=True).size().rename("n").reset_index()
            fr["pct"] = fr["n"] / fr.groupby("canal")["n"].transform("sum") * 100
            fig = px.bar(fr, x="compras", y="pct", color="canal", barmode="group", color_discrete_map=COLOR_CANAL,
                         title="Cantidad de compras por cliente (histórico)", text=fr["pct"].map(lambda v: fmt_dec(v, 0) + "%"))
            fig.update_traces(marker_line_width=0)
            fig.update_layout(xaxis_title="Compras", yaxis_title="% de clientes", bargap=0.25)
            st.plotly_chart(estilo(fig, 380), width="stretch")

        seccion("Valor", "Valor del cliente", "Acumulado desde que hay datos (Tienda: ene-2026 · MeLi: sep-2026).")
        k = st.columns(4)
        recompra = (rc["pedidos"] >= 2).mean() * 100 if len(rc) else 0
        g_sorted = rc["gasto"].sort_values(ascending=False)
        top10 = g_sorted.head(max(1, len(g_sorted) // 10)).sum() / g_sorted.sum() * 100 if g_sorted.sum() else 0
        k[0].markdown(kpi_card("Clientes (histórico)", fmt_num(len(rc)), "", "", "#22D3EE", sm=True), unsafe_allow_html=True)
        k[1].markdown(kpi_card("Tasa de recompra", f"{fmt_dec(recompra)}%", "<span class='delta flat'>compraron 2 o más veces</span>", "", "#34D399", sm=True), unsafe_allow_html=True)
        k[2].markdown(kpi_card("Gasto promedio por cliente", fmt_ars(rc["gasto"].mean() if len(rc) else 0), "", "", "#FBBF24", sm=True), unsafe_allow_html=True)
        k[3].markdown(kpi_card("Top 10% de clientes", f"{fmt_dec(top10)}%", "<span class='delta flat'>de la facturación</span>", "", "#F472B6", sm=True), unsafe_allow_html=True)
        st.write("")

        c1, c2 = st.columns([1.2, 1])
        with c1:
            canal_coh = sel_cl if sel_cl != "Consolidado" else "Tienda Online"
            ch = coh_c[coh_c["canal"] == canal_coh] if not coh_c.empty else coh_c
            if ch.empty:
                st.info("Sin datos de cohortes para este canal.")
            else:
                base0 = ch[ch["mes_n"] == 0].set_index("cohorte")["clientes"]
                base0 = base0[base0 >= 30]  # cohortes muy chicas distorsionan el %
                ch = ch[ch["cohorte"].isin(base0.index)]
                ch = ch[ch["mes_n"] > 0].copy()
                ch["ret"] = ch["clientes"] / ch["cohorte"].map(base0) * 100
                mat = ch.pivot(index="cohorte", columns="mes_n", values="ret").sort_index()
                mat.columns = [f"+{c} m" for c in mat.columns]
                fig = px.imshow(mat, text_auto=".1f", aspect="auto", color_continuous_scale=["#0F172A", "#155E75", "#22D3EE"],
                                title=f"Retención por cohorte · {canal_coh} (% que volvió a comprar)")
                fig.update_layout(xaxis_title="Meses después de la 1ª compra", yaxis_title="Mes de 1ª compra", coloraxis_showscale=False)
                st.plotly_chart(estilo(fig, 400), width="stretch")
        with c2:
            rt = res_c[(res_c["canal"] == "Tienda Online")]
            rt = rt[rt["marcas"].astype(str).apply(lambda s: any(m in s.split("|") for m in marcas_sel))]
            if rt.empty:
                st.info("Sin datos de Tienda Online para el cruce de marcas.")
            else:
                multi = (rt["n_marcas"] >= 2).mean() * 100
                html(kpi_card("Clientes multimarca (Tienda)", f"{fmt_dec(multi)}%", "<span class='delta flat'>compraron 2 o más marcas</span>", "", "#A78BFA", sm=True))
                mlist = [m for m in marcas_sel]
                mat = pd.DataFrame(0, index=mlist, columns=mlist)
                for s_ in rt.loc[rt["n_marcas"] >= 2, "marcas"].astype(str):
                    ms = [m for m in s_.split("|") if m in mlist]
                    for a_, b_ in combinations(ms, 2):
                        mat.loc[a_, b_] += 1
                        mat.loc[b_, a_] += 1
                fig = px.imshow(mat, text_auto=True, aspect="auto", color_continuous_scale=["#0F172A", "#5B21B6", "#A78BFA"],
                                title="Clientes que compraron ambas marcas")
                fig.update_layout(xaxis_title="", yaxis_title="", coloraxis_showscale=False)
                st.plotly_chart(estilo(fig, 300), width="stretch")

# ==============================================================================
# TAB 5 · OPERACIONES
# ==============================================================================
def dias_habiles(desde, hasta):
    a = np.array(pd.Series(desde).dt.date.tolist(), dtype="datetime64[D]")
    b = np.array(pd.Series(hasta).dt.date.tolist(), dtype="datetime64[D]") if not isinstance(hasta, type(hoy)) else np.datetime64(hasta)
    return np.maximum(np.busday_count(a, b), 0)


if tab_ops is not None:
    with tab_ops:
        sel_o = selector_canal("ops_canal")
        Po = por_canal(P, sel_o)
        if Po.empty:
            st.info("Sin ventas para este canal.")
        else:
            Po = Po.copy()
            Po["canal"] = Po["canal"].astype(str)
            Po["envio_estado"] = Po["envio_estado"].astype(str)
            canales_o = [c for c in CANALES if (Po["canal"] == c).any()]

            # ---------- EMBUDO ----------
            seccion("Envíos", "Embudo de envíos", f"Pedidos netos recibidos en el período ({rango_txt}) y en qué estado está cada uno hoy.")
            rec = Po
            pend = Po[Po["envio_estado"].isin(ENV_PEND)]
            desp = Po[Po["envio_estado"].isin(ENV_DESP)]
            curso = Po[Po["envio_estado"].isin(ENV_CURSO)]
            entr = Po[Po["envio_estado"] == "Entregado"]
            prob = Po[Po["envio_estado"].isin(ENV_PROB)]
            n = len(rec)
            pct = lambda a, b: f"{fmt_dec(a / b * 100 if b else 0)}%"
            k = st.columns(6)
            k[0].markdown(kpi_card("Recibidos", fmt_num(n), "<span class='delta flat'>pedidos netos</span>", split_html(por_canal_vals(rec, "ords")), "#22D3EE", sm=True), unsafe_allow_html=True)
            k[1].markdown(kpi_card("Pendientes de despacho", fmt_num(len(pend)), f"<span class='delta down'>{pct(len(pend), n)} de recibidos</span>", split_html(por_canal_vals(pend, "ords")), "#F87171", sm=True), unsafe_allow_html=True)
            k[2].markdown(kpi_card("Despachados", fmt_num(len(desp)), f"<span class='delta up'>{pct(len(desp), n)} de recibidos</span>", split_html(por_canal_vals(desp, "ords")), "#38BDF8", sm=True), unsafe_allow_html=True)
            k[3].markdown(kpi_card("En camino", fmt_num(len(curso)), "<span class='delta flat'>despachados sin entregar</span>", split_html(por_canal_vals(curso, "ords")), "#A78BFA", sm=True), unsafe_allow_html=True)
            k[4].markdown(kpi_card("Entregados", fmt_num(len(entr)), f"<span class='delta up'>{pct(len(entr), len(desp))} de despachados</span>", split_html(por_canal_vals(entr, "ords")), "#34D399", sm=True), unsafe_allow_html=True)
            k[5].markdown(kpi_card("Con problemas", fmt_num(len(prob)), "<span class='delta down'>fallidos / no entregados / devolución</span>", split_html(por_canal_vals(prob, "ords")), "#F472B6", sm=True), unsafe_allow_html=True)
            sin_entregas = [c for c in canales_o if not ((Po["canal"] == c) & (Po["envio_estado"] == "Entregado")).any()]
            if sin_entregas:
                st.caption(f"ℹ️ {', '.join(sin_entregas)}: todavía no hay entregas informadas. En Tienda Online la entrega solo se ve si el "
                           "transportista actualiza el seguimiento en Shopify; si no, el pedido queda como 'Despachado'.")
            st.write("")

            g1, g2 = st.columns([1, 1.3])
            with g1:
                ee = Po.groupby(["canal", "envio_estado"]).size().rename("n").reset_index()
                ee["pct"] = ee["n"] / ee.groupby("canal")["n"].transform("sum") * 100
                fig = px.bar(ee, y="canal", x="pct", color="envio_estado", orientation="h", color_discrete_map=COLOR_ENVIO,
                             category_orders={"envio_estado": ORDEN_ENVIO}, custom_data=["n", "envio_estado"],
                             title="Estado actual de los pedidos (% por canal)")
                fig.update_traces(marker_line_width=0, hovertemplate="%{customdata[1]}<br>%{x:.1f}% · %{customdata[0]} pedidos<extra></extra>")
                fig.update_layout(xaxis_title="% de pedidos", yaxis_title="", bargap=0.35, legend=dict(y=-0.25))
                st.plotly_chart(estilo(fig, 380), width="stretch")
            with g2:
                ini = max(d0, hoy - timedelta(days=44))
                serie = []
                r_ = Po[Po["dia"] >= ini].groupby("dia").size().rename("Recibidos")
                d_ = Po[Po["fecha_despacho"].notna()].assign(d=lambda x: x["fecha_despacho"].dt.date)
                d_ = d_[d_["d"] >= ini].groupby("d").size().rename("Despachados")
                e_ = Po[Po["fecha_entrega"].notna()].assign(d=lambda x: x["fecha_entrega"].dt.date)
                e_ = e_[e_["d"] >= ini].groupby("d").size().rename("Entregados")
                flujo = pd.concat([r_, d_, e_], axis=1).fillna(0).sort_index()
                flujo.index = pd.to_datetime(flujo.index)
                flujo = flujo.reset_index().rename(columns={"index": "dia"}).melt(id_vars="dia", var_name="tipo", value_name="pedidos")
                fig = px.line(flujo, x="dia", y="pedidos", color="tipo", markers=True, line_shape="spline",
                              color_discrete_map={"Recibidos": "#22D3EE", "Despachados": "#FBBF24", "Entregados": "#34D399"},
                              title="Recibidos vs. despachados vs. entregados por día")
                fig.update_layout(xaxis_title="", yaxis_title="Pedidos", hovermode="x unified")
                st.plotly_chart(estilo(fig, 380), width="stretch")

            # ---------- PENDIENTES POR ANTIGÜEDAD ----------
            seccion("Depósito", "Pendientes de despacho por antigüedad",
                    "Pedidos que todavía no salieron, según días hábiles desde la compra (excluye sábados y domingos).")
            if pend.empty:
                st.success("No hay pedidos pendientes de despacho. 🎉")
            else:
                pend = pend.copy()
                pend["dias_hab"] = dias_habiles(pend["fecha"], hoy)
                tramos = [("Hoy", 0, 0, "#34D399"), ("1 día háb.", 1, 1, "#FBBF24"), ("2 días háb.", 2, 2, "#FB923C"),
                          ("3 a 5 días háb.", 3, 5, "#F87171"), ("+5 días háb.", 6, 10**6, "#EF4444")]
                k = st.columns(len(tramos))
                for col, (lbl, lo, hi, colr) in zip(k, tramos):
                    sub = pend[(pend["dias_hab"] >= lo) & (pend["dias_hab"] <= hi)]
                    col.markdown(kpi_card(lbl, fmt_num(len(sub)), "", split_html(por_canal_vals(sub, "ords")), colr, sm=True), unsafe_allow_html=True)
                st.write("")
                viejos = pend.sort_values(["dias_hab", "fecha"], ascending=[False, True])
                filas = ""
                for _, r in viejos.head(30).iterrows():
                    dh = int(r["dias_hab"])
                    cls = "ok" if dh == 0 else ("warn" if dh <= 2 else "bad")
                    filas += (f"<tr><td class='strong'>{r['nro_pedido']}</td>"
                              f"<td><span class='dot' style='background:{COLOR_CANAL.get(r['canal'], '#94A3B8')}'></span>{CORTO.get(r['canal'], r['canal'])}</td>"
                              f"<td>{r['marca']}</td><td>{r['fecha']:%d/%m %H:%M}</td><td><span class='pill {cls}'>{dh} días háb.</span></td>"
                              f"<td>{r['envio_estado']}</td><td>{r['provincia']}</td><td>{fmt_num(r['unidades'])}</td><td>{fmt_ars(r['total_pedido'])}</td></tr>")
                html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Pedido</th><th>Canal</th><th>Marca</th><th>Compra</th>"
                     "<th>Esperando</th><th>Estado</th><th>Provincia</th><th>Unid.</th><th>Total</th></tr></thead>"
                     f"<tbody>{filas}</tbody></table></div>")
                exp = viejos[["nro_pedido", "canal", "marca", "fecha", "dias_hab", "envio_estado", "envio_detalle", "provincia", "unidades", "total_pedido"]].copy()
                exp["fecha"] = exp["fecha"].dt.strftime("%d/%m/%Y %H:%M")
                st.caption(f"Los 30 más atrasados de {fmt_num(len(pend))} pendientes.")
                st.download_button("Descargar todos los pendientes (CSV)", a_str(exp).to_csv(index=False).encode("utf-8"),
                                   file_name="pendientes_despacho.csv", mime="text/csv", icon=":material/download:")

            # ---------- TIEMPOS ----------
            seccion("Tiempos", "Tiempos de despacho y de entrega",
                    "Despacho = días hábiles de la compra a la salida. Tránsito = días corridos de la salida a la entrega.")
            env = Po[Po["envio_estado"].isin(ENV_DESP) & Po["fecha_despacho"].notna()].copy()
            if not env.empty:
                env["lt"] = dias_habiles(env["fecha"], env["fecha_despacho"])
            ent_t = Po[(Po["envio_estado"] == "Entregado") & Po["fecha_entrega"].notna()].copy()
            if not ent_t.empty:
                ent_t["total_d"] = (ent_t["fecha_entrega"] - ent_t["fecha"]).dt.total_seconds() / 86400
                ent_t["transito_d"] = np.where(ent_t["fecha_despacho"].notna(),
                                               (ent_t["fecha_entrega"] - ent_t["fecha_despacho"]).dt.total_seconds() / 86400, np.nan)
            filas = ""
            for c in canales_o:
                e_c = env[env["canal"] == c] if not env.empty else env
                t_c = ent_t[ent_t["canal"] == c] if not ent_t.empty else ent_t
                filas += (f"<tr><td class='strong'><span class='dot' style='background:{COLOR_CANAL[c]}'></span>{c}</td>"
                          f"<td>{fmt_dec(e_c['lt'].mean(), 2) if len(e_c) else '—'}</td>"
                          f"<td>{(fmt_dec((e_c['lt'] <= 1).mean() * 100) + '%') if len(e_c) else '—'}</td>"
                          f"<td>{fmt_dec(t_c['transito_d'].mean(), 1) if len(t_c) and t_c['transito_d'].notna().any() else '—'}</td>"
                          f"<td>{fmt_dec(t_c['total_d'].mean(), 1) if len(t_c) else '—'}</td>"
                          f"<td>{fmt_dec(t_c['total_d'].quantile(0.9), 1) if len(t_c) else '—'}</td>"
                          f"<td>{fmt_num(len(t_c))}</td></tr>")
            html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Canal</th><th>Despacho prom. (días háb.)</th><th>Despachados ≤ 24 hs háb.</th>"
                 "<th>Tránsito prom. (días)</th><th>Compra → entrega prom. (días)</th><th>Compra → entrega (90% de los pedidos)</th><th>Entregas medidas</th></tr></thead>"
                 f"<tbody>{filas}</tbody></table></div>")
            st.write("")
            g1, g2 = st.columns(2)
            with g1:
                if env.empty:
                    st.info("No hay despachos con fecha registrada para calcular el SLA.")
                else:
                    tr = {0: "Mismo día", 1: "24 hs háb.", 2: "48 hs háb."}
                    env["tramo"] = env["lt"].map(lambda x: tr.get(int(x), "+48 hs háb."))
                    sl = env.groupby(["canal", "tramo"]).size().rename("n").reset_index()
                    sl["pct"] = sl["n"] / sl.groupby("canal")["n"].transform("sum") * 100
                    fig = px.bar(sl, x="tramo", y="pct", color="canal", barmode="group", color_discrete_map=COLOR_CANAL,
                                 category_orders={"tramo": ["Mismo día", "24 hs háb.", "48 hs háb.", "+48 hs háb."]},
                                 text=sl["pct"].map(lambda v: fmt_dec(v, 0) + "%"), custom_data=["n"],
                                 title="Eficiencia de depósito (SLA de despacho)")
                    fig.update_traces(marker_line_width=0, hovertemplate="%{x}<br>%{y:.1f}% · %{customdata[0]} pedidos<extra></extra>")
                    fig.update_layout(xaxis_title="", yaxis_title="% de despachados", bargap=0.25)
                    st.plotly_chart(estilo(fig, 360), width="stretch")
            with g2:
                if ent_t.empty:
                    st.info("Todavía no hay entregas con fecha informada para medir el tiempo de entrega.")
                else:
                    ent_t["dias_ent"] = np.minimum(np.floor(ent_t["total_d"]).astype(int), 10)
                    he = ent_t.groupby(["canal", "dias_ent"]).size().rename("n").reset_index()
                    he["pct"] = he["n"] / he.groupby("canal")["n"].transform("sum") * 100
                    he["lbl"] = he["dias_ent"].map(lambda d: "10+" if d >= 10 else str(d))
                    fig = px.bar(he, x="lbl", y="pct", color="canal", barmode="group", color_discrete_map=COLOR_CANAL,
                                 category_orders={"lbl": [str(i) for i in range(10)] + ["10+"]}, custom_data=["n"],
                                 title="Días desde la compra hasta la entrega")
                    fig.update_traces(marker_line_width=0, hovertemplate="%{x} días<br>%{y:.1f}% · %{customdata[0]} pedidos<extra></extra>")
                    fig.update_layout(xaxis_title="Días corridos", yaxis_title="% de entregados", bargap=0.2)
                    st.plotly_chart(estilo(fig, 360), width="stretch")

            # ---------- TRANSPORTISTAS ----------
            tp = desp.copy()
            tp["transportista"] = tp["transportista"].astype(str).replace({"": "Sin informar", "nan": "Sin informar"})
            if tp["transportista"].nunique() > 1 or (tp["transportista"] != "Sin informar").any():
                seccion("Transportistas", "Rendimiento por transportista", "Pedidos despachados en el período.")
                ag = tp.groupby("transportista").agg(desp=("id_pedido", "count"),
                                                     entregados=("envio_estado", lambda s: (s == "Entregado").sum()),
                                                     problemas=("envio_estado", lambda s: s.isin(ENV_PROB).sum())).sort_values("desp", ascending=False)
                if not ent_t.empty:
                    ag = ag.join(ent_t.assign(transportista=ent_t["transportista"].astype(str).replace({"": "Sin informar", "nan": "Sin informar"}))
                                 .groupby("transportista")["total_d"].mean().rename("dias"), how="left")
                else:
                    ag["dias"] = np.nan
                filas = "".join(f"<tr><td class='strong'>{t}</td><td>{fmt_num(r['desp'])}</td><td>{fmt_num(r['entregados'])}</td>"
                                f"<td>{fmt_dec(r['entregados'] / r['desp'] * 100 if r['desp'] else 0)}%</td><td>{fmt_num(r['problemas'])}</td>"
                                f"<td>{fmt_dec(r['dias'], 1) if pd.notna(r['dias']) else '—'}</td></tr>" for t, r in ag.head(12).iterrows())
                html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Transportista</th><th>Despachados</th><th>Entregados</th>"
                     f"<th>% entregado</th><th>Con problemas</th><th>Compra → entrega (días)</th></tr></thead><tbody>{filas}</tbody></table></div>")

            # ---------- PROBLEMAS ----------
            if not prob.empty:
                seccion("Seguimiento", f"Envíos con problemas ({fmt_num(len(prob))})", "Intentos de entrega fallidos, no entregados y devoluciones.")
                filas = "".join(
                    f"<tr><td class='strong'>{r['nro_pedido']}</td><td>{CORTO.get(r['canal'], r['canal'])}</td><td>{r['marca']}</td>"
                    f"<td>{r['fecha']:%d/%m}</td><td><span class='pill bad'>{r['envio_estado']}</span></td><td>{r['envio_detalle']}</td>"
                    f"<td>{r['provincia']}</td><td>{fmt_ars(r['total_pedido'])}</td></tr>"
                    for _, r in prob.sort_values("fecha", ascending=False).head(30).iterrows())
                html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Pedido</th><th>Canal</th><th>Marca</th><th>Compra</th>"
                     f"<th>Estado</th><th>Detalle</th><th>Provincia</th><th>Total</th></tr></thead><tbody>{filas}</tbody></table></div>")

            # ---------- GEO ----------
            seccion("Geografía", "Distribución geográfica · TOP 10 provincias")
            top_prov = Po.groupby("provincia", observed=True)["total_pedido"].sum().nlargest(10).index
            gp = a_str(Po[Po["provincia"].isin(top_prov)].groupby(["provincia", "canal"], observed=True)
                       .agg(fact=("total_pedido", "sum"), un=("unidades", "sum")).reset_index())
            gp["txt_f"] = gp["fact"].map(fmt_compact)
            gp["txt_u"] = gp["un"].map(fmt_num)
            g1, g2 = st.columns(2)
            with g1:
                fig = px.bar(gp, x="fact", y="provincia", color="canal", orientation="h", color_discrete_map=COLOR_CANAL,
                             title="Facturación por provincia", text="txt_f")
                fig.update_layout(xaxis_title="", yaxis_title="", yaxis=dict(categoryorder="total ascending"))
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(estilo(fig, 420), width="stretch")
            with g2:
                fig = px.bar(gp, x="un", y="provincia", color="canal", orientation="h", color_discrete_map=COLOR_CANAL,
                             title="Unidades por provincia", text="txt_u")
                fig.update_layout(xaxis_title="", yaxis_title="", yaxis=dict(categoryorder="total ascending"))
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(estilo(fig, 420), width="stretch")
