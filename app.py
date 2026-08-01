import qrcode
from io import BytesIO
import streamlit as st
import pandas as pd
import ollama
import folium
import requests
import json
import numpy as np
import math
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# 1. Configuración principal de la página (DEBE IR PRIMERO)
st.set_page_config(layout="wide", page_title="Centinela GRD Híbrido")

# ==========================================
# FUNCIONES DE CARGA DE DATOS COMPARTIDAS
# ==========================================
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
def cargar_datos_oficiales():
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

@st.cache_data
def cargar_datos_clima():
    return pd.read_csv("all_189.csv")


# ==========================================
# MENÚ DE NAVEGACIÓN LATERAL
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Escudo_nacional_del_Per%C3%BA.svg/1200px-Escudo_nacional_del_Per%C3%BA.svg.png", width=100)
st.sidebar.title("Navegación del Sistema")
modulo_seleccionado = st.sidebar.radio(
    "Selecciona el módulo a visualizar:",
    ["Módulo 1: Centinela Básico (2 Pestañas)", "Módulo 2: Centinela Avanzado (4 Pestañas)"]
)

# ==========================================
# MÓDULO 1: CÓDIGO ORIGINAL (2 PESTAÑAS)
# ==========================================
if modulo_seleccionado == "Módulo 1: Centinela Básico (2 Pestañas)":
    st.title("🚨 Centinela GRD: Sistema Multi-Amenaza Híbrido (Módulo 1)")
    st.write("Impulsado por Gemma 2B (Edge AI) + APIs + Datos Oficiales (CENEPRED/IGP)")

    try:
        datos_oficiales = cargar_datos_oficiales()
        sismos = cargar_sismos()
    except:
        st.error("⚠️ Faltan archivos clave (1086_tabla.xlsx, distritos.geojson, o datos-sismicos_...xlsx)")
        datos_oficiales, sismos = pd.DataFrame(), pd.DataFrame()

    tab_clima, tab_sismo = st.tabs(["🌧️ Amenaza Hidrometeorológica (Edge AI)", "🌋 Amenaza Sísmica (IGP)"])

    with tab_clima:
        col1, col2 = st.columns(2)
        with col1:
            if not datos_oficiales.empty:
                st.write("### Motor de Evacuación (Gemma AI + Sensores en Vivo)")
                
                modo_offline = st.toggle("🔴 SIMULAR CAÍDA DE INTERNET (Modo Supervivencia / Edge AI)", key="toggle_m1")
                if modo_offline:
                    st.error("📡 ALERTA: Conexión a internet perdida. Operando 100% Offline con Gemma 2B local.")

                click_en_mapa = None
                if "mapa_clima_m1" in st.session_state and st.session_state["mapa_clima_m1"].get("last_object_clicked"):
                    lat_c = st.session_state["mapa_clima_m1"]["last_object_clicked"]["lat"]
                    lon_c = st.session_state["mapa_clima_m1"]["last_object_clicked"]["lng"]
                    df_temp = datos_oficiales.dropna(subset=['Latitud', 'Longitud']).copy()
                    df_temp['dist'] = ((df_temp['Latitud'] - lat_c)**2 + (df_temp['Longitud'] - lon_c)**2)
                    idxmin = df_temp['dist'].idxmin()
                    if df_temp.loc[idxmin, 'dist'] < 0.005: 
                        click_en_mapa = df_temp.loc[idxmin]

                if click_en_mapa is not None and "ignorar_click_m1" in st.session_state:
                    if st.session_state.ignorar_click_m1 == st.session_state["mapa_clima_m1"]["last_object_clicked"]:
                        click_en_mapa = None 
                        
                if click_en_mapa is not None:
                    st.success(f"📍 Has seleccionado **{click_en_mapa['Distrito']}** desde el mapa.")
                    if st.button("❌ Restaurar filtros", key="restaurar_m1"):
                        st.session_state.ignorar_click_m1 = st.session_state["mapa_clima_m1"]["last_object_clicked"]
                        st.rerun() 

                col_a, col_b, col_c = st.columns(3)
                lista_deptos = ["🌍 Todo el Perú"] + sorted(datos_oficiales['Departamento'].unique().tolist())
                depto_elegido = col_a.selectbox("1. Departamento:", lista_deptos, key="depto_m1")
                
                if depto_elegido != "🌍 Todo el Perú":
                    df_prov = datos_oficiales[datos_oficiales['Departamento'] == depto_elegido]
                    lista_provs = ["Todas"] + sorted(df_prov['Provincia'].unique().tolist())
                    prov_elegida = col_b.selectbox("2. Provincia:", lista_provs, key="prov_m1")
                    
                    if prov_elegida != "Todas":
                        df_dist = df_prov[df_prov['Provincia'] == prov_elegida]
                    else:
                        df_dist = df_prov
                    opciones_distrito = ["Seleccionar Distrito..."] + sorted(df_dist['Distrito'].tolist())
                else:
                    df_dist = datos_oficiales
                    prov_elegida = col_b.selectbox("2. Provincia:", ["Todas"], disabled=True, key="prov_m1_dis")
                    opciones_distrito = ["🌍 Vista General"] + sorted(df_dist['Distrito'].tolist())
                    
                distrito_elegido = col_c.selectbox("3. Distrito:", opciones_distrito, key="sel_clima_m1")
                
                if click_en_mapa is not None:
                    distrito_elegido = click_en_mapa['Distrito']

                lat_centro, lon_centro, zoom_mapa = -9.18, -75.01, 5
                datos_mapa = df_dist 
                
                if distrito_elegido not in ["🌍 Vista General", "Seleccionar Distrito..."]:
                    info = datos_oficiales[datos_oficiales['Distrito'] == distrito_elegido].iloc[0]
                    if pd.isna(info['Latitud']):
                        st.error("Coordenadas no encontradas para este distrito en el GeoJSON.")
                    else:
                        lat_centro, lon_centro, zoom_mapa = info['Latitud'], info['Longitud'], 12 
                        datos_mapa = pd.DataFrame([info])
                    
                    if not modo_offline:
                        url_api = f"https://api.open-meteo.com/v1/forecast?latitude={lat_centro}&longitude={lon_centro}&current_weather=true"
                        try:
                            respuesta_api = requests.get(url_api).json()['current_weather']
                            temp, viento = respuesta_api['temperature'], respuesta_api['windspeed']
                            condicion = "Lluvia/Tormenta 🌧️" if respuesta_api['weathercode'] > 50 else "Despejado/Nublado ☁️"
                            st.write("#### 📡 Nube: Condiciones en Vivo")
                        except:
                            temp, viento, condicion = "N/A", "N/A", "N/A"
                    else:
                        temp, viento, condicion = "22.5 (Caché)", "15 (Caché)", "Lluvias intensas 🌧️ (Caché)"
                        st.write("#### 📡 Edge: Última telemetría guardada")

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Temperatura", f"{temp} °C")
                    m2.metric("Viento", f"{viento} km/h")
                    m3.metric("Estado", condicion)
                    
                    st.warning(f"⚠️ Alerta Base: Riesgo {info['Nivel_Riesgo']}. Población expuesta: {int(info['Poblacion_Expuesta'])}.")
                    st.write("---")
                    st.write("#### 🎛️ Edge: Simulador de Sensores IoT")
                    nivel_sensor_mm = st.slider("Precipitación detectada (mm/h)", 0, 150, 85 if modo_offline else 10, key="slider_m1")
                    
                    if nivel_sensor_mm >= 75:
                        st.error(f"🚨 PELIGRO INMINENTE: Sensor local registra {nivel_sensor_mm} mm/h.")
                        if st.button("Generar Alerta de Evacuación Autónoma con Gemma", key="btn_evac_m1"):
                            with st.spinner("Gemma procesando protocolo de crisis offline..."):
                                prompt = f"""
                                Eres el Sistema Automático de Defensa Civil (INDECI) de Perú.
                                ESTADO: Alerta Roja (Modo Emergencia sin internet).
                                PARÁMETROS DEL DESASTRE:
                                - Ubicación: Distrito de {info['Distrito']} ({info['Departamento']})
                                - Riesgo Oficial: {info['Nivel_Riesgo']} (Muy Alto/Alto)
                                - Clima actual: {temp}°C con {condicion}
                                - Telemetría: Lluvias torrenciales críticas de {nivel_sensor_mm} mm/h. Desborde inminente.
                                - Impacto Humano: {int(info['Poblacion_Expuesta'])} ciudadanos en peligro.
                                - Infraestructura: {int(info['Colegios_Riesgo'])} colegios en la zona cero.
                                INSTRUCCIÓN ESTRICTA:
                                Redacta un SMS de alerta de evacuación de MÁXIMO 40 palabras. 
                                1. Evacuar a zonas altas.
                                """
                                respuesta = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
                                texto_alerta = respuesta['message']['content']
                                st.warning("📲 MENSAJE SMS GENERADO PARA TRANSMISIÓN:")
                                st.success(texto_alerta)
                                
                                st.write("---")
                                st.write("📸 **Simulación en vivo:** Escanea este QR para leer la alerta en tu celular")
                                qr = qrcode.make(texto_alerta)
                                img_buffer = BytesIO()
                                qr.save(img_buffer, format="PNG")
                                st.image(img_buffer, width=250)
                    else:
                        st.success("✅ Monitoreo estable. El sensor no registra peligro. Gemma AI en modo de ahorro de energía.")
                else:
                    st.info("👆 Selecciona un distrito para activar la IA o haz click en un punto del mapa interactivo.")

        with col2:
            st.write("### Mapa de Calor y Puntos de Monitoreo")
            mapa_clima = folium.Map(location=[lat_centro, lon_centro], zoom_start=zoom_mapa)
            if not datos_mapa.empty:
                df_validos = datos_mapa.dropna(subset=['Latitud', 'Longitud'])
                if not df_validos.empty:
                    coords_calor = df_validos[['Latitud', 'Longitud']].values.tolist()
                    HeatMap(
                        data=coords_calor, radius=18, blur=15, min_opacity=0.4,
                        gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1.0: 'red'}
                    ).add_to(mapa_clima)
                    
                    for idx, fila in df_validos.iterrows():
                        folium.CircleMarker(
                            location=[fila['Latitud'], fila['Longitud']],
                            radius=5, color="black", weight=1, fill=True, fill_color="black", fill_opacity=0.5,
                            tooltip=f"{fila['Distrito']} (Click para monitorear)"
                        ).add_to(mapa_clima)
                    
                    if distrito_elegido not in ["🌍 Vista General", "Seleccionar Distrito..."]:
                        info_pin = df_validos.iloc[0]
                        folium.Marker(
                            [info_pin['Latitud'], info_pin['Longitud']], 
                            popup=f"{info_pin['Distrito']} - Riesgo: {info_pin['Nivel_Riesgo']}", 
                            icon=folium.Icon(color="darkred", icon="info-sign")
                        ).add_to(mapa_clima)

            st_folium(mapa_clima, width=500, height=650, key="mapa_clima_m1", returned_objects=["last_object_clicked"])

    with tab_sismo:
        if not sismos.empty and not datos_oficiales.empty:
            col3, col4 = st.columns([1, 2])
            with col3:
                magnitud = st.number_input("Magnitud a consultar", 0.0, 9.0, 7.0, 0.1, key="mag_m1")
                solo_superficiales = st.checkbox("Solo sismos superficiales (< 70 km)", key="sup_m1")
                sismos_filt = sismos[sismos['mag'].round(1) == round(magnitud, 1)]
                if solo_superficiales: sismos_filt = sismos_filt[sismos_filt['prof'] < 70]
                
                st.metric(f"Sismos históricos de mag {magnitud:.1f}", f"{len(sismos_filt)}")
                if len(sismos_filt) > 0:
                    st.write("**Registros**")
                    st.dataframe(sismos_filt[['fecha UTC', 'mag', 'prof']].head(5), hide_index=True)
                    st.divider()
                    radio_km = st.number_input("Radio de impacto proyectado (km)", 10, 300, 50, 10, key="rad_m1")
                    afectados = set()
                    dist_validos = datos_oficiales.dropna(subset=['Latitud'])
                    for _, s in sismos_filt.iterrows():
                        for _, d in dist_validos.iterrows():
                            dx = (d['Longitud'] - s['lon']) * 111 * math.cos(math.radians(d['Latitud']))
                            dy = (d['Latitud'] - s['lat']) * 111
                            if math.hypot(dx, dy) <= radio_km: afectados.add(d['Ubigeo'])
                    exp = dist_validos[dist_validos['Ubigeo'].isin(afectados)]
                    poblacion_afectada = int(exp['Poblacion_Expuesta'].sum())
                    st.metric("Personas alcanzadas (Riesgo estimado)", f"{poblacion_afectada:,}")
                    
                    if st.button("Generar Alerta Sísmica con Gemma", type="primary", key="btn_sismo_m1"):
                        with st.spinner("Gemma procesando el reporte sísmico en el borde..."):
                            prompt = f"Eres Defensa Civil. Se simula un sismo de magnitud {magnitud}. Población en el radio de impacto: {poblacion_afectada} personas. Redacta un SMS de emergencia de máximo 40 palabras indicando protocolos de seguridad sísmica inmediatos."
                            respuesta = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
                            st.success(respuesta['message']['content'])
                else:
                    st.info("No hay sismos con esos filtros.")
            with col4:
                st.write("### Mapa de Calor Sísmico")
                mapa_sismo = folium.Map(location=[-9.18, -75.01], zoom_start=5)
                if len(sismos_filt) > 0:
                    HeatMap(data=sismos_filt[['lat', 'lon', 'mag']].values.tolist(), radius=12, blur=18).add_to(mapa_sismo)
                st_folium(mapa_sismo, width=600, height=500, key="mapa_sismico_hm_m1", returned_objects=[])

# ==========================================
# MÓDULO 2: SEGUNDO CÓDIGO (4 PESTAÑAS)
# ==========================================
elif modulo_seleccionado == "Módulo 2: Centinela Avanzado (4 Pestañas)":
    st.title("🚨 Centinela GRD: Sistema Multi-Amenaza Híbrido (Módulo 2)")
    st.write("Impulsado por Gemma 2B (Edge AI) + APIs + Datos Oficiales (CENEPRED/IGP)")

    try:
        datos_clima = cargar_datos_clima()
    except:
        st.error("⚠️ Falta el archivo 'all_189.csv' en la carpeta.")
        datos_clima = pd.DataFrame()

    try:
        datos_sismo = cargar_datos_oficiales()
        sismos = cargar_sismos()
    except:
        st.warning("⚠️ Faltan archivos sísmicos (1086_tabla.xlsx, distritos.geojson, o datos-sismicos_...xlsx)")
        datos_sismo, sismos = pd.DataFrame(), pd.DataFrame()

    tab_clima, tab_sismo, tab_lagunas, tab_agente = st.tabs([
        "🌊 Amenaza Hidrometeorológica",
        "🌋 Amenaza Sísmica",
        "🔴 Lagunas Sísmicas",
        "🤖 Consulta al agente"
    ])

    with tab_clima:
        col1, col2 = st.columns(2)
        with col1:
            if not datos_clima.empty:
                st.write("### Motor de Evacuación (Gemma AI + Sensores en Vivo)")
                opciones = ["🌍 Vista General del Perú"] + datos_clima['Distrito'].tolist()
                distrito_elegido = st.selectbox("Selecciona un distrito crítico:", opciones, key="sel_clima_m2")
                
                lat_centro, lon_centro, zoom_mapa = -9.18, -75.01, 5
                
                if distrito_elegido != "🌍 Vista General del Perú":
                    info = datos_clima[datos_clima['Distrito'] == distrito_elegido].iloc[0]
                    lat_centro, lon_centro, zoom_mapa = info['Latitud'], info['Longitud'], 12 
                    
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
                    st.write("---")
                    st.write("#### 🎛️ Edge: Simulador de Sensores IoT")
                    nivel_sensor_mm = st.slider("Precipitación detectada (mm/h)", 0, 150, 10, key="slider_m2")
                    
                    if nivel_sensor_mm >= 75:
                        st.error(f"🚨 PELIGRO INMINENTE: Sensor en {nivel_sensor_mm} mm/h.")
                        if st.button("Generar Alerta de Evacuación (Offline)", key="btn_evac_m2"):
                            with st.spinner("Gemma procesando sin internet..."):
                                prompt = f"Eres INDECI. Riesgo inminente por {nivel_sensor_mm}mm/h de lluvia en {info['Distrito']}. Vidas en peligro: {int(info['Poblacion_Expuesta'])}. Colegios: {int(info['Colegios_Riesgo'])}. Redacta un SMS de evacuación urgente (40 palabras). Prioriza colegios."
                                # Cambiado estrictamente a gemma:2b
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
            st_folium(mapa_clima, width=500, height=550, key="mapa_clima_m2")

    with tab_sismo:
        if not sismos.empty and not datos_sismo.empty:
            col3, col4 = st.columns([1, 2])
            with col3:
                magnitud = st.number_input("Magnitud a consultar", 0.0, 9.0, 7.0, 0.1, key="mag_m2")
                solo_superficiales = st.checkbox("Solo sismos superficiales (< 70 km)", key="sup_m2")
                sismos_filt = sismos[sismos['mag'].round(1) == round(magnitud, 1)]
                if solo_superficiales: sismos_filt = sismos_filt[sismos_filt['prof'] < 70]
                
                st.metric(f"Sismos de mag {magnitud:.1f}", f"{len(sismos_filt)}")
                if len(sismos_filt) > 0:
                    st.write("**Registros**")
                    st.dataframe(sismos_filt[['fecha UTC', 'mag', 'prof']].head(5), hide_index=True)
                    st.divider()
                    radio_km = st.number_input("Radio de análisis (km)", 10, 300, 50, 10, key="rad_m2")
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
                    
                    if st.button("Generar Alerta Sísmica con Gemma", key="btn_sismo_m2"):
                        with st.spinner("Gemma procesando el reporte sísmico offline..."):
                            prompt = f"Eres Defensa Civil. Se simula un sismo de magnitud {magnitud}. Población en el radio de impacto: {poblacion_afectada} personas. Redacta un SMS de emergencia de máximo 40 palabras indicando protocolos de seguridad sísmica inmediatos."
                            # Cambiado estrictamente a gemma:2b
                            respuesta = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
                            st.success(respuesta['message']['content'])
                else:
                    st.info("No hay sismos con esos filtros.")
        
            with col4:
                st.write("### Mapa de Calor Sísmico")
                mapa_sismo = folium.Map(location=[-9.18, -75.01], zoom_start=5)
                if len(sismos_filt) > 0:
                    HeatMap(data=sismos_filt[['lat', 'lon', 'mag']].values.tolist(), radius=12, blur=18).add_to(mapa_sismo)
                st_folium(mapa_sismo, width=600, height=500, key="mapa_sismico_hm_m2")
        else:
            st.error("Sube los archivos del catálogo sísmico para ver esta sección.")

    with tab_lagunas:
        st.caption("Historial y silencio sísmico por distrito — Fuente: IGP (1960–2026)")
        st.info("⚠️ Esto **no es una predicción**. Analiza el historial sísmico de la zona y cuánto tiempo lleva sin liberar energía.")

        @st.cache_data
        def cargar_todos_distritos():
            geo = cargar_geojson()
            filas = []
            for f in geo['features']:
                lat, lon = centroide(f.get('geometry'))
                if lat is None: continue
                p = f['properties']
                filas.append({
                    'etiqueta': f"{p['NOMBDIST']} ({p['NOMBDEP']})",
                    'distrito': p['NOMBDIST'], 'depto': p['NOMBDEP'],
                    'lat': lat, 'lon': lon
                })
            return pd.DataFrame(filas).sort_values('etiqueta')

        todos = cargar_todos_distritos()
        col5, col6 = st.columns([1, 2])

        with col5:
            lugar = st.selectbox("Busca un distrito", todos['etiqueta'],
                                 index=int(todos.reset_index(drop=True).query("etiqueta.str.startswith('LIMA (LIMA)')").index[0])
                                 if todos['etiqueta'].str.startswith('LIMA (LIMA)').any() else 0, key="lugar_m2")
            radio = st.number_input("Radio de análisis (km)", 50, 500, 150, 50, key="rad_lag_m2")
            mag_ref = st.number_input("Magnitud de referencia", 5.0, 8.0, 6.0, 0.5, key="mag_ref_m2")

            r = todos[todos['etiqueta'] == lugar].iloc[0]
            dx = (sismos['lon'] - r['lon']) * 111 * np.cos(np.radians(r['lat']))
            dy = (sismos['lat'] - r['lat']) * 111
            cerca = sismos[np.hypot(dx, dy) <= radio].copy()
            cerca['anio'] = pd.to_datetime(cerca['fecha UTC']).dt.year

            st.metric("Sismos registrados en la zona", f"{len(cerca):,}")

            if len(cerca) > 0:
                st.metric("Magnitud histórica máxima", f"{cerca['mag'].max():.1f}")
                fuertes = cerca[cerca['mag'] >= mag_ref]
                if len(fuertes) > 0:
                    ultimo = int(fuertes['anio'].max())
                    silencio = 2026 - ultimo
                    st.metric(f"Último sismo M≥{mag_ref}", ultimo)
                    st.metric("Años sin evento fuerte", silencio, delta="⚠️ Silencio prolongado" if silencio > 30 else None, delta_color="inverse")
                else:
                    st.info(f"Sin registros de M≥{mag_ref} en {radio} km.")

                st.write("**Sismos más fuertes de la zona**")
                top = cerca.nlargest(5, 'mag')[['fecha UTC', 'mag', 'prof']].copy()
                top.columns = ['Fecha', 'Magnitud', 'Prof. (km)']
                st.dataframe(top, hide_index=True)

                if st.button("Analizar con Gemma", key="btn_lag_m2"):
                    with st.spinner("Analizando..."):
                        ult_txt = (f"el último sismo de magnitud {mag_ref} o mayor fue en {ultimo}, hace {silencio} años" if len(fuertes) > 0 else f"no hay registros de magnitud {mag_ref} o mayor")
                        prompt = (
                            f"Eres sismólogo del IGP asesorando a autoridades locales. En {r['distrito']} ({r['depto']}), en un radio de {radio} km se han "
                            f"registrado {len(cerca)} sismos desde 1960, con magnitud máxima {cerca['mag'].max():.1f}. Además, {ult_txt}. "
                            f"Explica en 4 líneas qué significa esto para la preparación del distrito. NO predigas fechas: la ciencia no puede predecir sismos."
                        )
                        # Cambiado estrictamente a gemma:2b
                        resp = ollama.chat(model='gemma:2b', messages=[{'role': 'user', 'content': prompt}])
                        st.info(resp['message']['content'])

        with col6:
            st.write(f"### Actividad sísmica cerca de {r['distrito']}")
            mapa_lugar = folium.Map(location=[r['lat'], r['lon']], zoom_start=7)
            folium.Marker([r['lat'], r['lon']], tooltip=r['distrito'], icon=folium.Icon(color='blue', icon='home')).add_to(mapa_lugar)
            folium.Circle([r['lat'], r['lon']], radius=radio*1000, color='#3388ff', fill=False, weight=2).add_to(mapa_lugar)

            if len(cerca) > 0:
                HeatMap(data=cerca[['lat', 'lon', 'mag']].values.tolist(), radius=15, blur=20, min_opacity=0.3).add_to(mapa_lugar)
                for _, s in cerca.nlargest(5, 'mag').iterrows():
                    folium.CircleMarker(
                        [s['lat'], s['lon']], radius=6, color='darkred', fill=True,
                        tooltip=f"M{s['mag']} · {s['fecha UTC']} · {s['prof']:.0f} km"
                    ).add_to(mapa_lugar)
            st_folium(mapa_lugar, width=600, height=500, key="mapa_lugar_m2")

    with tab_agente:
        st.caption("Pregúntale al agente sobre riesgo de desastres en el Perú")

        def construir_contexto(pregunta):
            p = pregunta.upper()
            partes = []
            conteo = datos_sismo['Nivel_Riesgo'].value_counts()
            partes.append(
                f"RESUMEN NACIONAL: {len(datos_sismo)} distritos evaluados. "
                f"Muy Alto: {conteo.get('MA',0)}, Alto: {conteo.get('A',0)}. "
                f"Población total expuesta: {int(datos_sismo['Poblacion_Expuesta'].sum()):,}."
            )
            partes.append(f"CATÁLOGO SÍSMICO IGP: {len(sismos):,} sismos. Magnitud máxima histórica: {sismos['mag'].max():.1f}.")

            encontrados = datos_sismo[datos_sismo['Distrito'].apply(lambda d: d in p)]
            if len(encontrados) == 0:
                encontrados = datos_sismo[datos_sismo['Departamento'].apply(lambda d: d in p)].head(8)

            for _, f in encontrados.head(5).iterrows():
                partes.append(
                    f"DISTRITO {f['Distrito']} ({f['Departamento']}): riesgo {f['Nivel_Riesgo']}, "
                    f"{int(f['Poblacion_Expuesta'])} expuestos."
                )
                if pd.notna(f['Latitud']):
                    dx = (sismos['lon'] - f['Longitud']) * 111 * np.cos(np.radians(f['Latitud']))
                    dy = (sismos['lat'] - f['Latitud']) * 111
                    cercanos = sismos[np.hypot(dx, dy) <= 150]
                    if len(cercanos) > 0:
                        partes.append(f"SISMICIDAD cerca de {f['Distrito']}: {len(cercanos)} sismos en 150 km, max {cercanos['mag'].max():.1f}.")
            
            if len(encontrados) == 0:
                top = datos_sismo[datos_sismo['Nivel_Riesgo'] == 'MA'].nlargest(8, 'Poblacion_Expuesta')
                lista = ", ".join(f"{fila['Distrito']} ({int(fila['Poblacion_Expuesta'])} exp.)" for _, fila in top.iterrows())
                partes.append(f"DISTRITOS MÁS CRÍTICOS: {lista}.")

            return "\n".join(partes)

        if "mensajes" not in st.session_state:
            st.session_state.mensajes = []

        for m in st.session_state.mensajes:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if pregunta := st.chat_input("Escribe tu consulta..."):
            st.session_state.mensajes.append({"role": "user", "content": pregunta})
            with st.chat_message("user"):
                st.markdown(pregunta)

            with st.chat_message("assistant"):
                with st.spinner("Consultando datos oficiales..."):
                    contexto = construir_contexto(pregunta)
                    sistema = (
                        "Eres un asesor técnico en gestión de riesgos de desastres del Perú. "
                        "Respondes SOLO con los datos oficiales que se te entregan. "
                        "Responde en español, claro y breve.\n\n"
                        f"DATOS DISPONIBLES:\n{contexto}"
                    )
                    # Cambiado estrictamente a gemma:2b
                    r = ollama.chat(
                        model='gemma:2b',
                        messages=[{'role': 'system', 'content': sistema}, {'role': 'user', 'content': pregunta}],
                        options={'num_ctx': 8192}
                    )
                    texto = r['message']['content']
                    st.markdown(texto)
            st.session_state.mensajes.append({"role": "assistant", "content": texto})

        with st.expander("Ejemplos de preguntas"):
            st.write("""
            - ¿Qué distritos están en riesgo muy alto?
            - Háblame del riesgo en Aramango
            - ¿Cuántas personas están expuestas en Amazonas?
            - ¿Cómo es la sismicidad cerca de Imaza?
            """)