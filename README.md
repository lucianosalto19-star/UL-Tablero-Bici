# 🚲 EcoBici CDMX - Dashboard en Tiempo Real

Este proyecto es un tablero interactivo desarrollado con **Streamlit** y **Plotly** que visualiza el estado actual del sistema de bicicletas compartidas de la Ciudad de México (EcoBici). 

Utiliza los feeds oficiales de **GBFS (General Bikeshare Feed Specification)** para mostrar la disponibilidad de bicicletas y anclajes en tiempo real.



---

## 🚀 Características

* **Mapa Interactivo:** Visualización geográfica de todas las cicloestaciones mediante Plotly.
* **Disponibilidad en Vivo:** Consulta cuántas bicicletas y puertos libres hay en cada estación al instante.
* **Búsqueda por Estación:** Filtro rápido para encontrar estaciones específicas por nombre o ID.
* **Métricas Globales:** Resumen del estado general del sistema (Total de bicis, estaciones operativas, etc.).

## 🛠️ Tecnologías Utilizadas

* **Python 3.10+**
* **Streamlit:** Framework para la creación del tablero web.
* **Plotly:** Gráficos y mapas interactivos.
* **Pandas:** Procesamiento y limpieza de datos JSON.
* **Requests:** Conexión con la API de Lyft/EcoBici.

---

## 📦 Instalación y Configuración

Sigue estos pasos para ejecutar el proyecto de forma local:

1. **Clona el repositorio:**
   ```bash
   git clone [https://github.com/tu-usuario/ecobici-dashboard.git](https://github.com/tu-usuario/ecobici-dashboard.git)
   cd ecobici-dashboard
