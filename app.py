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
    st.error("⚠️ Asegúrate de haber guardado el archivo 'all_189.csv' en esta carpeta.")
    st.stop()

# 3. Diseño del Panel
col1, col2 = st.columns(2)

with col1:
    st.write("### Zonas Críticas (Riesgo Nacional)")
    st.dataframe(datos[['Departamento', 'Distrito', 'Nivel_Riesgo', 'Poblacion_Expuesta']])
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
        
        # Conexión a la API del Clima (Mejorada)
        url_api = f"https://api.open-meteo.com/v1/forecast?latitude={lat_centro}&longitude={lon_centro}&current_weather=true"
        
        with st.spinner("Consultando satélites meteorológicos en tiempo real..."):
            try:
                respuesta_api = requests.get(url_api).json()
                clima = respuesta_api['current_weather']
                
                # Extrayendo la información vital
                temp = clima['temperature']
                viento = clima['windspeed']
                codigo_clima = clima['weathercode']
                
                # Traductor de códigos meteorológicos WMO
                if codigo_clima in [0, 1, 2, 3]: condicion = "Despejado / Nublado ☁️"
                elif codigo_clima in [45, 48]: condicion = "Neblina 🌫️"
                elif codigo_clima in [51, 53, 55, 61, 63, 65, 80, 81, 82]: condicion = "Lluvia 🌧️"
                elif codigo_clima in [95, 96, 99]: condicion = "Tormenta ⛈️"
                else: condicion = "Variable 🌥️"

                # Mostrar métricas visuales en pantalla
                st.write("#### 📡 Condiciones Climáticas (Satélite)")
                m1, m2, m3 = st.columns(3)
                m1.metric("Temperatura", f"{temp} °C")
                m2.metric("Vel. Viento", f"{viento} km/h")
                m3.metric("Estado", condicion)

            except:
                temp, viento, condicion = "N/A", "N/A", "N/A"
                st.warning("No se pudo conectar a la API del clima.")
        
        st.warning(f"⚠️ Alerta en {info['Distrito']}: Nivel de Riesgo {info['Nivel_Riesgo']}. Población expuesta: {int(info['Poblacion_Expuesta'])}.")

        if st.button("Generar Alerta con Gemma"):
            with st.spinner("Gemma procesando el impacto social..."):
                # ¡Le pasamos TODO a Gemma para que razone!
                prompt = f"Eres Defensa Civil. Riesgo {info['Nivel_Riesgo']} inminente en {info['Distrito']}, {info['Departamento']}. {int(info['Poblacion_Expuesta'])} personas y {int(info['Colegios_Riesgo'])} colegios en peligro. El clima actual es de {temp}°C, con {condicion} y vientos de {viento}km/h. Escribe un SMS de evacuación urgente y específico de máximo 40 palabras."
                
                respuesta = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
                st.success(respuesta['message']['content'])
    else:
        st.info("👆 Selecciona un distrito para activar la IA y volar al lugar de la emergencia.")

with col2:
    st.write("### Mapa Geoespacial de Riesgos")
    
    mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=zoom_mapa)
    
    # Pines reales en las ciudades
    for idx, fila in datos.iterrows():
        color = "darkred" if fila['Nivel_Riesgo'] == 'MA' else "orange"
        folium.Marker(
            [fila['Latitud'], fila['Longitud']],
            popup=f"{fila['Distrito']} - Riesgo: {fila['Nivel_Riesgo']}",
            tooltip=fila['Distrito'],
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(mapa)
    
    # Altura del mapa aumentada un poco para cuadrar con el nuevo panel
    st_folium(mapa, width=500, height=550)