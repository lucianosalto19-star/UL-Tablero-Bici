import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import json
from pathlib import Path

# 1. Configuración de página
st.set_page_config(page_title="EcoBici Pro CDMX", layout="wide")

# --- FUNCIONES DE SOPORTE ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371  # Radio de la Tierra en km
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
    df = pd.merge(df1[['station_id', 'name', 'lat', 'lon', 'capacity']],
                  df2[['station_id', 'num_bikes_available', 'num_docks_available']], on='station_id')
    df.columns = ['ID', 'Nombre', 'Lat', 'Lon', 'Capacidad', 'Bicis', 'Anclajes']
    df['Disponibilidad_%'] = (df['Bicis'] / df['Capacidad'].replace(0, 1) * 100).round(1)
    return df

def cargar_geojson():
    # Buscamos el archivo en la misma carpeta que app.py
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

modo_vista = st.sidebar.radio("Modo de búsqueda:", ["Ver Todo el Sistema", "Planear Ruta (Radio 1.5km)"])
lista_ids = ["Ninguna"] + sorted(df['ID'].unique().tolist(), key=int)
id_seleccionada = st.sidebar.selectbox("Resaltar Estación por ID:", lista_ids)
zoom_level = st.sidebar.slider("Nivel de Zoom:", 10.0, 18.0, 12.5)

if modo_vista == "Planear Ruta (Radio 1.5km)":
    st.sidebar.markdown("---")
    st.sidebar.write("📍 **Punto de Referencia**")
    ref_lat = st.sidebar.number_input("Latitud Origen", value=19.4298, format="%.4f")
    ref_lon = st.sidebar.number_input("Longitud Origen", value=-99.1676, format="%.4f")
    
    df['Distancia_Km'] = df.apply(lambda row: calcular_distancia(ref_lat, ref_lon, row['Lat'], row['Lon']), axis=1)
    df_mapa = df[df['Distancia_Km'] <= 1.5].sort_values('Distancia_Km')
else:
    df_mapa = df

# --- MAPA ---
fig = px.scatter_mapbox(
    df_mapa, lat="Lat", lon="Lon", 
    color="Disponibilidad_%", size="Capacidad",
    hover_name="Nombre",
    hover_data={"ID": True, "Bicis": True, "Anclajes": True, "Lat": False, "Lon": False},
    color_continuous_scale="RdYlGn", range_color=[0, 100],
    zoom=zoom_level, height=650
)

# Integrar la capa GeoJSON si existe
if geojson_data:
    fig.update_layout(
        mapbox_layers=[{
            "sourcetype": "geojson",
            "source": geojson_data,
            "type": "line",
            "color": "#808080",
            "opacity": 0.5,
            "line": {"width": 1}
        }]
    )

# Resaltar estación con Diamante
if id_seleccionada != "Ninguna":
    sel = df[df['ID'] == id_seleccionada]
    fig.add_trace(go.Scattermapbox(
        lat=sel["Lat"], lon=sel["Lon"], mode='markers',
        marker=go.scattermapbox.Marker(size=22, color='gold', symbol='diamond'),
        name="Seleccionada",
        hovertext=f"ID: {id_seleccionada}<br>{sel['Nombre'].iloc[0]}"
    ))

# Marcador de ubicación actual
if modo_vista == "Planear Ruta (Radio 1.5km)":
    fig.add_trace(go.Scattermapbox(
        lat=[ref_lat], lon=[ref_lon], mode='markers',
        marker=go.scattermapbox.Marker(size=18, color='dodgerblue', symbol='circle'),
        name="Tu Origen"
    ))

fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

# --- BOTÓN GOOGLE MAPS ---
if modo_vista == "Planear Ruta (Radio 1.5km)" and not df_mapa.empty:
    mejor = df_mapa.iloc[0]
    st.success(f"Estación más cercana: **{mejor['Nombre']}** a {mejor['Distancia_Km']:.2f} km")
    url_gmaps = f"https://www.google.com/maps/dir/?api=1&origin={ref_lat},{ref_lon}&destination={mejor['Lat']},{mejor['Lon']}&travelmode=walking"
    st.link_button("🗺️ Abrir ruta en Google Maps", url_gmaps)

# --- TABLA ---
with st.expander("📊 Explorar Datos en Tabla"):
    st.dataframe(df_mapa, use_container_width=True, hide_index=True)
