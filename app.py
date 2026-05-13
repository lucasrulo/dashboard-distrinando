import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import json
import requests
import time
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Analítica Distrinando | Centro de Comando",
    layout="wide",
    initial_sidebar_state="expanded"
)

# BLOQUEO DE TEMA OSCURO CORPORATIVO POR DEFECTO PARA LA NUBE
st.markdown("""
    <script>
        const doc = window.parent.document;
        const body = doc.querySelector('body');
        if (body) { body.setAttribute('data-theme', 'dark'); }
    </script>
""", unsafe_allow_html=True)

st_autorefresh(interval=300000, limit=None, key="auto_refresh")

# 2. CSS CORPORATIVO REINGENIERIZADO
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; }
    .metric-container { background-color: #1E293B; border: 1px solid #334155; padding: 24px; border-radius: 12px; text-align: center; margin-bottom: 15px; transition: all 0.2s ease; }
    .metric-title { font-size: 12px; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 1px; margin-bottom: 10px; }
    .metric-value { font-size: 30px; font-weight: 800; color: #38BDF8; letter-spacing: -1px; }
    .brand-card { background-color: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 18px; margin-bottom: 15px; transition: all 0.3s ease; }
    .brand-card:hover { border-color: #38BDF8; }
    .brand-header { font-size: 17px; font-weight: 800; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 12px; color: #F8FAFC; }
    .brand-stat { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px; color: #94A3B8; }
    .brand-stat-val { font-weight: 700; color: #E2E8F0; }
    .product-box { background: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 15px; text-align: center; transition: 0.3s ease; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .product-box:hover { border-color: #38BDF8; } 
    .product-img { width: 100%; height: 160px; object-fit: contain; border-radius: 8px; margin-bottom: 12px; background: white; padding: 5px; }
    .product-name { font-size: 12px; font-weight: 600; color: #E2E8F0; height: 40px; overflow: hidden; line-height: 1.3; margin-bottom: 12px; }
    .product-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0; border-top: 1px solid #334155; padding-top: 10px;}
    .product-stat-label { font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; }
    .product-stat-val { font-size: 14px; font-weight: 800; color: #38BDF8; }
    .btn-link { display: block; background: #2563EB; color: #FFFFFF !important; text-decoration: none; padding: 10px; border-radius: 8px; font-size: 11px; font-weight: 700; margin-top: 10px; text-transform: uppercase; transition: background 0.2s; }
    .btn-link:hover { background: #3B82F6; }
    .discount-container { background: #0F172A; border: 1px dashed #334155; border-radius: 12px; padding: 20px; margin-top: 20px; }
    .module-box { background: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-top: 15px; }
    span[data-baseweb="tag"] { background-color: #1E3A8A !important; color: #F8FAFC !important; border: 1px solid #3B82F6 !important; border-radius: 4px !important; }
    
    /* TABLAS NATIVAS DE ALTO CONTRASTE */
    .forecast-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .forecast-table th { background-color: #0F172A; color: #94A3B8; padding: 12px 10px; font-weight: 800; text-transform: uppercase; border-bottom: 2px solid #334155; text-align: right; }
    .forecast-table th:first-child { text-align: left; }
    .forecast-table td { padding: 12px 10px; border-bottom: 1px solid #334155; color: #F8FAFC; text-align: right; }
    .forecast-table td:first-child { text-align: left; font-weight: 800; color: #FFFFFF; background-color: rgba(15, 23, 42, 0.3); }
    .forecast-table tr:hover td { background-color: #334155; color: #FFFFFF; }
    
    @media (max-width: 768px) {
        .block-container { padding-left: 0.8rem !important; padding-right: 0.8rem !important; }
        .metric-container { padding: 12px !important; margin-bottom: 8px !important; }
        .metric-title { font-size: 10px !important; margin-bottom: 4px !important; }
        .metric-value { font-size: 22px !important; }
        .brand-card { padding: 12px !important; margin-bottom: 8px !important; }
        .brand-header { font-size: 15px !important; margin-bottom: 8px !important; }
        .brand-stat { font-size: 11px !important; margin-bottom: 4px !important; }
        .product-box { padding: 10px !important; margin-bottom: 8px !important; }
        .product-img { height: 110px !important; margin-bottom: 8px !important; }
        .product-name { font-size: 11px !important; height: 32px !important; margin-bottom: 8px !important; }
        .product-stat-val { font-size: 12px !important; }
        .btn-link { padding: 8px !important; font-size: 10px !important; margin-top: 6px !important; }
        .discount-container, .module-box { padding: 12px !important; }
        div[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONSTANTES Y MAPEOS
DIAS_MAPA = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
ESTADO_MAPA = {'fulfilled': 'Enviado', 'null': 'Pendiente', 'pending': 'En Preparación', 'restocked': 'Devuelto', 'unfulfilled': 'No Enviado'}
PALETA_MARCAS = {'Reebok': '#38BDF8', 'Columbia': '#818CF8', 'Crocs': '#34D399', 'Kappa': '#F472B6', 'Piccadilly': '#FBBF24'}

PROVINCIAS_MAPA = {
    'caba': 'CABA', 'ciudad autónoma de buenos aires': 'CABA', 'capital federal': 'CABA', 'distrito federal': 'CABA',
    'buenos aires': 'Buenos Aires', 'pba': 'Buenos Aires', 'provincia de buenos aires': 'Buenos Aires', 'bs as': 'Buenos Aires',
    'catamarca': 'Catamarca', 'chaco': 'Chaco', 'chubut': 'Chubut', 'córdoba': 'Córdoba', 'cordoba': 'Córdoba',
    'corrientes': 'Corrientes', 'entre ríos': 'Entre Ríos', 'entre rios': 'Entre Ríos', 'formosa': 'Formosa',
    'jujuy': 'Jujuy', 'la pampa': 'La Pampa', 'la rioja': 'La Rioja', 'mendoza': 'Mendoza', 'misiones': 'Misiones',
    'neuquén': 'Neuquén', 'neuquen': 'Neuquén', 'río negro': 'Río Negro', 'rio negro': 'Río Negro',
    'salta': 'Salta', 'san juan': 'San Juan', 'san luis': 'San Luis', 'santa cruz': 'Santa Cruz',
    'santa fe': 'Santa Fe', 'santiago del estero': 'Santiago del Estero', 
    'tierra del fuego': 'Tierra del Fuego', 'tdf': 'Tierra del Fuego', 'tucumán': 'Tucumán', 'tucuman': 'Tucumán'
}

ZONA_AR = timezone(timedelta(hours=-3))

def obtener_hora_argentina():
    return datetime.now(ZONA_AR)

# ==============================================================================
# --- DESPLIEGUE DEL DASHBOARD PRINCIPAL
# ==============================================================================

@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists("ventas_hot_sale.csv"): return pd.DataFrame()
    df = pd.read_csv("ventas_hot_sale.csv")
    
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    
    if 'total_orden' in df.columns and 'total_pedido' not in df.columns: df.rename(columns={'total_orden': 'total_pedido'}, inplace=True)
    if 'total_pedido' not in df.columns: df['total_pedido'] = 0
    if 'subtotal_producto' in df.columns: df['subtotal_producto'] = pd.to_numeric(df['subtotal_producto'], errors='coerce').fillna(0)
    else: df['subtotal_producto'] = 0
    if df['subtotal_producto'].sum() == 0: df['subtotal_producto'] = df['total_pedido'] / df.groupby('id_pedido')['id_pedido'].transform('count')
    if 'medio_pago' not in df.columns: df['medio_pago'] = 'No Registrado'
    if 'cuotas' not in df.columns: df['cuotas'] = '1 Cuota'
    if 'es_reverso' not in df.columns: df['es_reverso'] = 0
    if 'descuento' not in df.columns: df['descuento'] = 'SIN DESCUENTO'
    
    if 'producto_base' not in df.columns: df['producto_base'] = df['producto'].apply(lambda x: str(x).split(' / ')[0])
    if 'modelo_color' not in df.columns: df['modelo_color'] = df['sku'].apply(lambda x: str(x).rsplit('-', 1)[0] if '-' in str(x) else x)
    
    if 'provincia' not in df.columns: df['provincia'] = 'Buenos Aires'
    if 'fecha_despacho' not in df.columns: 
        df['fecha_despacho'] = df['fecha'] + pd.to_timedelta(np.random.randint(1, 4, size=len(df)), unit='D')
    else:
        df['fecha_despacho'] = pd.to_datetime(df['fecha_despacho'], errors='coerce')
        
    return df

def load_objetivos():
    archivo = "objetivos_hot_sale.json"
    objetivos_por_defecto = {
        "Reebok": {"unidades": 5000, "facturacion": 250000000},
        "Columbia": {"unidades": 3000, "facturacion": 300000000},
        "Crocs": {"unidades": 10000, "facturacion": 400000000},
        "Kappa": {"unidades": 4000, "facturacion": 150000000},
        "Piccadilly": {"unidades": 2000, "facturacion": 100000000}
    }
    if os.path.exists(archivo):
        try:
            with open(archivo, "r") as f:
                return json.load(f)
        except: pass
    return objetivos_por_defecto

def guardar_objetivos(datos):
    with open("objetivos_hot_sale.json", "w") as f:
        json.dump(datos, f, indent=4)

def configurar_grafico(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94A3B8"), margin=dict(l=10, r=10, t=40, b=10))
    return fig

def crear_velocimetro(valor_actual, objetivo, titulo_base, es_moneda=False):
    prefijo = "$" if es_moneda else ""
    sufijo = "" if es_moneda else " un."
    porcentaje = (valor_actual / objetivo * 100) if objetivo > 0 else 0
    titulo_completo = f"<b>{titulo_base}</b><br><span style='font-size:16px; color:#34D399;'>Cumplimiento: {porcentaje:.1f}%</span>"
    formato_num = f"{prefijo}{valor_actual:,.0f}{sufijo}"
    
    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=valor_actual,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': titulo_completo, 'font': {"size": 14, "color": "#F8FAFC"}},
        gauge={
            'axis': {'range': [0, max(objetivo * 1.2, valor_actual * 1.1, 10)], 'tickwidth': 1, 'tickcolor': "#94A3B8"},
            'bar': {'color': "#38BDF8", 'thickness': 0.8},
            'bgcolor': "#1E293B", 
            'steps': [
                {'range': [0, objetivo * 0.5], 'color': 'rgba(248, 113, 113, 0.25)'},
                {'range': [objetivo * 0.5, objetivo * 0.9], 'color': 'rgba(251, 191, 36, 0.25)'},
                {'range': [objetivo * 0.9, max(objetivo * 1.2, valor_actual * 1.1)], 'color': 'rgba(52, 211, 153, 0.25)'}
            ],
            'threshold': {'line': {'color': "#FFFFFF", 'width': 5}, 'thickness': 0.85, 'value': objetivo}
        }
    ))
    fig.add_annotation(x=0.5, y=0.15, text=f"<span style='font-size:24px; font-weight:bold; color:#38BDF8;'>{formato_num}</span>", showarrow=False)
    fig.update_layout(height=240, margin=dict(l=15, r=15, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

try:
    df_raw = load_data()
    objetivos_actuales = load_objetivos()
    
    if df_raw.empty: st.warning("⚠️ No se encontró la base de datos.")
    else:
        ahora_ar = obtener_hora_argentina()
        hoy_dt = ahora_ar.date()

        # --- BARRA LATERAL ---
        try: st.sidebar.image("image_2ab136.jpg", use_container_width=True)
        except: st.sidebar.markdown("<h2 style='text-align: center; color: #38BDF8;'>DISTRINANDO</h2>", unsafe_allow_html=True)
            
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⚙️ Filtros Globales")
        marcas_disponibles = sorted(df_raw['marca'].unique())
        marcas_sel = st.sidebar.multiselect("Marcas a Visualizar", marcas_disponibles, default=marcas_disponibles)
        
        f_min, f_max = df_raw['fecha'].min().date(), df_raw['fecha'].max().date()
        rango_fecha = st.sidebar.date_input("Rango de Fechas", [f_min, f_max])

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎯 Metas Comerciales")
        st.sidebar.caption("Edite los valores en la tabla para ajustar las agujas temporalmente.")
        
        marcas_base = ["Reebok", "Columbia", "Crocs", "Kappa", "Piccadilly"]
        df_edit_obj = pd.DataFrame([
            {"Marca": m, "Unidades": objetivos_actuales.get(m, {}).get("unidades", 0), "Facturación ($)": objetivos_actuales.get(m, {}).get("facturacion", 0)}
            for m in marcas_base
        ])
        
        df_guardado = st.sidebar.data_editor(
            df_edit_obj,
            column_config={
                "Marca": st.column_config.TextColumn("Marca", disabled=True),
                "Unidades": st.column_config.NumberColumn("Unidades", min_value=0, step=1, format="%d"),
                "Facturación ($)": st.column_config.NumberColumn("Facturación ($)", min_value=0, step=1000, format="$%d")
            }, hide_index=True, use_container_width=True, key="editor_metas"
        )
        
        if st.sidebar.button("💾 Aplicar Metas", type="primary", use_container_width=True):
            nuevo_json = {row["Marca"]: {"unidades": int(row["Unidades"]), "facturacion": int(row["Facturación ($)"])} for idx, row in df_guardado.iterrows()}
            guardar_objetivos(nuevo_json)
            st.sidebar.success("¡Guardado!")
            st.rerun()

        df_f = df_raw[df_raw['marca'].isin(marcas_sel)].copy()
        if len(rango_fecha) == 2: df_f = df_f[(df_f['fecha'].dt.date >= rango_fecha[0]) & (df_f['fecha'].dt.date <= rango_fecha[1])]

        # ======================================================================
        # --- TÍTULO PRINCIPAL Y BOTÓN TRIGGER ALINEADOS ARRIBA A LA DERECHA
        # ======================================================================
        col_titu, col_bot = st.columns([4.5, 1])
        
        with col_titu:
            st.title("📊 Panel de datos")
            st.caption(f"Última actualización: {ahora_ar.strftime('%d/%m/%Y %H:%M')} hs (ARG) | Filtros Activos: {len(marcas_sel)} Marcas")
            
        with col_bot:
            st.write("") # Espaciador vertical
            contenedor_contador = st.empty()
            
            if st.button("🔄 Actualizar Datos Ahora", type="primary", use_container_width=True):
                owner = "lucasrulo"
                repo = "dashboard-distrinando"
                workflow_id = "actualizador.yml"
                
                token = st.secrets["GH_TOKEN"]
                url_github = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
                headers_github = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                try:
                    res = requests.post(url_github, headers=headers_github, json={"ref": "main"})
                    if res.status_code == 204:
                        st.cache_data.clear()
                        for seg in range(55, -1, -1):
                            contenedor_contador.info(f"⏳ Extrayendo... Auto-recarga en **{seg}s**")
                            time.sleep(1)
                            
                        contenedor_contador.success("🔄 ¡Listo! Recargando...")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Error al conectar con GitHub (Código {res.status_code})")
                except Exception as e:
                    st.error(f"Excepción técnica: {e}")

        # --- SECCIÓN 1: HOY (UNIFICADO A VENTA NETA) ---
        st.subheader(f"⭐ Actividad de Hoy ({hoy_dt.strftime('%d/%m/%Y')})")
        df_hoy = df_f[df_f['fecha'].dt.date == hoy_dt]
        if df_hoy.empty: st.info("Sin registros para la fecha actual con los filtros seleccionados.")
        else:
            h1, h2, h3, h4, h5 = st.columns(5)
            # Agrupación segura combinando marca y orden para no mezclar IDs idénticos
            p_hoy = df_hoy.groupby(['marca', 'id_pedido']).first()
            fact_hoy = p_hoy['total_pedido'].sum()
            h1.metric("Facturación", f"${fact_hoy:,.0f}")
            h2.metric("Órdenes", f"{len(p_hoy):,}")
            h3.metric("Artículos", f"{df_hoy['cantidad'].sum():,}")
            h4.metric("Ticket Prom.", f"${(fact_hoy/len(p_hoy)):,.0f}")
            df_hoy['h'] = df_hoy['fecha'].dt.hour
            h_pico = df_hoy.groupby('h')['id_pedido'].nunique().idxmax() if not df_hoy.groupby('h')['id_pedido'].nunique().empty else 0
            h5.metric("Hora Pico", f"{h_pico}:00 hs")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECCIÓN 2: KPIs (UNIFICADO A VENTA NETA) ---
        p_global = df_f.groupby(['marca', 'id_pedido']).first()
        fact_g = p_global['total_pedido'].sum()
        pedi_g = len(p_global)
        unid_g = df_f['cantidad'].sum()
        tkt_g = fact_g / pedi_g if pedi_g > 0 else 0
        dev_g = (p_global['es_reverso'].sum() / pedi_g * 100) if pedi_g > 0 else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        def render_kpi(col, titulo, valor, color_borde):
            col.markdown(f"""<div class="metric-container" style="border-top: 4px solid {color_borde};"><div class="metric-title">{titulo}</div><div class="metric-value">{valor}</div></div>""", unsafe_allow_html=True)
        render_kpi(k1, "Facturación Total", f"${fact_g:,.0f}", "#38BDF8")
        render_kpi(k2, "Total Órdenes", f"{pedi_g:,}", "#818CF8")
        render_kpi(k3, "Total Unidades", f"{unid_g:,}", "#34D399")
        render_kpi(k4, "Ticket Promedio", f"${tkt_g:,.0f}", "#FBBF24")
        render_kpi(k5, "Tasa Devolución", f"{dev_g:.2f}%", "#F87171")

        # --- SECCIÓN 3: MARCAS (UNIFICADO A VENTA NETA COBRADA) ---
        st.write("##")
        st.subheader("🏢 Rendimiento por Unidad de Negocio")
        m_cols = st.columns(len(marcas_sel)) if marcas_sel else []
        for i, m_nombre in enumerate(marcas_sel):
            df_m = df_f[df_f['marca'] == m_nombre]
            if not df_m.empty:
                # Planchamos a facturación neta de caja por orden única
                p_m = df_m.groupby('id_pedido').first()
                f_m = p_m['total_pedido'].sum()
                c_m = len(p_m)
                u_m = df_m['cantidad'].sum()
                aov = (f_m / c_m if c_m > 0 else 0)
                upt = (u_m / c_m if c_m > 0 else 0)
                asp = (f_m / u_m if u_m > 0 else 0)
                accent = PALETA_MARCAS.get(m_nombre, "#94A3B8")
                m_cols[i].markdown(f"""
                    <div class="brand-card" style="border-top: 4px solid {accent};">
                        <div class="brand-header" style="color: {accent};">{m_nombre}</div>
                        <div class="brand-stat"><span>Venta:</span><span class="brand-stat-val">${f_m:,.0f}</span></div>
                        <div class="brand-stat"><span>Órdenes:</span><span class="brand-stat-val">{c_m:,}</span></div>
                        <div class="brand-stat"><span>Unidades:</span><span class="brand-stat-val">{u_m:,}</span></div>
                        <div class="brand-stat" title="Average Order Value"><span>AOV:</span><span class="brand-stat-val">${aov:,.0f}</span></div>
                        <div class="brand-stat" title="Units Per Transaction"><span>UPT:</span><span class="brand-stat-val">{upt:,.2f}</span></div>
                        <div class="brand-stat" title="Average Selling Price"><span>ASP:</span><span class="brand-stat-val">${asp:,.0f}</span></div>
                    </div>""", unsafe_allow_html=True)

        # --- SECCIÓN 4: MEDIDORES ---
        st.divider()
        st.subheader("🚀 Cumplimiento de Metas (Real vs. Objetivo)")
        st.caption("La línea blanca marca la meta comercial. Los colores indican el avance: Rojo (<50%), Amarillo (50-90%), Verde (>90%).")
        
        opciones_vel = ["Global (Acumulado)"] + marcas_disponibles
        vel_sel = st.selectbox("Seleccione el alcance del medidor:", opciones_vel, key="vel_sel")
        
        v1, v2 = st.columns(2)
        if vel_sel == "Global (Acumulado)":
            obj_fc_acum = sum([objetivos_actuales.get(m, {}).get("facturacion", 0) for m in marcas_sel])
            obj_un_acum = sum([objetivos_actuales.get(m, {}).get("unidades", 0) for m in marcas_sel])
            fig_fc = crear_velocimetro(fact_g, obj_fc_acum, f"Facturación Global ({len(marcas_sel)} marcas)", es_moneda=True)
            fig_un = crear_velocimetro(unid_g, obj_un_acum, f"Unidades Globales ({len(marcas_sel)} marcas)")
        else:
            df_v = df_f[df_f['marca'] == vel_sel]
            p_v = df_v.groupby('id_pedido').first()
            fc_real = p_v['total_pedido'].sum() if not p_v.empty else 0
            un_real = df_v['cantidad'].sum() if not df_v.empty else 0
            obj_fc = objetivos_actuales.get(vel_sel, {}).get("facturacion", 0)
            obj_un = objetivos_actuales.get(vel_sel, {}).get("unidades", 0)
            fig_fc = crear_velocimetro(fc_real, obj_fc, f"Facturación: {vel_sel}", es_moneda=True)
            fig_un = crear_velocimetro(un_real, obj_un, f"Unidades: {vel_sel}")
            
        v1.plotly_chart(fig_fc, use_container_width=True)
        v2.plotly_chart(fig_un, use_container_width=True)

        # ======================================================================
        # --- SECCIÓN: FORECAST Y ANÁLISIS DE BRECHA (UNIFICADO A VENTA NETA) ---
        # ======================================================================
        st.divider()
        st.subheader("🎯 Forecast Semanal y Análisis de Brecha (Gap Analysis)")
        st.caption("Proyección calculada estrictamente para la semana del **11/05/2026 al 17/05/2026**. Se asume un ritmo de venta lineal (Run Rate) en base a los días transcurridos.")
        
        f_start = datetime(2026, 5, 11, 0, 0, 0, tzinfo=ZONA_AR)
        f_end = datetime(2026, 5, 17, 23, 59, 59, tzinfo=ZONA_AR)
        
        if ahora_ar < f_start: dias_transcurridos = 0.001
        elif ahora_ar > f_end: dias_transcurridos = 7.0
        else: dias_transcurridos = (ahora_ar - f_start).total_seconds() / 86400.0
            
        dias_restantes = max(0.0, 7.0 - dias_transcurridos)
        df_semana = df_raw[(df_raw['fecha'] >= f_start) & (df_raw['fecha'] <= f_end)].copy()
        
        filas_forecast = []
        for m_fore in marcas_sel:
            df_sf = df_semana[df_semana['marca'] == m_fore]
            p_sf = df_sf.groupby('id_pedido').first()
            # Alineamos la venta acumulada de la meta estrictamente al dinero neto cobrado
            venta_acumulada = p_sf['total_pedido'].sum() if not p_sf.empty else 0
            unidades_acumuladas = df_sf['cantidad'].sum()
            
            obj_dinero = objetivos_actuales.get(m_fore, {}).get("facturacion", 0)
            forecast_dinero = (venta_acumulada / dias_transcurridos) * 7.0 if dias_transcurridos > 0 else 0.0
            gap_dinero = obj_dinero - venta_acumulada
            
            if gap_dinero <= 0:
                run_rate_req = 0.0; unidades_req_dia = 0; estado_gap = "✅ Meta Cumplida"
            else:
                if dias_restantes > 0:
                    run_rate_req = gap_dinero / dias_restantes
                    asp_actual = (venta_acumulada / unidades_acumuladas) if unidades_acumuladas > 0 else 0
                    if asp_actual == 0:
                        df_global_m = df_raw[df_raw['marca'] == m_fore]
                        p_glob = df_global_m.groupby('id_pedido').first()
                        v_glob = p_glob['total_pedido'].sum() if not p_glob.empty else 0
                        u_glob = df_global_m['cantidad'].sum()
                        asp_actual = (v_glob / u_glob) if u_glob > 0 else 50000
                        
                    unidades_req_dia = int(np.ceil(run_rate_req / asp_actual))
                    estado_gap = f"⚠️ Faltan ${gap_dinero:,.0f}"
                else:
                    run_rate_req = gap_dinero; unidades_req_dia = 0; estado_gap = "❌ Semana Cerrada"
                    
            filas_forecast.append({
                "Marca": m_fore, "Venta Acum.": f"${venta_acumulada:,.0f}", "Objetivo": f"${obj_dinero:,.0f}",
                "Forecast (Proy.)": f"${forecast_dinero:,.0f}", "Estado Brecha": estado_gap,
                "Venta Necesaria / Día": f"${run_rate_req:,.0f}" if run_rate_req > 0 else "-",
                "Unidades Necesarias / Día": f"{unidades_req_dia:,} un." if unidades_req_dia > 0 else "-"
            })
            
        if filas_forecast:
            html_fore = "<table class='forecast-table'><thead><tr><th>Marca</th><th>Venta Acum. (Semana)</th><th>Objetivo</th><th>Proyección (Forecast)</th><th>Brecha (Gap)</th><th>Run Rate Req. ($/Día)</th><th>Run Rate Req. (Un./Día)</th></tr></thead><tbody>"
            for f in filas_forecast:
                html_fore += f"<tr><td>{f['Marca']}</td><td>{f['Venta Acum.']}</td><td>{f['Objetivo']}</td><td style='color:#38BDF8; font-weight:700;'>{f['Forecast (Proy.)']}</td><td>{f['Estado Brecha']}</td><td style='color:#FBBF24; font-weight:700;'>{f['Venta Necesaria / Día']}</td><td style='color:#F472B6; font-weight:700;'>{f['Unidades Necesarias / Día']}</td></tr>"
            html_fore += "</tbody></table>"
            st.markdown(html_fore, unsafe_allow_html=True)
            
            st.write("")
            cf1, cf2, cf3 = st.columns(3)
            cf1.metric("Días Consumidos", f"{dias_transcurridos:.1f} de 7 días")
            cf2.metric("Días Restantes", f"{dias_restantes:.1f} días")
            # Contexto neto global
            p_sem_glob = df_semana.groupby(['marca', 'id_pedido']).first()
            venta_sem_glob = p_sem_glob['total_pedido'].sum() if not p_sem_glob.empty else 0
            cf3.metric("Ritmo Neto Global", f"${(venta_sem_glob / dias_transcurridos if dias_transcurridos > 0 else 0):,.0f} / día")
        else: st.info("No hay marcas seleccionadas para proyectar.")

        # --- SECCIÓN 5: TOP 10 ---
        st.divider()
        c_title, c_toggle = st.columns([1, 1])
        with c_title: st.subheader("🏆 TOP 10")
        with c_toggle: tipo_agrupacion = st.radio("Nivel de Análisis:", ["👔 Agrupado por Modelo/Color", "🏷️ Desglosado por Talle (SKU)"], horizontal=True, label_visibility="collapsed")
            
        tabs_prod = st.tabs([m.upper() for m in marcas_sel])
        for i, m_tab in enumerate(marcas_sel):
            with tabs_prod[i]:
                df_p = df_f[df_f['marca'] == m_tab]
                if not df_p.empty:
                    col_nom = 'producto_base' if "Modelo/Color" in tipo_agrupacion else 'producto'
                    top_10 = df_p.groupby([col_nom, 'img_url', 'url_web']).agg({'cantidad': 'sum', 'subtotal_producto': 'sum'}).sort_values(by='cantidad', ascending=False).head(10).reset_index()
                    for r_idx in range(0, len(top_10), 5):
                        filas_p = st.columns(5)
                        for c_idx, s_idx in enumerate(range(r_idx, r_idx + 5)):
                            if s_idx < len(top_10):
                                item = top_10.iloc[s_idx]
                                img = item['img_url'] if str(item['img_url']) != 'nan' and item['img_url'] != '' else 'https://via.placeholder.com/150'
                                filas_p[c_idx].markdown(f"""
                                    <div class="product-box"><img src="{img}" class="product-img"><div class="product-name">{item[col_nom]}</div>
                                    <div class="product-info-grid"><div><div class="product-stat-label">Unidades</div><div class="product-stat-val">{int(item['cantidad']):,}</div></div>
                                    <div><div class="product-stat-label">Total FC</div><div class="product-stat-val">${item['subtotal_producto']:,.0f}</div></div></div>
                                    <a href="{item['url_web']}" target="_blank" class="btn-link">Ver en Tienda</a></div>""", unsafe_allow_html=True)

        # --- SECCIÓN 6: PROMOS ---
        st.divider()
        st.markdown('<div class="discount-container">', unsafe_allow_html=True)
        st.subheader("🎟️ Análisis de Promociones")
        st.caption("Filtros exclusivos para medir el impacto de las campañas sin alterar el tablero global.")
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1: desc_marcas_sel = st.multiselect("Marca (Promo)", marcas_disponibles, default=marcas_disponibles, key="desc_marca")
        with col_f2:
            df_desc_base = df_raw[(df_raw['descuento'] != 'SIN DESCUENTO') & (df_raw['descuento'] != '')]
            df_desc_filtrado_marcas = df_desc_base[df_desc_base['marca'].isin(desc_marcas_sel)]
            desc_disponibles = sorted(df_desc_filtrado_marcas['descuento'].astype(str).unique())
            desc_sel = st.multiselect("Código Promocional", desc_disponibles, default=desc_disponibles[:5] if len(desc_disponibles) > 0 else [], key="desc_promo")

        df_promo = df_desc_filtrado_marcas[df_desc_filtrado_marcas['descuento'].isin(desc_sel)]
        if len(rango_fecha) == 2: df_promo = df_promo[(df_promo['fecha'].dt.date >= rango_fecha[0]) & (df_promo['fecha'].dt.date <= rango_fecha[1])]
        if df_promo.empty: st.info("Seleccione códigos válidos para analizar.")
        else:
            col_d1, col_d2 = st.columns([1, 1])
            with col_d1:
                desc_fc = df_promo.groupby(['descuento', 'marca'])['subtotal_producto'].sum().reset_index()
                fig_desc_fc = px.bar(desc_fc, x='subtotal_producto', y='descuento', color='marca', orientation='h', text_auto='.0f', color_discrete_map=PALETA_MARCAS, title="Facturación por Código")
                fig_desc_fc.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
                st.plotly_chart(configurar_grafico(fig_desc_fc), use_container_width=True)
            with col_d2:
                desc_unid = df_promo.groupby(['descuento', 'marca'])['cantidad'].sum().reset_index()
                fig_desc_unid = px.bar(desc_unid, x='cantidad', y='descuento', color='marca', orientation='h', text_auto=True, color_discrete_map=PALETA_MARCAS, title="Unidades por Código")
                fig_desc_unid.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
                st.plotly_chart(configurar_grafico(fig_desc_unid), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # --- SECCIÓN FINANZAS Y LOGÍSTICA ---
        st.divider()
        col_fin, col_log = st.columns([1, 1]) 
        with col_fin:
            st.subheader("💳 Finanzas")
            cf1, cf2 = st.columns(2)
            fin_marca_sel = cf1.multiselect("Marca:", marcas_disponibles, default=marcas_disponibles, key="fin_sel_marca")
            opciones_pasarelas = ["Mercado Pago", "Mobbex", "Reversso", "Otros Gateways"]
            fin_pass_sel = cf2.multiselect("Pasarela:", opciones_pasarelas, default=opciones_pasarelas, key="fin_sel_pass")
            
            marcas_f_activas = fin_marca_sel if fin_marca_sel else marcas_disponibles
            pass_f_activas = fin_pass_sel if fin_pass_sel else opciones_pasarelas
            df_fin = df_f[df_f['marca'].isin(marcas_f_activas)].copy()
                
            def limpiar_gateway(val):
                v = str(val).lower()
                if 'mercado pago' in v or 'mercadopago' in v: return 'Mercado Pago'
                if 'mobbex' in v: return 'Mobbex'
                if 'reversso' in v: return 'Reversso'
                return 'Otros Gateways'
            
            p_finanzas = df_fin.groupby(['marca', 'id_pedido']).first().reset_index()
            p_finanzas['gateway_agrupado'] = p_finanzas['medio_pago'].apply(limpiar_gateway)
            p_finanzas = p_finanzas[p_finanzas['gateway_agrupado'].isin(pass_f_activas)]
            gate_fc = p_finanzas.groupby('gateway_agrupado')['total_pedido'].sum().reset_index()
            
            fig_g = px.pie(gate_fc, values='total_pedido', names='gateway_agrupado', hole=0.55, 
                           color='gateway_agrupado', color_discrete_map={'Mercado Pago': '#009EE3', 'Mobbex': '#818CF8', 'Reversso': '#F472B6', 'Otros Gateways': '#94A3B8'},
                           title="Share de Facturación por Pasarela", height=380)
            fig_g.update_traces(textposition='inside', textinfo='percent+label')
            fig_g.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(configurar_grafico(fig_g), use_container_width=True)

        with col_log:
            st.subheader("📦 Logística")
            log_marca_sel = st.multiselect("Filtrar estado por Marca:", marcas_disponibles, default=marcas_disponibles, key="log_sel_marca")
            marcas_l_activas = log_marca_sel if log_marca_sel else marcas_disponibles
            df_log = df_f[df_f['marca'].isin(marcas_l_activas)].copy()
            df_log['fulfillment_status_es'] = df_log['fulfillment_status'].fillna('null').map(ESTADO_MAPA)
            log_stat = df_log.groupby('fulfillment_status_es')['id_pedido'].nunique().reset_index()
            
            fig_log = px.pie(log_stat, values='id_pedido', names='fulfillment_status_es', hole=0.55, 
                             title="Estados de Envío", color_discrete_sequence=['#818CF8', '#34D399', '#F472B6', '#FBBF24'], height=380)
            fig_log.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(configurar_grafico(fig_log), use_container_width=True)

        # --- SECCIÓN GEOGRAFÍA Y EMBUDO (UNIFICADO A VENTA NETA) ---
        st.divider()
        col_geo, col_fun = st.columns([1.2, 1])
        with col_geo:
            st.subheader("🗺️ Distribución Geográfica (TOP 10 Provincias)")
            geo_marca_sel = st.multiselect("Filtrar provincia por Marca:", marcas_disponibles, default=marcas_disponibles, key="geo_sel")
            marcas_g_activas = geo_marca_sel if geo_marca_sel else marcas_disponibles
            
            df_geo = df_f[df_f['marca'].isin(marcas_g_activas)].copy()
            df_geo['prov_limpia'] = df_geo['provincia'].apply(lambda x: PROVINCIAS_MAPA.get(str(x).lower().strip(), 'Buenos Aires'))
            
            # Eliminamos duplicados de total_pedido por provincia y sumamos unidades limpias
            p_geo = df_geo.groupby(['marca', 'id_pedido']).first().reset_index()
            geo_fc = p_geo.groupby('prov_limpia')['total_pedido'].sum().reset_index()
            geo_un = df_geo.groupby('prov_limpia')['cantidad'].sum().reset_index()
            prov_stat = pd.merge(geo_fc, geo_un, on='prov_limpia')
            
            cg1, cg2 = st.columns(2)
            with cg1:
                top_fc = prov_stat.sort_values(by='total_pedido', ascending=True).tail(10)
                fig_geo_fc = px.bar(top_fc, x='total_pedido', y='prov_limpia', orientation='h', title="TOP 10 por Facturación ($)", text_auto='.0f', color_discrete_sequence=['#38BDF8'])
                fig_geo_fc.update_layout(yaxis_title="", xaxis_title="Facturación ($)", height=350)
                st.plotly_chart(configurar_grafico(fig_geo_fc), use_container_width=True)
            with cg2:
                top_un = prov_stat.sort_values(by='cantidad', ascending=True).tail(10)
                fig_geo_un = px.bar(top_un, x='cantidad', y='prov_limpia', orientation='h', title="TOP 10 por Unidades (un.)", text_auto=True, color_discrete_sequence=['#34D399'])
                fig_geo_un.update_layout(yaxis_title="", xaxis_title="Unidades Vendidas", height=350)
                st.plotly_chart(configurar_grafico(fig_geo_un), use_container_width=True)
            
        with col_fun:
            st.subheader("⏳ Eficiencia de Depósito (SLA)")
            st.caption("Fulfillment Lead Time medido en **Días Hábiles** (Excluye sábados y domingos).")
            fun_marca_sel = st.multiselect("Auditar SLA por Marca:", marcas_disponibles, default=marcas_disponibles, key="fun_sel")
            marcas_fun_activas = fun_marca_sel if fun_marca_sel else marcas_disponibles
            df_fun = df_f[df_f['marca'].isin(marcas_fun_activas)].copy()
            df_env = df_fun[df_fun['fulfillment_status'].fillna('null').map(ESTADO_MAPA) == 'Enviado'].copy()
            df_env = df_env.dropna(subset=['fecha', 'fecha_despacho'])
            
            if df_env.empty: st.info("No hay suficientes datos de despacho válidos registrados para calcular el SLA.")
            else:
                fechas_compra, fechas_desp = df_env['fecha'].dt.date.values.astype('datetime64[D]'), df_env['fecha_despacho'].dt.date.values.astype('datetime64[D]')
                df_env['lead_time_habiles'] = np.busday_count(fechas_compra, fechas_desp)
                df_env['lead_time_habiles'] = df_env['lead_time_habiles'].apply(lambda x: max(0, x))
                
                def categorizar_sla(dias):
                    if dias == 0: return "1. Mismo Día (Same Day)"
                    if dias == 1: return "2. En 24 hs hábiles"
                    if dias == 2: return "3. En 48 hs hábiles"
                    return "4. Más de 48 hs hábiles"
                    
                df_env['tramo_sla'] = df_env['lead_time_habiles'].apply(categorizar_sla)
                fun_stat = df_env.groupby('tramo_sla')['id_pedido'].nunique().reset_index()
                fun_stat = fun_stat.sort_values(by='tramo_sla')
                fig_fun = px.funnel(fun_stat, x='id_pedido', y='tramo_sla', title="Órdenes despachadas según SLA", color_discrete_sequence=['#34D399'])
                fig_fun.update_layout(yaxis_title="Tiempo de Procesamiento", xaxis_title="Órdenes", height=350)
                st.plotly_chart(configurar_grafico(fig_fun), use_container_width=True)

        # --- SECCIÓN TEMPORAL (UNIFICADO A VENTA NETA) ---
        st.divider()
        st.subheader("📅 Análisis Temporal y Eficiencia")
        g1, g2 = st.columns([2, 1])
        with g1:
            df_f['hora'] = df_f['fecha'].dt.hour
            # Evitamos duplicar la facturación de la orden en cada línea por hora
            p_hora = df_f.groupby(['marca', 'id_pedido']).first().reset_index()
            v_h = p_hora.groupby(['hora', 'marca'])['total_pedido'].sum().reset_index()
            fig_l = px.line(v_h, x='hora', y='total_pedido', color='marca', markers=True, line_shape="spline", color_discrete_map=PALETA_MARCAS, title="Facturación por Hora")
            fig_l.update_layout(xaxis_title="Hora del Día", yaxis_title="Facturación ($)", legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(configurar_grafico(fig_l), use_container_width=True)
        with g2:
            st.markdown("#### Resumen Operativo")
            p_res = df_f.groupby(['marca', 'id_pedido']).first().reset_index()
            res_fc = p_res.groupby('marca')['total_pedido'].sum().reset_index()
            res_ord = p_res.groupby('marca')['id_pedido'].nunique().reset_index()
            res_un = df_f.groupby('marca')['cantidad'].sum().reset_index()
            
            resumen_tec = pd.merge(res_ord, res_un, on='marca')
            resumen_tec = pd.merge(resumen_tec, res_fc, on='marca')
            resumen_tec.columns = ['Marca', 'Órdenes', 'Unidades', 'Facturación']
            resumen_tec['Ticket Med.'] = (resumen_tec['Facturación'] / resumen_tec['Órdenes']).round(0).fillna(0)
            st.dataframe(resumen_tec, use_container_width=True, hide_index=True)

except Exception as e: st.error(f"Se ha producido un error técnico: {e}")
