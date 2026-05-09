import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh  # <--- PASO B: Va en la línea 7

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Analítica Distrinando | Centro de Comando",
    layout="wide",
    initial_sidebar_state="expanded"
)
st_autorefresh(interval=300000, limit=None, key="auto_refresh") # <--- PASO C: Va justo en la línea 14

# 2. CSS CORPORATIVO DARK NAVY + OPTIMIZACIÓN MOBILE SILENCIOSA
st.markdown("""
    <style>
    /* Tarjetas de Métricas Globales (Desktop Base) */
    .metric-container {
        background-color: #1E293B; 
        border: 1px solid #334155;
        padding: 24px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 15px;
        transition: all 0.2s ease;
    }
    .metric-title { font-size: 12px; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 1px; margin-bottom: 10px; }
    .metric-value { font-size: 30px; font-weight: 800; color: #38BDF8; letter-spacing: -1px; }
    
    /* Tarjetas de Marcas (Desktop Base) */
    .brand-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    .brand-card:hover { border-color: #38BDF8; }
    .brand-header { font-size: 17px; font-weight: 800; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 12px; color: #F8FAFC; }
    .brand-stat { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px; color: #94A3B8; }
    .brand-stat-val { font-weight: 700; color: #E2E8F0; }

    /* Tarjetas de Productos (Desktop Base) */
    .product-box {
        background: #1E293B; border: 1px solid #334155; border-radius: 12px;
        padding: 15px; text-align: center; transition: 0.3s ease; height: 100%;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .product-box:hover { border-color: #38BDF8; } 
    .product-img { width: 100%; height: 160px; object-fit: contain; border-radius: 8px; margin-bottom: 12px; background: white; padding: 5px; }
    .product-name { font-size: 12px; font-weight: 600; color: #E2E8F0; height: 40px; overflow: hidden; line-height: 1.3; margin-bottom: 12px; }
    .product-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0; border-top: 1px solid #334155; padding-top: 10px;}
    .product-stat-label { font-size: 9px; color: #94A3B8; text-transform: uppercase; font-weight: 700; }
    .product-stat-val { font-size: 14px; font-weight: 800; color: #38BDF8; }
    .btn-link {
        display: block; background: #2563EB; color: #FFFFFF !important; 
        text-decoration: none; padding: 10px; border-radius: 8px;
        font-size: 11px; font-weight: 700; margin-top: 10px; text-transform: uppercase; transition: background 0.2s;
    }
    .btn-link:hover { background: #3B82F6; }
    
    /* Contenedores de Módulos */
    .discount-container { background: #0F172A; border: 1px dashed #334155; border-radius: 12px; padding: 20px; margin-top: 20px; }
    .module-box { background: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-top: 15px; }
    
    /* Ajustes visuales nativos */
    span[data-baseweb="tag"] { background-color: #1E3A8A !important; color: #F8FAFC !important; border: 1px solid #3B82F6 !important; border-radius: 4px !important; }
    
    /* --- CAPA DE OPTIMIZACIÓN EXCLUSIVA PARA MÓVILES --- */
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

# 3. CONSTANTES Y PALETAS
DIAS_MAPA = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
ESTADO_MAPA = {'fulfilled': 'Enviado', 'null': 'Pendiente', 'pending': 'En Preparación', 'restocked': 'Devuelto', 'unfulfilled': 'No Enviado'}
PALETA_MARCAS = {'Reebok': '#38BDF8', 'Columbia': '#818CF8', 'Crocs': '#34D399', 'Kappa': '#F472B6', 'Piccadilly': '#FBBF24'}

# Normalizador robusto de Provincias Argentinas
PROVINCIAS_MAPA = {
    'caba': 'CABA', 'ciudad autónoma de buenos aires': 'CABA', 'capital federal': 'CABA',
    'buenos aires': 'Buenos Aires', 'pba': 'Buenos Aires', 'provincia de buenos aires': 'Buenos Aires',
    'catamarca': 'Catamarca', 'chaco': 'Catamarca', 'chubut': 'Chubut', 'córdoba': 'Córdoba', 'cordoba': 'Córdoba',
    'corrientes': 'Corrientes', 'entre ríos': 'Entre Ríos', 'entre rios': 'Entre Ríos', 'formosa': 'Formosa',
    'jujuy': 'Jujuy', 'la pampa': 'La Pampa', 'la rioja': 'La Rioja', 'mendoza': 'Mendoza', 'misiones': 'Misiones',
    'neuquén': 'Neuquén', 'neuquen': 'Neuquén', 'río negro': 'Río Negro', 'rio negro': 'Río Negro',
    'salta': 'Salta', 'san juan': 'San Juan', 'san luis': 'San Luis', 'santa cruz': 'Santa Cruz',
    'santa fe': 'Santa Fe', 'santiago del estero': 'Santiago del Estero', 
    'tierra del fuego': 'Tierra del Fuego', 'tdf': 'Tierra del Fuego', 'tucumán': 'Tucumán', 'tucuman': 'Tucumán'
}

# 4. CARGA DE DATOS
@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists("ventas_hot_sale.csv"): return pd.DataFrame()
    df = pd.read_csv("ventas_hot_sale.csv")
    df['fecha'] = pd.to_datetime(df['fecha'])
    
    # Parches de seguridad
    if 'total_orden' in df.columns and 'total_pedido' not in df.columns: df.rename(columns={'total_orden': 'total_pedido'}, inplace=True)
    if 'total_pedido' not in df.columns: df['total_pedido'] = 0
    if 'subtotal_producto' in df.columns: df['subtotal_producto'] = pd.to_numeric(df['subtotal_producto'], errors='coerce').fillna(0)
    else: df['subtotal_producto'] = 0
    if df['subtotal_producto'].sum() == 0: df['subtotal_producto'] = df['total_pedido'] / df.groupby('id_pedido')['id_pedido'].transform('count')
    if 'medio_pago' not in df.columns: df['medio_pago'] = 'No Registrado'
    if 'cuotas' not in df.columns: df['cuotas'] = '1 Cuota'
    if 'es_reverso' not in df.columns: df['es_reverso'] = 0
    if 'descuento' not in df.columns: df['descuento'] = 'SIN DESCUENTO'
    
    # Parches si el CSV es viejo
    if 'producto_base' not in df.columns: df['producto_base'] = df['producto'].apply(lambda x: str(x).split(' / ')[0])
    if 'modelo_color' not in df.columns: df['modelo_color'] = df['sku'].apply(lambda x: str(x).rsplit('-', 1)[0] if '-' in str(x) else x)
    
    # Parche logístico: asegurar que exista columna de provincia y fecha de despacho
    if 'provincia' not in df.columns: df['provincia'] = 'Buenos Aires' # Default fallback
    if 'fecha_despacho' not in df.columns: 
        # Si no existe en la API, simulamos despachos para órdenes enviadas como fallback de demostración
        df['fecha_despacho'] = df['fecha'] + pd.to_timedelta(np.random.randint(1, 4, size=len(df)), unit='D')
    else:
        df['fecha_despacho'] = pd.to_datetime(df['fecha_despacho'], errors='coerce')
        
    return df

def configurar_grafico(fig):
    fig.update_layout(
        template="plotly_dark", 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)", 
        font=dict(color="#94A3B8"),
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

try:
    df_raw = load_data()
    
    if df_raw.empty:
        st.warning("⚠️ No se encontró la base de datos. Por favor, ejecute 'python extractor.py'.")
    else:
        hoy_dt = datetime.now().date()

        # --- LOGO Y BARRA LATERAL ---
        try:
            st.sidebar.image("image_2ab136.jpg", use_container_width=True)
        except:
            st.sidebar.markdown("<h2 style='text-align: center; color: #38BDF8;'>DISTRINANDO</h2>", unsafe_allow_html=True)
            
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⚙️ Filtros Globales")
        marcas_disponibles = sorted(df_raw['marca'].unique())
        marcas_sel = st.sidebar.multiselect("Marcas a Visualizar", marcas_disponibles, default=marcas_disponibles)
        
        f_min, f_max = df_raw['fecha'].min().date(), df_raw['fecha'].max().date()
        rango_fecha = st.sidebar.date_input("Rango de Fechas", [f_min, f_max])

        df_f = df_raw[df_raw['marca'].isin(marcas_sel)]
        if len(rango_fecha) == 2:
            df_f = df_f[(df_f['fecha'].dt.date >= rango_fecha[0]) & (df_f['fecha'].dt.date <= rango_fecha[1])]

        # --- TÍTULO PRINCIPAL ---
        st.title("📊 Panel de datos")
        st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Filtros Activos: {len(marcas_sel)} Marcas")
        
        # --- SECCIÓN 1: EL PULSO DE HOY ---
        st.subheader("⭐ Actividad de Hoy")
        df_hoy = df_f[df_f['fecha'].dt.date == hoy_dt]
        
        if df_hoy.empty:
            st.info("Sin registros para la fecha actual con los filtros seleccionados.")
        else:
            h1, h2, h3, h4, h5 = st.columns(5)
            p_hoy = df_hoy.groupby('id_pedido').first()
            fact_hoy = p_hoy['total_pedido'].sum()
            h1.metric("Facturación", f"${fact_hoy:,.0f}")
            h2.metric("Órdenes", f"{len(p_hoy):,}")
            h3.metric("Artículos", f"{df_hoy['cantidad'].sum():,}")
            h4.metric("Ticket Prom.", f"${(fact_hoy/len(p_hoy)):,.0f}")
            df_hoy['h'] = df_hoy['fecha'].dt.hour
            h_pico = df_hoy.groupby('h')['id_pedido'].nunique().idxmax() if not df_hoy.groupby('h')['id_pedido'].nunique().empty else 0
            h5.metric("Hora Pico", f"{h_pico}:00 hs")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECCIÓN 2: KPIs GLOBALES ---
        p_global = df_f.groupby('id_pedido').first()
        fact_g = p_global['total_pedido'].sum()
        pedi_g = len(p_global)
        unid_g = df_f['cantidad'].sum()
        tkt_g = fact_g / pedi_g if pedi_g > 0 else 0
        dev_g = (p_global['es_reverso'].sum() / pedi_g * 100) if pedi_g > 0 else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        def render_kpi(col, titulo, valor, color_borde):
            col.markdown(f"""<div class="metric-container" style="border-top: 4px solid {color_borde};">
                <div class="metric-title">{titulo}</div><div class="metric-value">{valor}</div></div>""", unsafe_allow_html=True)

        render_kpi(k1, "Facturación Total", f"${fact_g:,.0f}", "#38BDF8")
        render_kpi(k2, "Total Órdenes", f"{pedi_g:,}", "#818CF8")
        render_kpi(k3, "Total Unidades", f"{unid_g:,}", "#34D399")
        render_kpi(k4, "Ticket Promedio", f"${tkt_g:,.0f}", "#FBBF24")
        render_kpi(k5, "Tasa Devolución", f"{dev_g:.2f}%", "#F87171")

        # --- SECCIÓN 3: DESGLOSE POR MARCA ---
        st.write("##")
        st.subheader("🏢 Rendimiento por Unidad de Negocio")
        m_cols = st.columns(len(marcas_sel)) if marcas_sel else []
        for i, m_nombre in enumerate(marcas_sel):
            df_m = df_f[df_f['marca'] == m_nombre]
            if not df_m.empty:
                f_m = df_m['subtotal_producto'].sum()
                c_m = df_m['id_pedido'].nunique()
                u_m = df_m['cantidad'].sum()
                
                aov = f_m / c_m if c_m > 0 else 0
                upt = u_m / c_m if c_m > 0 else 0
                asp = f_m / u_m if u_m > 0 else 0
                
                accent = PALETA_MARCAS.get(m_nombre, "#94A3B8")
                m_cols[i].markdown(f"""
                    <div class="brand-card" style="border-top: 4px solid {accent};">
                        <div class="brand-header" style="color: {accent};">{m_nombre}</div>
                        <div class="brand-stat"><span>Venta:</span><span class="brand-stat-val">${f_m:,.0f}</span></div>
                        <div class="brand-stat"><span>Órdenes:</span><span class="brand-stat-val">{c_m:,}</span></div>
                        <div class="brand-stat"><span>Unidades:</span><span class="brand-stat-val">{u_m:,}</span></div>
                        <div class="brand-stat" title="Average Order Value (Ticket Promedio)"><span>AOV:</span><span class="brand-stat-val">${aov:,.0f}</span></div>
                        <div class="brand-stat" title="Units Per Transaction (Unidades por Ticket)"><span>UPT:</span><span class="brand-stat-val">{upt:,.2f}</span></div>
                        <div class="brand-stat" title="Average Selling Price (Precio Promedio)"><span>ASP:</span><span class="brand-stat-val">${asp:,.0f}</span></div>
                    </div>""", unsafe_allow_html=True)

        # --- SECCIÓN 4: RANKING DUAL ---
        st.divider()
        c_title, c_toggle = st.columns([1, 1])
        with c_title:
            st.subheader("🏆 TOP 10")
        with c_toggle:
            tipo_agrupacion = st.radio(
                "Nivel de Análisis:", 
                ["👔 Agrupado por Modelo/Color", "🏷️ Desglosado por Talle (SKU)"], 
                horizontal=True,
                label_visibility="collapsed"
            )
            
        tabs_prod = st.tabs([m.upper() for m in marcas_sel])
        for i, m_tab in enumerate(marcas_sel):
            with tabs_prod[i]:
                df_p = df_f[df_f['marca'] == m_tab]
                if not df_p.empty:
                    if "Modelo/Color" in tipo_agrupacion:
                        col_nom = 'producto_base'
                        top_10 = df_p.groupby([col_nom, 'img_url', 'url_web']).agg({'cantidad': 'sum', 'subtotal_producto': 'sum'}).sort_values(by='cantidad', ascending=False).head(10).reset_index()
                    else:
                        col_nom = 'producto'
                        top_10 = df_p.groupby([col_nom, 'img_url', 'url_web']).agg({'cantidad': 'sum', 'subtotal_producto': 'sum'}).sort_values(by='cantidad', ascending=False).head(10).reset_index()
                    
                    for r_idx in range(0, len(top_10), 5):
                        filas_p = st.columns(5)
                        for c_idx, s_idx in enumerate(range(r_idx, r_idx + 5)):
                            if s_idx < len(top_10):
                                item = top_10.iloc[s_idx]
                                img = item['img_url'] if str(item['img_url']) != 'nan' and item['img_url'] != '' else 'https://via.placeholder.com/150'
                                filas_p[c_idx].markdown(f"""
                                    <div class="product-box">
                                        <img src="{img}" class="product-img">
                                        <div class="product-name">{item[col_nom]}</div>
                                        <div class="product-info-grid">
                                            <div><div class="product-stat-label">Unidades</div><div class="product-stat-val">{int(item['cantidad']):,}</div></div>
                                            <div><div class="product-stat-label">Total FC</div><div class="product-stat-val">${item['subtotal_producto']:,.0f}</div></div>
                                        </div>
                                        <a href="{item['url_web']}" target="_blank" class="btn-link">Ver en Tienda</a>
                                    </div>""", unsafe_allow_html=True)

        # --- SECCIÓN 5: DESCUENTOS EN CASCADA ---
        st.divider()
        st.markdown('<div class="discount-container">', unsafe_allow_html=True)
        st.subheader("🎟️ Análisis de Promociones")
        st.caption("Filtros exclusivos para medir el impacto de las campañas sin alterar el tablero global.")
        
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            desc_marcas_sel = st.multiselect("Marca (Promo)", marcas_disponibles, default=marcas_disponibles, key="desc_marca")
        
        with col_f2:
            df_desc_base = df_raw[(df_raw['descuento'] != 'SIN DESCUENTO') & (df_raw['descuento'] != '')]
            df_desc_filtrado_marcas = df_desc_base[df_desc_base['marca'].isin(desc_marcas_sel)]
            desc_disponibles = sorted(df_desc_filtrado_marcas['descuento'].astype(str).unique())
            default_descs = desc_disponibles[:5] if len(desc_disponibles) > 0 else []
            desc_sel = st.multiselect("Código Promocional", desc_disponibles, default=default_descs, key="desc_promo")

        df_promo = df_desc_filtrado_marcas[df_desc_filtrado_marcas['descuento'].isin(desc_sel)]
        if len(rango_fecha) == 2:
            df_promo = df_promo[(df_promo['fecha'].dt.date >= rango_fecha[0]) & (df_promo['fecha'].dt.date <= rango_fecha[1])]
            
        if df_promo.empty:
            st.info("Seleccione códigos válidos para analizar.")
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

        # --- SECCIÓN FINANZAS Y LOGÍSTICA (ALINEACIÓN VISUAL 100% SIMÉTRICA) ---
        st.divider()
        col_fin, col_log = st.columns([1, 1]) # Mismo ancho relativo para garantizar simetría visual
        
        with col_fin:
            st.subheader("💳 Finanzas")
            
            # 1. Doble filtro en cascada en la misma fila para no romper alturas
            cf1, cf2 = st.columns(2)
            opciones_finanzas = ["Todas las marcas"] + sorted(df_f['marca'].unique())
            fin_marca_sel = cf1.selectbox("Marca:", opciones_finanzas, key="fin_sel_marca")
            
            opciones_pasarelas = ["Todas las pasarelas", "Mercado Pago", "Mobbex", "Reversso", "Otros Gateways"]
            fin_pass_sel = cf2.selectbox("Pasarela:", opciones_pasarelas, key="fin_sel_pass")
            
            # 2. Aislamos la base financiera según los filtros elegidos
            df_fin = df_f.copy()
            if fin_marca_sel != "Todas las marcas":
                df_fin = df_fin[df_fin['marca'] == fin_marca_sel]
                
            def limpiar_gateway(val):
                v = str(val).lower()
                if 'mercado pago' in v or 'mercadopago' in v: return 'Mercado Pago'
                if 'mobbex' in v: return 'Mobbex'
                if 'reversso' in v: return 'Reversso'
                return 'Otros Gateways'
            
            p_finanzas = df_fin.groupby('id_pedido').first().reset_index()
            p_finanzas['gateway_agrupado'] = p_finanzas['medio_pago'].apply(limpiar_gateway)
            
            if fin_pass_sel != "Todas las pasarelas":
                p_finanzas = p_finanzas[p_finanzas['gateway_agrupado'] == fin_pass_sel]
                
            gate_fc = p_finanzas.groupby('gateway_agrupado')['total_pedido'].sum().reset_index()
            
            colores_gateways = {
                'Mercado Pago': '#009EE3',     
                'Mobbex': '#818CF8',           
                'Reversso': '#F472B6',         
                'Otros Gateways': '#94A3B8'    
            }
            
            titulo_fin = "Share de Facturación por Pasarela"
            
            # 3. Forzamos dimensiones idénticas al gráfico de logística
            fig_g = px.pie(
                gate_fc, 
                values='total_pedido', 
                names='gateway_agrupado', 
                hole=0.55, 
                color='gateway_agrupado', 
                color_discrete_map=colores_gateways,
                title=titulo_fin,
                height=380 # Altura fija inyectada
            )
            fig_g.update_traces(textposition='inside', textinfo='percent+label')
            # Leyenda forzada horizontal abajo idéntica a logística
            fig_g.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(configurar_grafico(fig_g), use_container_width=True)

        with col_log:
            st.subheader("📦 Logística")
            
            # Filtro logístico que ocupa el mismo espacio vertical que los de finanzas
            opciones_logistica = ["Todas las marcas"] + sorted(df_f['marca'].unique())
            log_marca_sel = st.selectbox("Filtrar estado por Marca:", opciones_logistica, key="log_sel_marca")
            
            df_log = df_f.copy()
            if log_marca_sel != "Todas las marcas":
                df_log = df_log[df_log['marca'] == log_marca_sel]
                
            df_log['fulfillment_status_es'] = df_log['fulfillment_status'].fillna('null').map(ESTADO_MAPA)
            log_stat = df_log.groupby('fulfillment_status_es')['id_pedido'].nunique().reset_index()
            
            titulo_log = "Estados de Envío"
            
            fig_log = px.pie(
                log_stat, 
                values='id_pedido', 
                names='fulfillment_status_es', 
                title=titulo_log, 
                hole=0.55, 
                color_discrete_sequence=['#818CF8', '#34D399', '#F472B6', '#FBBF24'],
                height=380 # Altura fija inyectada simétrica
            )
            fig_log.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(configurar_grafico(fig_log), use_container_width=True)

        # --- SECCIÓN 6: MAPA GEOGRÁFICO Y EMBUDO DE ENVÍOS (NUEVO) ---
        st.divider()
        col_geo, col_fun = st.columns([1.2, 1])
        
        with col_geo:
            st.subheader("🗺️ Distribución Geográfica")
            
            # Filtro exclusivo para el mapa
            geo_marca_sel = st.selectbox("Filtrar provincia por Marca:", ["Todas las marcas"] + marcas_disponibles, key="geo_sel")
            df_geo = df_f.copy()
            if geo_marca_sel != "Todas las marcas":
                df_geo = df_geo[df_geo['marca'] == geo_marca_sel]
                
            # Normalizamos provincias usando nuestro diccionario robusto
            df_geo['prov_limpia'] = df_geo['provincia'].apply(lambda x: PROVINCIAS_MAPA.get(str(x).lower().strip(), 'Buenos Aires'))
            prov_stat = df_geo.groupby('prov_limpia')['total_pedido'].sum().reset_index()
            prov_stat = prov_stat.sort_values(by='total_pedido', ascending=True).tail(10) # TOP 10 Provincias
            
            fig_geo = px.bar(
                prov_stat, 
                x='total_pedido', 
                y='prov_limpia', 
                orientation='h', 
                title="TOP 10 Provincias por Facturación",
                text_auto='.0f',
                color_discrete_sequence=['#38BDF8']
            )
            fig_geo.update_layout(yaxis_title="", xaxis_title="Facturación ($)", height=350)
            st.plotly_chart(configurar_grafico(fig_geo), use_container_width=True)
            
        with col_fun:
            st.subheader("⏳ Eficiencia de Depósito (SLA)")
            st.caption("Fulfillment Lead Time medido en **Días Hábiles** (Excluye sábados y domingos).")
            
            # Filtro exclusivo para el embudo
            fun_marca_sel = st.selectbox("Auditar SLA por Marca:", ["Todas las marcas"] + marcas_disponibles, key="fun_sel")
            df_fun = df_f.copy()
            if fun_marca_sel != "Todas las marcas":
                df_fun = df_fun[df_fun['marca'] == fun_marca_sel]
                
            # Aislamos solo pedidos enviados que tengan fecha de despacho válida
            df_env = df_fun[df_fun['fulfillment_status'].fillna('null').map(ESTADO_MAPA) == 'Enviado'].copy()
            
            if df_env.empty or 'fecha_despacho' not in df_env.columns:
                st.info("No hay suficientes datos de despacho registrados para calcular el SLA.")
            else:
                # CÁLCULO MATEMÁTICO DE DÍAS HÁBILES (Fulfillment Lead Time)
                # Convertimos a fechas puras (sin horas) para la función de numpy
                fechas_compra = df_env['fecha'].dt.date.values.astype('datetime64[D]')
                fechas_desp = df_env['fecha_despacho'].dt.date.values.astype('datetime64[D]')
                
                # np.busday_count resta automáticamente fines de semana
                df_env['lead_time_habiles'] = np.busday_count(fechas_compra, fechas_desp)
                # Evitamos negativos si hay desfasajes de zona horaria
                df_env['lead_time_habiles'] = df_env['lead_time_habiles'].apply(lambda x: max(0, x))
                
                # Agrupamos en un embudo de tramos de atención
                def categorizar_sla(dias):
                    if dias == 0: return "1. Mismo Día (Same Day)"
                    if dias == 1: return "2. En 24 hs hábiles"
                    if dias == 2: return "3. En 48 hs hábiles"
                    return "4. Más de 48 hs hábiles"
                    
                df_env['tramo_sla'] = df_env['lead_time_habiles'].apply(categorizar_sla)
                fun_stat = df_env.groupby('tramo_sla')['id_pedido'].nunique().reset_index()
                fun_stat = fun_stat.sort_values(by='tramo_sla')
                
                fig_fun = px.funnel(
                    fun_stat, 
                    x='id_pedido', 
                    y='tramo_sla', 
                    title="Órdenes despachadas según SLA",
                    color_discrete_sequence=['#34D399']
                )
                fig_fun.update_layout(yaxis_title="Tiempo de Procesamiento", xaxis_title="Órdenes", height=350)
                st.plotly_chart(configurar_grafico(fig_fun), use_container_width=True)

        # --- SECCIÓN TEMPORAL ---
        st.divider()
        st.subheader("📅 Análisis Temporal y Eficiencia")
        g1, g2 = st.columns([2, 1])
        
        with g1:
            df_f['hora'] = df_f['fecha'].dt.hour
            v_h = df_f.groupby(['hora', 'marca'])['total_pedido'].sum().reset_index()
            fig_l = px.line(v_h, x='hora', y='total_pedido', color='marca', markers=True, line_shape="spline", color_discrete_map=PALETA_MARCAS, title="Facturación por Hora")
            fig_l.update_layout(xaxis_title="Hora del Día", yaxis_title="Facturación ($)", legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(configurar_grafico(fig_l), use_container_width=True)

        with g2:
            st.markdown("#### Resumen Operativo")
            resumen_tec = df_f.groupby('marca').agg({'id_pedido': 'nunique', 'cantidad': 'sum', 'subtotal_producto': 'sum'}).reset_index()
            resumen_tec.columns = ['Marca', 'Órdenes', 'Unidades', 'Facturación']
            resumen_tec['Ticket Med.'] = (resumen_tec['Facturación'] / resumen_tec['Órdenes']).round(0)
            st.dataframe(resumen_tec, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Se ha producido un error técnico: {e}")