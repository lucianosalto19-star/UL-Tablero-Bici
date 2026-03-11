import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Configuración inicial
st.set_page_config(page_title="EcoBici Explorer", layout="wide")

# --- LÓGICA MATEMÁTICA PARA RADIO ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    # Fórmula de Haversine para distancia entre coordenadas
    R = 6371  # Radio de la Tierra en km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

# --- CARGA DE DATOS (Mantenemos la función anterior) ---
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

df = cargar_datos_ecobici()

# --- SIDEBAR: PLANIFICADOR DE RUTA ---
st.sidebar.header("🗺️ Planificador de Ruta")

modo_vista = st.sidebar.radio("Selecciona modo:", ["Mapa General", "Buscar Cercanas"])

if modo_vista == "Buscar Cercanas":
    st.sidebar.write("### Punto de Referencia")
    # Coordenadas por defecto (Ángel de la Independencia)
    ref_lat = st.sidebar.number_input("Latitud Origen", value=19.4298)
    ref_lon = st.sidebar.number_input("Longitud Origen", value=-99.1676)
    radio = st.sidebar.slider("Radio de búsqueda (KM)", 0.5, 3.0, 1.5)
    
    # Filtrado por radio
    df['Distancia_Km'] = df.apply(lambda row: calcular_distancia(ref_lat, ref_lon, row['Lat'], row['Lon']), axis=1)
    df_filtrado = df[df['Distancia_Km'] <= radio].sort_values('Distancia_Km')
    
else:
    df_filtrado = df

# --- MAPA PRINCIPAL ---
st.write("# Planificador EcoBici CDMX")

# Crear Mapa
fig = px.scatter_mapbox(
    df_filtrado, lat="Lat", lon="Lon", color="Disponibilidad_%", 
    size="Capacidad", hover_name="Nombre",
    color_continuous_scale="RdYlGn", range_color=[0, 100],
    zoom=13, height=600
)

# Si estamos en modo búsqueda, añadir el punto central
if modo_vista == "Buscar Cercanas":
    fig.add_trace(go.Scattermapbox(
        lat=[ref_lat], lon=[ref_lon], mode='markers',
        marker=go.scattermapbox.Marker(size=15, color='blue', symbol='marker'),
        name="Tu Ubicación"
    ))
    
fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

# --- RUTAS DE GOOGLE MAPS (SIMULADO) ---
if modo_vista == "Buscar Cercanas":
    st.subheader("🚶 Estaciones en el radio seleccionado")
    if not df_filtrado.empty:
        col_list, col_link = st.columns([2, 1])
        with col_list:
            st.dataframe(df_filtrado[['Nombre', 'Bicis', 'Anclajes', 'Distancia_Km']])
        
        with col_link:
            st.info("Para ver la ruta en Google Maps:")
            # Generar link dinámico
            destino_nombre = df_filtrado.iloc[0]['Nombre'].replace(" ", "+")
            url_gmaps = f"https://www.google.com/maps/dir/?api=1&origin={ref_lat},{ref_lon}&destination={df_filtrado.iloc[0]['Lat']},{df_filtrado.iloc[0]['Lon']}&travelmode=walking"
            st.link_button("Ir a la estación más cercana", url_gmaps)
    else:
        st.warning("No se encontraron estaciones en este radio.")

# --- EXPANDER PARA ALCALDÍAS (EXPLICACIÓN) ---
with st.expander("ℹ️ Sobre la capa de Alcaldías"):
    st.write("Para habilitar esta capa, necesitamos un archivo `alcaldias.json`. Una vez que lo tengas en tu repositorio, usaremos `fig.update_layout(mapbox_layers=[...])`.")
