# --- CONFIGURACIÓN DE CAPAS DEL MAPA ---
if geojson_data:
    fig.update_layout(
        mapbox_layers=[{
            "sourcetype": "geojson",
            "source": geojson_data,
            "type": "line",
            "color": "#808080",  # Color gris para los límites
            "opacity": 0.5,
            "line": {"width": 1}
        }]
    )
else:
    st.info("Nota: No se pudo cargar la capa geográfica de CDMX.")

# Configuración estética final
fig.update_layout(
    mapbox_style="carto-positron", 
    margin={"r":0,"t":0,"l":0,"b":0},
    # Añadimos explícitamente el centro y zoom para evitar errores de validación
    mapbox_zoom=zoom_level,
    mapbox_center={"lat": ref_lat, "lon": ref_lon}
)

st.plotly_chart(fig, use_container_width=True)
