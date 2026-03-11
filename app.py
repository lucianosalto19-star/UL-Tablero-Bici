import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Tablero EcoBici", layout="wide")

st.write("# Tablero EcoBici")
st.caption("Visualización y Storytelling Usando Datos")
st.caption("Luciano Salto")

# Función para obtener y limpiar datos con Caché para que sea veloz
@st.cache_data(ttl=60) # Se actualiza cada 60 segundos
def cargar_datos_ecobici():
    url_info = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json"
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"
    
    # Obtener información fija
    resp_info = requests.get(url_info).json()
    df_info = pd.DataFrame(resp_info['data']['stations'])
    
    # Obtener disponibilidad en tiempo real
    resp_status = requests.get(url_status).json()
    df_status = pd.DataFrame(resp_status['data']['stations'])
    
    # Unir tablas
    df = pd.merge(
        df_info[['station_id', 'name', 'lat', 'lon', 'capacity']],
        df_status[['station_id', 'num_bikes_available', 'num_docks_available', 'is_renting']],
        on='station_id'
    )
    
    # Limpieza de nombres
    df.columns = ['ID', 'Nombre', 'Latitud', 'Longitud', 'Capacidad', 'Bicis', 'Anclajes', 'Operativa']
    return df

# Ejecutar la carga
with st.spinner('Cargando datos de EcoBici...'):
    df_mapa = cargar_datos_ecobici()

# --- SECCIÓN DEL MAPA CON PLOTLY ---
st.subheader("📍 Ubicación de Estaciones y Disponibilidad")

# Crear el mapa interactivo
fig = px.scatter_mapbox(
    df_mapa, 
    lat="Latitud", 
    lon="Longitud", 
    color="Bicis", # El color cambia según cuántas bicis hay
    size="Capacidad", # El tamaño del punto depende de la capacidad total
    hover_name="Nombre", 
    hover_data={"Bicis": True, "Anclajes": True, "Latitud": False, "Longitud": False},
    color_continuous_scale=px.colors.cyclical.IceFire, 
    zoom=12, 
    height=600
)

# Configurar el estilo del mapa (OpenStreetMap no requiere token de Mapbox)
fig.update_layout(mapbox_style="open-street-map")
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# Mostrar el mapa en Streamlit
st.plotly_chart(fig, use_container_width=True)

# --- MÉTRICAS RÁPIDAS ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Estaciones", len(df_mapa))
col2.metric("Bicis Disponibles", df_mapa['Bicis'].sum())
col3.metric("Anclajes Libres", df_mapa['Anclajes'].sum())
