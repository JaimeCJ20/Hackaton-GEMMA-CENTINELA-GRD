import streamlit as st
import pandas as pd
import ollama
import folium
import requests
import json
import math
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# 1. Configuración de la página
st.set_page_config(layout="wide")
st.title("🚨 Centinela GRD: Sistema Multi-Amenaza Híbrido")
st.write("Impulsado por Gemma 2B (Edge AI) + APIs + Datos Oficiales (CENEPRED/IGP)")

# ==========================================
# FUNCIONES DE CARGA DE DATOS (CACHED)
# ==========================================
@st.cache_data
def cargar_datos_clima():
    return pd.read_csv("all_189.csv")

@st.cache_data
def cargar_geojson():
    with open("distritos.geojson", encoding="utf-8") as f:
        return json.load(f)

def centroide(geom):
    if not geom or 'type' not in geom: return None, None
    try:
        if geom['type'] == 'Polygon':
            anillos = [geom['coordinates'][0]]
        elif geom['type'] == 'MultiPolygon':
            anillos = [p[0] for p in geom['coordinates']]
        else: return None, None
        pts = [p for a in anillos for p in a]
        if not pts: return None, None
        return sum(p[1] for p in pts)/len(pts), sum(p[0] for p in pts)/len(pts)
    except: return None, None

@st.cache_data
def cargar_datos_oficiales_sismo():
    df = pd.read_excel("1086_tabla.xlsx", sheet_name='Distritos_riesgo_274_MM', skiprows=2)
    df.columns = [
        'Departamento', 'Provincia', 'Ubigeo', 'Distrito', 'Cond_Territorio',
        'Eventos_Masa', 'Val_Susceptib', 'Incid_Pobreza', 'Desnutricion',
        'Analfabetismo', 'Val_Exposicion', 'Nivel_Riesgo', 'Poblacion_Expuesta',
        'Viviendas', 'Hospitales_Riesgo', 'Colegios_Riesgo', 'Alumnos', 'Docentes'
    ]
    df = df.dropna(subset=['Distrito'])
    df['Ubigeo'] = df['Ubigeo'].astype(int).astype(str).str.zfill(6)
    geo = cargar_geojson()
    coords = {}
    for f in geo['features']:
        lat, lon = centroide(f.get('geometry'))
        if lat is not None: coords[f['properties']['IDDIST']] = (lat, lon)
    df['Latitud'] = df['Ubigeo'].map(lambda u: coords.get(u, (None, None))[0])
    df['Longitud'] = df['Ubigeo'].map(lambda u: coords.get(u, (None, None))[1])
    return df

@st.cache_data
def cargar_sismos():
    df = pd.read_excel("datos-sismicos_Instrumental_1960-01-01_2026-07-31.xlsx")
    df = df.rename(columns={'latitud (º)': 'lat', 'longitud (º)': 'lon', 'magnitud (M)': 'mag', 'profundidad (km)': 'prof'})
    return df.dropna(subset=['lat', 'lon', 'mag'])

# ==========================================
# INICIALIZACIÓN Y MANEJO DE ERRORES DE DATOS
# ==========================================
try:
    datos_clima = cargar_datos_clima()
except:
    st.error("⚠️ Falta el archivo 'all_189.csv' en la carpeta.")
    datos_clima = pd.DataFrame()

try:
    datos_sismo = cargar_datos_oficiales_sismo()
    sismos = cargar_sismos()
except:
    st.warning("⚠️ Faltan archivos sísmicos (1086_tabla.xlsx, distritos.geojson, o datos-sismicos_...xlsx)")
    datos_sismo, sismos = pd.DataFrame(), pd.DataFrame()

# ==========================================
# INTERFAZ SEPARADA POR PESTAÑAS (TABS)
# ==========================================
tab_clima, tab_sismo = st.tabs(["🌧️ Amenaza Hidrometeorológica (Edge AI)", "🌋 Amenaza Sísmica (IGP)"])

# ---------------------------------------------------------
# PESTAÑA 1: HIDROMETEOROLÓGICO HÍBRIDO
# ---------------------------------------------------------
with tab_clima:
    col1, col2 = st.columns(2)
    with col1:
        if not datos_clima.empty:
            st.write("### Motor de Evacuación (Gemma AI + Sensores en Vivo)")
            opciones = ["🌍 Vista General del Perú"] + datos_clima['Distrito'].tolist()
            distrito_elegido = st.selectbox("Selecciona un distrito crítico:", opciones, key="sel_clima")
            
            lat_centro, lon_centro, zoom_mapa = -9.18, -75.01, 5
            
            if distrito_elegido != "🌍 Vista General del Perú":
                info = datos_clima[datos_clima['Distrito'] == distrito_elegido].iloc[0]
                lat_centro, lon_centro, zoom_mapa = info['Latitud'], info['Longitud'], 12 
                
                # FASE 1: NUBE (API OPEN-METEO)
                url_api = f"https://api.open-meteo.com/v1/forecast?latitude={lat_centro}&longitude={lon_centro}&current_weather=true"
                try:
                    respuesta_api = requests.get(url_api).json()['current_weather']
                    temp, viento = respuesta_api['temperature'], respuesta_api['windspeed']
                    condicion = "Lluvia/Tormenta 🌧️" if respuesta_api['weathercode'] > 50 else "Despejado/Nublado ☁️"
                    st.write("#### 📡 Nube: Condiciones Climáticas")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Temperatura", f"{temp} °C")
                    m2.metric("Viento", f"{viento} km/h")
                    m3.metric("Estado", condicion)
                except:
                    temp, condicion = "N/A", "N/A"
                
                st.warning(f"⚠️ Alerta Base: Riesgo {info['Nivel_Riesgo']}. Población expuesta: {int(info['Poblacion_Expuesta'])}.")

                # FASE 2: EDGE AI (SIMULADOR DE TELEMETRÍA)
                st.write("---")
                st.write("#### 🎛️ Edge: Simulador de Sensores IoT")
                nivel_sensor_mm = st.slider("Precipitación detectada (mm/h)", 0, 150, 10)
                
                if nivel_sensor_mm >= 75:
                    st.error(f"🚨 PELIGRO INMINENTE: Sensor en {nivel_sensor_mm} mm/h.")
                    if st.button("Generar Alerta de Evacuación (Offline)"):
                        with st.spinner("Gemma procesando sin internet..."):
                            prompt = f"Eres INDECI. Riesgo inminente por {nivel_sensor_mm}mm/h de lluvia en {info['Distrito']}. Vidas en peligro: {int(info['Poblacion_Expuesta'])}. Colegios: {int(info['Colegios_Riesgo'])}. Redacta un SMS de evacuación urgente (40 palabras). Prioriza colegios."
                            respuesta = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
                            st.success(respuesta['message']['content'])
                else:
                    st.success("✅ Monitoreo estable. Gemma en reposo.")
            else:
                st.info("👆 Selecciona un distrito para activar la IA.")

    with col2:
        st.write("### Mapa Geoespacial de Riesgos")
        mapa_clima = folium.Map(location=[lat_centro, lon_centro], zoom_start=zoom_mapa)
        if not datos_clima.empty:
            for idx, fila in datos_clima.iterrows():
                color = "darkred" if fila['Nivel_Riesgo'] == 'MA' else "orange"
                folium.Marker([fila['Latitud'], fila['Longitud']], popup=fila['Distrito'], icon=folium.Icon(color=color)).add_to(mapa_clima)
        st_folium(mapa_clima, width=500, height=550, key="mapa_clima")

# ---------------------------------------------------------
# PESTAÑA 2: AMENAZA SÍSMICA (CÓDIGO INTEGRADO)
# ---------------------------------------------------------
with tab_sismo:
    if not sismos.empty and not datos_sismo.empty:
        col3, col4 = st.columns([1, 2])
        with col3:
            magnitud = st.number_input("Magnitud a consultar", 0.0, 9.0, 7.0, 0.1)
            solo_superficiales = st.checkbox("Solo sismos superficiales (< 70 km)")
            sismos_filt = sismos[sismos['mag'].round(1) == round(magnitud, 1)]
            if solo_superficiales: sismos_filt = sismos_filt[sismos_filt['prof'] < 70]
            
            st.metric(f"Sismos de mag {magnitud:.1f}", f"{len(sismos_filt)}")
            if len(sismos_filt) > 0:
                st.write("**Registros**")
                st.dataframe(sismos_filt[['fecha UTC', 'mag', 'prof']].head(5), hide_index=True)
                
                st.divider()
                radio_km = st.number_input("Radio de análisis (km)", 10, 300, 50, 10)
                afectados = set()
                dist_validos = datos_sismo.dropna(subset=['Latitud'])
                for _, s in sismos_filt.iterrows():
                    for _, d in dist_validos.iterrows():
                        dx = (d['Longitud'] - s['lon']) * 111 * math.cos(math.radians(d['Latitud']))
                        dy = (d['Latitud'] - s['lat']) * 111
                        if math.hypot(dx, dy) <= radio_km: afectados.add(d['Ubigeo'])
                exp = dist_validos[dist_validos['Ubigeo'].isin(afectados)]
                
                poblacion_afectada = int(exp['Poblacion_Expuesta'].sum())
                st.metric("Personas alcanzadas (Riesgo estimado)", f"{poblacion_afectada:,}")
                
                # BOTÓN DE GEMMA SÍSMICO CON EL MODELO CORRECTO
                if st.button("Generar Alerta Sísmica con Gemma"):
                    with st.spinner("Gemma procesando el reporte sísmico offline..."):
                        prompt = f"Eres Defensa Civil. Se simula un sismo de magnitud {magnitud}. Población en el radio de impacto: {poblacion_afectada} personas. Redacta un SMS de emergencia de máximo 40 palabras indicando protocolos de seguridad sísmica inmediatos."
                        
                        # Uso estricto de gemma:2b
                        respuesta = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
                        st.success(respuesta['message']['content'])
            else:
                st.info("No hay sismos con esos filtros.")
        
        with col4:
            st.write("### Mapa de Calor Sísmico")
            mapa_sismo = folium.Map(location=[-9.18, -75.01], zoom_start=5)
            if len(sismos_filt) > 0:
                HeatMap(data=sismos_filt[['lat', 'lon', 'mag']].values.tolist(), radius=12, blur=18).add_to(mapa_sismo)
            st_folium(mapa_sismo, width=600, height=500, key="mapa_sismico_hm")
    else:
        st.error("Sube los archivos del catálogo sísmico para ver esta sección.")