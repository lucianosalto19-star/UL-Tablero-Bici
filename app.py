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

try:
    from geopy.geocoders import Nominatim
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False

# --- FUNCIONES DE SOPORTE ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

@st.cache_data(ttl=300) # Caché más largo para estabilidad
def cargar_datos_ecobici():
    try:
        r1 = requests.get("https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json").json()
        r2 = requests.get("https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json").json()
        df1 = pd.DataFrame(r1['data']['stations'])[['station_id', 'name', 'lat', 'lon', 'capacity']]
        df2 = pd.DataFrame(r2['data']['stations'])[['station_id', 'num_bikes_available', 'num_docks_available']]
        df = pd.merge(df1, df2, on='station_id')
        df.columns = ['ID', 'Nombre', 'Lat', 'Lon', 'Capacidad', 'Bicis', 'Anclajes']
        df['Disponibilidad_%'] = (df['Bicis'] / df['Capacidad'].replace(0, 1) * 100).round(1)
        return df
    except:
        return pd.DataFrame()

@st.cache_data
def cargar_geojson_optimizado():
    ruta = Path(__file__).parent / "09-Cdmx.geojson"
    if ruta.exists():
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Extraer lista de CPs/Alcaldías para el filtro
            opciones = sorted(list(set(f['properties'].get('d_codigo', 'Desconocido') for f in data['features'])))
            return data, opciones
    return None, []

# --- CARGA ---
df_raw = cargar_datos_ecobici()
geojson_data, lista_sectores = cargar_geojson_optimizado()

st.write("# 🚲 EcoBici Pro CDMX")
st.caption("Filtros inteligentes y búsqueda por dirección/coordenada")

# --- SIDEBAR ---
st.sidebar.header("🛠️ Configuración")

modo_ubicacion = st.sidebar.selectbox("Método de ubicación:", ["Dirección", "Coordenadas Manuales"])
ref_lat, ref_lon = 19.4298, -99.1676

if modo_ubicacion == "Dirección" and GEOPY_AVAILABLE:
    direccion = st.sidebar.text_input("Dirección:", "Paseo de la Reforma 222")
    if direccion:
        try:
            geolocator = Nominatim(user_agent="ecobici_pro_v2")
            loc = geolocator.geocode(direccion + ", Ciudad de México")
            if loc:
                ref_lat, ref_lon = loc.latitude, loc.longitude
                st.sidebar.success("Ubicación encontrada")
        except:
            st.sidebar.warning("Servicio lento, usando coordenadas base")
else:
    ref_lat = st.sidebar.number_input("Latitud", value=19.4298, format="%.4f")
    ref_lon = st.sidebar.number_input("Longitud", value=-99.1676, format="%.4f")

st.sidebar.markdown("---")
# FILTRO POR SECTOR (CP/Alcaldía del GeoJSON)
sector_sel = st.sidebar.multiselect("Filtrar por sectores del mapa (CP):", lista_sectores)

id_sel = st.sidebar.selectbox("Resaltar Estación por ID:", ["Ninguna"] + sorted(df_raw['ID'].tolist(), key=int))
zoom_level = st.sidebar.slider("Zoom:", 10.0, 18.0, 12.5)

# --- PROCESAMIENTO ---
df_mapa = df_raw.copy()

# Aplicar radio si se activa la búsqueda
df_mapa['Dist_Km'] = df_mapa.apply(lambda r: calcular_distancia(ref_lat, ref_lon, r['Lat'], r['Lon']), axis=1)
df_mapa = df_mapa[df_mapa['Dist_Km'] <= 2.0] # Radio de 2km por defecto para mejor contexto

# --- MAPA ---
fig = px.scatter_mapbox(
    df_mapa, lat="Lat", lon="Lon", color="Disponibilidad_%", size="Capacidad",
    hover_name="Nombre", color_continuous_scale="RdYlGn", range_color=[0, 100],
    zoom=zoom_level, height=600
)

# Capa GeoJSON optimizada (solo líneas)
if geojson_data:
    # Filtrar el geojson para mostrar solo lo seleccionado o todo si está vacío
    if sector_sel:
        geojson_filt = {
            "type": "FeatureCollection",
            "features": [f for f in geojson_data['features'] if f['properties'].get('d_codigo') in sector_sel]
        }
    else:
        geojson_filt = geojson_data

    fig.update_layout(mapbox_layers=[{
        "sourcetype": "geojson", "source": geojson_filt, "type": "line",
        "color": "gray", "opacity": 0.3, "line": {"width": 1}
    }])

# Estación resaltada
if id_sel != "Ninguna":
    s = df_raw[df_raw['ID'] == id_sel]
    fig.add_trace(go.Scattermapbox(lat=s["Lat"], lon=s["Lon"], mode='markers',
                  marker=go.scattermapbox.Marker(size=20, color='gold', symbol='diamond'), name="Destino"))

fig.update_layout(mapbox_style="carto-positron", mapbox_center={"lat": ref_lat, "lon": ref_lon},
                  margin={"r":0,"t":0,"l":0,"b":0})

st.plotly_chart(fig, use_container_width=True)

# --- GOOGLE MAPS ---
if not df_mapa.empty:
    m = df_mapa.sort_values('Dist_Km').iloc[0]
    url = f"https://www.google.com/maps/dir/?api=1&origin={ref_lat},{ref_lon}&destination={m['Lat']},{m['Lon']}&travelmode=walking"
    st.link_button(f"🗺️ Caminar a {m['Nombre']} ({m['Dist_Km']:.2f} km)", url)

with st.expander("📊 Datos de la zona"):
    st.dataframe(df_mapa.drop(columns=['Dist_Km']))
