import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Tablero EcoBici", layout="wide")

st.write("# Tablero EcoBici")
st.caption("Visualización y Storytelling Usando Datos | Luciano Salto")

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_datos_ecobici():
    url_info = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json"
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"
    
    resp_info = requests.get(url_info).json()
    df_info = pd.DataFrame(resp_info['data']['stations'])
    
    resp_status = requests.get(url_status).json()
    df_status = pd.DataFrame(resp_status['data']['stations'])
    
    df = pd.merge(
        df_info[['station_id', 'name', 'lat', 'lon', 'capacity']],
        df_status[['station_id', 'num_bikes_available', 'num_docks_available']],
        on='station_id'
    )
    
    df.columns = ['ID', 'Nombre', 'Latitud', 'Longitud', 'Capacidad', 'Bicis', 'Anclajes']
    
    # Cálculo de disponibilidad normalizada (0 a 100%)
    # Evitamos división por cero si la capacidad es 0
    df['Disponibilidad_%'] = (df['Bicis'] / df['Capacidad'].replace(0, 1) * 100).round(1)
    
    return df

with st.spinner('Actualizando datos en tiempo real...'):
    df_mapa = cargar_datos_ecobici()

# --- BARRA LATERAL (WIDGETS) ---
st.sidebar.header("Configuración de Vista")

# Widget 1: Selección de Estación por ID
lista_ids = ["Ninguna"] + sorted(df_mapa['ID'].unique().tolist(), key=int)
id_seleccionada = st.sidebar.selectbox("Selecciona una Estación por ID para resaltar:", lista_ids)

# Widget 2: Control de Zoom
zoom_level = st.sidebar.slider("Ajustar Zoom del Mapa:", min_value=10, max_value=18, value=12)

# --- LÓGICA DEL MAPA ---
st.subheader("📍 Mapa de Disponibilidad Normalizada")

# Base del mapa: Todas las estaciones
fig = px.scatter_mapbox(
    df_mapa, 
    lat="Latitud", 
    lon="Longitud", 
    color="Disponibilidad_%", 
    size="Capacidad",
    hover_name="Nombre", 
    hover_data={"ID": True, "Bicis": True, "Anclajes": True, "Disponibilidad_%": True, "Latitud": False, "Longitud": False},
    color_continuous_scale="RdYlGn", # Rojo (vacío) a Verde (lleno)
    range_color=[0, 100],
    zoom=zoom_level, 
    height=700
)

# Resaltar estación seleccionada si aplica
if id_seleccionada != "Ninguna":
    estacion_sel = df_mapa[df_mapa['ID'] == id_seleccionada]
    
    # Agregamos una capa adicional (trace) para la estación resaltada
    fig.add_trace(go.Scattermapbox(
        lat=estacion_sel["Latitud"],
        lon=estacion_sel["Longitud"],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=20,
            color='gold',
            symbol='diamond'
        ),
        text=estacion_sel['Nombre'],
        hovertemplate=(
            f"<b>ESTACIÓN RESALTADA</b><br>" +
            f"ID: {estacion_sel['ID'].iloc[0]}<br>" +
            f"Nombre: {estacion_sel['Nombre'].iloc[0]}<br>" +
            f"Bicis: {estacion_sel['Bicis'].iloc[0]}<br>" +
            f"Anclajes: {estacion_sel['Anclajes'].iloc[0]}<br>" +
            "<extra></extra>"
        )
    ))

fig.update_layout(mapbox_style="open-street-map")
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

st.plotly_chart(fig, use_container_width=True)

# --- MÉTRICAS ---
col1, col2, col3 = st.columns(3)
col1.metric("Estaciones Totales", len(df_mapa))
col2.metric("Bicis en Red", df_mapa['Bicis'].sum())
col3.metric("Puertos Libres", df_mapa['Anclajes'].sum())

# --- VISUALIZACIÓN DE DATOS AL FINAL ---
st.divider()
with st.expander("📊 Ver tabla de datos completa"):
    st.dataframe(
        df_mapa.sort_values(by="ID", ascending=True), 
        use_container_width=True,
        hide_index=True
    )
