import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Carga de Objetivos | Distrinando", layout="wide")

st.markdown("""
    <style>
    .save-box { background-color: #1E293B; border-left: 4px solid #34D399; padding: 15px; border-radius: 8px; margin-top: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Data Entry: Objetivos de Negocio (Hot Sale)")
st.caption("Ingrese las metas comerciales acordadas con la Gerencia. Estos datos alimentarán los velocímetros en vivo.")

MARCAS = ["Reebok", "Columbia", "Crocs", "Kappa", "Piccadilly"]
ARCHIVO_OBJ = "objetivos_hot_sale.json"

if os.path.exists(ARCHIVO_OBJ):
    try:
        with open(ARCHIVO_OBJ, "r") as f:
            datos_actuales = json.load(f)
    except:
        datos_actuales = {m: {"unidades": 0, "facturacion": 0} for m in MARCAS}
else:
    datos_actuales = {m: {"unidades": 0, "facturacion": 0} for m in MARCAS}

df_obj = pd.DataFrame([
    {"Marca": m, "Objetivo Unidades": datos_actuales.get(m, {}).get("unidades", 0), "Objetivo Facturación ($)": datos_actuales.get(m, {}).get("facturacion", 0)}
    for m in MARCAS
])

st.subheader("📝 Planilla de Metas")
df_editado = st.data_editor(
    df_obj,
    column_config={
        "Marca": st.column_config.TextColumn("Unidad de Negocio", disabled=True),
        "Objetivo Unidades": st.column_config.NumberColumn("Objetivo Unidades", min_value=0, step=1, format="%d"),
        "Objetivo Facturación ($)": st.column_config.NumberColumn("Objetivo Facturación ($)", min_value=0, step=1000, format="$%d")
    },
    hide_index=True,
    use_container_width=True
)

if st.button("💾 Guardar Objetivos en la Nube", type="primary"):
    nuevo_json = {}
    for idx, row in df_editado.iterrows():
        nuevo_json[row["Marca"]] = {
            "unidades": int(row["Objetivo Unidades"]),
            "facturacion": int(row["Objetivo Facturación ($)"])
        }
    
    with open(ARCHIVO_OBJ, "w") as f:
        json.dump(nuevo_json, f, indent=4)
        
    st.success("✅ ¡Objetivos guardados temporalmente en la sesión de la nube! Vuelva al Centro de Comando para ver los medidores.")

st.divider()
st.markdown("### 📊 Resumen Global Proyectado")
c1, c2 = st.columns(2)
c1.metric("Meta de Facturación Global", f"${df_editado['Objetivo Facturación ($)'].sum():,.0f}")
c2.metric("Meta de Unidades Globales", f"{df_editado['Objetivo Unidades'].sum():,} un.")
