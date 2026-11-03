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
st.set_page_config(page_title="Distrinando | Centro de datos", page_icon="📊",
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
ORDEN_ENVIO = ["Esperando pago", "Pendiente", "Listo para despachar", "Despachado", "En camino", "En reparto", "Listo para retirar",
               "Intento fallido", "Entregado", "No entregado", "Devolución", "Cancelado"]
COLOR_ENVIO = {"Esperando pago": "#94A3B8", "Pendiente": "#F87171", "Listo para despachar": "#FBBF24", "Despachado": "#38BDF8", "En camino": "#22D3EE",
               "En reparto": "#A78BFA", "Listo para retirar": "#818CF8", "Intento fallido": "#F472B6", "Entregado": "#34D399",
               "No entregado": "#EF4444", "Devolución": "#FB923C", "Cancelado": "#64748B"}
ENV_PEND = {"Pendiente", "Listo para despachar"}
ENV_CURSO = {"Despachado", "En camino", "En reparto", "Listo para retirar", "Intento fallido"}
ENV_DESP = ENV_CURSO | {"Entregado", "No entregado", "Devolución"}
ENV_PROB = {"Intento fallido", "No entregado", "Devolución"}
# Estado de pago (Shopify financial_status): vencido/anulado = no es venta; pendiente/reintegrado = no se despacha
PAGO_EXCLUIR = {"expired", "voided"}
PAGO_SIN_DESPACHO = {"pending", "authorized", "partially_paid", "refunded"}
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
.ftable .sep { border-left:1px solid var(--border); }
.ftable.compact td, .ftable.compact th { padding-left:9px; padding-right:9px; }
.ftable tr.grp-h th { font-size:10px; padding:8px 12px 2px; border-bottom:none; }
.ftable tr:hover td { background:rgba(34,211,238,.05); }
.ftable td.strong { font-weight:700; color:#F8FAFC; }
.ftable tr.total td { font-weight:800; color:#F8FAFC; background:rgba(148,163,184,.06); }
.grp-row { display:grid; gap:10px; align-items:center; padding:10px 14px; border-bottom:1px solid rgba(148,163,184,.07); font-size:13px; color:#E5E7EB; }
.grp-row > div { text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.grp-row > div:first-child, .grp-row > div:nth-child(2) { text-align:left; }
.grp-head > div { white-space:normal; line-height:1.25; }
.grp-head { color:var(--muted); font-weight:700; font-size:10.5px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid var(--border); padding-left:34px; }
details.grp > summary { list-style:none; cursor:pointer; position:relative; padding-left:34px; }
details.grp > summary::-webkit-details-marker { display:none; }
details.grp > summary::before { content:"›"; position:absolute; left:14px; top:50%; transform:translateY(-50%); color:#22D3EE; font-size:18px; font-weight:800; transition:transform .15s; }
details.grp[open] > summary::before { transform:translateY(-50%) rotate(90deg); }
details.grp > summary:hover { background:rgba(34,211,238,.05); }
details.grp[open] > summary { background:rgba(34,211,238,.07); }
.grp-tit { display:flex; align-items:center; gap:10px; }
.grp-tit img { width:38px; height:38px; object-fit:contain; background:#fff; border-radius:8px; flex:none; }
.grp-tit span { display:flex; flex-direction:column; overflow:hidden; }
.grp-tit b { overflow:hidden; text-overflow:ellipsis; color:#F8FAFC; }
.grp-tit small { color:var(--muted); font-size:11px; overflow:hidden; text-overflow:ellipsis; }
.grp-det { background:rgba(2,6,23,.45); font-size:12px; }
.grp-det th { font-size:9.5px; padding:8px 10px; }
.grp-det td { padding:7px 10px; }
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
    # 💳 Estado de pago: los pedidos con pago vencido o anulado no son ventas -> se excluyen de todo el dashboard.
    #    Los que todavía esperan el pago (o se reintegraron) no cuentan como pendientes de despacho.
    df["estado_pago"] = (df["estado_pago"] if "estado_pago" in df.columns else pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    df = df[~df["estado_pago"].isin(PAGO_EXCLUIR)].copy()
    sin_pago = df["estado_pago"].isin(PAGO_SIN_DESPACHO) & df["envio_estado"].astype(str).isin(ENV_PEND)
    df.loc[sin_pago, "envio_estado"] = "Esperando pago"
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
    out = {c: {m: {"unidades": int((v or {}).get("unidades", 0) or 0), "facturacion": int((v or {}).get("facturacion", 0) or 0)}
               for m, v in (base.get(c) or {}).items()} for c in CANALES}
    if isinstance(o.get("cyber"), dict):   # meta del Cyber Monday (se guarda en el mismo archivo)
        det = o["cyber"].get("detalle") or {}
        out["cyber"] = {"facturacion": int(o["cyber"].get("facturacion", 0) or 0),
                        "detalle": {c: {m: int(v or 0) for m, v in (det.get(c) or {}).items()} for c in CANALES}}
    return out


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
         "<div style='font-size:11px;color:#8B95A7;letter-spacing:3px;text-transform:uppercase;margin-top:4px'>E-commerce · Centro de datos</div></div>")
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
     "<div class='hero-title'>Centro de datos</div>"
     f"<div class='hero-sub'>Venta neta consolidada · <b>{' + '.join(canales_con_datos)}</b> · <b>{len(marcas_sel)}</b> marcas · <b>{rango_txt}</b></div></div>"
     f"<div class='live'><span class='live-dot'></span>EN VIVO · {ahora:%H:%M} hs</div></div>")

if P.empty:
    st.info("No hay ventas para los filtros seleccionados.")
    st.stop()

_tabs = [":material/space_dashboard: Resumen", ":material/flag: Metas & Forecast", ":material/local_mall: Productos",
         ":material/inventory_2: Stock & Publicaciones", ":material/payments: Comercial", ":material/campaign: Publicidad MeLi",
         ":material/group: Clientes"]
# Post-venta MeLi (devoluciones, reclamos, cancelaciones): solo estos usuarios
VER_POSTVENTA = {"afredes", "lruiz", "maguirre"}
VE_PV = str(AUTH.get("usuario", "")).lower() in VER_POSTVENTA
VE_CYBER = VE_PV   # Cyber Monday: mismos usuarios (lruiz y afredes)
if VE_CYBER:
    _tabs.insert(0, ":material/local_fire_department: Cyber Monday")
if VE_PV:
    _tabs.append(":material/assignment_return: Post-venta MeLi")
if ES_ADMIN:  # Operaciones (logística) solo para super admins
    _tabs.append(":material/local_shipping: Operaciones")
_t = st.tabs(_tabs)
_o = 1 if VE_CYBER else 0
tab_cyber = _t[0] if VE_CYBER else None
tab_res, tab_metas, tab_prod, tab_stock, tab_com, tab_ads, tab_cli = _t[_o:_o + 7]
_i = _o + 7
tab_pv = _t[_i] if VE_PV else None
_i += 1 if VE_PV else 0
tab_ops = _t[_i] if ES_ADMIN else None

# ==============================================================================
# TAB 1 · RESUMEN
# ==============================================================================
def dias_habiles(desde, hasta):
    a = np.array(pd.Series(desde).dt.date.tolist(), dtype="datetime64[D]")
    b = np.array(pd.Series(hasta).dt.date.tolist(), dtype="datetime64[D]") if not isinstance(hasta, type(hoy)) else np.datetime64(hasta)
    return np.maximum(np.busday_count(a, b), 0)


with tab_res:
    # ---------- QUÉ ATENDER HOY ----------
    alertas = []
    try:
        _cat, _pub, _ads = load_aux("catalogo_stock.csv"), load_aux("meli_publicaciones.csv"), load_aux("meli_ads_items.csv")
        if not _cat.empty:
            _c = _cat[_cat["marca"].isin(marcas_sel)].copy()
            _c["stock"] = pd.to_numeric(_c["stock"], errors="coerce").fillna(0).clip(lower=0)
            _stk = _c.groupby(["marca", "modelo_color"])["stock"].sum()
            _v = base_net[(base_net["dia"] > hoy - timedelta(days=30)) & (base_net["modelo_color"].astype(str) != "S/D") & (base_net["cantidad"] > 0)]
            _vel = _v.assign(marca=_v["marca"].astype(str), modelo_color=_v["modelo_color"].astype(str)).groupby(["marca", "modelo_color"])["cantidad"].sum() / 30
            _j = pd.concat([_vel.rename("vel"), _stk.rename("stock")], axis=1, join="inner")
            alertas.append(("Agotados con demanda", int((_j["stock"] <= 0).sum()), "modelos en 0 que vendieron en 30 días", "Stock & Publicaciones", "#F87171"))
            alertas.append(("Stock crítico", int(((_j["stock"] > 0) & (_j["stock"] / _j["vel"] < 15)).sum()), "modelos con menos de 15 días de stock", "Stock & Publicaciones", "#FB923C"))
        if not _ads.empty and not _pub.empty:
            _a = _ads[_ads["marca"].isin(marcas_sel) & (_ads["estado_ad"] == "active")].merge(_pub[["item_id", "stock"]], on="item_id", how="left")
            _sin = _a[pd.to_numeric(_a["stock"], errors="coerce") <= 0]
            _g7 = pd.to_numeric(_sin.get("m7_cost", pd.Series(dtype=float)), errors="coerce").sum()
            alertas.append(("Anuncios sin stock MeLi", len(_sin), f"activos en Product Ads · gastaron {fmt_compact(_g7)} en 7 días", "Publicidad MeLi", "#F472B6"))
        if not _pub.empty and "catalogo_estado" in _pub.columns:
            _cp = _pub[_pub["marca"].isin(marcas_sel) & (_pub["estado"] == "active") & (_pub["catalogo_estado"].astype(str) == "competing")]
            alertas.append(("Catálogo perdiendo", len(_cp), "publicaciones que no ganan la compra", "Stock & Publicaciones", "#FFE600"))
        if ES_ADMIN and "envio_estado" in P.columns:
            _pe = P[P["envio_estado"].astype(str).isin(ENV_PEND)]
            _dh = dias_habiles(_pe["fecha"], hoy) if len(_pe) else np.array([])
            _n = int(((_dh >= 3) & (_dh <= 20)).sum())
            alertas.append(("Despachos demorados", _n, "sin salir hace 3 a 20 días hábiles", "Operaciones", "#EF4444"))
    except Exception:
        alertas = []
    if alertas:
        seccion("Prioridades", "Qué atender hoy", "Alertas cruzadas de stock, publicidad, catálogo y logística. El detalle está en cada pestaña.")
        ca = st.columns(len(alertas))
        for col, (tit, n, txt, tab_, colr) in zip(ca, alertas):
            est_ = "<span class='delta up'>✓ todo en orden</span>" if n == 0 else f"<span class='delta down'>{txt}</span>"
            col.markdown(kpi_card(tit, fmt_num(n), est_, f"<div class='split-legend' style='margin-top:10px'><span>→ {tab_}</span></div>",
                                  "#34D399" if n == 0 else colr, sm=True), unsafe_allow_html=True)

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
                if isinstance(objetivos.get("cyber"), dict):
                    nuevo["cyber"] = objetivos["cyber"]
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
        tot_u, tot_ou, tot_fu, tot_ur = 0, 0, 0, 0
        for m in marcas_sel:
            Pm_ = Psem[Psem["marca"] == m]
            venta = Pm_["total_pedido"].sum()
            uni = Pm_["unidades"].sum()
            obj = meta(objetivos, sc_f, [m], "facturacion")
            fc = venta / dias_trans * dias_tot if dias_trans > 0 else 0
            gap = obj - venta
            obj_u = meta(objetivos, sc_f, [m], "unidades")
            fcu = uni / dias_trans * dias_tot if dias_trans > 0 else 0
            gap_u = obj_u - uni
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
            # Unidades: si hay meta de unidades, el ritmo necesario sale de esa meta; si no, de la brecha en $ / precio promedio
            if obj_u > 0 and dias_rest > 0:
                ur = int(np.ceil(max(gap_u, 0) / div_r))
            if obj_u <= 0:
                estado_u = "<span class='pill warn'>Sin meta</span>"
            elif gap_u <= 0:
                estado_u = "<span class='pill ok'>✓ Cumplida</span>"
            else:
                cls_u = "ok" if fcu >= obj_u else ("warn" if fcu >= obj_u * 0.8 else "bad")
                estado_u = f"<span class='pill {cls_u}'>Faltan {fmt_num(gap_u)} un.</span>"
            pct_u = uni / obj_u * 100 if obj_u else 0
            tot_u, tot_ou, tot_fu, tot_ur = tot_u + uni, tot_ou + obj_u, tot_fu + fcu, tot_ur + ur
            pct = venta / obj * 100 if obj else 0
            filas += (f"<tr><td class='strong'><span class='dot' style='background:{PALETA_MARCAS.get(m, '#94A3B8')}'></span>{m}</td>"
                      f"<td>{fmt_ars(venta)}</td><td>{fmt_ars(obj)}</td><td>{pct:.0f}%</td>"
                      f"<td style='color:#22D3EE;font-weight:700'>{fmt_ars(fc)}</td><td>{estado}</td>"
                      f"<td style='color:#FBBF24;font-weight:700'>{fmt_ars(rr) if rr > 0 else '—'}</td>"
                      f"<td class='sep'>{fmt_num(uni)}</td><td>{fmt_num(obj_u) if obj_u else '—'}</td><td>{f'{pct_u:.0f}%' if obj_u else '—'}</td>"
                      f"<td style='color:#22D3EE;font-weight:700'>{fmt_num(fcu)}</td><td>{estado_u}</td>"
                      f"<td style='color:#F472B6;font-weight:700'>{(fmt_num(ur) + ' un.') if ur > 0 else '—'}</td></tr>")
        filas += (f"<tr class='total'><td>Total</td><td>{fmt_ars(tot_v)}</td><td>{fmt_ars(tot_o)}</td>"
                  f"<td>{(tot_v / tot_o * 100 if tot_o else 0):.0f}%</td><td>{fmt_ars(tot_f)}</td><td></td><td></td>"
                  f"<td class='sep'>{fmt_num(tot_u)}</td><td>{fmt_num(tot_ou) if tot_ou else '—'}</td>"
                  f"<td>{f'{tot_u / tot_ou * 100:.0f}%' if tot_ou else '—'}</td><td>{fmt_num(tot_fu)}</td><td></td>"
                  f"<td>{(fmt_num(tot_ur) + ' un.') if tot_ur > 0 else ''}</td></tr>")
        html("<div class='tbl-wrap'><table class='ftable compact'><thead>"
             "<tr class='grp-h'><th></th><th colspan='6' style='text-align:center;color:#22D3EE'>Facturación</th>"
             "<th colspan='6' class='sep' style='text-align:center;color:#F472B6'>Unidades</th></tr>"
             "<tr><th>Marca</th><th>Venta acum.</th><th>Objetivo</th><th>Avance</th>"
             f"<th>Proyección</th><th>Brecha</th><th>Necesario $/{etq}</th>"
             f"<th class='sep'>Vendidas</th><th>Objetivo</th><th>Avance</th><th>Proyección</th><th>Brecha</th><th>Necesario un./{etq}</th></tr></thead><tbody>"
             + filas + "</tbody></table></div>")
        st.write("")
        cf = st.columns(4)
        div_g = dias_trans * 24.0 if contra else dias_trans
        cf[0].markdown(kpi_card("Tiempo consumido", f"{fmt_dec(dias_trans)} de {dias_tot:.0f} días", "", "", "#A78BFA", sm=True),
                       unsafe_allow_html=True)
        cf[1].markdown(kpi_card("Tiempo restante", f"{fmt_dec(dias_rest)} días" if dias_rest >= 1 else f"{fmt_dec(dias_rest * 24)} horas",
                                "", "", "#FBBF24", sm=True), unsafe_allow_html=True)
        cf[2].markdown(kpi_card(f"Ritmo neto actual (/{etq})", fmt_ars(tot_v / div_g if dias_trans > 0 else 0), "", "",
                                COLOR_SCOPE[sc_f], sm=True), unsafe_allow_html=True)
        cf[3].markdown(kpi_card(f"Ritmo unidades (/{etq})", f"{fmt_dec(tot_u / div_g if dias_trans > 0 else 0)} un.", "",
                                f"<div class='split-legend' style='margin-top:10px'><span>proyección {fmt_num(tot_fu)} un.</span></div>",
                                "#F472B6", sm=True), unsafe_allow_html=True)
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

        # ---------- TICKET ALTO Y FINANCIACIÓN ----------
        seccion("Ticket alto", "¿Cómo se pagan los tickets altos?",
                "Pedidos por rango de ticket: cuántos hay, con qué medio de pago y en cuántas cuotas. "
                "Las cuotas solo las informa MercadoLibre (Shopify no trae la cantidad de cuotas en el pedido).")
        TRAMOS_TK = [(0, 50000, "Menos de 50 mil"), (50000, 100000, "50 a 100 mil"), (100000, 150000, "100 a 150 mil"),
                     (150000, 250000, "150 a 250 mil"), (250000, 300000, "250 a 300 mil"), (300000, 10**12, "300 mil o más")]
        NOM_TK = [t[2] for t in TRAMOS_TK]
        T_ = Pc.copy()
        T_["canal"] = T_["canal"].astype(str)
        T_["medio_grupo"] = T_["medio_grupo"].astype(str)
        T_["tramo"] = pd.cut(T_["total_pedido"], bins=[t[0] for t in TRAMOS_TK] + [10**12], labels=NOM_TK, right=False)
        T_["n_cuotas"] = T_["cuotas_grupo"].astype(str).str.extract(r"(\d+)\s*cuota")[0].astype(float)
        T_.loc[T_["cuotas_grupo"].astype(str) == "1 pago", "n_cuotas"] = 1
        es_cred = T_["medio_grupo"].isin(["MeLi · Tarjeta de crédito", "MeLi · Mercado Crédito"])
        T_["cred"] = es_cred
        hay_cuotas = (T_["canal"] == "MercadoLibre").any()

        filas = ""
        for nom in NOM_TK:
            d_ = T_[T_["tramo"] == nom]
            if d_.empty:
                continue
            ml_ = d_[(d_["canal"] == "MercadoLibre")]
            cr_ = ml_[ml_["cred"] & ml_["n_cuotas"].notna()]
            prom = cr_["n_cuotas"].mean() if len(cr_) else np.nan
            prom_p = np.average(cr_["n_cuotas"], weights=cr_["total_pedido"]) if len(cr_) and cr_["total_pedido"].sum() else np.nan
            pc_cred = len(ml_[ml_["cred"]]) / len(ml_) * 100 if len(ml_) else np.nan
            dist = {k_: (cr_["n_cuotas"].between(*rg).sum() / len(cr_) * 100 if len(cr_) else np.nan)
                    for k_, rg in [("1", (1, 1)), ("2-3", (2, 3)), ("4-6", (4, 6)), ("9+", (7, 99))]}
            fp = lambda v: (fmt_dec(v, 0) + "%") if pd.notna(v) else "—"
            filas += (f"<tr><td class='strong' style='text-align:left'>{nom}</td><td>{fmt_num(len(d_))}</td>"
                      f"<td>{fmt_dec(len(d_) / len(T_) * 100)}%</td><td>{fmt_ars(d_['total_pedido'].sum())}</td><td>{fmt_ars(d_['total_pedido'].mean())}</td>"
                      f"<td class='sep'>{fmt_num(len(ml_))}</td><td>{fp(pc_cred)}</td>"
                      f"<td class='strong' style='color:#FFE600'>{fmt_dec(prom, 1) if pd.notna(prom) else '—'}</td><td>{fmt_dec(prom_p, 1) if pd.notna(prom_p) else '—'}</td>"
                      f"<td>{fp(dist['1'])}</td><td>{fp(dist['2-3'])}</td><td>{fp(dist['4-6'])}</td><td>{fp(dist['9+'])}</td></tr>")
        html("<div class='tbl-wrap'><table class='ftable compact'><thead>"
             "<tr class='grp-h'><th></th><th colspan='4' style='text-align:center;color:#22D3EE'>Todos los pedidos del canal elegido</th>"
             "<th colspan='8' class='sep' style='text-align:center;color:#FFE600'>MercadoLibre · financiación</th></tr>"
             "<tr><th style='text-align:left'>Ticket</th><th>Pedidos</th><th>% pedidos</th><th>Facturación</th><th>Ticket prom.</th>"
             "<th class='sep'>Pedidos MeLi</th><th>% con crédito</th><th>Cuotas prom.</th><th>Cuotas prom. ($)</th>"
             f"<th>1 pago</th><th>2-3 cuotas</th><th>4-6 cuotas</th><th>9 o más</th></tr></thead><tbody>{filas}</tbody></table></div>")
        st.caption("Cuotas prom. = promedio de cuotas de los pagos con tarjeta de crédito o Mercado Crédito. "
                   "Cuotas prom. ($) = ponderado por el monto del pedido. Las columnas de cuotas son % sobre esos pagos.")

        # Ventas mensuales por medio de pago para los rangos elegidos
        tk1, tk2 = st.columns([1.8, 1])
        with tk1:
            tramos_sel = st.pills("Rangos de ticket", NOM_TK, selection_mode="multi", default=["150 a 250 mil", "300 mil o más"],
                                  key="tk_tramos") or ["300 mil o más"]
        with tk2:
            vista_tk = st.segmented_control("Ver", ["Pedidos", "Facturación"], default="Pedidos", key="tk_vista") or "Pedidos"
        for nom in [n_ for n_ in NOM_TK if n_ in tramos_sel]:
            d_ = T_[T_["tramo"] == nom].copy()
            if d_.empty:
                st.caption(f"{nom}: sin pedidos en el período.")
                continue
            d_["mes"] = d_["fecha"].dt.tz_localize(None).dt.to_period("M").astype(str)
            val = "total_pedido"
            pv_ = (d_.pivot_table(index="mes", columns="medio_grupo", values=val, aggfunc="count" if vista_tk == "Pedidos" else "sum", fill_value=0)
                   .sort_index())
            pv_ = pv_[pv_.sum().sort_values(ascending=False).index]
            pv_["Total"] = pv_.sum(axis=1)
            fmt_v = fmt_num if vista_tk == "Pedidos" else fmt_compact
            cab = "".join(f"<th>{c_}</th>" for c_ in pv_.columns)
            filas = ""
            for mes_, r_ in pv_.iterrows():
                filas += f"<tr><td class='strong' style='text-align:left'>{pd.Period(mes_).strftime('%m/%Y')}</td>" + "".join(
                    ("<td class='strong'>" if c_ == "Total" else "<td>") + (fmt_v(v_) if v_ else "·") + "</td>" for c_, v_ in r_.items()) + "</tr>"
            tot_ = pv_.sum()
            filas += "<tr class='total'><td>Total</td>" + "".join(f"<td>{fmt_v(v_)}</td>" for v_ in tot_.values) + "</tr>"
            prom_cu = d_.loc[d_["cred"] & d_["n_cuotas"].notna(), "n_cuotas"].mean()
            st.markdown((f"**Ticket {nom}** · {fmt_num(len(d_))} pedidos · ticket promedio {fmt_ars(d_['total_pedido'].mean())}"
                         + (f" · en MeLi se pagan en **{fmt_dec(prom_cu, 1)} cuotas** en promedio" if pd.notna(prom_cu) else "")).replace("$", "\\$"))
            html(f"<div class='tbl-wrap'><table class='ftable compact'><thead><tr><th style='text-align:left'>Mes</th>{cab}</tr></thead>"
                 f"<tbody>{filas}</tbody></table></div>")
        st.caption("Meses según el período del filtro de la izquierda: elegí 'Todo' para ver todos los meses (MercadoLibre tiene datos desde el 1/09). "
                   "En Tienda Online el medio de pago dice la pasarela (Mercado Pago, Mobbex, transferencia), no si fue tarjeta o dinero en cuenta.")

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
    # Campañas reales (las que el anunciante creó). Los anuncios "idle" quedan en una campaña técnica de MeLi = sin campaña.
    camp_reales = set(a_camp["campaign_id"]) if not a_camp.empty else set()
    a_dia = load_aux("meli_ads_diario.csv")
    a_items = load_aux("meli_ads_items.csv")
    _mets = ["cost", "prints", "clicks", "total_amount", "direct_amount", "indirect_amount", "units_quantity",
             "direct_units_quantity", "indirect_units_quantity", "organic_units_quantity", "organic_units_amount"]
    # Plan B: si MeLi no devolvió campañas o el diario, se arma todo con los anuncios (métricas de 30 días)
    if a_camp.empty and not a_items.empty:
        _act = a_items.assign(_a=(a_items["estado_ad"] == "active").astype(int)).groupby(["marca", "campaign_id"])["_a"].sum().reset_index()
        a_camp = _act.assign(nombre=_act["marca"] + " · Campaña " + _act["campaign_id"].astype(str),
                             estado=np.where(_act["_a"] > 0, "active", "sin anuncios activos")).drop(columns="_a")
    modo30 = a_dia.empty or "marca" not in a_dia.columns or "fecha" not in a_dia.columns
    if modo30 and not a_items.empty:
        _upd = pd.to_datetime(a_items["actualizado"].iloc[0], errors="coerce") if "actualizado" in a_items.columns else pd.NaT
        _fin = (_upd.date() if pd.notna(_upd) else hoy) - timedelta(days=1)
        a_dia = a_items[["marca", "campaign_id"]].copy()
        for m_ in _mets:
            a_dia[m_] = pd.to_numeric(a_items.get(f"m30_{m_}", 0), errors="coerce").fillna(0)
        a_dia["fecha"] = _fin.isoformat()

    if a_dia.empty and a_items.empty:
        st.info("Todavía no hay datos de publicidad. Se generan con el workflow diario (Publicidad de MercadoLibre). "
                "Si el log muestra error 403, hay que habilitar el permiso de 'Publicidad' en la app de MeLi.")
    else:
        a_dia = a_dia[a_dia["marca"].isin(marcas_sel)].copy()
        a_dia["dia"] = pd.to_datetime(a_dia["fecha"]).dt.date
        a_camp = a_camp[a_camp["marca"].isin(marcas_sel)].copy() if not a_camp.empty else a_camp
        nombres_c = dict(zip(a_camp["campaign_id"], a_camp["nombre"])) if not a_camp.empty else {}
        f_ads_min, f_ads_max = a_dia["dia"].min(), a_dia["dia"].max()
        if modo30:
            a0, a1 = f_ads_max - timedelta(days=29), f_ads_max
            a_dia["dia"] = a1
        else:
            a0, a1 = max(d0, f_ads_min), min(d1, f_ads_max)
            if a0 > a1:
                a0, a1 = max(f_ads_min, f_ads_max - timedelta(days=29)), f_ads_max
        nd = (a1 - a0).days + 1
        pa0, pa1 = a0 - timedelta(days=nd), a0 - timedelta(days=1)

        # Etiqueta legible de cada campaña: "Marca · Nombre" (+ ID para distinguir)
        if not a_camp.empty:
            _nom = a_camp["nombre"].fillna("").astype(str)
            _tiene_marca = [n.startswith(f"{m} ·") for n, m in zip(_nom, a_camp["marca"])]
            a_camp["etiqueta"] = [n if tm else f"{m} · {n}" for n, m, tm in zip(_nom, a_camp["marca"], _tiene_marca)]
            a_camp["etiqueta"] = [e if "Campaña " in e else f"{e}  ·  #{cid}" for e, cid in zip(a_camp["etiqueta"], a_camp["campaign_id"])]
            nombres_c = dict(zip(a_camp["campaign_id"], a_camp["etiqueta"]))
            estado_c = dict(zip(a_camp["campaign_id"], a_camp["estado"].astype(str)))
        else:
            estado_c = {}
        marcas_ads_disp = [m for m in MARCAS_BASE if m in set(a_dia["marca"])] + sorted(set(a_dia["marca"]) - set(MARCAS_BASE))
        f1, f2 = st.columns([1.6, 1])
        with f1:
            marcas_ads = st.pills("Marcas", marcas_ads_disp, selection_mode="multi", default=marcas_ads_disp, key="ads_marcas") or marcas_ads_disp
        with f2:
            ver_est = st.segmented_control("Estado de campaña", ["Todas", "Activas", "Pausadas"], default="Todas", key="ads_estado") or "Todas"
        camp_opts = [c_ for c_ in a_dia.loc[a_dia["marca"].isin(marcas_ads), "campaign_id"].unique()
                     if ver_est == "Todas" or (estado_c.get(c_, "active") == "active") == (ver_est == "Activas")]
        camp_opts = sorted(camp_opts, key=lambda x: str(nombres_c.get(x, x)))
        f1, f2 = st.columns([1.6, 1])
        with f2:
            if modo30:
                html("<div class='hero-sub' style='margin-top:30px'>Período fijo: últimos 30 días (sin detalle diario).</div>")
            else:
                per_ads = st.segmented_control("Período de la publicidad", ["7D", "14D", "30D", "60D", "90D", "Rango"], default="30D", key="ads_periodo") or "30D"
                if per_ads == "Rango":
                    rg = st.date_input("Desde / hasta", value=(max(f_ads_min, f_ads_max - timedelta(days=29)), f_ads_max),
                                       min_value=f_ads_min, max_value=f_ads_max, key="ads_rango", format="DD/MM/YYYY")
                    if isinstance(rg, (list, tuple)) and len(rg) == 2:
                        a0, a1 = rg
                    elif isinstance(rg, (list, tuple)) and len(rg) == 1:
                        a0 = a1 = rg[0]
                else:
                    a1 = f_ads_max
                    a0 = max(f_ads_min, a1 - timedelta(days=int(per_ads[:-1]) - 1))
                nd = (a1 - a0).days + 1
                pa0, pa1 = a0 - timedelta(days=nd), a0 - timedelta(days=1)
        with f1:
            camp_elegidas = st.multiselect(f"Campañas ({len(camp_opts)} disponibles)", camp_opts, default=[], key="ads_camps",
                                           placeholder="Todas las campañas · escribí para buscar por nombre o marca",
                                           format_func=lambda x: str(nombres_c.get(x, x)))
            camp_sel = camp_elegidas or camp_opts
        html(f"<div class='hero-sub'>📅 <b>{a0:%d/%m/%Y} → {a1:%d/%m/%Y}</b> ({nd} días)" + ("" if modo30 else f" · comparado con {pa0:%d/%m} → {pa1:%d/%m}") + " · "
             f"MeLi consolida la publicidad 1 vez por día (datos hasta {f_ads_max:%d/%m}).</div>")
        met_ef = st.segmented_control("Analizar eficiencia por", ["ACOS", "ROAS"], default="ACOS", key="ads_metrica",
                                      help="ACOS = inversión / ventas por ads (más bajo es mejor). ROAS = ventas por ads / inversión (más alto es mejor). "
                                           "Son la misma medida invertida: ACOS 10% = ROAS 10x.") or "ACOS"
        EsR = met_ef == "ROAS"
        dsel = a_dia[a_dia["campaign_id"].isin(camp_sel)]
        cur = dsel[(dsel["dia"] >= a0) & (dsel["dia"] <= a1)]
        if modo30:
            st.warning("MeLi todavía no devolvió el detalle diario de campañas: se muestran los **últimos 30 días** "
                       "sumando los anuncios (sin comparación con el período anterior ni gráfico diario).")
        prv = dsel[(dsel["dia"] >= pa0) & (dsel["dia"] <= pa1)]
        k, kp = _ads_kpis(cur), _ads_kpis(prv)
        hay_prev_ads = (not prv.empty) and pa0 >= f_ads_min
        pv = (lambda x: kp[x]) if hay_prev_ads else (lambda x: None)
        # Venta total MeLi del período (para TACOS y % atribuido a publicidad)
        def _venta_meli(x0, x1):
            b = base_net[(base_net["canal"] == "MercadoLibre") & base_net["marca"].astype(str).isin(marcas_ads) & (base_net["dia"] >= x0) & (base_net["dia"] <= x1)]
            pp = a_pedidos(b)
            return float(pp["total_pedido"].sum()) if len(pp) else 0.0, float(pp["unidades"].sum()) if len(pp) else 0.0
        vm, um = _venta_meli(a0, a1)
        vm_p, _ = _venta_meli(pa0, pa1) if hay_prev_ads else (0, 0)
        tacos = k["cost"] / vm * 100 if vm else 0
        tacos_p = kp["cost"] / vm_p * 100 if vm_p else None

        # ---------- KPIs ----------
        seccion("Mercado Ads", "Rendimiento de la inversión", "Product Ads de MercadoLibre · últimos 30 días." if modo30 else f"Product Ads de MercadoLibre · comparado con los {nd} días anteriores.")
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
        cc[5].markdown(kpi_card("CPM", fmt_ars(k["cpm"]), delta_html(k["cpm"], pv("cpm"), invert=True),
                                "<div class='split-legend' style='margin-top:10px'><span>costo cada 1.000 impresiones</span></div>", "#38BDF8", sm=True), unsafe_allow_html=True)

        # ---------- ORIGEN DE LA VENTA ----------
        seccion("Origen de la venta", "Directa, indirecta y orgánica",
                "Ventas vinculadas a los productos publicitados, según cómo llegó el comprador.")
        org_tot_m = k["total_amount"] + k["organic_units_amount"]
        org_tot_u = k["units_quantity"] + k["organic_units_quantity"]
        origen = [("Directa", "direct_amount", "direct_units_quantity", "#34D399",
                   "Hizo clic en el anuncio y compró ese mismo producto."),
                  ("Indirecta", "indirect_amount", "indirect_units_quantity", "#22D3EE",
                   "Hizo clic en un anuncio y compró otro producto tuyo (hasta 7 días)."),
                  ("Orgánica", "organic_units_amount", "organic_units_quantity", "#A78BFA",
                   "Compró un producto publicitado sin pasar por el anuncio.")]
        co = st.columns(4)
        for col, (lbl, cm_, cu_, colr, expl) in zip(co, origen):
            pm_ = k[cm_] / org_tot_m * 100 if org_tot_m else 0
            col.markdown(kpi_card(f"Venta {lbl.lower()}", fmt_kpi(k[cm_]), delta_html(k[cm_], pv(cm_)),
                                  f"<div class='split-legend' style='margin-top:10px'><span><b>{fmt_num(k[cu_])}</b> unidades</span><span>{fmt_dec(pm_)}% del total</span></div>"
                                  f"<div class='split-legend' style='margin-top:6px'><span>{expl}</span></div>", colr, sm=True), unsafe_allow_html=True)
        co[3].markdown(kpi_card("Total vinculado", fmt_kpi(org_tot_m), "",
                                f"<div class='split-legend' style='margin-top:10px'><span><b>{fmt_num(org_tot_u)}</b> unidades</span>"
                                f"<span>{fmt_dec(k['total_amount'] / org_tot_m * 100 if org_tot_m else 0)}% por ads</span></div>"
                                f"<div class='split-legend' style='margin-top:6px'><span>Directa + indirecta = 'ventas por publicidad'.</span></div>", "#FFE600", sm=True), unsafe_allow_html=True)
        if not modo30:
            og1, og2 = st.columns([1.7, 1])
            vista_o = og2.segmented_control("Ver en", ["Facturación", "Unidades"], default="Facturación", key="ads_origen_v") or "Facturación"
            cols_o = (["direct_amount", "indirect_amount", "organic_units_amount"] if vista_o == "Facturación"
                      else ["direct_units_quantity", "indirect_units_quantity", "organic_units_quantity"])
            to = cur.groupby("dia")[[c_ for c_ in cols_o if c_ in cur.columns]].sum().reset_index()
            to = to.rename(columns=dict(zip(cols_o, ["Directa", "Indirecta", "Orgánica"]))).melt(id_vars="dia", var_name="Origen", value_name="v")
            fig = px.bar(to, x="dia", y="v", color="Origen", title=f"Origen de la venta por día · {vista_o.lower()}",
                         color_discrete_map={"Directa": "#34D399", "Indirecta": "#22D3EE", "Orgánica": "#A78BFA"})
            fig.update_traces(marker_line_width=0)
            fig.update_layout(xaxis_title="", yaxis_title="", bargap=0.2, barmode="stack", hovermode="x unified")
            og1.plotly_chart(estilo(fig, 360), width="stretch")
            with og2:
                vals = [k[c_] for c_ in cols_o]
                fig = go.Figure(go.Pie(labels=["Directa", "Indirecta", "Orgánica"], values=vals, hole=0.62, sort=False,
                                       marker=dict(colors=["#34D399", "#22D3EE", "#A78BFA"]), textinfo="percent"))
                fig.update_layout(title="Participación", showlegend=True,
                                  annotations=[dict(text=(fmt_compact(sum(vals)) if vista_o == "Facturación" else fmt_num(sum(vals)) + " u"),
                                                    showarrow=False, font=dict(size=18, color="#F8FAFC"))])
                st.plotly_chart(estilo(fig, 300), width="stretch")

        # ---------- TENDENCIA + EMBUDO ----------
        from plotly.subplots import make_subplots
        g1, g2 = st.columns([1.7, 1])
        with g1:
          if modo30:
            st.info("El gráfico diario aparece cuando el extractor traiga el detalle por día de las campañas.")
          else:
            td = cur.groupby("dia")[["cost", "total_amount"]].sum().reset_index()
            td["acos"] = np.where(td["total_amount"] > 0, td["cost"] / td["total_amount"] * 100, np.nan)
            td["roas"] = np.where(td["cost"] > 0, td["total_amount"] / td["cost"], np.nan)
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=td["dia"], y=td["cost"], name="Inversión", marker_color="#F472B6", opacity=0.85)
            fig.add_scatter(x=td["dia"], y=td["total_amount"], name="Ventas por ads", line=dict(color="#34D399", width=2.5, shape="spline"))
            fig.add_scatter(x=td["dia"], y=td["roas" if EsR else "acos"], name="ROAS (x)" if EsR else "ACOS %",
                            line=dict(color="#FBBF24", width=2, dash="dot"), secondary_y=True)
            fig.update_layout(title=f"Inversión, ventas y {met_ef} por día", hovermode="x unified", bargap=0.3)
            fig.update_yaxes(title_text="$", secondary_y=False)
            fig.update_yaxes(title_text=met_ef, secondary_y=True, showgrid=False, ticksuffix="x" if EsR else "%", tickformat=".1f", rangemode="tozero")
            st.plotly_chart(estilo(fig, 400), width="stretch")
        with g2:
            fig = go.Figure(go.Funnel(y=["Impresiones", "Clics", "Unidades vendidas"],
                                      x=[k["prints"], k["clicks"], k["units_quantity"]], textinfo="text",
                                      text=[fmt_compact(k["prints"], moneda=False) + "<br>100%",
                                            fmt_num(k["clicks"]) + f"<br>CTR {fmt_dec(k['ctr'], 2)}%",
                                            fmt_num(k["units_quantity"]) + f"<br>CVR {fmt_dec(k['cvr'], 2)}%"],
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
            bm["roas"] = np.where(bm["cost"] > 0, bm["total_amount"] / bm["cost"], 0)
            bm["roas total"] = [vm_marca.get(m, 0) / bm.loc[i, "cost"] if bm.loc[i, "cost"] else 0 for i, m in zip(bm.index, bm["marca"])]
            ml = bm.melt(id_vars="marca", value_vars=["roas", "roas total"] if EsR else ["acos", "tacos"], var_name="m", value_name="pct")
            ml["m"] = ml["m"].str.upper()
            _suf = "x" if EsR else "%"
            fig = px.bar(ml, x="marca", y="pct", color="m", barmode="group", text=ml["pct"].map(lambda v: fmt_dec(v) + _suf),
                         color_discrete_map={"ACOS": "#FBBF24", "TACOS": "#A78BFA", "ROAS": "#22D3EE", "ROAS TOTAL": "#A78BFA"},
                         title="ROAS y ROAS total por marca" if EsR else "ACOS y TACOS por marca")
            fig.update_traces(marker_line_width=0)
            fig.update_layout(xaxis_title="", yaxis_title=_suf, bargap=0.3, legend_title_text="")
            st.plotly_chart(estilo(fig, 380), width="stretch")

        # ---------- CAMPAÑAS ----------
        seccion("Campañas", "Rendimiento y salud de cada campaña",
                f"Participación de impresiones y pérdidas son de los últimos 30 días. La recomendación cruza {met_ef} real vs. objetivo y por qué se pierden impresiones."
                + (" ROAS objetivo = 100 / ACOS objetivo de la campaña." if EsR else ""))
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
                    rec, cls = ("🔻 ROAS bajo el objetivo" if EsR else "🔻 ACOS sobre objetivo") + ": revisar anuncios que gastan sin vender", "bad"
                elif pd.notna(lb) and lb >= 20 and (pd.isna(obj) or pd.isna(acos_r) or acos_r <= obj):
                    rec, cls = f"⬆️ Subir presupuesto: pierde {fmt_dec(lb, 0)}% de impresiones con {met_ef} sano", "ok"
                elif pd.notna(lr) and lr >= 30:
                    rec, cls = f"🎯 Pierde {fmt_dec(lr, 0)}% por ranking: mejorar precio/publicación o " + ("bajar ROAS objetivo" if EsR else "subir ACOS objetivo"), "warn"
                elif r["cost"] > 0 and r["total_amount"] == 0:
                    rec, cls = "⚪ Gasta sin ventas", "bad"
                else:
                    rec, cls = "✅ Mantener", "ok"
                est_cls = "ok" if r.get("estado") == "active" else "warn"
                fpct = lambda v: f"{fmt_dec(v, 0)}%" if pd.notna(v) else "—"
                filas += (f"<tr><td class='strong' style='text-align:left'><span class='dot' style='background:{PALETA_MARCAS.get(r['marca'], '#94A3B8')}'></span>{r['nombre']}<br><small style='color:var(--muted);font-weight:500;margin-left:14px'>{r['marca']}</small></td>"
                          f"<td style='text-align:left;white-space:normal;min-width:230px'><span class='pill {cls}'>{rec}</span></td>"
                          f"<td><span class='pill {est_cls}'>{r.get('estado', '')}</span></td><td>{str(r.get('estrategia', '')).title()}</td>"
                          f"<td>{fmt_ars(pd.to_numeric(r.get('presupuesto'), errors='coerce')) if pd.notna(pd.to_numeric(r.get('presupuesto'), errors='coerce')) else '—'}</td>"
                          + (f"<td>{fmt_dec(100 / obj, 1) + 'x' if pd.notna(obj) and obj else '—'}</td>"
                             f"<td class='strong'>{fmt_dec(r['total_amount'] / r['cost'], 1) + 'x' if r['cost'] else '—'}</td><td>{fpct(acos_r)}</td>"
                             if EsR else
                             f"<td>{fpct(obj)}</td><td class='strong'>{fpct(acos_r)}</td>"
                             f"<td>{fmt_dec(r['total_amount'] / r['cost'], 1) + 'x' if r['cost'] else '—'}</td>") +
                          f"<td>{fmt_ars(r['cost'])}</td><td>{fmt_ars(r['total_amount'])}</td>"
                          f"<td>{fmt_dec(r['clicks'] / r['prints'] * 100, 2) + '%' if r['prints'] else '—'}</td>"
                          f"<td>{fmt_ars(r['cost'] / r['clicks']) if r['clicks'] else '—'}</td>"
                          f"<td>{fmt_dec(r['units_quantity'] / r['clicks'] * 100, 2) + '%' if r['clicks'] else '—'}</td>"
                          f"<td>{fpct(r.get('is_impression_share'))}</td><td>{fpct(lb)}</td><td>{fpct(lr)}</td></tr>")
            html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Campaña</th><th style='text-align:left'>Recomendación</th><th>Estado</th><th>Estrategia</th>"
                 "<th>Presup./día</th>" + ("<th>ROAS obj.</th><th>ROAS real</th><th>ACOS</th>" if EsR else "<th>ACOS obj.</th><th>ACOS real</th><th>ROAS</th>") + "<th>Inversión</th><th>Ventas</th><th>CTR</th><th>CPC</th><th>CVR</th>"
                 "<th>Impr. share</th><th>Pérdida x presup.</th><th>Pérdida x ranking</th></tr></thead>"
                 f"<tbody>{filas}</tbody></table></div>")

        # ---------- PRODUCTOS: EN CAMPAÑA / SIN CAMPAÑA ----------
        seccion("Productos", "Productos y publicidad",
                "Qué publicaciones están en Product Ads y cómo rinden contra el stock, y cuáles con stock no se están publicitando. "
                "Métricas por producto: últimos 30 días (MeLi las informa así por anuncio).")
        pub_a = load_aux("meli_publicaciones.csv")
        cat_a = load_aux("catalogo_stock.csv")
        if not cat_a.empty:
            cat_a = cat_a.copy()
            cat_a["stock"] = pd.to_numeric(cat_a["stock"], errors="coerce").fillna(0).clip(lower=0)
        MAXG = 60

        def _fpct(v, d=0):
            return fmt_dec(v, d) + "%" if pd.notna(v) and np.isfinite(v) else "—"

        def _fcob(v):
            return "∞" if not np.isfinite(v) else f"{v:.0f} d"

        def _fn(v):
            return fmt_num(v) if pd.notna(v) else "—"

        tp1, tp2 = st.tabs([":material/campaign: Productos en campaña", ":material/visibility_off: Productos sin campaña"])
        with tp1:
          if a_items.empty:
            st.info("Sin datos de anuncios.")
          else:
                it = a_items[a_items["marca"].isin(marcas_ads) & a_items["campaign_id"].isin(camp_sel)].copy()
                for c_ in ["m30_cost", "m30_clicks", "m30_prints", "m30_units_quantity", "m30_total_amount", "m7_cost",
                           "m30_direct_units_quantity", "m30_indirect_units_quantity", "m30_organic_units_quantity", "m30_organic_units_amount"]:
                    it[c_] = pd.to_numeric(it[c_], errors="coerce").fillna(0) if c_ in it.columns else 0.0
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
                it["roas30"] = np.where(it["m30_cost"] > 0, it["m30_total_amount"] / it["m30_cost"], np.nan)
                ACC_EF = "🔻 ROAS bajo" if EsR else "🔻 ACOS alto"
                it["cvr30"] = np.where(it["m30_clicks"] > 0, it["m30_units_quantity"] / it["m30_clicks"] * 100, np.nan)
                obj_c = dict(zip(a_camp["campaign_id"], pd.to_numeric(a_camp["acos_objetivo"], errors="coerce"))) if "acos_objetivo" in a_camp.columns else {}
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
                        return ACC_EF
                    if activo and pd.notna(r["acos30"]) and r["acos30"] <= obj and r["cobertura"] >= 30:
                        return "🟢 Escalar"
                    if (not activo and pd.notna(r["stock_meli"]) and r["stock_meli"] <= 0 and pd.notna(r["stock_dep"]) and r["stock_dep"] > 0):
                        return "🔵 Cargar stock en MeLi"
                    if not activo and not sin_stock and pd.notna(r["stock_ref"]) and r["stock_ref"] > 0 and r["vel"] > 0:
                        return "🟣 Reactivar anuncio"
                    return "Mantener"
                it["accion"] = it.apply(accion, axis=1)

                desperdicio7 = it.loc[it["accion"] == "🔴 Pausar: sin stock", "m7_cost"].sum()
                desperdicio30 = it.loc[it["accion"] == "🔴 Pausar: sin stock", "m30_cost"].sum()
                cnt = it["accion"].value_counts()
                n_pm = int((it["estado_ad"] == "paused").sum())
                n_ph = int((it["estado_ad"] == "hold").sum())
                k6 = st.columns(6)
                k6[0].markdown(kpi_card("Anuncios activos", fmt_num((it["estado_ad"] == "active").sum()), f"<span class='delta flat'>{fmt_num(len(it))} en campañas</span>",
                                        f"<div class='split-legend' style='margin-top:10px'><span>⏸️ {fmt_num(n_pm + n_ph)} pausados</span>"
                                        f"<span>{fmt_num(n_pm)} manual · {fmt_num(n_ph)} MeLi</span></div>", "#22D3EE", sm=True), unsafe_allow_html=True)
                k6[1].markdown(kpi_card("🔴 Sin stock y con anuncio", fmt_num(cnt.get("🔴 Pausar: sin stock", 0)), f"<span class='delta down'>gastaron {fmt_compact(desperdicio7)} en 7 días</span>", "", "#EF4444", sm=True), unsafe_allow_html=True)
                k6[2].markdown(kpi_card("🟠 Para reponer", fmt_num(cnt.get("🟠 Reponer: stock crítico", 0)), "<span class='delta flat'>&lt; 15 días de stock</span>", "", "#FB923C", sm=True), unsafe_allow_html=True)
                k6[3].markdown(kpi_card("⚪ Gastan sin vender", fmt_num(cnt.get("⚪ Revisar: gasta sin vender", 0)), "", "", "#94A3B8", sm=True), unsafe_allow_html=True)
                k6[4].markdown(kpi_card(ACC_EF, fmt_num(cnt.get(ACC_EF, 0)),
                                        "<span class='delta flat'>" + ("&lt; objetivo ÷ 1,5" if EsR else "&gt; 1,5x el objetivo") + "</span>", "", "#FBBF24", sm=True), unsafe_allow_html=True)
                k6[5].markdown(kpi_card("🟢 Para escalar", fmt_num(cnt.get("🟢 Escalar", 0)), f"<span class='delta up'>{met_ef} sano y stock &gt; 30 días</span>", "", "#34D399", sm=True), unsafe_allow_html=True)
                if desperdicio30 > 0:
                    st.caption(f"💸 Inversión en anuncios de productos sin stock en los últimos 30 días: **{fmt_ars(desperdicio30)}**.")
                opciones_acc = ["Todas"] + [a for a in ["🔴 Pausar: sin stock", "🟠 Reponer: stock crítico", "⚪ Revisar: gasta sin vender",
                                                        ACC_EF, "🔵 Cargar stock en MeLi", "🟢 Escalar", "🟣 Reactivar anuncio", "Mantener"] if cnt.get(a, 0)]
                ac1, ac2 = st.columns([2.6, 1])
                with ac1:
                    ver_acc = st.segmented_control("Acción", opciones_acc, default="Todas", key=f"ads_accion_{met_ef}") or "Todas"
                with ac2:
                    ver_est_ad = st.segmented_control("Estado del anuncio", ["Todos", "Activos", "Pausados"], default="Todos", key="ads_est_ad",
                                                      help="Pausados = pausados a mano en la campaña + pausados automáticamente por MeLi "
                                                           "(publicación pausada o sin stock).") or "Todos"
                _prio = {"🔴 Pausar: sin stock": 0, "🟠 Reponer: stock crítico": 1, "⚪ Revisar: gasta sin vender": 2, ACC_EF: 3,
                         "🔵 Cargar stock en MeLi": 4, "🟣 Reactivar anuncio": 4, "🟢 Escalar": 5, "Mantener": 6}
                pill = {"🔴": "bad", "🟠": "warn", "⚪": "warn", "🔻": "bad", "🟢": "ok", "🟣": "warn", "🔵": "warn"}
                it["_p"] = it["accion"].map(_prio).fillna(6)
                it["sku"] = it["sku"].fillna("").astype(str)
                it["modelo_color"] = it["modelo_color"].fillna("").astype(str)
                it["talle"] = [sk.rsplit("-", 1)[1] if "-" in sk else "—" for sk in it["sku"]]
                it["grupo"] = [f"{m}|{mc}" if mc else f"{m}|{t}" for m, mc, t in zip(it["marca"], it["modelo_color"], it["titulo"].astype(str))]
                b1, b2, b3 = st.columns([1.2, 1.9, 0.9])
                with b1:
                    busca = st.text_input("Buscar", placeholder="Buscar por modelo, título o SKU…", key="ads_buscar")
                with b2:
                    orden_p = st.segmented_control("Ordenar por", ["Urgencia", "Inversión", "Ventas ads", "Venta orgánica"], default="Urgencia", key="ads_orden") or "Urgencia"
                with b3:
                    st.write("")
                    solo_org = st.toggle("Solo con venta orgánica", key="ads_solo_org",
                                         help="Productos publicitados que además vendieron sin que el comprador haga clic en el anuncio.")
                G = it
                if ver_est_ad == "Activos":
                    G = G[G["estado_ad"] == "active"]
                elif ver_est_ad == "Pausados":
                    G = G[G["estado_ad"].isin(["paused", "hold"])]
                if solo_org:
                    G = G[G["grupo"].isin(G.loc[G["m30_organic_units_quantity"] > 0, "grupo"])]
                if ver_acc != "Todas":
                    G = G[G["grupo"].isin(G.loc[G["accion"] == ver_acc, "grupo"])]
                if busca:
                    q = busca.strip().lower()
                    G = G[G["grupo"].isin(G.loc[G["titulo"].astype(str).str.lower().str.contains(q, regex=False) |
                                                G["sku"].str.lower().str.contains(q, regex=False) |
                                                G["modelo_color"].str.lower().str.contains(q, regex=False), "grupo"])]
                T = G.sort_values(["_p", "m30_cost"], ascending=[True, False])

                def _fpct(v, d=0):
                    return fmt_dec(v, d) + "%" if pd.notna(v) and np.isfinite(v) else "—"

                def _fcob(v):
                    return "∞" if not np.isfinite(v) else f"{v:.0f} d"

                def _fn(v):
                    return fmt_num(v) if pd.notna(v) else "—"

                resumen = []
                for g, d in T.groupby("grupo", sort=False):
                    m, mc = d["marca"].iloc[0], d["modelo_color"].iloc[0]
                    pmin = d["_p"].min()
                    acc = d.loc[d["_p"] == pmin, "accion"].iloc[0]
                    n_acc = int((d["_p"] == pmin).sum())
                    cost, ventas, clics, unid = d["m30_cost"].sum(), d["m30_total_amount"].sum(), d["m30_clicks"].sum(), d["m30_units_quantity"].sum()
                    org_u, org_m = d["m30_organic_units_quantity"].sum(), d["m30_organic_units_amount"].sum()
                    st_meli = d["stock_meli"].sum(min_count=1)
                    st_dep = pmod.get((m, mc), d["stock_dep"].sum(min_count=1)) if (mc and not cat_a.empty) else d["stock_dep"].sum(min_count=1)
                    vel_g = vel_mod.get(mc, d["vel"].sum()) if mc else d["vel"].sum()
                    ref = np.nanmin([x for x in [st_meli, st_dep] if pd.notna(x)]) if any(pd.notna(x) for x in [st_meli, st_dep]) else np.nan
                    resumen.append({"grupo": g, "d": d, "marca": m, "mc": mc, "acc": acc, "n_acc": n_acc, "p": pmin, "cost": cost, "ventas": ventas,
                                    "clics": clics, "unid": unid, "org_u": org_u, "org_m": org_m, "st_meli": st_meli, "st_dep": st_dep,
                                    "cob": (ref / vel_g) if vel_g > 0 and pd.notna(ref) else np.inf,
                                    "sin_stock": int(((d["stock_meli"] <= 0) | (d["stock_dep"] <= 0)).sum()),
                                    "activos": int((d["estado_ad"] == "active").sum()),
                                    "pausados": int(d["estado_ad"].isin(["paused", "hold"]).sum())})
                _ordk = {"Urgencia": lambda x: (x["p"], -x["cost"]), "Inversión": lambda x: -x["cost"],
                         "Ventas ads": lambda x: -x["ventas"], "Venta orgánica": lambda x: -x["org_m"]}[orden_p]
                resumen.sort(key=_ordk)
                MAXG = 60
                cols_g = "minmax(230px,2.4fr) minmax(190px,1.6fr) 1fr 0.85fr 0.95fr 0.55fr 0.55fr 1fr 0.65fr 0.65fr 0.65fr"
                cab = ["Modelo", "Acción sugerida", "Talles", "Inversión 30d", "Ventas ads", met_ef, "CVR", "Venta orgánica", "Stock MeLi", "Depósito", "Cobertura"]
                bloques = ""
                for r in resumen[:MAXG]:
                    d = r["d"].sort_values("talle", key=lambda s_: s_.map(lambda x: (0, float(x.replace(",", "."))) if x.replace(",", ".").replace(".", "", 1).isdigit() else (1, x)))
                    top = r["d"].sort_values("m30_cost", ascending=False).iloc[0]
                    img = top["thumbnail"] if str(top.get("thumbnail", "")).startswith("http") else img_azure(r["marca"], r["mc"])
                    titulo = str(top["titulo"])
                    nombre = r["mc"] if r["mc"] else titulo[:40]
                    cls = pill.get(r["acc"][:1], "")
                    acc_txt = r["acc"] + (f" · {r['n_acc']} talle{'s' if r['n_acc'] > 1 else ''}" if len(d) > 1 and r["acc"] != "Mantener" else "")
                    tl = f"{len(d)}" + (f" · <span style='color:#F87171'>{r['sin_stock']} sin stock</span>" if r["sin_stock"] else "")
                    acos_g = r["cost"] / r["ventas"] * 100 if r["ventas"] else np.nan
                    ef_g = (fmt_dec(r["ventas"] / r["cost"], 1) + "x" if r["cost"] else "—") if EsR else _fpct(acos_g)
                    est_txt = f"{r['activos']} activo{'s' if r['activos'] != 1 else ''}" + (f" · <span style='color:#FBBF24'>{r['pausados']} pausado{'s' if r['pausados'] != 1 else ''}</span>" if r["pausados"] else "")
                    cvr_g = r["unid"] / r["clics"] * 100 if r["clics"] else np.nan
                    celdas = [f"<span class='grp-tit'><img src='{img}'><span><b>{titulo[:46]}</b><small>{r['marca']} · {nombre} · {est_txt}</small></span></span>",
                              f"<span class='pill {cls}'>{acc_txt}</span>", tl, fmt_ars(r["cost"]), fmt_ars(r["ventas"]), ef_g,
                              _fpct(cvr_g, 1),
                              (fmt_ars(r["org_m"]) if r["org_u"] else "—"),
                              _fn(r["st_meli"]), _fn(r["st_dep"]), _fcob(r["cob"])]
                    fil = ""
                    for _, x in d.iterrows():
                        cx = pill.get(str(x["accion"])[:1], "")
                        _ea = str(x["estado_ad"])
                        est_ad_txt = {"active": "<span class='pill ok'>Activo</span>", "paused": "<span class='pill warn'>Pausado</span>",
                                      "hold": "<span class='pill warn'>Pausado por MeLi</span>"}.get(_ea, _ea)
                        ef_x = (fmt_dec(x["roas30"], 1) + "x" if pd.notna(x["roas30"]) else "—") if EsR else _fpct(x["acos30"])
                        fil += (f"<tr><td><b>{x['talle']}</b></td><td>{x['sku'] or '—'}</td><td style='text-align:left'><span class='pill {cx}'>{x['accion']}</span></td>"
                                f"<td>{est_ad_txt}</td><td style='max-width:200px;overflow:hidden;text-overflow:ellipsis'>{nombres_c.get(x['campaign_id'], x['campaign_id'])}</td>"
                                f"<td>{fmt_ars(x['m30_cost'])}</td><td>{fmt_ars(x['m30_total_amount'])}</td><td>{ef_x}</td>"
                                f"<td>{fmt_num(x['m30_clicks'])}</td><td>{_fpct(x['cvr30'], 1)}</td>"
                                f"<td>{fmt_num(x['m30_direct_units_quantity'])} / {fmt_num(x['m30_indirect_units_quantity'])}</td>"
                                f"<td>{fmt_num(x['m30_organic_units_quantity'])} · {fmt_ars(x['m30_organic_units_amount'])}</td>"
                                f"<td>{fmt_ars(x['m7_cost'] if 'm7_cost' in x else 0)}</td>"
                                f"<td>{_fn(x['stock_meli'])}</td><td>{_fn(x['stock_dep'])}</td><td>{fmt_dec(x['vel'] * 30, 0)}</td><td>{_fcob(x['cobertura'])}</td>"
                                f"<td><a href='{x['permalink']}' target='_blank' style='color:#22D3EE'>Ver ↗</a></td></tr>")
                    det = ("<table class='ftable grp-det'><thead><tr><th>Talle</th><th>SKU</th><th style='text-align:left'>Acción</th><th>Anuncio</th><th>Campaña</th>"
                           f"<th>Inversión 30d</th><th>Ventas ads</th><th>{met_ef}</th><th>Clics</th><th>CVR</th><th>U. directas / indirectas</th><th>Orgánica (u · $)</th><th>Inversión 7d</th><th>Stock MeLi</th><th>Depósito</th>"
                           f"<th>Venta 30d (u)</th><th>Cobertura</th><th></th></tr></thead><tbody>{fil}</tbody></table>")
                    bloques += ("<details class='grp'><summary class='grp-row' style='grid-template-columns:" + cols_g + "'>" +
                                "".join(f"<div>{c_}</div>" for c_ in celdas) + "</summary>" + det + "</details>")
                if bloques:
                    cab_html = "<div class='grp-row grp-head' style='grid-template-columns:" + cols_g + "'>" + "".join(f"<div>{c_}</div>" for c_ in cab) + "</div>"
                    html("<div class='tbl-wrap'><div style='min-width:1180px'>" + cab_html + bloques + "</div></div>")
                    st.caption(f"{fmt_num(min(len(resumen), MAXG))} de {fmt_num(len(resumen))} modelos ({fmt_num(len(T))} anuncios), ordenados por {orden_p.lower()}. "
                               "Tocá un modelo para ver todos sus talles. La acción del modelo es la más urgente entre sus talles. Cobertura = días de stock a la velocidad de venta actual.")
                else:
                    st.info("No hay productos para ese filtro.")
                exp = T[["marca", "modelo_color", "talle", "item_id", "titulo", "sku", "campaign_id", "estado_ad", "m30_cost", "m30_total_amount", "acos30", "roas30", "m30_clicks",
                         "m30_units_quantity", "m30_direct_units_quantity", "m30_indirect_units_quantity", "m30_organic_units_quantity", "m30_organic_units_amount",
                         "cvr30", "stock_meli", "stock_dep", "vel", "cobertura", "accion", "permalink"]].copy()
                exp["campaign_id"] = exp["campaign_id"].map(lambda x: nombres_c.get(x, x))
                st.download_button("Descargar productos en campaña (CSV)", exp.to_csv(index=False).encode("utf-8"),
                                   file_name="productos_en_campania.csv", mime="text/csv", icon=":material/download:")

        with tp2:
          if pub_a.empty:
            st.info("Falta el archivo de publicaciones (meli_publicaciones.csv).")
          else:
            if a_items.empty:
                en_ads = set()
            elif camp_reales:
                en_ads = set(a_items.loc[a_items["campaign_id"].isin(camp_reales), "item_id"].astype(str))
            else:
                en_ads = set(a_items.loc[a_items["estado_ad"] != "idle", "item_id"].astype(str))
            fu = pub_a[pub_a["marca"].isin(marcas_ads) & (pub_a["estado"] == "active") & ~pub_a["item_id"].astype(str).isin(en_ads)].copy()
            fu["sku"] = fu["sku"].fillna("").astype(str)
            fu["modelo_color"] = fu["modelo_color"].fillna("").astype(str)
            for c_ in ["stock", "visitas_30d", "precio"]:
                fu[c_] = pd.to_numeric(fu[c_], errors="coerce").fillna(0)
            if not cat_a.empty:
                ps2, pmod2 = cat_a.groupby(["marca", "sku"])["stock"].sum(), cat_a.groupby(["marca", "modelo_color"])["stock"].sum()
                fu["stock_dep"] = [ps2.get((m, s_), pmod2.get((m, mc), np.nan)) for m, s_, mc in zip(fu["marca"], fu["sku"], fu["modelo_color"])]
            else:
                ps2, pmod2 = pd.Series(dtype=float), pd.Series(dtype=float)
                fu["stock_dep"] = np.nan
            vm30 = base_net[(base_net["canal"] == "MercadoLibre") & (base_net["dia"] > hoy - timedelta(days=30)) & (base_net["cantidad"] > 0)]
            u_it = vm30.groupby("item_id")["cantidad"].sum() if "item_id" in vm30.columns else pd.Series(dtype=float)
            f_it = vm30.groupby("item_id")["subtotal_producto"].sum() if "item_id" in vm30.columns else pd.Series(dtype=float)
            fu["u30"] = fu["item_id"].astype(str).map(u_it).fillna(0)
            fu["f30"] = fu["item_id"].astype(str).map(f_it).fillna(0)
            fu["conv"] = np.where(fu["visitas_30d"] > 0, fu["u30"] / fu["visitas_30d"] * 100, np.nan)
            fu["stock_ref"] = fu[["stock", "stock_dep"]].min(axis=1, skipna=True)

            def accion_fuera(r):
                if r["stock_ref"] <= 0:
                    return "⚫ Sin stock: no sumar"
                if r["u30"] > 0 and r["stock_ref"] >= 10:
                    return "🟢 Sumar a campaña"
                if r["u30"] > 0:
                    return "🟡 Sumar con presupuesto bajo"
                if r["visitas_30d"] >= 50:
                    return "🟣 Probar: tiene visitas, no vende"
                return "⚪ Evaluar"
            fu["accion"] = fu.apply(accion_fuera, axis=1)
            fu["talle"] = [sk.rsplit("-", 1)[1] if "-" in sk else "—" for sk in fu["sku"]]
            fu["grupo"] = [f"{m}|{mc}" if mc else f"{m}|{t}" for m, mc, t in zip(fu["marca"], fu["modelo_color"], fu["titulo"].astype(str))]
            _pr2 = {"🟢 Sumar a campaña": 0, "🟡 Sumar con presupuesto bajo": 1, "🟣 Probar: tiene visitas, no vende": 2, "⚪ Evaluar": 3, "⚫ Sin stock: no sumar": 4}
            fu["_p"] = fu["accion"].map(_pr2)
            con_stk = fu[fu["stock_ref"] > 0]
            k4 = st.columns(4)
            k4[0].markdown(kpi_card("Activas sin campaña", fmt_num(len(fu)), f"<span class='delta flat'>{fmt_num(fu['grupo'].nunique())} modelos</span>", "", "#94A3B8", sm=True), unsafe_allow_html=True)
            k4[1].markdown(kpi_card("Con stock", fmt_num(len(con_stk)), f"<span class='delta flat'>{fmt_num(con_stk['stock'].sum())} u. en MeLi</span>", "", "#22D3EE", sm=True), unsafe_allow_html=True)
            k4[2].markdown(kpi_card("Venden sin publicidad", fmt_num(int((con_stk["u30"] > 0).sum())), f"<span class='delta up'>{fmt_num(con_stk['u30'].sum())} u. en 30 días</span>", "", "#34D399", sm=True), unsafe_allow_html=True)
            k4[3].markdown(kpi_card("Facturación 30 días", fmt_kpi(con_stk["f30"].sum()), "<span class='delta flat'>de publicaciones sin anuncio</span>", "", "#FFE600", sm=True), unsafe_allow_html=True)
            o1, o2, o3 = st.columns([1.6, 1.6, 0.9])
            with o1:
                busca2 = st.text_input("Buscar", placeholder="Buscar por modelo, título o SKU…", key="sin_buscar")
            with o2:
                orden2 = st.segmented_control("Ordenar por", ["Sugerencia", "Ventas 30d", "Visitas", "Stock"], default="Sugerencia", key="sin_orden") or "Sugerencia"
            with o3:
                st.write("")
                incl_0 = st.toggle("Incluir sin stock", key="sin_incl0")
            F = fu if incl_0 else con_stk
            if busca2:
                q = busca2.strip().lower()
                F = F[F["grupo"].isin(F.loc[F["titulo"].astype(str).str.lower().str.contains(q, regex=False) |
                                            F["sku"].str.lower().str.contains(q, regex=False) |
                                            F["modelo_color"].str.lower().str.contains(q, regex=False), "grupo"])]
            pill2 = {"🟢": "ok", "🟡": "warn", "🟣": "warn", "⚪": "", "⚫": "bad"}
            res2 = []
            for g, d in F.groupby("grupo", sort=False):
                m, mc = d["marca"].iloc[0], d["modelo_color"].iloc[0]
                pmin = d["_p"].min()
                dep = pmod2.get((m, mc), d["stock_dep"].sum(min_count=1)) if (mc and len(pmod2)) else d["stock_dep"].sum(min_count=1)
                res2.append({"d": d, "marca": m, "mc": mc, "p": pmin, "acc": d.loc[d["_p"] == pmin, "accion"].iloc[0],
                             "n_acc": int((d["_p"] == pmin).sum()), "stk": d["stock"].sum(), "dep": dep, "vis": d["visitas_30d"].sum(),
                             "u30": d["u30"].sum(), "f30": d["f30"].sum(), "precio": d["precio"].median()})
            _ok2 = {"Sugerencia": lambda x: (x["p"], -x["u30"], -x["vis"]), "Ventas 30d": lambda x: -x["u30"],
                    "Visitas": lambda x: -x["vis"], "Stock": lambda x: -x["stk"]}[orden2]
            res2.sort(key=_ok2)
            cols2 = "minmax(240px,2.6fr) minmax(200px,1.7fr) 0.6fr 0.75fr 0.75fr 0.75fr 0.8fr 1fr 0.75fr 0.8fr"
            cab2 = ["Modelo", "Sugerencia", "Talles", "Stock MeLi", "Depósito", "Visitas 30d", "Ventas 30d", "Facturación 30d", "Conversión", "Precio"]
            bl2 = ""
            for r in res2[:MAXG]:
                d = r["d"].sort_values("talle", key=lambda s_: s_.map(lambda x: (0, float(x.replace(",", "."))) if x.replace(",", ".").replace(".", "", 1).isdigit() else (1, x)))
                top = r["d"].sort_values(["u30", "visitas_30d"], ascending=False).iloc[0]
                titulo = str(top["titulo"])
                img = img_azure(r["marca"], r["mc"]) if r["mc"] else ""
                cls = pill2.get(r["acc"][:1], "")
                acc_txt = r["acc"] + (f" · {r['n_acc']} talles" if len(d) > 1 and r["n_acc"] > 1 else "")
                conv = r["u30"] / r["vis"] * 100 if r["vis"] else np.nan
                celdas = [f"<span class='grp-tit'><img src='{img}'><span><b>{titulo[:46]}</b><small>{r['marca']} · {r['mc'] or '—'}</small></span></span>",
                          f"<span class='pill {cls}'>{acc_txt}</span>", str(len(d)), fmt_num(r["stk"]), _fn(r["dep"]), fmt_num(r["vis"]),
                          fmt_num(r["u30"]), fmt_ars(r["f30"]), _fpct(conv, 1), fmt_ars(r["precio"])]
                fil = ""
                for _, x in d.iterrows():
                    cx = pill2.get(str(x["accion"])[:1], "")
                    fil += (f"<tr><td><b>{x['talle']}</b></td><td>{x['sku'] or '—'}</td><td style='text-align:left'><span class='pill {cx}'>{x['accion']}</span></td>"
                            f"<td>{fmt_num(x['stock'])}</td><td>{_fn(x['stock_dep'])}</td><td>{fmt_num(x['visitas_30d'])}</td><td>{fmt_num(x['u30'])}</td>"
                            f"<td>{fmt_ars(x['f30'])}</td><td>{_fpct(x['conv'], 1)}</td><td>{fmt_ars(x['precio'])}</td>"
                            f"<td><a href='{x['permalink']}' target='_blank' style='color:#22D3EE'>Ver ↗</a></td></tr>")
                det = ("<table class='ftable grp-det'><thead><tr><th>Talle</th><th>SKU</th><th style='text-align:left'>Sugerencia</th><th>Stock MeLi</th><th>Depósito</th>"
                       f"<th>Visitas 30d</th><th>Ventas 30d</th><th>Facturación</th><th>Conversión</th><th>Precio</th><th></th></tr></thead><tbody>{fil}</tbody></table>")
                bl2 += ("<details class='grp'><summary class='grp-row' style='grid-template-columns:" + cols2 + "'>" +
                        "".join(f"<div>{c_}</div>" for c_ in celdas) + "</summary>" + det + "</details>")
            if bl2:
                cab_html = "<div class='grp-row grp-head' style='grid-template-columns:" + cols2 + "'>" + "".join(f"<div>{c_}</div>" for c_ in cab2) + "</div>"
                html("<div class='tbl-wrap'><div style='min-width:1120px'>" + cab_html + bl2 + "</div></div>")
                st.caption(f"{fmt_num(min(len(res2), MAXG))} de {fmt_num(len(res2))} modelos ({fmt_num(len(F))} publicaciones activas que no están en ningún anuncio). "
                           "Ventas y facturación = MercadoLibre, últimos 30 días, sin publicidad. Stock depósito = inventario de Shopify.")
            else:
                st.success("Todas las publicaciones activas con stock están en alguna campaña.")
            exp2 = F[["marca", "modelo_color", "talle", "item_id", "titulo", "sku", "stock", "stock_dep", "visitas_30d", "u30", "f30", "conv", "precio", "accion", "permalink"]]
            st.download_button("Descargar productos sin campaña (CSV)", exp2.to_csv(index=False).encode("utf-8"),
                               file_name="productos_sin_campania.csv", mime="text/csv", icon=":material/download:", key="dl_sin")

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
# TAB · POST-VENTA MELI (cancelaciones, reclamos y devoluciones) · solo dirección
# ==============================================================================
# Motivos de reclamo de MeLi (reason name) -> (texto claro, categoría)
PV_MOTIVOS = {
    "repentant_buyer": ("Lo recibió bien pero no lo quiere", "Arrepentimiento (ya lo recibió)"),
    "repentant_beneficiary": ("Lo recibió bien pero no lo quiere", "Arrepentimiento (ya lo recibió)"),
    "dont_want_it_another_cause_fashion": ("No lo quiere por otro motivo", "Arrepentimiento (ya lo recibió)"),
    "purchase_no_longer_wanted": ("Ya no quiere la compra", "Arrepentimiento antes de recibir"),
    "undelivered_repentant_buyer": ("Se arrepintió antes de recibir", "Arrepentimiento antes de recibir"),
    "undelivered_repentant_buyer_v2": ("Se arrepintió antes de recibir", "Arrepentimiento antes de recibir"),
    "estimated_delivery_out_of_time": ("No puede esperar la fecha de entrega", "Arrepentimiento antes de recibir"),
    "change_receiver_address": ("No puede recibir en la dirección que cargó", "Arrepentimiento antes de recibir"),
    "selected_wrong_product_features": ("Eligió mal las características", "Arrepentimiento antes de recibir"),
    "other_cancellation": ("Otro motivo de cancelación", "Arrepentimiento antes de recibir"),
    "other_cancellation_reason": ("Otro motivo de cancelación", "Arrepentimiento antes de recibir"),
    "undelivered_other": ("Otro motivo (antes de recibir)", "Arrepentimiento antes de recibir"),
    "different_color_or_size_fashion": ("No es el color, talle o modelo que eligió", "Talle, color o medida"),
    "different_color_or_size": ("No es el color, tamaño o modelo que eligió", "Talle, color o medida"),
    "bigger_than_expected_fashion": ("Le quedó grande", "Talle, color o medida"),
    "smaller_than_expected_fashion": ("Le quedó chico", "Talle, color o medida"),
    "not_match_size_guide_fashion": ("Las medidas no coinciden con la guía de talles", "Talle, color o medida"),
    "different_than_published": ("No cumple con lo publicado", "Distinto a lo publicado"),
    "different_item_other": ("Recibió otro producto", "Distinto a lo publicado"),
    "fake_different": ("Dice que no es original", "Distinto a lo publicado"),
    "broken_item_fashion": ("Llegó roto o con fallas", "Dañado, roto o incompleto"),
    "broken_item": ("Llegó roto o con fallas", "Dañado, roto o incompleto"),
    "not_working_item": ("No funciona", "Dañado, roto o incompleto"),
    "damaged_package_broken_item_fashion": ("Embalaje dañado y producto roto", "Dañado, roto o incompleto"),
    "damaged_package_broken_item": ("Embalaje dañado y producto roto", "Dañado, roto o incompleto"),
    "damaged_package_empty_box": ("Embalaje dañado y caja vacía", "Dañado, roto o incompleto"),
    "empty_box": ("Llegó la caja vacía", "Dañado, roto o incompleto"),
    "missing_item": ("Faltan productos", "Dañado, roto o incompleto"),
    "missing_accessories": ("Faltan accesorios", "Dañado, roto o incompleto"),
    "missing_invoice": ("No llegó la factura", "Dañado, roto o incompleto"),
    "delivered_but_not_receive_package": ("Figura entregado pero no lo recibió", "No lo recibió / problema de entrega"),
    "product_not_received": ("No recibió el producto", "No lo recibió / problema de entrega"),
    "delivery_delayed": ("La entrega está demorada", "No lo recibió / problema de entrega"),
    "delivery_date_was_not_met": ("No se cumplió la fecha de entrega", "No lo recibió / problema de entrega"),
    "respondent_unanswered": ("El vendedor no le respondió", "Atención del vendedor"),
    "out_of_stock": ("El vendedor no tiene stock", "Sin stock / no disponible"),
    "unauthorized_purchase": ("No reconoce la compra", "Compra no reconocida / fraude"),
    "other_complaint": ("Otro tipo de reclamo", "Otros"),
    "event_cancelled": ("Se canceló el evento o servicio", "Otros"),
}
PV_CAT_ORIGEN = {"Arrepentimiento (ya lo recibió)": "Comprador", "Arrepentimiento antes de recibir": "Comprador",
                 "Talle, color o medida": "Comprador", "Distinto a lo publicado": "Nosotros", "Dañado, roto o incompleto": "Nosotros",
                 "No lo recibió / problema de entrega": "Logística", "Atención del vendedor": "Nosotros",
                 "Sin stock / no disponible": "Nosotros", "Compra no reconocida / fraude": "MercadoLibre", "Otros": "Comprador",
                 "Cancelada por MeLi sin causa informada": "MercadoLibre", "Envío no entregado / fallido": "Logística",
                 "Etiqueta no impresa a tiempo": "Nosotros", "Técnico (no es pérdida)": "Técnico", "Pago rechazado (no es venta)": "Pago"}
PV_COLOR_ORIGEN = {"Comprador": "#38BDF8", "Nosotros": "#F87171", "MercadoLibre": "#FFE600", "Logística": "#A78BFA",
                   "Técnico": "#64748B", "Pago": "#475569"}
PV_TIPO = {"returns": "Devolución", "return": "Devolución", "cancel_purchase": "Cancelación antes del envío", "mediations": "Reclamo",
           "cancel_sale": "Cancelación del vendedor", "change": "Cambio", "fulfillment": "Full", "ml_case": "Caso MeLi", "service": "Servicio"}
PV_ETAPA = {"claim": "Con el vendedor", "dispute": "En mediación de MeLi", "recontact": "Recontacto", "stale": "Vencido", "none": "—"}
PV_RES = {"item_returned": "Devolvió el producto y se reembolsó", "coverage_decision": "MeLi reembolsó al comprador (protección)",
          "no_bpp": "Sin cobertura de MeLi", "return_expired": "Venció el plazo para devolver", "product_delivered": "Se entregó el producto",
          "timeout": "Venció el plazo", "payment_refunded": "Se reintegró el pago", "worked_out_with_seller": "Lo resolvió con nosotros",
          "return_cancelled": "Se canceló la devolución", "opened_claim_by_mistake": "Abierto por error", "prefered_to_keep_product": "Prefirió quedarse el producto",
          "seller_did_not_help": "Consideró que no lo ayudamos", "seller_asked_to_close_claim": "Pedimos cerrar el reclamo",
          "already_shipped": "Ya estaba despachado", "user_risk": "Riesgo del usuario", "other": "Otro", "": "Abierto (sin resolver)"}
PV_DEV = {"opened": "Iniciada", "label_generated": "Etiqueta generada (no la despachó aún)", "shipped": "En camino de vuelta",
          "delivered": "Recibida en el depósito", "closed": "Cerrada", "not_delivered": "No llegó al depósito", "cancelled": "Cancelada",
          "failed": "Fallida", "expired": "Venció (no la envió)"}


def _pv_fecha(s):
    return pd.to_datetime(s, errors="coerce", format="mixed", utc=True).dt.tz_convert(ZONA_AR)


def _pv_motivo(nombre, detalle=""):
    n = str(nombre or "").strip()
    if n in PV_MOTIVOS:
        return PV_MOTIVOS[n]
    d = str(detalle or "").strip()
    if d and d.lower() not in ("llegó bien", "otro motivo") and not any(x in d.lower() for x in ("não", "recebi")):
        return d, "Otros"
    return (n.replace("_", " ").capitalize() if n else "Sin motivo informado"), "Otros"


def _pv_clasificar(r):
    """Cancelación de MeLi -> (categoría, motivo claro, origen, cuándo, es_pérdida)"""
    g, cod, pago = str(r.get("cancel_grupo") or ""), str(r.get("cancel_codigo") or ""), str(r.get("pago_estado") or "")
    entregada = bool(r.get("entregada"))
    cuando = "Después de entregar" if entregada else "Antes de entregar"
    if pago in ("rejected", "cancelled", "in_process", "pending", "") and g not in ("seller", "mediations"):
        return "Pago rechazado (no es venta)", "El pago no se aprobó", "Pago", cuando, False
    if g in ("buyer", "mediations"):
        if pd.notna(r.get("cl_motivo")) and str(r.get("cl_motivo")):
            mot, cat = _pv_motivo(r.get("cl_motivo"), r.get("cl_detalle"))
        else:
            mot, cat = (("Se arrepintió antes de recibir", "Arrepentimiento antes de recibir") if g == "buyer"
                        else ("Reclamo / devolución (sin detalle)", "Otros"))
        return cat, mot, PV_CAT_ORIGEN.get(cat, "Comprador"), cuando, True
    if g == "seller":
        mot = "Sin stock" if "out_of_stock" in cod else "Producto no disponible"
        return "Sin stock / no disponible", mot, "Nosotros", cuando, True
    if g == "shipment":
        if "unprinted_label" in cod:
            return "Etiqueta no impresa a tiempo", "No se imprimió/despachó la etiqueta a tiempo", "Nosotros", cuando, True
        if "creation" in cod:
            return "Técnico (no es pérdida)", "Falla al crear el envío", "Técnico", cuando, False
        return "Envío no entregado / fallido", "El envío no se pudo entregar", "Logística", cuando, True
    if g == "fraud":
        return "Compra no reconocida / fraude", "MeLi detectó fraude", "MercadoLibre", cuando, True
    if g == "internal":
        if cod.startswith("pack_"):
            return "Técnico (no es pérdida)", "MeLi dividió el carrito en varias órdenes", "Técnico", cuando, False
        return "Cancelada por MeLi sin causa informada", "MeLi canceló sin informar la causa", "MercadoLibre", cuando, True
    return "Otros", (str(r.get("cancel_motivo") or "") or "Sin motivo informado"), "MercadoLibre", cuando, True


if tab_pv is not None:
    with tab_pv:
        pv_c = load_aux("meli_cancelaciones.csv")
        pv_r = load_aux("meli_reclamos.csv")
        if pv_c.empty and pv_r.empty:
            st.info("Todavía no hay datos de post-venta. Se generan con el workflow diario (paso 'Post-venta MercadoLibre').")
        else:
            # ---------- reclamos (para motivos) ----------
            R = pv_r.copy() if not pv_r.empty else pd.DataFrame(columns=["marca", "claim_id", "orden_meli", "fecha"])
            for c_ in ["tipo", "etapa", "estado", "motivo", "motivo_detalle", "res_motivo", "res_beneficiado", "dev_estado", "dev_dinero", "titulos", "skus"]:
                R[c_] = R[c_].fillna("").astype(str) if c_ in R.columns else ""
            R["fecha"] = _pv_fecha(R["fecha"])
            R["dia"] = R["fecha"].dt.date
            R["monto"] = pd.to_numeric(R["monto"], errors="coerce") if "monto" in R.columns else np.nan
            R["orden_meli"] = pd.to_numeric(R["orden_meli"], errors="coerce")
            _mc = [_pv_motivo(n, d) for n, d in zip(R["motivo"], R["motivo_detalle"])]
            R["motivo_es"] = [m_[0] for m_ in _mc]
            R["categoria"] = [m_[1] for m_ in _mc]
            R["tipo_es"] = R["tipo"].map(PV_TIPO).fillna(R["tipo"])
            R["etapa_es"] = R["etapa"].map(PV_ETAPA).fillna(R["etapa"])
            R["resolucion_es"] = R["res_motivo"].map(PV_RES).fillna(R["res_motivo"].str.replace("_", " "))
            R["a_favor"] = np.select([R["res_beneficiado"].str.contains("complainant") & R["res_beneficiado"].str.contains("respondent"),
                                      R["res_beneficiado"].str.contains("complainant"), R["res_beneficiado"].str.contains("respondent")],
                                     ["Parcial (ambos)", "Comprador", "Nosotros"], default="Abierto")
            R["cubierto"] = R["res_cobertura"].astype(str).str.lower().isin(["true", "1"]) if "res_cobertura" in R.columns else False
            R["dev_es"] = R["dev_estado"].map(PV_DEV).fillna(R["dev_estado"])

            # ---------- cancelaciones = toda venta revertida (incluye devoluciones reembolsadas) ----------
            C = pv_c.copy() if not pv_c.empty else pd.DataFrame(columns=["marca", "orden_meli", "fecha", "monto", "cancel_grupo", "cancel_codigo", "pago_estado", "tags"])
            C["fecha"] = _pv_fecha(C["fecha"])
            C["dia"] = C["fecha"].dt.date
            C["monto"] = pd.to_numeric(C["monto"], errors="coerce").fillna(0)
            C["unidades"] = pd.to_numeric(C.get("unidades", 0), errors="coerce").fillna(0)
            C["orden_meli"] = pd.to_numeric(C["orden_meli"], errors="coerce")
            C["pago_estado"] = C["pago_estado"].fillna("").astype(str).str.lower()
            C["entregada"] = C["tags"].fillna("").astype(str).str.split(",").apply(lambda t: "delivered" in t)
            ult_cl = R.dropna(subset=["orden_meli"]).sort_values("fecha").drop_duplicates("orden_meli", keep="last")
            C = C.merge(ult_cl[["orden_meli", "motivo", "motivo_detalle", "tipo_es", "claim_id"]].rename(
                columns={"motivo": "cl_motivo", "motivo_detalle": "cl_detalle", "tipo_es": "cl_tipo"}), on="orden_meli", how="left")
            if len(C):
                _cl = C.apply(_pv_clasificar, axis=1, result_type="expand")
                _cl.columns = ["categoria", "motivo_es", "origen", "cuando", "perdida"]
                C = pd.concat([C, _cl], axis=1)
            else:
                for c_ in ["categoria", "motivo_es", "origen", "cuando"]:
                    C[c_] = ""
                C["perdida"] = False
            C["producto"] = C["titulos"].fillna("").astype(str).str.split(" | ", regex=False).str[0] if "titulos" in C.columns else ""
            C["sku1"] = C["skus"].fillna("").astype(str).str.split(" | ", regex=False).str[0] if "skus" in C.columns else ""

            # ---------- filtros ----------
            marcas_pv_disp = [m for m in MARCAS_BASE if m in set(C["marca"]) | set(R["marca"])]
            q1, q2 = st.columns([1.6, 1])
            with q1:
                marcas_pv = st.pills("Marcas", marcas_pv_disp, selection_mode="multi", default=marcas_pv_disp, key="pv_marcas") or marcas_pv_disp
            with q2:
                per_pv = st.segmented_control("Período", ["7D", "30D", "60D", "90D", "Desde 1/09"], default="30D", key="pv_periodo") or "30D"
            pv_ini = datetime(2026, 9, 1).date() if per_pv == "Desde 1/09" else hoy - timedelta(days=int(per_pv[:-1]) - 1)
            nd_pv = (hoy - pv_ini).days + 1
            pv_ini_prev = pv_ini - timedelta(days=nd_pv)
            html(f"<div class='hero-sub'>📅 <b>{pv_ini:%d/%m/%Y} → {hoy:%d/%m/%Y}</b> · ventas revertidas según la fecha de la compra · "
                 "reclamos según la fecha en que se abrieron · se actualiza 2 veces por día.</div>")
            Cm, Rm = C[C["marca"].isin(marcas_pv)], R[R["marca"].isin(marcas_pv)]
            Cp = Cm[(Cm["dia"] >= pv_ini) & (Cm["dia"] <= hoy)]
            Cpp = Cm[(Cm["dia"] >= pv_ini_prev) & (Cm["dia"] < pv_ini)]
            Rp = Rm[(Rm["dia"] >= pv_ini) & (Rm["dia"] <= hoy)]
            Lp, Lpp = Cp[Cp["perdida"]], Cpp[Cpp["perdida"]]          # ventas realmente perdidas

            # ---------- base: órdenes y venta MeLi ----------
            def _base_meli(x0, x1):
                b = base_m[(base_m["canal"] == "MercadoLibre") & base_m["marca"].astype(str).isin(marcas_pv) & (base_m["dia"] >= x0) & (base_m["dia"] <= x1)]
                if b.empty:
                    return pd.DataFrame(columns=["ordenes", "venta", "unidades"])
                key = "orden_meli" if "orden_meli" in b.columns else "id_pedido"
                o = b.drop_duplicates(key)
                monto = "total_orden_meli" if "total_orden_meli" in o.columns else "total_pedido"
                g = o.groupby(o["marca"].astype(str)).agg(ordenes=(key, "nunique"), venta=(monto, "sum"))
                g["unidades"] = b.groupby(b["marca"].astype(str))["cantidad"].sum()
                return g
            Bm, Bmp = _base_meli(pv_ini, hoy), _base_meli(pv_ini_prev, pv_ini - timedelta(days=1))
            n_ord, venta_t = float(Bm["ordenes"].sum()), float(Bm["venta"].sum())
            n_ord_p, venta_p = float(Bmp["ordenes"].sum()), float(Bmp["venta"].sum())

            def _k(L, nord, vta):
                antes, desp = L[L["cuando"] == "Antes de entregar"], L[L["cuando"] == "Después de entregar"]
                nos = L[L["origen"] == "Nosotros"]
                return {"n": len(L), "m": float(L["monto"].sum()), "tasa": len(L) / nord * 100 if nord else 0,
                        "pct_v": float(L["monto"].sum()) / vta * 100 if vta else 0,
                        "an": len(antes), "am": float(antes["monto"].sum()), "dn": len(desp), "dm": float(desp["monto"].sum()),
                        "nn": len(nos), "nm": float(nos["monto"].sum())}
            K, KP = _k(Lp, n_ord, venta_t), (_k(Lpp, n_ord_p, venta_p) if n_ord_p else None)
            pvp = (lambda x: KP[x]) if KP else (lambda x: None)

            # ---------- KPIs ----------
            seccion("Post-venta MercadoLibre", "Ventas que se revierten después de vender",
                    f"Sobre {fmt_num(n_ord)} órdenes y {fmt_compact(venta_t)} vendidos en MeLi en el período · comparado con los {nd_pv} días anteriores. "
                    "Una venta revertida es una orden cancelada o devuelta con reembolso al comprador.")
            kk = st.columns(4)
            kk[0].markdown(kpi_card("Facturación revertida", fmt_kpi(K["m"]), delta_html(K["pct_v"], pvp("pct_v"), invert=True, pp=True, cap="% de la venta vs anterior"),
                                    f"<div class='split-legend' style='margin-top:10px'><span><b>{fmt_dec(K['pct_v'])}%</b> de la venta MeLi</span></div>"
                                    f"<div class='split-legend' style='margin-top:6px'><span>Antes de entregar {fmt_compact(K['am'])}</span><span>Después {fmt_compact(K['dm'])}</span></div>",
                                    "#EF4444"), unsafe_allow_html=True)
            kk[1].markdown(kpi_card("Ventas revertidas", fmt_num(K["n"]), delta_html(K["tasa"], pvp("tasa"), invert=True, pp=True, cap="tasa vs anterior"),
                                    f"<div class='split-legend' style='margin-top:10px'><span><b>{fmt_dec(K['tasa'])}%</b> de las órdenes</span></div>", "#F87171"), unsafe_allow_html=True)
            kk[2].markdown(kpi_card("Antes de entregar", fmt_num(K["an"]), delta_html(K["an"], pvp("an"), invert=True),
                                    f"<div class='split-legend' style='margin-top:10px'><span>{fmt_compact(K['am'])}</span>"
                                    f"<span>{fmt_dec(K['an'] / n_ord * 100 if n_ord else 0)}% de las órdenes</span></div>"
                                    "<div class='split-legend' style='margin-top:6px'><span>cancelaciones: arrepentimiento, stock, envío</span></div>", "#38BDF8"), unsafe_allow_html=True)
            kk[3].markdown(kpi_card("Después de entregar", fmt_num(K["dn"]), delta_html(K["dn"], pvp("dn"), invert=True),
                                    f"<div class='split-legend' style='margin-top:10px'><span>{fmt_compact(K['dm'])}</span>"
                                    f"<span>{fmt_dec(K['dn'] / n_ord * 100 if n_ord else 0)}% de las órdenes</span></div>"
                                    "<div class='split-legend' style='margin-top:6px'><span>devoluciones con reembolso</span></div>", "#A78BFA"), unsafe_allow_html=True)
            st.write("")
            kk = st.columns(4)
            n_ab = int((Rp["estado"] != "closed").sum())
            n_med = int((Rp["etapa"] == "dispute").sum())
            n_cerr = int((Rp["estado"] == "closed").sum())
            n_fav = int((Rp["a_favor"] == "Comprador").sum())
            kk[0].markdown(kpi_card("Evitables (responsabilidad nuestra)", fmt_kpi(K["nm"]), "",
                                    f"<div class='split-legend' style='margin-top:10px'><span>{fmt_num(K['nn'])} ventas</span>"
                                    f"<span>{fmt_dec(K['nm'] / K['m'] * 100 if K['m'] else 0)}% de lo revertido</span></div>"
                                    "<div class='split-legend' style='margin-top:6px'><span>sin stock, distinto a lo publicado, dañado, etiqueta</span></div>",
                                    "#FB923C", sm=True), unsafe_allow_html=True)
            kk[1].markdown(kpi_card("Reclamos del período", fmt_num(len(Rp)), "",
                                    f"<div class='split-legend' style='margin-top:10px'><span>{fmt_dec(len(Rp) / n_ord * 100 if n_ord else 0, 2)}% de las órdenes</span>"
                                    f"<span>{fmt_num(n_ab)} abiertos hoy</span></div>", "#FBBF24", sm=True), unsafe_allow_html=True)
            kk[2].markdown(kpi_card("Escalados a mediación de MeLi", fmt_num(n_med), "",
                                    f"<div class='split-legend' style='margin-top:10px'><span>{fmt_dec(n_med / len(Rp) * 100 if len(Rp) else 0)}% de los reclamos · impactan en la reputación</span></div>",
                                    "#FFE600", sm=True), unsafe_allow_html=True)
            kk[3].markdown(kpi_card("Resueltos a favor del comprador", f"{fmt_dec(n_fav / n_cerr * 100 if n_cerr else 0)}%", "",
                                    f"<div class='split-legend' style='margin-top:10px'><span>{fmt_num(n_fav)} de {fmt_num(n_cerr)} cerrados</span>"
                                    f"<span>{fmt_num(int(Rp['cubierto'].sum()))} con protección de MeLi</span></div>", "#38BDF8", sm=True), unsafe_allow_html=True)
            n_tec = int((~Cp["perdida"]).sum())
            if n_tec:
                st.caption(f"No se cuentan como venta perdida {fmt_num(n_tec)} órdenes: pagos rechazados ({fmt_num(int((Cp['origen'] == 'Pago').sum()))}) "
                           f"y casos técnicos de MeLi, como carritos divididos ({fmt_num(int((Cp['origen'] == 'Técnico').sum()))}).")

            # ---------- POR QUÉ ----------
            seccion("Motivos", "¿Por qué se revierten las ventas?",
                    "Cada venta revertida con su motivo real: el que eligió el comprador al cancelar o reclamar, o la causa que informa MeLi.")
            if Lp.empty:
                st.info("Sin ventas revertidas en el período.")
            else:
                g1, g2 = st.columns([1.7, 1])
                with g1:
                    ca = Lp.groupby(["categoria", "cuando"]).agg(n=("orden_meli", "count"), monto=("monto", "sum")).reset_index()
                    orden_cat = Lp.groupby("categoria")["monto"].sum().sort_values(ascending=False).index.tolist()
                    fig = px.bar(ca, y="categoria", x="monto", color="cuando", orientation="h", title="Facturación revertida por motivo",
                                 category_orders={"categoria": orden_cat}, custom_data=["n"],
                                 color_discrete_map={"Antes de entregar": "#38BDF8", "Después de entregar": "#A78BFA"})
                    fig.update_traces(marker_line_width=0, hovertemplate="%{y}<br>$%{x:,.0f} · %{customdata[0]} ventas<extra></extra>")
                    fig.update_layout(xaxis_title="", yaxis_title="", barmode="stack", legend_title_text="")
                    fig = estilo(fig, 60 + 38 * max(5, len(orden_cat)))
                    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), margin=dict(t=90))
                    st.plotly_chart(fig, width="stretch")
                with g2:
                    og = Lp.groupby("origen").agg(n=("orden_meli", "count"), monto=("monto", "sum")).reset_index().sort_values("monto", ascending=False)
                    fig = go.Figure(go.Pie(labels=og["origen"], values=og["monto"], hole=0.62, sort=False, textinfo="percent+label",
                                           marker=dict(colors=[PV_COLOR_ORIGEN.get(x, "#94A3B8") for x in og["origen"]]),
                                           customdata=og["n"], hovertemplate="%{label}<br>$%{value:,.0f} · %{customdata} ventas<extra></extra>"))
                    fig.update_layout(title="¿De quién depende?", showlegend=False,
                                      annotations=[dict(text=fmt_compact(K["m"]), showarrow=False, font=dict(size=20, color="#F8FAFC"))])
                    st.plotly_chart(estilo(fig, 60 + 38 * max(5, len(orden_cat))), width="stretch")
                # tabla categoría -> motivo
                dm = Lp.groupby(["categoria", "origen", "motivo_es"]).agg(n=("orden_meli", "count"), monto=("monto", "sum"),
                                                                       antes=("cuando", lambda s_: (s_ == "Antes de entregar").sum())).reset_index()
                tot_cat = dm.groupby("categoria")["monto"].sum()
                dm["_o"] = dm["categoria"].map(tot_cat)
                dm = dm.sort_values(["_o", "monto"], ascending=False)
                filas, ult = "", None
                for _, r_ in dm.iterrows():
                    nueva = r_["categoria"] != ult
                    ult = r_["categoria"]
                    cat_txt = (f"<b>{r_['categoria']}</b><br><small style='color:{PV_COLOR_ORIGEN.get(r_['origen'], '#94A3B8')}'>● {r_['origen']}</small>" if nueva else "")
                    tr_attr = ' style="border-top:1px solid var(--border)"' if nueva else ""
                    filas += (f"<tr{tr_attr}><td style='text-align:left;white-space:normal'>{cat_txt}</td>"
                              f"<td style='text-align:left;white-space:normal'>{r_['motivo_es']}</td><td>{fmt_num(r_['n'])}</td>"
                              f"<td>{fmt_dec(r_['n'] / K['n'] * 100 if K['n'] else 0)}%</td><td>{fmt_ars(r_['monto'])}</td>"
                              f"<td>{fmt_num(r_['antes'])} / {fmt_num(r_['n'] - r_['antes'])}</td></tr>")
                html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Motivo</th><th style='text-align:left'>Detalle</th>"
                     "<th>Ventas</th><th>% del total</th><th>Facturación</th><th>Antes / después de entregar</th></tr></thead>"
                     f"<tbody>{filas}</tbody></table></div>")

            # ---------- POR MARCA ----------
            seccion("Por marca", "Ventas revertidas por marca", "Tasas sobre las órdenes de MeLi de cada marca en el período.")
            filas = ""
            tot = dict(o=0, v=0, n=0, m=0, an=0, dn=0, nm=0, r=0, ab=0)
            for m_ in marcas_pv:
                o_ = float(Bm["ordenes"].get(m_, 0)) if len(Bm) else 0
                v_ = float(Bm["venta"].get(m_, 0)) if len(Bm) else 0
                L_ = Lp[Lp["marca"] == m_]
                R_ = Rp[Rp["marca"] == m_]
                n_, mm_ = len(L_), float(L_["monto"].sum())
                an_, dn_ = int((L_["cuando"] == "Antes de entregar").sum()), int((L_["cuando"] == "Después de entregar").sum())
                nm_ = float(L_.loc[L_["origen"] == "Nosotros", "monto"].sum())
                ab_ = int((R_["estado"] != "closed").sum())
                top = L_.groupby("categoria")["monto"].sum().sort_values(ascending=False)
                tc = n_ / o_ * 100 if o_ else 0
                cls = "ok" if tc < 5 else ("warn" if tc < 10 else "bad")
                filas += (f"<tr><td class='strong'><span class='dot' style='background:{PALETA_MARCAS.get(m_, '#94A3B8')}'></span>{m_}</td>"
                          f"<td>{fmt_num(o_)}</td><td class='sep'>{fmt_num(n_)}</td><td><span class='pill {cls}'>{fmt_dec(tc)}%</span></td>"
                          f"<td>{fmt_num(an_)}</td><td>{fmt_num(dn_)}</td><td class='strong' style='color:#F87171'>{fmt_ars(mm_)}</td>"
                          f"<td>{fmt_dec(mm_ / v_ * 100 if v_ else 0)}%</td><td>{fmt_ars(nm_)}</td>"
                          f"<td style='text-align:left;white-space:normal'>{top.index[0] if len(top) else '—'}</td><td>{fmt_num(len(R_))}</td><td>{fmt_num(ab_)}</td></tr>")
                for k_, val in zip(["o", "v", "n", "m", "an", "dn", "nm", "r", "ab"], [o_, v_, n_, mm_, an_, dn_, nm_, len(R_), ab_]):
                    tot[k_] += val
            filas += (f"<tr class='total'><td>Total</td><td>{fmt_num(tot['o'])}</td><td class='sep'>{fmt_num(tot['n'])}</td>"
                      f"<td>{fmt_dec(tot['n'] / tot['o'] * 100 if tot['o'] else 0)}%</td><td>{fmt_num(tot['an'])}</td><td>{fmt_num(tot['dn'])}</td>"
                      f"<td>{fmt_ars(tot['m'])}</td><td>{fmt_dec(tot['m'] / tot['v'] * 100 if tot['v'] else 0)}%</td><td>{fmt_ars(tot['nm'])}</td><td></td>"
                      f"<td>{fmt_num(tot['r'])}</td><td>{fmt_num(tot['ab'])}</td></tr>")
            html("<div class='tbl-wrap'><table class='ftable compact'><thead><tr><th>Marca</th><th>Órdenes</th><th class='sep'>Revertidas</th><th>Tasa</th>"
                 "<th>Antes de entregar</th><th>Después de entregar</th><th>Facturación revertida</th><th>% de la venta</th><th>Evitable (nuestra)</th>"
                 f"<th style='text-align:left'>Motivo principal</th><th>Reclamos</th><th>Abiertos</th></tr></thead><tbody>{filas}</tbody></table></div>")

            # ---------- TENDENCIA ----------
            if len(Lp):
                from plotly.subplots import make_subplots as _msp
                sem = Lp.assign(sem=Lp["fecha"].dt.tz_localize(None).dt.to_period("W").dt.start_time).groupby(["sem", "origen"])["monto"].sum().reset_index()
                bb = base_m[(base_m["canal"] == "MercadoLibre") & base_m["marca"].astype(str).isin(marcas_pv) & (base_m["dia"] >= pv_ini)]
                key_ = "orden_meli" if "orden_meli" in bb.columns else "id_pedido"
                bb = bb.drop_duplicates(key_)
                mcol = "total_orden_meli" if "total_orden_meli" in bb.columns else "total_pedido"
                vsem = bb.assign(sem=bb["fecha"].dt.tz_localize(None).dt.to_period("W").dt.start_time).groupby("sem")[mcol].sum()
                fig = _msp(specs=[[{"secondary_y": True}]])
                for og_ in ["Nosotros", "Comprador", "Logística", "MercadoLibre"]:
                    s_ = sem[sem["origen"] == og_]
                    if len(s_):
                        fig.add_bar(x=s_["sem"], y=s_["monto"], name=og_, marker_color=PV_COLOR_ORIGEN.get(og_))
                tasa = (sem.groupby("sem")["monto"].sum() / vsem * 100).dropna()
                fig.add_scatter(x=tasa.index, y=tasa.values, name="% de la venta revertida", line=dict(color="#F8FAFC", width=2, dash="dot"), secondary_y=True)
                fig.update_layout(title="Facturación revertida por semana (según de quién depende)", barmode="stack", bargap=0.25, hovermode="x unified", legend_title_text="")
                fig.update_yaxes(title_text="", secondary_y=False)
                fig.update_yaxes(ticksuffix="%", secondary_y=True, showgrid=False, rangemode="tozero")
                fig = estilo(fig, 380)
                fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), margin=dict(t=90))
                st.plotly_chart(fig, width="stretch")
                st.caption("La última semana todavía está en curso y los reclamos aparecen días después de la compra: sus números van a subir.")

            # ---------- PRODUCTOS ----------
            seccion("Productos", "Productos con más ventas revertidas",
                    "Tasa = ventas revertidas / órdenes del SKU en MeLi en el período. Sirve para detectar problemas de talle, calidad o publicación.")
            if len(Lp):
                b_sku = base_m[(base_m["canal"] == "MercadoLibre") & (base_m["dia"] >= pv_ini)]
                ped_sku = b_sku.groupby("sku")["orden_meli" if "orden_meli" in b_sku.columns else "id_pedido"].nunique()
                pr = Lp.groupby(["marca", "producto", "sku1"]).agg(n=("orden_meli", "count"), monto=("monto", "sum"),
                                                                  antes=("cuando", lambda s_: (s_ == "Antes de entregar").sum()),
                                                                  motivo=("motivo_es", lambda s_: s_.value_counts().index[0]),
                                                                  cat=("categoria", lambda s_: s_.value_counts().index[0])).reset_index()
                pr["ordenes"] = pr["sku1"].map(ped_sku).fillna(0)
                pr["tasa"] = np.where(pr["ordenes"] > 0, pr["n"] / pr["ordenes"] * 100, np.nan)
                ver_pr = st.segmented_control("Ver", ["Más facturación revertida", "Mayor tasa (mín. 5 órdenes)", "Responsabilidad nuestra"],
                                              default="Más facturación revertida", key="pv_prod_ver") or "Más facturación revertida"
                if ver_pr.startswith("Mayor"):
                    pr = pr[pr["ordenes"] >= 5].sort_values(["tasa", "n"], ascending=False)
                elif ver_pr.startswith("Resp"):
                    pr = pr[pr["cat"].map(PV_CAT_ORIGEN) == "Nosotros"].sort_values("monto", ascending=False)
                else:
                    pr = pr.sort_values("monto", ascending=False)
                filas = "".join(f"<tr><td style='text-align:left;max-width:360px;overflow:hidden;text-overflow:ellipsis'>{str(r_['producto'])[:62]}</td>"
                                f"<td>{r_['marca']}</td><td>{r_['sku1']}</td><td>{fmt_num(r_['n'])}</td><td>{fmt_num(r_['ordenes'])}</td>"
                                f"<td>{fmt_dec(r_['tasa'], 1) + '%' if pd.notna(r_['tasa']) else '—'}</td><td>{fmt_ars(r_['monto'])}</td>"
                                f"<td>{fmt_num(r_['antes'])} / {fmt_num(r_['n'] - r_['antes'])}</td>"
                                f"<td style='text-align:left;white-space:normal'>{r_['motivo']}</td></tr>" for _, r_ in pr.head(20).iterrows())
                if filas:
                    html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Producto</th><th>Marca</th><th>SKU</th>"
                         "<th>Revertidas</th><th>Órdenes</th><th>Tasa</th><th>Facturación</th><th>Antes / después</th>"
                         f"<th style='text-align:left'>Motivo principal</th></tr></thead><tbody>{filas}</tbody></table></div>")
                else:
                    st.info("Sin productos para este filtro.")
                exp = Cp[["marca", "orden_meli", "fecha", "monto", "unidades", "cuando", "origen", "categoria", "motivo_es", "perdida", "producto", "sku1"]].copy()
                exp["fecha"] = exp["fecha"].dt.strftime("%d/%m/%Y %H:%M")
                exp.columns = ["Marca", "Orden", "Fecha compra", "Monto", "Unidades", "Cuándo", "Depende de", "Motivo", "Detalle", "Es venta perdida", "Producto", "SKU"]
                st.download_button("Descargar ventas revertidas (CSV)", a_str(exp).to_csv(index=False).encode("utf-8"), file_name="meli_ventas_revertidas.csv",
                                   mime="text/csv", icon=":material/download:", key="dl_pv_canc")

            # ---------- MAPA DE PROBLEMAS POR ARTÍCULO ----------
            seccion("Artículos", "¿Qué artículos tienen problemas y cuáles?",
                    "Cada artículo (modelo + color) con todos sus casos: ventas revertidas y reclamos, separados por tipo de problema. "
                    "Tocá un artículo para ver cada caso con su talle y motivo.")
            PV_CATS_PROD = ["Talle, color o medida", "Distinto a lo publicado", "Dañado, roto o incompleto", "Sin stock / no disponible",
                            "Etiqueta no impresa a tiempo", "No lo recibió / problema de entrega", "Envío no entregado / fallido", "Atención del vendedor"]
            PV_CATS_ARR = ["Arrepentimiento (ya lo recibió)", "Arrepentimiento antes de recibir"]
            PV_CAT_CORTO = {"Talle, color o medida": "Talle / color", "Distinto a lo publicado": "Distinto a lo publicado",
                            "Dañado, roto o incompleto": "Dañado / incompleto", "Sin stock / no disponible": "Sin stock",
                            "Etiqueta no impresa a tiempo": "Etiqueta", "No lo recibió / problema de entrega": "No lo recibió",
                            "Envío no entregado / fallido": "Envío fallido", "Atención del vendedor": "Atención",
                            "Arrepentimiento (ya lo recibió)": "Arrepentido (recibido)", "Arrepentimiento antes de recibir": "Arrepentido (antes)",
                            "Cancelada por MeLi sin causa informada": "MeLi sin causa", "Compra no reconocida / fraude": "Fraude", "Otros": "Otros"}
            PV_DIAG = {"Talle, color o medida": "Revisar guía de talles y horma",
                       "Distinto a lo publicado": "Revisar fotos, título y ficha de la publicación",
                       "Dañado, roto o incompleto": "Revisar calidad y embalaje del lote",
                       "Sin stock / no disponible": "Sincronizar stock con MeLi",
                       "Etiqueta no impresa a tiempo": "Despachar a tiempo (etiqueta vencida)",
                       "No lo recibió / problema de entrega": "Revisar envío y comprobantes de entrega",
                       "Envío no entregado / fallido": "Revisar envío y dirección",
                       "Atención del vendedor": "Responder más rápido las consultas/reclamos",
                       "Arrepentimiento (ya lo recibió)": "Alta devolución: revisar expectativa (fotos, descripción, precio)",
                       "Arrepentimiento antes de recibir": "Cancelan antes de recibir: revisar tiempos de despacho y entrega"}
            casos = []
            if len(Lp):
                a_ = Lp[["marca", "orden_meli", "fecha", "monto", "categoria", "motivo_es", "cuando", "producto", "sku1"]].copy()
                a_["fuente"] = np.where(a_["cuando"] == "Antes de entregar", "Cancelación", "Devolución con reembolso")
                a_["estado_caso"] = "Venta revertida"
                casos.append(a_)
            if len(Rp):
                ords_rev = set(Lp["orden_meli"].dropna()) if len(Lp) else set()
                b_ = Rp[~Rp["orden_meli"].isin(ords_rev)].copy()
                if len(b_):
                    prod_ord = dict(zip(C["orden_meli"], C["producto"]))
                    b_["producto"] = [str(t).split(" | ")[0] if str(t) not in ("", "nan") else prod_ord.get(o, "")
                                      for t, o in zip(b_["titulos"], b_["orden_meli"])]
                    b_["sku1"] = [str(s_).split(" | ")[0] if str(s_) not in ("", "nan") else "" for s_ in b_["skus"]]
                    b_["fuente"] = b_["tipo_es"].replace({"Devolución": "Devolución (reclamo)"})
                    b_["estado_caso"] = np.where(b_["estado"] == "closed", "Reclamo cerrado · a favor de " + b_["a_favor"].str.lower(), "Reclamo abierto")
                    b_["cuando"] = ""
                    casos.append(b_[["marca", "orden_meli", "fecha", "monto", "categoria", "motivo_es", "cuando", "producto", "sku1", "fuente", "estado_caso"]])
            CA = pd.concat(casos, ignore_index=True) if casos else pd.DataFrame()
            if CA.empty:
                st.info("Sin casos en el período.")
            else:
                CA["sku1"] = CA["sku1"].fillna("").astype(str).str.strip()
                CA["producto"] = CA["producto"].fillna("").astype(str).str.strip()
                sin_art = int(((CA["sku1"] == "") & (CA["producto"] == "")).sum())
                CA = CA[(CA["sku1"] != "") | (CA["producto"] != "")].copy()
                CA["modelo"] = [s_.rsplit("-", 1)[0] if "-" in s_ else (s_ or p_[:40]) for s_, p_ in zip(CA["sku1"], CA["producto"])]
                CA["talle"] = [s_.rsplit("-", 1)[1] if "-" in s_ else "—" for s_ in CA["sku1"]]
                CA["monto"] = pd.to_numeric(CA["monto"], errors="coerce").fillna(0)
                m1, m2, m3 = st.columns([1.3, 1.6, 0.9])
                with m1:
                    ver_m = st.segmented_control("Mostrar", ["Problemas de producto y servicio", "Todos los motivos"],
                                                 default="Problemas de producto y servicio", key="pv_mapa_ver",
                                                 help="'Problemas de producto y servicio' deja afuera el arrepentimiento del comprador y las cancelaciones de MeLi sin causa.") or "Problemas de producto y servicio"
                with m2:
                    cats_disp = [c_ for c_ in PV_CATS_PROD + PV_CATS_ARR + ["Compra no reconocida / fraude", "Cancelada por MeLi sin causa informada", "Otros"]
                                 if (CA["categoria"] == c_).any() and (ver_m == "Todos los motivos" or c_ in PV_CATS_PROD)]
                    cats_sel = st.pills("Tipo de problema", cats_disp, selection_mode="multi", default=cats_disp, key=f"pv_mapa_cats_{ver_m[:5]}",
                                        format_func=lambda x: PV_CAT_CORTO.get(x, x)) or cats_disp
                with m3:
                    min_c = st.number_input("Mínimo de casos", min_value=1, max_value=50, value=2, step=1, key="pv_mapa_min")
                busca_m = st.text_input("Buscar artículo", placeholder="Buscar por nombre o SKU…", key="pv_mapa_buscar")
                CF = CA[CA["categoria"].isin(cats_sel)]
                if busca_m:
                    q_ = busca_m.strip().lower()
                    CF = CF[CF["producto"].str.lower().str.contains(q_, regex=False) | CF["sku1"].str.lower().str.contains(q_, regex=False)]
                b_mod = base_m[(base_m["canal"] == "MercadoLibre") & (base_m["dia"] >= pv_ini)].copy()
                if len(b_mod):
                    b_mod["mod"] = b_mod["sku"].astype(str).map(lambda s_: s_.rsplit("-", 1)[0] if "-" in s_ else s_)
                    ord_mod = b_mod.groupby("mod")["orden_meli" if "orden_meli" in b_mod.columns else "id_pedido"].nunique()
                else:
                    ord_mod = pd.Series(dtype=float)
                cats_cols = [c_ for c_ in PV_CATS_PROD + PV_CATS_ARR + ["Compra no reconocida / fraude", "Cancelada por MeLi sin causa informada", "Otros"] if c_ in cats_sel and (CF["categoria"] == c_).any()]
                res_m = []
                for (mk, md), d in CF.groupby(["marca", "modelo"]):
                    if len(d) < min_c:
                        continue
                    cnt_c = d["categoria"].value_counts()
                    princ = cnt_c.index[0]
                    det_p = d.loc[d["categoria"] == princ, "motivo_es"].value_counts()
                    diag = PV_DIAG.get(princ, "Revisar casos")
                    if princ == "Talle, color o medida":
                        ch, gr = int(d["motivo_es"].eq("Le quedó chico").sum()), int(d["motivo_es"].eq("Le quedó grande").sum())
                        if ch > gr and ch >= 2:
                            diag = "Calza chico: sugerir medio/un talle más en la publicación"
                        elif gr > ch and gr >= 2:
                            diag = "Calza grande: sugerir un talle menos en la publicación"
                    tall = d.loc[d["talle"] != "—", "talle"].value_counts()
                    ords = float(ord_mod.get(md, 0))
                    res_m.append({"marca": mk, "modelo": md, "d": d, "n": len(d), "monto": float(d["monto"].sum()), "cnt": cnt_c,
                                  "princ": princ, "det": det_p.index[0] if len(det_p) else "", "diag": diag,
                                  "talles": ", ".join(f"{t_} ({v_})" for t_, v_ in tall.head(3).items()),
                                  "ordenes": ords, "tasa": len(d) / ords * 100 if ords else np.nan,
                                  "producto": d["producto"].value_counts().index[0] if (d["producto"] != "").any() else md})
                orden_m = st.segmented_control("Ordenar por", ["Cantidad de casos", "Tasa sobre ventas", "Facturación afectada"],
                                               default="Cantidad de casos", key="pv_mapa_orden") or "Cantidad de casos"
                kf = {"Cantidad de casos": lambda x: (-x["n"], -x["monto"]), "Facturación afectada": lambda x: -x["monto"],
                      "Tasa sobre ventas": lambda x: -(x["tasa"] if pd.notna(x["tasa"]) and x["ordenes"] >= 5 else -1)}[orden_m]
                res_m.sort(key=kf)
                if not res_m:
                    st.info("Ningún artículo cumple el filtro (probá bajar el mínimo de casos).")
                else:
                    mx = max(int(r_["cnt"].max()) for r_ in res_m)
                    cols_m = "minmax(230px,2.3fr) 0.5fr 0.6fr 0.55fr minmax(230px,1.9fr) " + " ".join(["0.72fr"] * len(cats_cols))
                    cab = ["Artículo", "Casos", "Órdenes", "Tasa", "Problema principal → qué hacer"] + [PV_CAT_CORTO.get(c_, c_) for c_ in cats_cols]
                    bloques = ""
                    for r_ in res_m[:60]:
                        celdas = [f"<span class='grp-tit'><img src='{img_azure(r_['marca'], r_['modelo'])}'><span><b>{str(r_['producto'])[:46]}</b>"
                                  f"<small>{r_['marca']} · {r_['modelo']}{' · talles: ' + r_['talles'] if r_['talles'] else ''}</small></span></span>",
                                  f"<b>{fmt_num(r_['n'])}</b>", fmt_num(r_['ordenes']) if r_["ordenes"] else "—",
                                  (fmt_dec(r_["tasa"], 1) + "%") if pd.notna(r_["tasa"]) else "—",
                                  f"<span style='white-space:normal;font-size:12px;text-align:left;display:block'><b>{PV_CAT_CORTO.get(r_['princ'], r_['princ'])}</b>: {r_['det']}<br>"
                                  f"<span style='color:#FBBF24'>→ {r_['diag']}</span></span>"]
                        for c_ in cats_cols:
                            v_ = int(r_["cnt"].get(c_, 0))
                            col_ = PV_COLOR_ORIGEN.get(PV_CAT_ORIGEN.get(c_, ""), "#94A3B8")
                            alpha = int((0.15 + 0.6 * v_ / mx) * 255) if v_ else 0
                            celdas.append(f"<span style='display:inline-block;min-width:34px;padding:2px 6px;border-radius:6px;"
                                          f"background:{col_}{alpha:02x};font-weight:700'>{v_}</span>" if v_ else "<span style='color:#475569'>·</span>")
                        fil = ""
                        for _, x in r_["d"].sort_values("fecha", ascending=False).head(40).iterrows():
                            fil += (f"<tr><td>{x['fecha']:%d/%m/%Y}</td><td><b>{x['talle']}</b></td><td>{x['sku1'] or '—'}</td>"
                                    f"<td style='text-align:left'>{PV_CAT_CORTO.get(x['categoria'], x['categoria'])}</td>"
                                    f"<td style='text-align:left;white-space:normal'>{x['motivo_es']}</td><td style='text-align:left'>{x['fuente']}</td>"
                                    f"<td style='text-align:left'>{x['estado_caso']}</td><td>{fmt_ars(x['monto']) if x['monto'] else '—'}</td>"
                                    f"<td>{int(x['orden_meli']) if pd.notna(x['orden_meli']) else '—'}</td></tr>")
                        det = ("<table class='ftable grp-det'><thead><tr><th>Fecha</th><th>Talle</th><th>SKU</th><th style='text-align:left'>Problema</th>"
                               "<th style='text-align:left'>Detalle</th><th style='text-align:left'>Caso</th><th style='text-align:left'>Estado</th><th>Monto</th><th>Orden</th></tr></thead>"
                               f"<tbody>{fil}</tbody></table>")
                        bloques += ("<details class='grp'><summary class='grp-row' style='grid-template-columns:" + cols_m + "'>" +
                                    "".join(f"<div>{c_}</div>" for c_ in celdas) + "</summary>" + det + "</details>")
                    cab_html = "<div class='grp-row grp-head' style='grid-template-columns:" + cols_m + "'>" + "".join(f"<div>{c_}</div>" for c_ in cab) + "</div>"
                    html("<div class='tbl-wrap'><div style='min-width:" + str(900 + 85 * len(cats_cols)) + "px'>" + cab_html + bloques + "</div></div>")
                    st.caption(f"{fmt_num(min(len(res_m), 60))} de {fmt_num(len(res_m))} artículos con {min_c}+ casos. Tasa = casos / órdenes de MeLi del artículo en el período. "
                               "Colores: rojo = depende de nosotros, celeste = del comprador, violeta = logística."
                               + (f" {fmt_num(sin_art)} casos no traen el artículo y no se muestran." if sin_art else ""))
                    exp = CF[["marca", "modelo", "producto", "talle", "sku1", "fecha", "categoria", "motivo_es", "fuente", "estado_caso", "monto", "orden_meli"]].copy()
                    exp["fecha"] = exp["fecha"].dt.strftime("%d/%m/%Y")
                    exp.columns = ["Marca", "Artículo", "Producto", "Talle", "SKU", "Fecha", "Problema", "Detalle", "Caso", "Estado", "Monto", "Orden"]
                    st.download_button("Descargar casos por artículo (CSV)", a_str(exp).to_csv(index=False).encode("utf-8"),
                                       file_name="meli_problemas_por_articulo.csv", mime="text/csv", icon=":material/download:", key="dl_pv_mapa")

            # ---------- RECLAMOS: gestión ----------
            seccion("Reclamos", "Cómo se resuelven los reclamos y dónde están las devoluciones",
                    "Devolución = el comprador devuelve el producto. Cancelación antes del envío = la pidió el comprador. Reclamo = problema con la compra.")
            if Rp.empty:
                st.info("Sin reclamos en el período.")
            else:
                g1, g2, g3 = st.columns(3)
                with g1:
                    tt = Rp["tipo_es"].value_counts().reset_index()
                    tt.columns = ["tipo", "n"]
                    fig = go.Figure(go.Pie(labels=tt["tipo"], values=tt["n"], hole=0.6, textinfo="percent+label",
                                           marker=dict(colors=["#A78BFA", "#38BDF8", "#FBBF24", "#64748B"])))
                    fig.update_layout(title="Tipo de reclamo", showlegend=False)
                    st.plotly_chart(estilo(fig, 340), width="stretch")
                with g2:
                    af = Rp["a_favor"].value_counts()
                    fig = go.Figure(go.Pie(labels=af.index, values=af.values, hole=0.6, textinfo="percent+label",
                                           marker=dict(colors=[{"Comprador": "#F87171", "Nosotros": "#34D399", "Abierto": "#FBBF24",
                                                                "Parcial (ambos)": "#38BDF8"}.get(x, "#94A3B8") for x in af.index])))
                    fig.update_layout(title="¿A favor de quién se resolvió?", showlegend=False)
                    st.plotly_chart(estilo(fig, 340), width="stretch")
                with g3:
                    dv = Rp[Rp["dev_estado"] != ""]["dev_es"].value_counts().reset_index()
                    dv.columns = ["estado", "n"]
                    fig = px.bar(dv, x="n", y="estado", orientation="h", text="n", title="¿Dónde están las devoluciones?", color_discrete_sequence=["#A78BFA"])
                    fig.update_traces(marker_line_width=0)
                    fig.update_layout(xaxis_title="", yaxis_title="", yaxis=dict(autorange="reversed"))
                    st.plotly_chart(estilo(fig, 340), width="stretch")
                rs = Rp[Rp["estado"] == "closed"].groupby("resolucion_es").size().sort_values(ascending=False)
                filas = "".join(f"<tr><td style='text-align:left'>{k_}</td><td>{fmt_num(v_)}</td><td>{fmt_dec(v_ / rs.sum() * 100 if rs.sum() else 0)}%</td></tr>"
                                for k_, v_ in rs.items())
                g1, g2 = st.columns([1, 1.4])
                with g1:
                    st.markdown("**Cómo se cerraron**")
                    html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Resolución</th><th>Reclamos</th><th>%</th></tr></thead>"
                         f"<tbody>{filas}</tbody></table></div>")
                with g2:
                    mr = Rp.groupby(["categoria", "motivo_es"]).size().rename("n").reset_index().sort_values("n", ascending=False).head(12)
                    filas = "".join(f"<tr><td style='text-align:left;white-space:normal'>{r_['motivo_es']}</td><td style='text-align:left'>{r_['categoria']}</td>"
                                    f"<td>{fmt_num(r_['n'])}</td><td>{fmt_dec(r_['n'] / len(Rp) * 100)}%</td></tr>" for _, r_ in mr.iterrows())
                    st.markdown("**Motivos que eligen los compradores al reclamar**")
                    html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Motivo</th><th style='text-align:left'>Categoría</th>"
                         f"<th>Reclamos</th><th>%</th></tr></thead><tbody>{filas}</tbody></table></div>")
                ab = Rp[Rp["estado"] != "closed"].sort_values("fecha")
                if len(ab):
                    prod_ord = dict(zip(C["orden_meli"], C["producto"]))
                    st.markdown(f"**Reclamos abiertos para gestionar ({fmt_num(len(ab))})** · los más viejos primero")
                    filas = ""
                    for _, r_ in ab.head(40).iterrows():
                        dias_ = (hoy - r_["dia"]).days
                        cls = "ok" if dias_ <= 2 else ("warn" if dias_ <= 6 else "bad")
                        prod = str(r_["titulos"] or prod_ord.get(r_["orden_meli"], "") or "—").split(" | ")[0]
                        filas += (f"<tr><td class='strong'>{r_['claim_id']}</td><td>{r_['marca']}</td><td>{r_['fecha']:%d/%m}</td>"
                                  f"<td><span class='pill {cls}'>{dias_} días</span></td><td>{r_['tipo_es']}</td><td>{r_['etapa_es']}</td>"
                                  f"<td style='text-align:left;white-space:normal'>{r_['motivo_es']}</td><td>{r_['dev_es'] or '—'}</td>"
                                  f"<td>{fmt_ars(r_['monto']) if pd.notna(r_['monto']) else '—'}</td>"
                                  f"<td style='text-align:left;max-width:260px;overflow:hidden;text-overflow:ellipsis'>{prod[:50]}</td></tr>")
                    html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Reclamo</th><th>Marca</th><th>Abierto</th><th>Hace</th><th>Tipo</th>"
                         "<th>Instancia</th><th style='text-align:left'>Motivo</th><th>Devolución</th><th>Monto</th><th style='text-align:left'>Producto</th></tr></thead>"
                         f"<tbody>{filas}</tbody></table></div>")
                exp = Rp[["marca", "claim_id", "orden_meli", "fecha", "tipo_es", "etapa_es", "estado", "categoria", "motivo_es", "a_favor", "resolucion_es",
                          "cubierto", "dev_es", "monto", "titulos", "skus"]].copy()
                exp["fecha"] = exp["fecha"].dt.strftime("%d/%m/%Y %H:%M")
                exp["estado"] = exp["estado"].map({"closed": "Cerrado", "opened": "Abierto"}).fillna(exp["estado"])
                exp.columns = ["Marca", "Reclamo", "Orden", "Fecha", "Tipo", "Instancia", "Estado", "Categoría", "Motivo", "A favor de", "Resolución",
                               "Protección MeLi", "Devolución", "Monto", "Producto", "SKU"]
                st.download_button("Descargar reclamos (CSV)", a_str(exp).to_csv(index=False).encode("utf-8"), file_name="meli_reclamos.csv",
                                   mime="text/csv", icon=":material/download:", key="dl_pv_recl")


# ==============================================================================
# TAB 5 · OPERACIONES
# ==============================================================================
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
            # Filtros propios de esta sección (parten de todos los canales, no del selector de arriba)
            pend_all = P[P["envio_estado"].astype(str).isin(ENV_PEND)].copy()
            pend_all["canal"] = pend_all["canal"].astype(str)
            pend_all["marca"] = pend_all["marca"].astype(str)
            pc1, pc2 = st.columns([1, 1.6])
            with pc1:
                sel_p = st.segmented_control("Canal", OPC_CANAL, default=sel_o, key="pend_canal") or "Consolidado"
            marcas_p_disp = [m for m in MARCAS_BASE if m in set(pend_all["marca"])] + sorted(set(pend_all["marca"]) - set(MARCAS_BASE))
            with pc2:
                marcas_p = st.pills("Marcas", marcas_p_disp, selection_mode="multi", default=marcas_p_disp, key="pend_marcas") or marcas_p_disp
            pend = por_canal(pend_all, sel_p)
            pend = pend[pend["marca"].isin(marcas_p)]
            _esp = por_canal(P[P["envio_estado"].astype(str) == "Esperando pago"], sel_p)
            _esp = _esp[_esp["marca"].astype(str).isin(marcas_p)]
            st.caption(f"No se cuentan: pedidos Reversso, con pago vencido/anulado y cancelados. "
                       f"{fmt_num(len(_esp))} pedido(s) de Tienda esperando acreditación del pago tampoco suman (todavía no se pueden despachar).")
            if pend.empty:
                st.success("No hay pedidos pendientes de despacho para este filtro. 🎉")
            else:
                pend = pend.copy()
                pend["dias_hab"] = dias_habiles(pend["fecha"], hoy)
                tramos = [("Hoy", 0, 0, "#34D399"), ("1 día háb.", 1, 1, "#FBBF24"), ("2 días háb.", 2, 2, "#FB923C"),
                          ("3 a 5 días háb.", 3, 5, "#F87171"), ("+5 días háb.", 6, 10**6, "#EF4444")]
                pend["tramo"] = pd.cut(pend["dias_hab"], bins=[-1, 0, 1, 2, 5, 10**6], labels=[t[0] for t in tramos])

                def _split_marcas(sub):
                    vc = sub["marca"].value_counts()
                    tot = int(vc.sum())
                    if tot == 0:
                        return ""
                    segs = "".join(f"<div style='width:{v / tot * 100:.2f}%;background:{PALETA_MARCAS.get(m_, '#94A3B8')}'></div>" for m_, v in vc.items())
                    leg = "".join(f"<span><span class='dot' style='background:{PALETA_MARCAS.get(m_, '#94A3B8')}'></span>{m_} {v}</span>" for m_, v in vc.head(3).items())
                    return f"<div class='split'>{segs}</div><div class='split-legend'>{leg}</div>"

                k = st.columns(len(tramos))
                for col, (lbl, lo, hi, colr) in zip(k, tramos):
                    sub = pend[(pend["dias_hab"] >= lo) & (pend["dias_hab"] <= hi)]
                    spl = split_html(por_canal_vals(sub, "ords")) if sel_p == "Consolidado" else _split_marcas(sub)
                    col.markdown(kpi_card(lbl, fmt_num(len(sub)), f"<span class='delta flat'>{fmt_num(sub['unidades'].sum())} unid.</span>",
                                          spl, colr, sm=True), unsafe_allow_html=True)
                st.write("")

                # ---- Por marca: matriz antigüedad + gráfico ----
                mat = pend.pivot_table(index="marca", columns="tramo", values="nro_pedido", aggfunc="count", fill_value=0, observed=False)
                mat = mat.reindex(columns=[t[0] for t in tramos], fill_value=0)
                mat["Total"] = mat.sum(axis=1)
                mat = mat.sort_values("Total", ascending=False)
                uni_m = pend.groupby("marca")["unidades"].sum()
                monto_m = pend.groupby("marca")["total_pedido"].sum()
                por_canal_m = pend.groupby(["marca", "canal"]).size().unstack(fill_value=0)
                g1, g2 = st.container(), st.container()
                with g1:
                    filas = ""
                    mx = max(1, int(mat[[t[0] for t in tramos]].values.max()))
                    for m_, r in mat.iterrows():
                        celdas = ""
                        for (lbl, _, _, colr) in tramos:
                            v = int(r[lbl])
                            alpha = 0.08 + 0.55 * (v / mx) if v else 0
                            bg = f"background:{colr}{int(alpha * 255):02x};" if v else ""
                            celdas += f"<td style='{bg}text-align:center;font-weight:{700 if v else 400}'>{fmt_num(v) if v else '·'}</td>"
                        atr = int(r["3 a 5 días háb."] + r["+5 días háb."])
                        pct_atr = atr / r["Total"] * 100 if r["Total"] else 0
                        cls = "ok" if pct_atr < 5 else ("warn" if pct_atr < 15 else "bad")
                        canal_txt = " · ".join(f"{CORTO.get(c_, c_)} {int(por_canal_m.loc[m_, c_])}" for c_ in por_canal_m.columns if por_canal_m.loc[m_, c_] > 0)
                        filas += (f"<tr><td class='strong'><span class='dot' style='background:{PALETA_MARCAS.get(m_, '#94A3B8')}'></span>{m_}"
                                  f"<br><small style='color:var(--muted);font-weight:500;margin-left:14px'>{canal_txt}</small></td>{celdas}"
                                  f"<td class='strong sep'>{fmt_num(r['Total'])}</td><td>{fmt_num(uni_m.get(m_, 0))}</td><td>{fmt_compact(monto_m.get(m_, 0))}</td>"
                                  f"<td><span class='pill {cls}'>{pct_atr:.0f}%</span></td></tr>")
                    tot_r = mat.sum()
                    atr_t = int(tot_r["3 a 5 días háb."] + tot_r["+5 días háb."])
                    filas += ("<tr class='total'><td>Total</td>" + "".join(f"<td style='text-align:center'>{fmt_num(tot_r[t[0]])}</td>" for t in tramos) +
                              f"<td class='sep'>{fmt_num(tot_r['Total'])}</td><td>{fmt_num(pend['unidades'].sum())}</td><td>{fmt_compact(pend['total_pedido'].sum())}</td>"
                              f"<td>{atr_t / tot_r['Total'] * 100 if tot_r['Total'] else 0:.0f}%</td></tr>")
                    html("<div class='tbl-wrap'><table class='ftable compact'><thead><tr><th>Marca</th>" +
                         "".join(f"<th style='text-align:center'>{t[0]}</th>" for t in tramos) +
                         "<th class='sep'>Total</th><th>Unid.</th><th>Monto</th><th>% 3+ días</th></tr></thead>"
                         f"<tbody>{filas}</tbody></table></div>")
                    st.caption("Pedidos pendientes por marca y antigüedad. '% 3+ días' = parte de los pendientes de la marca con 3 o más días hábiles de espera.")
                with g2:
                    bar = pend.groupby(["marca", "tramo"], observed=False).size().rename("pedidos").reset_index()
                    bar["marca"] = bar["marca"].astype(str)
                    bar = bar[bar["marca"].isin(mat.index)]
                    fig = px.bar(bar, y="marca", x="pedidos", color="tramo", orientation="h", title="Pendientes por marca y antigüedad",
                                 category_orders={"marca": list(mat.index), "tramo": [t[0] for t in tramos]},
                                 color_discrete_map={t[0]: t[3] for t in tramos})
                    fig.update_traces(marker_line_width=0)
                    fig.update_layout(xaxis_title="", yaxis_title="", barmode="stack", bargap=0.3, legend_title_text="")
                    fig = estilo(fig, 110 + 48 * max(3, len(mat)))
                    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0), margin=dict(t=80))
                    st.plotly_chart(fig, width="stretch")

                # ---- Detalle de pedidos ----
                ver_tr = st.segmented_control("Ver pedidos", ["Todos"] + [t[0] for t in tramos], default="Todos", key="pend_tramo") or "Todos"
                det_p = pend if ver_tr == "Todos" else pend[pend["tramo"].astype(str) == ver_tr]
                viejos = det_p.sort_values(["dias_hab", "fecha"], ascending=[False, True])
                filas = ""
                for _, r in viejos.head(30).iterrows():
                    dh = int(r["dias_hab"])
                    cls = "ok" if dh == 0 else ("warn" if dh <= 2 else "bad")
                    filas += (f"<tr><td class='strong'>{r['nro_pedido']}</td>"
                              f"<td><span class='dot' style='background:{COLOR_CANAL.get(r['canal'], '#94A3B8')}'></span>{CORTO.get(r['canal'], r['canal'])}</td>"
                              f"<td>{r['marca']}</td><td>{r['fecha']:%d/%m %H:%M}</td><td><span class='pill {cls}'>{dh} días háb.</span></td>"
                              f"<td>{r['envio_estado']}</td><td>{r['provincia']}</td><td>{fmt_num(r['unidades'])}</td><td>{fmt_ars(r['total_pedido'])}</td></tr>")
                if filas:
                    html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Pedido</th><th>Canal</th><th>Marca</th><th>Compra</th>"
                         "<th>Esperando</th><th>Estado</th><th>Provincia</th><th>Unid.</th><th>Total</th></tr></thead>"
                         f"<tbody>{filas}</tbody></table></div>")
                exp = viejos[["nro_pedido", "canal", "marca", "fecha", "dias_hab", "envio_estado", "envio_detalle", "provincia", "unidades", "total_pedido"]].copy()
                exp["fecha"] = exp["fecha"].dt.strftime("%d/%m/%Y %H:%M")
                st.caption(f"Los 30 más atrasados de {fmt_num(len(det_p))} pendientes del filtro.")
                st.download_button("Descargar pendientes del filtro (CSV)", a_str(exp).to_csv(index=False).encode("utf-8"),
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


# ==============================================================================
# TAB · CYBER MONDAY (en vivo)
# ==============================================================================
CYBER_INI_DEF = datetime(2026, 11, 2, 0, 0, tzinfo=ZONA_AR)
CYBER_FIN_DEF = datetime(2026, 11, 9, 23, 59, 59, tzinfo=ZONA_AR)


CYBER_PREV_INI = datetime(2025, 11, 3, 0, 0, tzinfo=ZONA_AR)


@st.cache_data(ttl=1800, show_spinner=False)
def cyber_prev_ref():
    """Cyber Monday 2025 (3/11 al 9/11/2025) desde cyber_2025.csv (archivo liviano). Si todavía no existe, no hay comparativa."""
    try:
        c = leer_csv_repo("cyber_2025.csv")
    except Exception:
        c = pd.DataFrame()
    if not c.empty:
        c = c[pd.to_numeric(c["es_reverso"], errors="coerce").fillna(0) == 0].copy()
        c["fecha"] = pd.to_datetime(c["fecha"], errors="coerce", format="mixed", utc=True).dt.tz_convert(ZONA_AR)
        c = c.dropna(subset=["fecha"])
        c["hora_ev"] = ((c["fecha"] - CYBER_PREV_INI).dt.total_seconds() // 3600).astype(int)
        c["canal"] = c["canal"].astype(str)
        c["marca"] = c["marca"].astype(str)
        return c, "Cyber Monday 2025", CYBER_PREV_INI.date()
    return pd.DataFrame(), "", None


if tab_cyber is not None:
    with tab_cyber:
        ev_ini, ev_fin = CYBER_INI_DEF, CYBER_FIN_DEF
        if ES_ADMIN:
            with st.expander("⚙️ Fechas del evento", expanded=False):
                fe = st.date_input("Inicio y fin del Cyber Monday", (CYBER_INI_DEF.date(), CYBER_FIN_DEF.date()), key="cy_fechas", format="DD/MM/YYYY")
                if isinstance(fe, (list, tuple)) and len(fe) == 2:
                    ev_ini = datetime.combine(fe[0], datetime.min.time(), tzinfo=ZONA_AR)
                    ev_fin = datetime.combine(fe[1], datetime.max.time(), tzinfo=ZONA_AR)
        dur_h = (ev_fin - ev_ini).total_seconds() / 3600
        en_curso = ev_ini <= ahora <= ev_fin
        trans_h = min(max((ahora - ev_ini).total_seconds() / 3600, 0), dur_h)

        Ev_T = base_net[(base_net["fecha"] >= ev_ini) & (base_net["fecha"] <= ev_fin)]
        PE_T = a_pedidos(Ev_T)
        PE_T["canal"] = PE_T["canal"].astype(str)
        PE_T["marca"] = PE_T["marca"].astype(str)
        # Día normal de referencia: promedio diario de los 28 días previos al evento
        ref_T = base_net[(base_net["fecha"] < ev_ini) & (base_net["fecha"] >= ev_ini - timedelta(days=28))]
        Pref_T = a_pedidos(ref_T)
        Pref_T["canal"] = Pref_T["canal"].astype(str)
        prev_all, prev_lbl, prev_ini = cyber_prev_ref()
        if len(prev_all):
            prev_all = prev_all[prev_all["marca"].isin(marcas_sel)]

        def prev_hasta(canales_, marca_=None, hasta_h=None):
            """(facturación, pedidos, unidades) del evento anterior hasta la misma hora del evento."""
            if not len(prev_all):
                return None
            h_ = trans_h if hasta_h is None else hasta_h
            d_ = prev_all[prev_all["canal"].isin(canales_) & (prev_all["hora_ev"] < h_)]
            if marca_:
                d_ = d_[d_["marca"] == marca_]
            pdp = d_.drop_duplicates(["canal", "marca", "id_pedido"])
            return float(pdp["total_pedido"].sum()), float(len(pdp)), float(pd.to_numeric(d_["cantidad"], errors="coerce").sum())

        def _var(a_, b_):
            if not b_:
                return "—"
            v_ = (a_ / b_ - 1) * 100
            return f"<span style='color:{'#34D399' if v_ >= 0 else '#F87171'};font-weight:700'>{'+' if v_ >= 0 else ''}{fmt_dec(v_, 0)}%</span>"
        prev_canales = set(prev_all["canal"]) if len(prev_all) else set()

        # ---------- cabecera ----------
        if ahora < ev_ini:
            falta = ev_ini - ahora
            estado_txt = f"⏳ Arranca en {falta.days * 24 + falta.seconds // 3600} h {(falta.seconds % 3600) // 60} min"
            col_e = "#FBBF24"
        elif en_curso:
            estado_txt = f"🔴 EN VIVO · hora {int(trans_h) + 1} de {int(round(dur_h))}"
            col_e = "#F87171"
        else:
            estado_txt = "✅ Evento finalizado"
            col_e = "#34D399"
        rb = estado_robot()
        ult = df_raw["fecha"].max() if len(df_raw) else None
        html(f"<div class='hero' style='padding:18px 26px;margin-bottom:14px'><div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px'>"
             f"<div><div class='hero-eyebrow'>Evento</div><div class='hero-title' style='font-size:34px'>Cyber Monday 2026</div>"
             f"<div class='hero-sub'>{ev_ini:%d/%m %H:%M} → {ev_fin:%d/%m %H:%M} · {len(marcas_sel)} marcas · Tienda Online + MercadoLibre</div></div>"
             f"<div style='text-align:right'><div style='font-size:20px;font-weight:800;color:{col_e}'>{estado_txt}</div>"
             f"<div class='hero-sub'>Última venta registrada: {ult:%d/%m %H:%M} hs · se actualiza cada ~5 min</div></div></div></div>")

        # ---------- TIENDA vs MELI ----------
        cc_ = st.columns(2)
        tot_T = float(PE_T["total_pedido"].sum())
        for col, c_ in zip(cc_, CANALES):
            d_ = PE_T[PE_T["canal"] == c_]
            f_, n_, u_ = float(d_["total_pedido"].sum()), len(d_), float(d_["unidades"].sum())
            dn_ = float(Pref_T.loc[Pref_T["canal"] == c_, "total_pedido"].sum()) / 28 if len(Pref_T) else 0
            h1_ = d_[d_["fecha"] >= ahora - timedelta(hours=1)]
            rit_ = f_ / trans_h if trans_h > 0 else 0
            pr_ = rit_ * dur_h if en_curso and trans_h >= 1 else (f_ if ahora > ev_fin else 0)
            x_ = f_ / (dn_ * max(trans_h / 24, 1 / 24)) if dn_ and trans_h > 0 else None
            celdas = [("Facturación", fmt_compact(f_), f"{fmt_dec(f_ / tot_T * 100 if tot_T else 0, 0)}% del total"),
                      ("Pedidos", fmt_num(n_), f"ticket {fmt_compact(f_ / n_ if n_ else 0)}"),
                      ("Unidades", fmt_num(u_), f"{fmt_dec(u_ / n_ if n_ else 0, 2)} por pedido"),
                      ("Última hora", fmt_compact(float(h1_["total_pedido"].sum())), f"{fmt_num(len(h1_))} pedidos"),
                      ("Ritmo vs normal", (fmt_dec(x_, 1) + "x") if x_ else "—", "promedio 28 días previos"),
                      ("Proyección", fmt_compact(pr_) if pr_ else "—", f"{fmt_compact(rit_)}/hora")]
            pv_ = prev_hasta([c_]) if c_ in prev_canales else None
            if pv_:
                celdas.append((f"vs {prev_lbl.split(' (')[0]} (misma hora)", _var(f_, pv_[0]),
                               f"pedidos {_var(n_, pv_[1])} · unidades {_var(u_, pv_[2])}"))
            cuerpo = "".join(f"<div style='flex:1 1 30%;min-width:120px;padding:10px 12px;background:rgba(148,163,184,.06);border-radius:12px'>"
                             f"<div style='font-size:10.5px;letter-spacing:1px;text-transform:uppercase;color:var(--muted);font-weight:700'>{a}</div>"
                             f"<div style='font-size:22px;font-weight:800;color:#F8FAFC;margin:2px 0'>{b}</div>"
                             f"<div style='font-size:11.5px;color:var(--muted)'>{c}</div></div>" for a, b, c in celdas)
            col.markdown(f"<div style='background:var(--card);border:1px solid var(--border);border-top:3px solid {COLOR_CANAL[c_]};border-radius:18px;padding:14px 16px'>"
                         f"<div style='font-size:15px;font-weight:800;color:{COLOR_CANAL[c_]};margin-bottom:10px'>● {c_}</div>"
                         f"<div style='display:flex;flex-wrap:wrap;gap:8px'>{cuerpo}</div></div>", unsafe_allow_html=True)
        st.write("")
        canal_cy = st.segmented_control("Ver el detalle de", ["General", "Tienda Online", "MercadoLibre"], default="General", key="cy_canal") or "General"
        if canal_cy == "General":
            Ev, PE, Pref = Ev_T, PE_T, Pref_T
        else:
            Ev = Ev_T[Ev_T["canal"].astype(str) == canal_cy]
            PE = PE_T[PE_T["canal"] == canal_cy]
            Pref = Pref_T[Pref_T["canal"] == canal_cy]
        dia_normal = float(Pref["total_pedido"].sum()) / 28 if len(Pref) else 0
        hora_normal = dia_normal / 24

        # ---------- KPIs ----------
        fact, ped, uni = float(PE["total_pedido"].sum()), len(PE), float(PE["unidades"].sum())
        tk = fact / ped if ped else 0
        u1h = PE[PE["fecha"] >= ahora - timedelta(hours=1)]
        ritmo = fact / trans_h if trans_h > 0 else 0
        proy = ritmo * dur_h if en_curso and trans_h >= 1 else (fact if ahora > ev_fin else 0)
        cy_obj = (objetivos.get("cyber", {}) or {}) if isinstance(objetivos, dict) else {}
        cy_det = cy_obj.get("detalle") or {}
        hay_det = any(v for c_ in CANALES for v in (cy_det.get(c_) or {}).values())

        def meta_cm(canales_, marcas_):
            if hay_det:
                return float(sum((cy_det.get(c_) or {}).get(m_, 0) for c_ in canales_ for m_ in marcas_))
            # sin apertura: la meta total solo aplica a todas las marcas y ambos canales
            return float(cy_obj.get("facturacion", 0)) if (set(canales_) == set(CANALES) and set(marcas_) >= set(MARCAS_BASE)) else 0.0
        meta_tot = float(cy_obj.get("facturacion", 0) or 0)
        meta_cy = meta_cm(CANALES if canal_cy == "General" else [canal_cy], marcas_sel)
        esp_pct = trans_h / dur_h * 100 if dur_h else 0
        k = st.columns(6)
        k[0].markdown(kpi_card("Facturación del evento", fmt_compact(fact),
                               f"<span class='delta up'>{fmt_dec(fact / (dia_normal * max(trans_h / 24, 1 / 24)), 1)}x el ritmo normal</span>" if dia_normal and fact and trans_h > 0 else "",
                               split_html(por_canal_vals(PE, "total_pedido")), "#22D3EE"), unsafe_allow_html=True)
        k[1].markdown(kpi_card("Pedidos", fmt_num(ped), "", split_html(por_canal_vals(PE, "ords")), "#A78BFA"), unsafe_allow_html=True)
        k[2].markdown(kpi_card("Unidades", fmt_num(uni), "", f"<div class='split-legend' style='margin-top:10px'><span>{fmt_dec(uni / ped if ped else 0, 2)} por pedido</span></div>", "#34D399"), unsafe_allow_html=True)
        k[3].markdown(kpi_card("Ticket promedio", fmt_ars(tk), "", "", "#FBBF24"), unsafe_allow_html=True)
        k[4].markdown(kpi_card("Última hora", fmt_compact(float(u1h["total_pedido"].sum())),
                               f"<span class='delta up'>{fmt_dec(u1h['total_pedido'].sum() / hora_normal, 1)}x una hora normal</span>" if hora_normal and len(u1h) else "",
                               f"<div class='split-legend' style='margin-top:10px'><span>{fmt_num(len(u1h))} pedidos</span></div>", "#F472B6"), unsafe_allow_html=True)
        k[5].markdown(kpi_card("Proyección al cierre", fmt_compact(proy) if proy else "—",
                               (f"<span class='delta {'up' if proy >= meta_cy else 'down'}'>{fmt_dec(proy / meta_cy * 100, 0)}% de la meta</span>" if meta_cy and proy else ""),
                               f"<div class='split-legend' style='margin-top:10px'><span>ritmo {fmt_compact(ritmo)}/hora</span></div>", "#FFE600"), unsafe_allow_html=True)
        if ES_ADMIN:
            with st.expander("🎯 Metas de facturación del evento (por marca y canal)", expanded=False):
                ed_cy = pd.DataFrame({"Marca": MARCAS_BASE,
                                      "Tienda Online": [int((cy_det.get("Tienda Online") or {}).get(m_, 0)) for m_ in MARCAS_BASE],
                                      "MercadoLibre": [int((cy_det.get("MercadoLibre") or {}).get(m_, 0)) for m_ in MARCAS_BASE]})
                ed_cy_out = st.data_editor(ed_cy, hide_index=True, width="stretch", key="cy_meta_ed", column_config={
                    "Marca": st.column_config.TextColumn(disabled=True),
                    "Tienda Online": st.column_config.NumberColumn("Tienda Online ($)", min_value=0, step=1_000_000, format="localized"),
                    "MercadoLibre": st.column_config.NumberColumn("MercadoLibre ($)", min_value=0, step=1_000_000, format="localized")})
                tot_ed = int(ed_cy_out[["Tienda Online", "MercadoLibre"]].fillna(0).values.sum())
                st.caption(f"Total de la apertura: **{fmt_ars(tot_ed)}**".replace("$", "\\$") +
                           (f" · meta total cargada antes: {fmt_ars(meta_tot)}".replace("$", "\\$") if meta_tot and not hay_det else ""))
                if st.button("Guardar metas", key="cy_meta_btn", type="primary"):
                    o2 = dict(objetivos) if isinstance(objetivos, dict) else {}
                    det_new = {c_: {r_["Marca"]: int(r_[c_] or 0) for _, r_ in ed_cy_out.iterrows()} for c_ in CANALES}
                    nv = tot_ed if tot_ed else int(meta_tot)
                    o2["cyber"] = {"facturacion": nv, "detalle": det_new}
                    ok_, msg_ = guardar_objetivos(o2)
                    (st.success if ok_ else st.error)(msg_)
                    if ok_:
                        load_objetivos.clear()
                        st.rerun()
        if meta_cy:
            av = fact / meta_cy * 100
            esp = esp_pct
            html(f"<div style='margin:6px 0 4px;font-size:13px;color:#CBD5E1'>Meta {fmt_compact(meta_cy)} · <b>{fmt_dec(av, 1)}%</b> logrado · "
                 f"debería ir {fmt_dec(esp, 0)}% según el tiempo transcurrido</div>"
                 f"<div style='height:12px;background:rgba(148,163,184,.15);border-radius:99px;position:relative;overflow:hidden'>"
                 f"<div style='width:{min(av, 100):.1f}%;height:100%;background:linear-gradient(90deg,#22D3EE,#A78BFA)'></div>"
                 f"<div style='position:absolute;left:{min(esp, 100):.1f}%;top:-2px;width:2px;height:16px;background:#F8FAFC'></div></div>")

        # ---------- METAS POR MARCA Y CANAL ----------
        if hay_det:
            seccion("Metas", "Avance de metas por marca y canal",
                    f"Avance = facturado / meta. Esperado a esta hora: {fmt_dec(esp_pct, 0)}% (tiempo transcurrido del evento). "
                    "Proyección = ritmo actual llevado al cierre.")

            def _pill_av(real_, meta_):
                if not meta_:
                    return "<span style='color:#475569'>—</span>"
                a_ = real_ / meta_ * 100
                cls_ = "ok" if a_ >= esp_pct else ("warn" if a_ >= esp_pct * 0.8 else "bad")
                return f"<span class='pill {cls_}'>{fmt_dec(a_, 1)}%</span>"
            filas = ""
            tots = {c_: [0.0, 0.0] for c_ in CANALES}
            for m_ in marcas_sel:
                fila = f"<tr><td class='strong'><span class='dot' style='background:{PALETA_MARCAS.get(m_, '#94A3B8')}'></span>{m_}</td>"
                rt, mt = 0.0, 0.0
                for c_ in CANALES:
                    r_ = float(PE_T.loc[(PE_T["marca"] == m_) & (PE_T["canal"] == c_), "total_pedido"].sum())
                    mm_ = meta_cm([c_], [m_])
                    tots[c_][0] += r_
                    tots[c_][1] += mm_
                    rt, mt = rt + r_, mt + mm_
                    fila += f"<td class='sep'>{fmt_compact(r_)}</td><td>{fmt_compact(mm_) if mm_ else '—'}</td><td>{_pill_av(r_, mm_)}</td>"
                pr_ = rt / trans_h * dur_h if en_curso and trans_h >= 1 else (rt if ahora > ev_fin else 0)
                cp_ = pr_ / mt * 100 if mt and pr_ else None
                fila += (f"<td class='sep strong'>{fmt_compact(rt)}</td><td>{fmt_compact(mt) if mt else '—'}</td><td>{_pill_av(rt, mt)}</td>"
                         f"<td>{fmt_compact(pr_) if pr_ else '—'}</td>"
                         f"<td style='color:{'#34D399' if cp_ and cp_ >= 100 else '#F87171'};font-weight:700'>{fmt_dec(cp_, 0) + '%' if cp_ else '—'}</td></tr>")
                filas += fila
            rt = sum(v[0] for v in tots.values())
            mt = sum(v[1] for v in tots.values())
            pr_ = rt / trans_h * dur_h if en_curso and trans_h >= 1 else (rt if ahora > ev_fin else 0)
            cp_ = pr_ / mt * 100 if mt and pr_ else None
            filas += ("<tr class='total'><td>Total</td>" +
                      "".join(f"<td class='sep'>{fmt_compact(tots[c_][0])}</td><td>{fmt_compact(tots[c_][1])}</td><td>{_pill_av(*tots[c_])}</td>" for c_ in CANALES) +
                      f"<td class='sep'>{fmt_compact(rt)}</td><td>{fmt_compact(mt)}</td><td>{_pill_av(rt, mt)}</td><td>{fmt_compact(pr_) if pr_ else '—'}</td>"
                      f"<td>{fmt_dec(cp_, 0) + '%' if cp_ else '—'}</td></tr>")
            html("<div class='tbl-wrap'><table class='ftable compact'><thead><tr class='grp-h'><th></th>"
                 f"<th colspan='3' class='sep' style='text-align:center;color:{COLOR_CANAL['Tienda Online']}'>Tienda Online</th>"
                 f"<th colspan='3' class='sep' style='text-align:center;color:{COLOR_CANAL['MercadoLibre']}'>MercadoLibre</th>"
                 "<th colspan='5' class='sep' style='text-align:center;color:#F8FAFC'>Total</th></tr>"
                 "<tr><th>Marca</th><th class='sep'>Real</th><th>Meta</th><th>Avance</th><th class='sep'>Real</th><th>Meta</th><th>Avance</th>"
                 f"<th class='sep'>Real</th><th>Meta</th><th>Avance</th><th>Proyección</th><th>Proy. vs meta</th></tr></thead><tbody>{filas}</tbody></table></div>")
            st.caption("Avance en verde = va igual o mejor que el tiempo transcurrido · amarillo = hasta 20% por debajo · rojo = más atrasado.")

        # ---------- HORA A HORA ----------
        seccion("Ritmo", "Venta hora a hora", f"Barras = cada hora del evento. Línea = acumulado. Punteada = {prev_lbl or 'evento anterior'} a la misma hora desde su inicio (lunes 00:00).")
        met_cy = st.segmented_control("Métrica", ["Facturación", "Pedidos", "Unidades"], default="Facturación", key="cy_met") or "Facturación"
        fmt_cy = fmt_compact if met_cy == "Facturación" else fmt_num
        if len(PE):
            _g = PE.assign(h=PE["fecha"].dt.floor("h")).groupby(["h", "canal"])
            ph = (_g["total_pedido"].sum() if met_cy == "Facturación" else (_g.size() if met_cy == "Pedidos" else _g["unidades"].sum())).unstack(fill_value=0)
        else:
            ph = pd.DataFrame()
        from plotly.subplots import make_subplots as _msp_c
        fig = _msp_c(specs=[[{"secondary_y": True}]])
        for c_ in CANALES:
            if c_ in ph.columns:
                fig.add_bar(x=ph.index, y=ph[c_], name=c_, marker_color=COLOR_CANAL[c_])
        if len(ph):
            fig.add_scatter(x=ph.index, y=ph.sum(axis=1).cumsum(), name="Acumulado", line=dict(color="#F8FAFC", width=3), secondary_y=True)
        hs = prev_all if canal_cy == "General" else (prev_all[prev_all["canal"] == canal_cy] if len(prev_all) else prev_all)
        if len(hs):
            hs_m = hs
            _hp = hs_m.drop_duplicates(["marca", "id_pedido"])
            hph = (_hp.groupby("hora_ev")["total_pedido"].sum() if met_cy == "Facturación" else
                   (_hp.groupby("hora_ev").size() if met_cy == "Pedidos" else
                    pd.to_numeric(hs_m["cantidad"], errors="coerce").groupby(hs_m["hora_ev"]).sum())).reindex(range(int(dur_h) + 1), fill_value=0)
            n_ = int(trans_h) + 1 if en_curso else len(hph)
            xs = [ev_ini + timedelta(hours=i) for i in range(len(hph))]
            fig.add_scatter(x=xs[:max(n_, 1) + 6], y=hph.cumsum().values[:max(n_, 1) + 6], name=f"{prev_lbl} acumulado (misma hora del evento)",
                            line=dict(color="#FBBF24", width=2, dash="dot"), secondary_y=True)
        fig.update_layout(barmode="stack", bargap=0.15, hovermode="x unified", legend_title_text="")
        _u = {"Facturación": "$", "Pedidos": "pedidos", "Unidades": "unidades"}[met_cy]
        fig.update_yaxes(title_text=f"{_u} por hora", secondary_y=False)
        fig.update_yaxes(title_text=f"{_u} acumulado", secondary_y=True, showgrid=False, rangemode="tozero")
        fig.update_yaxes(rangemode="tozero", secondary_y=False)
        fig = estilo(fig, 400)
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), margin=dict(t=60))
        st.plotly_chart(fig, width="stretch")
        if len(hs) and en_curso:
            can_cmp = [c_ for c_ in (CANALES if canal_cy == "General" else [canal_cy]) if c_ in prev_canales]
            pv_ = prev_hasta(can_cmp)
            _pt = PE[PE["canal"].isin(can_cmp)]
            cur_ = (float(_pt["total_pedido"].sum()), float(len(_pt)), float(_pt["unidades"].sum()))
            if pv_ and any(pv_):
                st.markdown(f"<div style='font-size:14px;color:#CBD5E1'>📊 <b>{' + '.join(CORTO.get(c_, c_) for c_ in can_cmp)}</b> vs <b>{prev_lbl}</b> "
                            f"a la misma hora del evento: facturación {_var(cur_[0], pv_[0])} ({fmt_compact(cur_[0])} vs {fmt_compact(pv_[0])}) · "
                            f"pedidos {_var(cur_[1], pv_[1])} ({fmt_num(cur_[1])} vs {fmt_num(pv_[1])}) · "
                            f"unidades {_var(cur_[2], pv_[2])} ({fmt_num(cur_[2])} vs {fmt_num(pv_[2])})</div>", unsafe_allow_html=True)
                if prev_lbl.startswith("Cyber"):
                    st.caption("La facturación está en pesos corrientes (sin ajustar por inflación): para comparar volumen real mirá pedidos y unidades.")

        # ---------- MARCAS ----------
        seccion("Marcas", "¿Cómo va cada marca?", "Facturación del evento por marca y canal, contra un día normal (promedio de los 28 días previos).")
        ref_m = Pref.groupby(Pref["marca"].astype(str))["total_pedido"].sum() / 28 if len(Pref) else pd.Series(dtype=float)
        can_m = [c_ for c_ in (CANALES if canal_cy == "General" else [canal_cy]) if c_ in prev_canales]
        cols_m = st.columns(max(1, len(marcas_sel)))
        for col, m_ in zip(cols_m, marcas_sel):
            d_ = PE[PE["marca"] == m_]
            f_ = float(d_["total_pedido"].sum())
            x_ = f_ / (ref_m.get(m_, 0) * max(trans_h / 24, 1 / 24)) if ref_m.get(m_, 0) and trans_h > 0 else None
            pvm = prev_hasta(can_m, m_) if can_m else None
            hs_txt = (f"<span>vs {prev_lbl.split(' (')[0]}: $ {_var(f_, pvm[0])} · u. {_var(float(d_['unidades'].sum()), pvm[2])}</span>" if pvm and pvm[0] else "")
            col.markdown(kpi_card(m_, fmt_compact(f_), (f"<span class='delta up'>{fmt_dec(x_, 1)}x ritmo normal</span>" if x_ else ""),
                                  split_html(por_canal_vals(d_, "total_pedido")) +
                                  f"<div class='split-legend' style='margin-top:6px'><span>{fmt_num(len(d_))} pedidos</span><span>{fmt_num(d_['unidades'].sum())} u.</span></div>"
                                  + (f"<div class='split-legend' style='margin-top:4px'>{hs_txt}</div>" if hs_txt else ""),
                                  PALETA_MARCAS.get(m_, "#94A3B8"), sm=True), unsafe_allow_html=True)

        # ---------- SHARE POR MARCA ----------
        seccion("Participación", "Share de cada marca en el evento",
                "Qué porcentaje del total aporta cada marca, en facturación y en unidades (según el canal elegido arriba).")
        if PE.empty:
            st.info("Todavía no hay ventas del evento.")
        else:
            sh = PE.groupby("marca").agg(fact=("total_pedido", "sum"), uni=("unidades", "sum"), ped=("id_pedido", "count")).reindex(
                [m_ for m_ in marcas_sel if m_ in set(PE["marca"])]).fillna(0)
            g1, g2 = st.columns(2)
            for col, campo, tit in [(g1, "fact", "Share por facturación"), (g2, "uni", "Share por unidades")]:
                fig = go.Figure(go.Pie(labels=sh.index, values=sh[campo], hole=0.6, sort=False, textinfo="percent+label",
                                       marker=dict(colors=[PALETA_MARCAS.get(m_, "#94A3B8") for m_ in sh.index], line=dict(color="#060A13", width=2)),
                                       hovertemplate="%{label}<br>%{percent} · " + ("$%{value:,.0f}" if campo == "fact" else "%{value:,.0f} u.") + "<extra></extra>"))
                fig.update_layout(title=tit, showlegend=False,
                                  annotations=[dict(text=(fmt_compact(sh[campo].sum()) if campo == "fact" else fmt_num(sh[campo].sum()) + " u."),
                                                    showarrow=False, font=dict(size=18, color="#F8FAFC"))])
                col.plotly_chart(estilo(fig, 340), width="stretch", key=f"cy_share_{campo}")
            tf, tu, tp_ = sh["fact"].sum(), sh["uni"].sum(), sh["ped"].sum()
            canal_m = PE.groupby(["marca", "canal"])["total_pedido"].sum().unstack(fill_value=0)
            filas = ""
            for m_, r_ in sh.sort_values("fact", ascending=False).iterrows():
                sf, su = r_["fact"] / tf * 100 if tf else 0, r_["uni"] / tu * 100 if tu else 0
                dif = sf - su
                ct = " · ".join(f"{CORTO.get(c_, c_)} {fmt_dec(canal_m.loc[m_, c_] / r_['fact'] * 100 if r_['fact'] else 0, 0)}%"
                                for c_ in CANALES if c_ in canal_m.columns and m_ in canal_m.index)
                filas += (f"<tr><td class='strong'><span class='dot' style='background:{PALETA_MARCAS.get(m_, '#94A3B8')}'></span>{m_}</td>"
                          f"<td>{fmt_ars(r_['fact'])}</td><td class='strong'>{fmt_dec(sf)}%</td>"
                          f"<td class='sep'>{fmt_num(r_['uni'])}</td><td class='strong'>{fmt_dec(su)}%</td>"
                          f"<td class='sep'>{fmt_num(r_['ped'])}</td><td>{fmt_dec(r_['ped'] / tp_ * 100 if tp_ else 0)}%</td>"
                          f"<td>{fmt_ars(r_['fact'] / r_['ped'] if r_['ped'] else 0)}</td>"
                          f"<td>{fmt_ars(r_['fact'] / r_['uni'] if r_['uni'] else 0)}</td>"
                          f"<td style='color:{'#34D399' if dif > 0 else '#F87171'}'>{'+' if dif > 0 else ''}{fmt_dec(dif)} pp</td>"
                          f"<td style='text-align:left'>{ct}</td></tr>")
            html("<div class='tbl-wrap'><table class='ftable compact'><thead><tr><th>Marca</th><th>Facturación</th><th>Share $</th>"
                 "<th class='sep'>Unidades</th><th>Share u.</th><th class='sep'>Pedidos</th><th>Share ped.</th><th>Ticket</th><th>Precio prom. u.</th>"
                 f"<th>Share $ − u.</th><th style='text-align:left'>Tienda / MeLi</th></tr></thead><tbody>{filas}</tbody></table></div>")
            st.caption("'Share $ − u.' positivo = la marca pesa más en plata que en unidades (vende productos más caros que el promedio).")

        # ---------- PRODUCTOS + STOCK ----------
        seccion("Productos", "Lo más vendido y riesgo de quiebre",
                "Ranking del evento por modelo/color. 'Se agota en' = stock del depósito dividido el ritmo de venta del evento.")
        if Ev.empty:
            st.info("Todavía no hay ventas del evento.")
        else:
            cat_cy = load_aux("catalogo_stock.csv")
            stk_mc = (cat_cy.assign(stock=pd.to_numeric(cat_cy["stock"], errors="coerce").fillna(0).clip(lower=0))
                      .groupby(["marca", "modelo_color"])["stock"].sum()) if not cat_cy.empty else pd.Series(dtype=float)
            tp = Ev.groupby([Ev["marca"].astype(str), "modelo_color"]).agg(
                producto=("producto_base", "first"), unidades=("cantidad", "sum"), fact=("subtotal_producto", "sum"),
                tienda=("canal", lambda s_: int((s_ == "Tienda Online").sum())), img=("img_url", "first")).reset_index()
            tp = tp[tp["modelo_color"] != "S/D"].sort_values("unidades", ascending=False)
            tp["stock"] = [stk_mc.get((m_, mc_), np.nan) for m_, mc_ in zip(tp["marca"], tp["modelo_color"])]
            vel_h = tp["unidades"] / max(trans_h, 1)
            tp["agota_h"] = np.where(vel_h > 0, tp["stock"] / vel_h, np.inf)
            ver_tp = st.segmented_control("Ver", ["Top 20 en unidades", "Top 20 en facturación", "En riesgo de quiebre"], default="Top 20 en unidades", key="cy_tp") or "Top 20 en unidades"
            if ver_tp == "Top 20 en facturación":
                tv = tp.sort_values("fact", ascending=False).head(20)
            elif ver_tp == "En riesgo de quiebre":
                tv = tp[(tp["agota_h"] < 24) | (tp["stock"] <= 0)].sort_values("unidades", ascending=False).head(30)
            else:
                tv = tp.head(20)
            filas = ""
            for i_, (_, r_) in enumerate(tv.iterrows(), 1):
                img = r_["img"] if str(r_["img"]).startswith("http") else img_azure(r_["marca"], r_["modelo_color"])
                stk = r_["stock"]
                if pd.isna(stk):
                    st_txt, cls = "—", ""
                elif stk <= 0:
                    st_txt, cls = "Agotado", "bad"
                elif r_["agota_h"] < 6:
                    st_txt, cls = f"{r_['agota_h']:.0f} h", "bad"
                elif r_["agota_h"] < 24:
                    st_txt, cls = f"{r_['agota_h']:.0f} h", "warn"
                else:
                    st_txt, cls = ("+1 día" if np.isfinite(r_["agota_h"]) else "—"), "ok"
                filas += (f"<tr><td class='strong'>{i_}</td><td style='text-align:left;max-width:360px;overflow:hidden;text-overflow:ellipsis'>"
                          f"<img src='{img}' style='width:34px;height:34px;object-fit:contain;background:#fff;border-radius:6px;vertical-align:middle;margin-right:8px'>"
                          f"{str(r_['producto'])[:55]}</td><td>{r_['marca']}</td><td>{r_['modelo_color']}</td><td class='strong'>{fmt_num(r_['unidades'])}</td>"
                          f"<td>{fmt_ars(r_['fact'])}</td><td>{fmt_num(stk) if pd.notna(stk) else '—'}</td><td><span class='pill {cls}'>{st_txt}</span></td></tr>")
            html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>#</th><th style='text-align:left'>Producto</th><th>Marca</th><th>Modelo/color</th>"
                 f"<th>Unidades</th><th>Facturación</th><th>Stock depósito</th><th>Se agota en</th></tr></thead><tbody>{filas}</tbody></table></div>")
            st.caption("El stock de depósito se actualiza cada 2 horas (inventario de Shopify).")

            # ---------- CÓDIGOS + ÚLTIMOS PEDIDOS ----------
            g1, g2 = st.columns([1, 1.4])
            with g1:
                dsc = Ev[(Ev["canal"].astype(str) == "Tienda Online")].drop_duplicates(["marca", "id_pedido"])
                dsc = dsc[dsc["descuento"].astype(str).str.upper() != "SIN DESCUENTO"]
                if len(dsc):
                    dd = dsc.groupby(dsc["descuento"].astype(str))["total_pedido"].agg(["count", "sum"]).sort_values("sum", ascending=False).head(10).reset_index()
                    filas = "".join(f"<tr><td style='text-align:left'>{r_['descuento']}</td><td>{fmt_num(r_['count'])}</td><td>{fmt_ars(r_['sum'])}</td></tr>" for _, r_ in dd.iterrows())
                    st.markdown("**Códigos de descuento más usados (Tienda)**")
                    html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th style='text-align:left'>Código</th><th>Pedidos</th><th>Facturación</th></tr></thead>"
                         f"<tbody>{filas}</tbody></table></div>")
                else:
                    st.caption("Sin códigos de descuento usados todavía.")
            with g2:
                ul = Ev.sort_values("fecha", ascending=False).drop_duplicates(["canal", "marca", "id_pedido"]).head(15)
                filas = "".join(f"<tr><td>{r_['fecha']:%H:%M}</td><td><span class='dot' style='background:{COLOR_CANAL.get(str(r_['canal']), '#94A3B8')}'></span>{CORTO.get(str(r_['canal']), r_['canal'])}</td>"
                                f"<td>{r_['marca']}</td><td style='text-align:left;max-width:260px;overflow:hidden;text-overflow:ellipsis'>{str(r_['producto_base'])[:40]}</td>"
                                f"<td class='strong'>{fmt_ars(r_['total_pedido'])}</td></tr>" for _, r_ in ul.iterrows())
                st.markdown("**Últimos pedidos**")
                html("<div class='tbl-wrap'><table class='ftable'><thead><tr><th>Hora</th><th>Canal</th><th>Marca</th><th style='text-align:left'>Producto</th><th>Total</th></tr></thead>"
                     f"<tbody>{filas}</tbody></table></div>")


