import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh  # <--- PASO B: Va en la línea 6

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Analítica Distrinando | Centro de Comando",
    layout="wide",
    initial_sidebar_state="expanded"
)
st_autorefresh(interval=300000, limit=None, key="auto_refresh") # <--- PASO C: Va justo en la línea 13 (después de set_page_config)

# 2. CSS CORPORATIVO DARK NAVY
st.markdown("""
    <style>
    /* Tarjetas de Métricas Globales */
    .metric-container {
        background-color: #1E293B; 
        border: 1px solid #334155;
        padding: 24px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 15px;
    }
    .metric-title { font-size: 12px; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 1px; margin-bottom: 10px; }
    .metric-value { font-size: 30px; font-weight: 800; color: #38BDF8; letter-spacing: -1px; }
    
    /* Tarjetas de Marcas */
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

    /* Tarjetas de Productos */
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
    
    /* Contenedor de Descuentos Independiente */
    .discount-container { background: #0F172A; border: 1px dashed #334155; border-radius: 12px; padding: 20px; margin-top: 20px; }
    
    /* Ajustes visuales nativos */
    span[data-baseweb="tag"] { background-color: #1E3A8A !important; color: #F8FAFC !important; border: 1px solid #3B82F6 !important; border-radius: 4px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONSTANTES Y PALETAS
DIAS_MAPA = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
ESTADO_MAPA = {'fulfilled': 'Enviado', 'null': 'Pendiente', 'pending': 'En Preparación', 'restocked': 'Devuelto', 'unfulfilled': 'No Enviado'}
PALETA_MARCAS = {'Reebok': '#38BDF8', 'Columbia': '#818CF8', 'Crocs': '#34D399', 'Kappa': '#F472B6', 'Piccadilly': '#FBBF24'}

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
    
    # Parches si el CSV es viejo y no tiene las nuevas columnas modelo/color
    if 'producto_base' not in df.columns: df['producto_base'] = df['producto'].apply(lambda x: str(x).split(' / ')[0])
    if 'modelo_color' not in df.columns: df['modelo_color'] = df['sku'].apply(lambda x: str(x).rsplit('-', 1)[0] if '-' in str(x) else x)
    
    return df

def configurar_grafico(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94A3B8"))
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
                p_m = df_m.groupby('id_pedido').first()
                f_m, c_m = p_m['total_pedido'].sum(), len(p_m)
                accent = PALETA_MARCAS.get(m_nombre, "#94A3B8")
                m_cols[i].markdown(f"""
                    <div class="brand-card" style="border-top: 4px solid {accent};">
                        <div class="brand-header" style="color: {accent};">{m_nombre}</div>
                        <div class="brand-stat"><span>Venta:</span><span class="brand-stat-val">${f_m:,.0f}</span></div>
                        <div class="brand-stat"><span>Órdenes:</span><span class="brand-stat-val">{c_m:,}</span></div>
                        <div class="brand-stat"><span>Unidades:</span><span class="brand-stat-val">{df_m['cantidad'].sum():,}</span></div>
                        <div class="brand-stat"><span>TK Prom.:</span><span class="brand-stat-val">${(f_m/c_m if c_m>0 else 0):,.0f}</span></div>
                    </div>""", unsafe_allow_html=True)

        # --- SECCIÓN 4: RANKING DUAL (MODELO VS SKU) ---
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
                    
                    # Lógica de agrupación según el switch elegido
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
            # 1. Obtenemos toda la base de pedidos con algún descuento real
            df_desc_base = df_raw[(df_raw['descuento'] != 'SIN DESCUENTO') & (df_raw['descuento'] != '')]
            
            # 2. LÓGICA DE CASCADA: Filtramos la base para que solo queden las marcas seleccionadas en col_f1
            df_desc_filtrado_marcas = df_desc_base[df_desc_base['marca'].isin(desc_marcas_sel)]
            
            # 3. Extraemos los códigos únicos SOLO de ese dataframe filtrado
            desc_disponibles = sorted(df_desc_filtrado_marcas['descuento'].astype(str).unique())
            
            # 4. Seleccionamos los primeros 5 por defecto (si hay) para no saturar la vista
            default_descs = desc_disponibles[:5] if len(desc_disponibles) > 0 else []
            
            desc_sel = st.multiselect("Código Promocional", desc_disponibles, default=default_descs, key="desc_promo")

        # Aplicamos filtro de fecha y armamos los gráficos
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
                st.plotly_chart(configurar_grafico(fig_desc_fc), use_container_width=True)
            with col_d2:
                desc_unid = df_promo.groupby(['descuento', 'marca'])['cantidad'].sum().reset_index()
                fig_desc_unid = px.bar(desc_unid, x='cantidad', y='descuento', color='marca', orientation='h', text_auto=True, color_discrete_map=PALETA_MARCAS, title="Unidades por Código")
                st.plotly_chart(configurar_grafico(fig_desc_unid), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # --- SECCIÓN FINANZAS Y LOGÍSTICA ---
        st.divider()
        col_fin, col_log = st.columns([1.5, 1])
        
        with col_fin:
            st.subheader("💳 Finanzas")
            f1, f2 = st.columns(2)
            with f1:
                cuotas_df = df_f.groupby('id_pedido').first()['cuotas'].value_counts().reset_index()
                fig_c = px.pie(cuotas_df, values='count', names='cuotas', hole=0.5, color_discrete_sequence=['#38BDF8', '#818CF8', '#34D399', '#FBBF24'], title="Financiación")
                st.plotly_chart(configurar_grafico(fig_c), use_container_width=True)
            with f2:
                gate_df = df_f.groupby('id_pedido').first()['medio_pago'].value_counts().reset_index()
                fig_g = px.bar(gate_df, x='count', y='medio_pago', orientation='h', text_auto=True, title="Gateways", color_discrete_sequence=['#38BDF8'])
                fig_g.update_layout(showlegend=False, yaxis_title="")
                st.plotly_chart(configurar_grafico(fig_g), use_container_width=True)

        with col_log:
            st.subheader("📦 Logística")
            df_f['fulfillment_status_es'] = df_f['fulfillment_status'].fillna('null').map(ESTADO_MAPA)
            log_stat = df_f.groupby('fulfillment_status_es')['id_pedido'].nunique().reset_index()
            fig_log = px.pie(log_stat, values='id_pedido', names='fulfillment_status_es', title="Estados de Envío", hole=0.6, color_discrete_sequence=['#818CF8', '#34D399', '#F472B6'])
            st.plotly_chart(configurar_grafico(fig_log), use_container_width=True)

        # --- SECCIÓN TEMPORAL ---
        st.divider()
        st.subheader("📅 Análisis Temporal y Eficiencia")
        g1, g2 = st.columns([2, 1])
        
        with g1:
            df_f['hora'] = df_f['fecha'].dt.hour
            v_h = df_f.groupby(['hora', 'marca'])['total_pedido'].sum().reset_index()
            fig_l = px.line(v_h, x='hora', y='total_pedido', color='marca', markers=True, line_shape="spline", color_discrete_map=PALETA_MARCAS, title="Facturación por Hora")
            fig_l.update_layout(xaxis_title="Hora del Día", yaxis_title="Facturación ($)")
            st.plotly_chart(configurar_grafico(fig_l), use_container_width=True)

        with g2:
            st.markdown("#### Resumen Operativo")
            resumen_tec = df_f.groupby('marca').agg({'id_pedido': 'nunique', 'cantidad': 'sum', 'subtotal_producto': 'sum'}).reset_index()
            resumen_tec.columns = ['Marca', 'Órdenes', 'Unidades', 'Facturación']
            resumen_tec['Ticket Med.'] = (resumen_tec['Facturación'] / resumen_tec['Órdenes']).round(0)
            st.dataframe(resumen_tec, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Se ha producido un error técnico: {e}")