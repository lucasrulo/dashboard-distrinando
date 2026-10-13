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
st_autorefresh(interval=300000, limit=None, key="auto_refresh")

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
ORDEN_CUOTAS = ["1 pago", "Débito", "3 cuotas", "6 cuotas", "9 cuotas", "12 cuotas", "18 cuotas"]
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
              "sku": "S/D", "producto": "S/D"}
    for c, default in textos.items():
        if c not in df.columns:
            df[c] = default
        df[c] = df[c].fillna(default).astype(str)
    if "producto_base" not in df.columns:
        df["producto_base"] = df["producto"].str.split(" / ").str[0]
    if "modelo_color" not in df.columns:
        df["modelo_color"] = df["sku"].str.rsplit("-", n=1).str[0]
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
    df["dia"] = df["fecha"].dt.date
    df["cantidad"] = df["cantidad"].astype("int32")

    for c in ["marca", "canal", "medio_pago", "medio_grupo", "cuotas", "cuotas_grupo", "descuento", "provincia", "estado"]:
        df[c] = df[c].astype("category")
    return df


COLS_PED = ["canal", "marca", "id_pedido", "fecha", "dia", "total_pedido", "es_reverso", "unidades", "medio_grupo",
            "cuotas_grupo", "provincia", "estado", "fecha_despacho", "comision"]


def a_pedidos(d):
    """Una fila por pedido (canal + marca + id)."""
    if d.empty:
        return pd.DataFrame(columns=COLS_PED)
    return d.groupby(["canal", "marca", "id_pedido"], observed=True, sort=False).agg(
        fecha=("fecha", "first"), dia=("dia", "first"), total_pedido=("total_pedido", "first"),
        es_reverso=("es_reverso", "max"), unidades=("cantidad", "sum"), medio_grupo=("medio_grupo", "first"),
        cuotas_grupo=("cuotas_grupo", "first"), provincia=("provincia", "first"), estado=("estado", "first"),
        fecha_despacho=("fecha_despacho", "first"), comision=("comision_meli", "sum"),
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
# 6. APP
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

    periodo = st.segmented_control("Período", ["Hoy", "7D", "30D", "Todo", "Rango"], default="Todo", key="periodo") or "Todo"
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
    html("<div class='kpi-label' style='margin-bottom:8px'>Última venta registrada</div>")
    for c in CANALES:
        sub = df_raw[df_raw["canal"] == c]
        txt = sub["fecha"].max().strftime("%d/%m %H:%M") + " hs" if not sub.empty else "sin datos"
        html(f"<div class='row'><span><span class='dot' style='background:{COLOR_CANAL[c]}'></span>{c}</span><b>{txt}</b></div>")

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

tab_res, tab_metas, tab_prod, tab_com, tab_ops = st.tabs([
    ":material/space_dashboard: Resumen", ":material/flag: Metas & Forecast", ":material/local_mall: Productos",
    ":material/payments: Comercial", ":material/local_shipping: Operaciones"])

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
    seccion("Unidades de negocio", "Rendimiento por marca", "Venta neta del período, hoy y mix de canal.")
    marcas_orden = [m for m in marcas_sel if m in set(P["marca"].astype(str))]
    for i in range(0, len(marcas_orden), 5):
        cols = st.columns(5)
        for j, m in enumerate(marcas_orden[i:i + 5]):
            Pm_ = P[P["marca"] == m]
            r = resumen(Pm_)
            rp = resumen(P_prev[P_prev["marca"] == m]) if hay_prev else None
            hoy_m = P_hoy[P_hoy["marca"] == m]["total_pedido"].sum() if not P_hoy.empty else 0
            acc = PALETA_MARCAS.get(m, "#94A3B8")
            upt = r["un"] / r["ords"] if r["ords"] else 0
            asp = r["fact"] / r["un"] if r["un"] else 0
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
                f"{split_html(por_canal_vals(Pm_, 'total_pedido'))}</div>", unsafe_allow_html=True)

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
    seccion("Cobros", "Finanzas", "Medios de pago y financiación en cuotas.")
    if Pc.empty:
        st.info("Sin ventas para este canal.")
    else:
        g1, g2 = st.columns([1, 1.3])
        with g1:
            mp = a_str(Pc.groupby("medio_grupo", observed=True)["total_pedido"].sum().reset_index())
            fig = px.pie(mp, values="total_pedido", names="medio_grupo", hole=0.62, title="Facturación por medio de pago",
                         color="medio_grupo", color_discrete_map={
                             "Mercado Pago": "#009EE3", "Mobbex": "#A78BFA", "Reversso": "#F472B6", "Transferencia": "#34D399",
                             "Otros": "#64748B", "MeLi · Tarjeta de crédito": "#FFE600", "MeLi · Débito": "#FDE68A",
                             "MeLi · Dinero en cuenta": "#FBBF24", "MeLi · Efectivo": "#F59E0B", "MeLi · Otros": "#CA8A04"})
            fig.update_traces(textinfo="percent", marker=dict(line=dict(color="#060A13", width=2)),
                              hovertemplate="%{label}<br>$%{value:,.0f}<extra></extra>")
            st.plotly_chart(estilo(fig, 400), width="stretch")
        with g2:
            cu = Pc.groupby(["cuotas_grupo", "canal"], observed=True).size().rename("ped").reset_index()
            cu["pct"] = cu["ped"] / cu.groupby("canal", observed=True)["ped"].transform("sum") * 100
            cu = a_str(cu)
            orden = [c for c in ORDEN_CUOTAS if c in set(cu["cuotas_grupo"])] + sorted(set(cu["cuotas_grupo"]) - set(ORDEN_CUOTAS))
            fig = px.bar(cu, x="cuotas_grupo", y="pct", color="canal", barmode="group", color_discrete_map=COLOR_CANAL,
                         category_orders={"cuotas_grupo": orden}, title="Pedidos por financiación (% dentro de cada canal)",
                         text_auto=".0f", custom_data=["ped"])
            fig.update_traces(marker_line_width=0, hovertemplate="%{x}<br>%{y:.1f}% · %{customdata[0]} pedidos<extra></extra>")
            fig.update_layout(xaxis_title="", yaxis_title="% de pedidos", bargap=0.25)
            st.plotly_chart(estilo(fig, 400), width="stretch")

# ==============================================================================
# TAB 5 · OPERACIONES
# ==============================================================================
with tab_ops:
    sel_o = selector_canal("ops_canal")
    Po = por_canal(P, sel_o)
    if Po.empty:
        st.info("Sin ventas para este canal.")
    else:
        env = Po[(Po["estado"] == "Enviado") & Po["fecha_despacho"].notna()].copy()
        if not env.empty:
            fc_ = np.array(env["fecha"].dt.date.tolist(), dtype="datetime64[D]")
            fd_ = np.array(env["fecha_despacho"].dt.date.tolist(), dtype="datetime64[D]")
            env["lt"] = np.maximum(np.busday_count(fc_, fd_), 0)

        # ---------- LOGÍSTICA ----------
        seccion("Logística", "Estado de despachos y eficiencia de depósito",
            "Órdenes netas del período. SLA = días hábiles entre la compra y el despacho (excluye sábados y domingos).")
        enviadas = Po[Po["estado"] == "Enviado"]
        pend = Po[Po["estado"].isin(["En preparación", "Pendiente"])]
        lt_prom = env["lt"].mean() if not env.empty else 0
        pct_24 = (env["lt"] <= 1).mean() * 100 if not env.empty else 0
        ck = st.columns(4)
        ck[0].markdown(kpi_card("% enviadas", f"{fmt_dec(len(enviadas) / len(Po) * 100)}%", "",
                                split_html(por_canal_vals(enviadas, "ords")), "#34D399", sm=True), unsafe_allow_html=True)
        ck[1].markdown(kpi_card("Pendientes de despacho", fmt_num(len(pend)), "",
                                split_html(por_canal_vals(pend, "ords")), "#FBBF24", sm=True), unsafe_allow_html=True)
        ck[2].markdown(kpi_card("Lead time promedio", f"{fmt_dec(lt_prom, 2)} días háb.", "", "", "#A78BFA", sm=True),
                       unsafe_allow_html=True)
        ck[3].markdown(kpi_card("Despachadas ≤ 24 hs háb.", f"{fmt_dec(pct_24)}%", "", "", "#22D3EE", sm=True),
                       unsafe_allow_html=True)
        st.write("")

        g1, g2 = st.columns(2)
        with g1:
            if sel_o == "Consolidado":
                es = a_str(Po.groupby(["canal", "estado"], observed=True).size().rename("n").reset_index())
                es["txt"] = es["n"].map(fmt_num)
                fig = px.bar(es, x="canal", y="n", color="estado", color_discrete_map=COLOR_ESTADO, title="Estados de envío por canal",
                             text="txt")
                fig.update_traces(marker_line_width=0)
                fig.update_layout(xaxis_title="", yaxis_title="Órdenes", bargap=0.4)
            else:
                es = a_str(Po.groupby("estado", observed=True).size().rename("n").reset_index())
                fig = px.pie(es, values="n", names="estado", hole=0.62, color="estado", color_discrete_map=COLOR_ESTADO,
                             title="Estados de envío")
                fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="#060A13", width=2)))
            st.plotly_chart(estilo(fig, 380), width="stretch")
        with g2:
            if env.empty:
                st.info("No hay despachos con fecha registrada para calcular el SLA.")
            else:
                tramos = {0: "Mismo día", 1: "24 hs háb.", 2: "48 hs háb."}
                env["tramo"] = env["lt"].map(lambda x: tramos.get(int(x), "+48 hs háb."))
                orden_t = ["Mismo día", "24 hs háb.", "48 hs háb.", "+48 hs háb."]
                sl = env.groupby(["canal", "tramo"], observed=True).size().rename("n").reset_index()
                sl["pct"] = sl["n"] / sl.groupby("canal", observed=True)["n"].transform("sum") * 100
                sl = a_str(sl)
                fig = px.bar(sl, x="tramo", y="pct", color="canal", barmode="group", color_discrete_map=COLOR_CANAL,
                             category_orders={"tramo": orden_t}, text_auto=".0f", custom_data=["n"],
                             title="Eficiencia de depósito (SLA) · % de órdenes despachadas")
                fig.update_traces(marker_line_width=0, hovertemplate="%{x}<br>%{y:.1f}% · %{customdata[0]} órdenes<extra></extra>")
                fig.update_layout(xaxis_title="", yaxis_title="% de órdenes", bargap=0.25)
                st.plotly_chart(estilo(fig, 380), width="stretch")

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
