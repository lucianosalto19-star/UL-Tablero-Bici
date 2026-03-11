import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import json
from pathlib import Path

# Intentar importar geopy, si falla, desactivamos la función de búsqueda
try:
    from geopy.geocoders import Nominatim
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False

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
    try:
        url_info = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json"
        url_status = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"
        r1 = requests.get(url_info).json()
        r2 = requests.get(url_status).json()
        df1 = pd.DataFrame(r1['data']['stations'])
        df2 = pd.DataFrame(r2['data']['stations'])
        df = pd.merge(df1[['station_id', 'name', 'lat', 'lon', 'capacity']],
                      df2[['station_id', 'num_bikes_available', 'num_docks_available']], on='station_id')
        df.columns = ['ID', 'Nombre', 'Lat', 'Lon', 'Capacidad', 'Bicis', 'Anclajes']
        df['Disponibilidad_%'] = (df['Bicis'] / df['Capacidad'].replace(0, 1) * 100).round(1)
        return df
    except Exception as e:
        st.error(f"Error al conectar con la API de EcoBici: {e}")
        return pd.DataFrame()

def cargar_geojson():
    ruta_geojson = Path(__file__).parent / "09-Cdmx.geojson"
    if ruta_geojson.exists():
        try:
            with open(ruta_geojson, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

# --- CARGA DE DATOS ---
st.write("# 🚲 EcoBici Pro: Navegador de Ciudad")
st.caption("Visualización Avanzada | Luciano Salto")

df = cargar_datos_ecobici()
geojson_data = cargar_geojson()

if df.empty:
    st.warning("No se pudieron cargar los datos. Reintenta en unos momentos.")
    st.stop()

# --- SIDEBAR: CONTROLES ---
st.sidebar.header("🛠️ Panel de Control")

modo_vista = st.sidebar.radio("Modo de búsqueda:", ["Ver Todo el Sistema", "Buscar por Dirección (1.5km)"])
id_seleccionada = st.sidebar.selectbox("Resaltar Estación por ID:", ["Ninguna"] + sorted(df['ID'].unique().tolist(), key=int))
zoom_level = st.sidebar.slider("Nivel de Zoom:", 10.0, 18.0, 12.5)

# --- LÓGICA DE DIRECCIÓN ---
ref_lat, ref_lon = 19.4298, -99.1676

if modo_vista == "Buscar por Dirección (1.5km)":
    if not GEOPY_AVAILABLE:
        st.sidebar.error("Búsqueda de dirección no disponible. Revisa requirements.txt")
    else:
        direccion = st.sidebar.text_input("Escribe una dirección en CDMX:", "Ángel de la Independencia")
        if direccion:
            try:
                geolocator = Nominatim(user_agent="ecobici_analytics_app")
                location = geolocator.geocode(direccion + ", Ciudad de México")
                if location:
                    ref_lat, ref_lon = location.latitude, location.longitude
                    st.sidebar.success("Ubicación encontrada")
            except:
                st.sidebar.warning("Servicio de mapas saturado, intenta de nuevo.")

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
            "type": "fill",
            "color": "rgba(100, 100, 100, 0.15)",
            "below": "traces"
        }]
    )

# Estación Resaltada
if id_seleccionada != "Ninguna":
    sel = df[df['ID'] == id_seleccionada]
    fig.add_trace(go.Scattermapbox(
        lat=sel["Lat"], lon=sel["Lon"], mode='markers',
        marker=go.scattermapbox.Marker(size=25, color='gold', symbol='diamond'),
        name="Seleccionada"
    ))

# Origen de búsqueda
if modo_vista == "Buscar por Dirección (1.5km)":
    fig.add_trace(go.Scattermapbox(
        lat=[ref_lat], lon=[ref_lon], mode='markers',
        marker=go.scattermapbox.Marker(size=20, color='dodgerblue', symbol='circle'),
        name="Tu Punto"
    ))

fig.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

# --- BOTÓN GOOGLE MAPS ---
if modo_vista == "Buscar por Dirección (1.5km)" and not df_mapa.empty:
    mejor = df_mapa.iloc[0]
    url_gmaps = f"https://www.google.com/maps/dir/?api=1&origin={ref_lat},{ref_lon}&destination={mejor['Lat']},{mejor['Lon']}&travelmode=walking"
    st.link_button(f"🗺️ Ir a {mejor['Nombre']} ({mejor['Distancia_Km']:.2f} km)", url_gmaps)

with st.expander("📊 Tabla de Datos"):
    st.dataframe(df_mapa)
