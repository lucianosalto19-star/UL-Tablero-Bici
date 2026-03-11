import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import json
from pathlib import Path
from geopy.geocoders import Nominatim # Para buscar direcciones

# 1. Configuración de página
st.set_page_config(page_title="EcoBici Pro CDMX", layout="wide")

# --- FUNCIONES DE SOPORTE ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

@st.cache_data(ttl=60)
def cargar_datos_ecobici():
    url_info = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json"
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"
    r1 = requests.get(url_info).json()
    r2 = requests.get(url_status).json()
    df1 = pd.DataFrame(r1['data']['stations'])
    df2 = pd.DataFrame(r2['data']['stations'])
    # Intentamos extraer alcaldía si el feed la provee, si no, se queda como dato general
    df = pd.merge(df1[['station_id', 'name', 'lat', 'lon', 'capacity']],
                  df2[['station_id', 'num_bikes_available', 'num_docks_available']], on='station_id')
    df.columns = ['ID', 'Nombre', 'Lat', 'Lon', 'Capacidad', 'Bicis', 'Anclajes']
    df['Disponibilidad_%'] = (df['Bicis'] / df['Capacidad'].replace(0, 1) * 100).round(1)
    return df

def cargar_geojson():
    ruta_geojson = Path(__file__).parent / "09-Cdmx.geojson"
    try:
        with open(ruta_geojson, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Capa geográfica no cargada: {e}")
        return None

# --- CARGA DE DATOS ---
st.write("# 🚲 EcoBici Pro: Navegador de Ciudad")
st.caption("Visualización Avanzada | Luciano Salto")

df = cargar_datos_ecobici()
geojson_data = cargar_geojson()

# --- SIDEBAR: CONTROLES ---
st.sidebar.header("🛠️ Panel de Control")

# 1. Modo de Vista
modo_vista = st.sidebar.radio("Modo de búsqueda:", ["Ver Todo el Sistema", "Buscar por Dirección (1.5km)"])

# 2. Resaltar por ID
id_seleccionada = st.sidebar.selectbox("Resaltar Estación por ID:", ["Ninguna"] + sorted(df['ID'].unique().tolist(), key=int))

# 3. Zoom
zoom_level = st.sidebar.slider("Nivel de Zoom:", 10.0, 18.0, 12.5)

# --- LÓGICA DE GEOLOCALIZACIÓN ---
ref_lat, ref_lon = 19.4298, -99.1676 # Default: Ángel de la Independencia

if modo_vista == "Buscar por Dirección (1.5km)":
    st.sidebar.markdown("---")
    direccion = st.sidebar.text_input("Escribe una dirección (ej: Palacio de Bellas Artes):", "")
    
    if direccion:
        try:
            geolocator = Nominatim(user_agent="ecobici_app")
            location = geolocator.geocode(direccion + ", Ciudad de México")
            if location:
                ref_lat, ref_lon = location.latitude, location.longitude
                st.sidebar.success(f"Ubicación encontrada: {location.address[:30]}...")
            else:
                st.sidebar.error("No se encontró la dirección.")
        except:
            st.sidebar.error("Servicio de búsqueda temporalmente lento.")

    df['Distancia_Km'] = df.apply(lambda row: calcular_distancia(ref_lat, ref_lon, row['Lat'], row['Lon']), axis=1)
    df_mapa = df[df['Distancia_Km'] <= 1.5].sort_values('Distancia_Km')
else:
    df_mapa = df

# --- MAPA ---
fig = px.scatter_mapbox(
    df_mapa, lat="Lat", lon="Lon", 
    color="Disponibilidad_%", size="Capacidad",
    hover_name="Nombre",
    color_continuous_scale="RdYlGn", range_color=[0, 100],
    zoom=zoom_level, height=650
)

# Capa GeoJSON (Alcaldías/Polígonos)
if geojson_data:
    fig.update_layout(
        mapbox_layers=[{
            "sourcetype": "geojson",
            "source": geojson_data,
            "type": "fill", # Cambiado de 'line' a 'fill' para mejor visualización
            "color": "rgba(128, 128, 128, 0.1)",
            "below": "traces"
        }]
    )

# Estación Resaltada
if id_seleccionada != "Ninguna":
    sel = df[df['ID'] == id_seleccionada]
    fig.add_trace(go.Scattermapbox(
        lat=sel["Lat"], lon=sel["Lon"], mode='markers',
        marker=go.scattermapbox.Marker(size=22, color='gold', symbol='diamond'),
        name="Seleccionada"
    ))

# Origen
if modo_vista == "Buscar por Dirección (1.5km)":
    fig.add_trace(go.Scattermapbox(
        lat=[ref_lat], lon=[ref_lon], mode='markers',
        marker=go.scattermapbox.Marker(size=18, color='dodgerblue', symbol='circle'),
        name="Tu Destino"
    ))

fig.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

# --- BOTÓN GOOGLE MAPS ---
if modo_vista == "Buscar por Dirección (1.5km)" and not df_mapa.empty:
    mejor = df_mapa.iloc[0]
    url_gmaps = f"https://www.google.com/maps/dir/?api=1&origin={ref_lat},{ref_lon}&destination={mejor['Lat']},{mejor['Lon']}&travelmode=walking"
    st.link_button(f"🗺️ Caminar a {mejor['Nombre']} ({mejor['Distancia_Km']:.2f} km)", url_gmaps)

with st.expander("📊 Datos Detallados"):
    st.dataframe(df_mapa, use_container_width=True)
