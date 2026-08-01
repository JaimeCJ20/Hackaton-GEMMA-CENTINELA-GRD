import streamlit as st
import pandas as pd
import ollama
import folium
from streamlit_folium import st_folium
import random
import requests

# 1. Configuración de la página
st.set_page_config(layout="wide")
st.title("🚨 Panel de Riesgo CENEPRED / INDECI")
st.write("Sistema de alerta temprana impulsado por Gemma 2B y API de clima en vivo")

# 2. Cargar datos del Excel Oficial (Magia de Python)
@st.cache_data
def cargar_datos_oficiales():
    # Leer el Excel ignorando las 2 primeras filas de títulos feos
    df = pd.read_excel("1086_tabla.xlsx", sheet_name='Distritos_riesgo_274_MM', skiprows=2)
    
    # Ponerle nombres limpios a las columnas
    columnas_limpias = [
        'Departamento', 'Provincia', 'Ubigeo', 'Distrito', 'Cond_Territorio', 
        'Eventos_Masa', 'Val_Susceptib', 'Incid_Pobreza', 'Desnutricion', 
        'Analfabetismo', 'Val_Exposicion', 'Nivel_Riesgo', 'Poblacion_Expuesta', 
        'Viviendas', 'Hospitales_Riesgo', 'Colegios_Riesgo', 'Alumnos', 'Docentes'
    ]
    df.columns = columnas_limpias
    df = df.dropna(subset=['Distrito']) # Limpiar vacíos
    
    # HACK HACKATHON: Generar coordenadas automáticas cerca al centro de Perú
    df['Latitud'] = [-9.1899 + random.uniform(-3.0, 3.0) for _ in range(len(df))]
    df['Longitud'] = [-75.0151 + random.uniform(-3.0, 3.0) for _ in range(len(df))]
    
    return df

# Cargar la data ANTES de mostrar la interfaz
try:
    datos = cargar_datos_oficiales()
    # Tomar solo los primeros 100 para no saturar el mapa
    datos_mapa = datos.head(100)
except Exception as e:
    st.error("⚠️ Asegúrate de que '1086_tabla.xlsx' esté en la misma carpeta.")
    st.stop()

# 3. Diseño del Panel
col1, col2 = st.columns(2)

with col1:
    st.write("### Base de Datos CENEPRED (En Vivo)")
    # Mostramos solo columnas clave
    st.dataframe(datos[['Departamento', 'Distrito', 'Nivel_Riesgo', 'Poblacion_Expuesta', 'Colegios_Riesgo']])
    
    st.write("### Motor de Evacuación (Gemma AI + API en Vivo)")
    distrito_elegido = st.selectbox("Selecciona un distrito crítico:", datos['Distrito'])
    
    # Extraer data real de ese distrito
    info = datos[datos['Distrito'] == distrito_elegido].iloc[0]
    
    # --- AQUÍ ENTRA LA API EN TIEMPO REAL ---
    url_api = f"https://api.open-meteo.com/v1/forecast?latitude={info['Latitud']}&longitude={info['Longitud']}&current_weather=true"
    
    with st.spinner("Consultando satélites meteorológicos en tiempo real..."):
        try:
            respuesta_api = requests.get(url_api).json()
            clima_actual = respuesta_api['current_weather']
            temp = clima_actual['temperature']
            st.info(f"🌐 API EN VIVO: Temperatura actual en {distrito_elegido}: {temp}°C")
        except:
            temp = "Desconocida (Error de red)"
            st.warning("No se pudo conectar a la API del clima.")
    
    st.warning(f"⚠️ Alerta en {info['Distrito']}: Nivel de Riesgo {info['Nivel_Riesgo']}. Población expuesta: {int(info['Poblacion_Expuesta'])}.")

    if st.button("Generar Alerta con Gemma"):
        with st.spinner("Gemma procesando el impacto social..."):
            prompt = f"Eres Director de Defensa Civil de Perú. Riesgo nivel {info['Nivel_Riesgo']} por huaicos en {info['Distrito']}. Hay {int(info['Poblacion_Expuesta'])} personas en peligro. Temperatura actual: {temp}°C. Escribe un SMS de evacuación urgente y dramático de máximo 40 palabras."
            
            respuesta = ollama.chat(model='gemma:2b', messages=[
                {'role': 'user', 'content': prompt}
            ])
            st.success(respuesta['message']['content'])

with col2:
    st.write("### Mapa Geoespacial de Vulnerabilidad")
    # Centrar el mapa en Perú
    mapa = folium.Map(location=[-9.18, -75.01], zoom_start=5)
    
    # Dibujar los pines de los distritos
    for idx, fila in datos_mapa.iterrows():
        color = "red" if fila['Nivel_Riesgo'] in ['MA', 'Muy Alto'] else "orange"
        folium.Marker(
            [fila['Latitud'], fila['Longitud']],
            popup=f"Población en riesgo: {fila['Poblacion_Expuesta']}",
            tooltip=fila['Distrito'],
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(mapa)
    
    st_folium(mapa, width=500, height=450)