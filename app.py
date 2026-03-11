import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import json
from pathlib import Path

# Configuración de página - DEBE SER LA PRIMERA LÍNEA DE STREAMLIT
st.set_page_config(page_title="EcoBici Pro CDMX", layout="wide")

# --- CARGA SEGURA DE GEOPY ---
try:
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="ecobici_analytics_cdmx")
    GEOPY_READY = True
except Exception:
    GEOPY_READY = False

# --- FUNCIONES ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

@st.cache_data(ttl=300) # Caché de 5 minutos
def cargar_datos():
    try:
        r1 = requests.get("https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json").json()
        r2 = requests.get("https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json").json()
        df1 = pd.DataFrame(r1['data']['stations'])[['station_id', 'name', 'lat', 'lon', 'capacity']]
        df2 = pd.DataFrame(r2['data']['stations'])[['station_id', 'num_bikes_available', 'num_docks_available']]
        df = pd.merge(df1, df2, on='station_id')
        df.columns = ['ID', 'Nombre', 'Lat', 'Lon', 'Capacidad', 'Bicis', 'Anclajes']
        df['Disponibilidad_%'] = (df['Bicis'] / df['Capacidad'].replace(0, 1) * 100).clip(0, 100).round(1)
        return df
    except:
        return pd.DataFrame()

def cargar_capa_geojson():
    ruta = Path(__file__).parent / "09-Cdmx.geojson"
    if ruta.exists():
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# --- UI ---
st.title("🚲 EcoBici Pro CDMX")
st.caption("Dashboard de Movilidad | Luciano Salto")

df = cargar_datos()
geojson = cargar_capa_geojson()

if df.empty:
    st.error("Error al cargar datos de la API.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuración")
    modo = st.radio("Modo:", ["Global", "Dirección"])
    id_sel = st.selectbox("Resaltar ID:", ["Ninguna"] + sorted(df['ID'].tolist(), key=int))
    zoom = st.slider("Zoom", 10.0, 18.0, 12.0)
    
    ref_lat, ref_lon = 19.4298, -99.1676
    if modo == "Dirección" and GEOPY_READY:
        dir_input = st.text_input("Buscar dirección:", "Reforma 222")
        loc = geolocator.geocode(dir_input + ", CDMX")
        if loc:
            ref_lat, ref_lon = loc.latitude, loc.longitude
            st.success("Ubicación fijada")

# --- PROCESAMIENTO ---
if modo == "Dirección":
    df['Dist'] = calcular_distancia(ref_lat, ref_lon, df['Lat'], df['Lon'])
    df_mapa = df[df['Dist'] <= 1.5].copy()
else:
    df_mapa = df.copy()

# --- MAPA ---
fig = px.scatter_mapbox(
    df_mapa, lat="Lat", lon="Lon", color="Disponibilidad_%", size="Capacidad",
    hover_name="Nombre", color_continuous_scale="RdYlGn", range_color=[0, 100],
    zoom=zoom, center={"lat": ref_lat, "lon": ref_lon}, height=600
)

if geojson:
    fig.update_layout(mapbox_layers=[{
        "sourcetype": "geojson", "source": geojson, "type": "line",
        "color": "rgba(100,100,100,0.5)", "width": 1
    }])

if id_sel != "Ninguna":
    s = df[df['ID'] == id_sel]
    fig.add_trace(go.Scattermapbox(lat=s["Lat"], lon=s["Lon"], mode='markers',
                  marker=go.scattermapbox.Marker(size=20, color='gold', symbol='diamond')))

fig.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

# --- GOOGLE MAPS ---
if modo == "Dirección" and not df_mapa.empty:
    m = df_mapa.sort_values('Dist').iloc[0]
    url = f"https://www.google.com/maps/dir/?api=1&origin={ref_lat},{ref_lon}&destination={m['Lat']},{m['Lon']}&travelmode=walking"
    st.link_button(f"Ir a {m['Nombre']} ({m['Dist']:.2f} km)", url)

with st.expander("Tabla"):
    st.dataframe(df_mapa)
