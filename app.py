import streamlit as st
import pandas as pd
import ollama
import folium
from streamlit_folium import st_folium
import requests

# 1. Configuración de la página
st.set_page_config(layout="wide")
st.title("🚨 Panel de Riesgo CENEPRED / INDECI")
st.write("Sistema de alerta temprana impulsado por Gemma 2B (Data Oficial Geolocalizada)")

# 2. Cargar los 189 distritos
@st.cache_data
def cargar_datos_reales():
    return pd.read_csv("all_189.csv")

try:
    datos = cargar_datos_reales()
except Exception as e:
    st.error("⚠️ Asegúrate de haber guardado el archivo 'distritos_reales.csv'.")
    st.stop()

# 3. Diseño del Panel
col1, col2 = st.columns(2)

with col1:
    st.write("### Zonas Críticas (Riesgo Nacional)")
    st.dataframe(datos[['Departamento', 'Distrito', 'Nivel_Riesgo', 'Poblacion_Expuesta']])
    
    # Confirmación visual del total de datos
    st.success(f"✅ Total de zonas monitoreadas: {len(datos)} distritos.")
    
    st.write("### Motor de Evacuación (Gemma AI + API en Vivo)")
    
    opciones = ["🌍 Vista General del Perú"] + datos['Distrito'].tolist()
    distrito_elegido = st.selectbox("Selecciona un distrito crítico:", opciones)
    
    # Variables por defecto para centrar en Perú
    lat_centro = -9.18
    lon_centro = -75.01
    zoom_mapa = 5
    
    if distrito_elegido != "🌍 Vista General del Perú":
        info = datos[datos['Distrito'] == distrito_elegido].iloc[0]
        
        # Volar a las coordenadas reales
        lat_centro = info['Latitud']
        lon_centro = info['Longitud']
        zoom_mapa = 12 
        
        # Conexión a la API del Clima
        url_api = f"https://api.open-meteo.com/v1/forecast?latitude={lat_centro}&longitude={lon_centro}&current_weather=true"
        
        with st.spinner("Consultando satélites meteorológicos en tiempo real..."):
            try:
                respuesta_api = requests.get(url_api).json()
                temp = respuesta_api['current_weather']['temperature']
                st.info(f"🌐 API EN VIVO: Temperatura actual en {distrito_elegido}: {temp}°C")
            except:
                temp = "Desconocida (Error de red)"
                st.warning("No se pudo conectar a la API del clima.")
        
        st.warning(f"⚠️ Alerta en {info['Distrito']}: Nivel de Riesgo {info['Nivel_Riesgo']}. Población expuesta: {int(info['Poblacion_Expuesta'])}.")

        if st.button("Generar Alerta con Gemma"):
            with st.spinner("Gemma procesando el impacto social..."):
                prompt = f"Eres Defensa Civil. Riesgo {info['Nivel_Riesgo']} inminente en {info['Distrito']}, {info['Departamento']}. {int(info['Poblacion_Expuesta'])} personas y {int(info['Colegios_Riesgo'])} colegios en peligro. Temperatura: {temp}°C. Escribe un SMS de evacuación urgente de máximo 40 palabras."
                
                respuesta = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
                st.success(respuesta['message']['content'])
    else:
        st.info("👆 Selecciona un distrito para activar la IA y volar al lugar de la emergencia.")

with col2:
    st.write("### Mapa Geoespacial de Riesgos")
    
    mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=zoom_mapa)
    
    # Pines reales en las ciudades
    for idx, fila in datos.iterrows():
        # Lógica de color: Rojo oscuro para 'MA', Naranja para 'A'
        color = "darkred" if fila['Nivel_Riesgo'] == 'MA' else "orange"
        folium.Marker(
            [fila['Latitud'], fila['Longitud']],
            popup=f"{fila['Distrito']} - Riesgo: {fila['Nivel_Riesgo']} | Población: {fila['Poblacion_Expuesta']} | Colegios: {fila['Colegios_Riesgo']}",
            tooltip=fila['Distrito'],
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(mapa)
    
    st_folium(mapa, width=500, height=450)