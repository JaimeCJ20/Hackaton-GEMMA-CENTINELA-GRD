import streamlit as st
import pandas as pd
import ollama
import json
import math
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import random

st.set_page_config(layout="wide")
st.title("🚨 Centinela GRD")
st.write("Sistema multi-amenaza de gestión de riesgos impulsado por Gemma 3 4B")

# ---------- CARGA DE DATOS ----------
@st.cache_data
def cargar_geojson():
    with open("distritos.geojson", encoding="utf-8") as f:
        return json.load(f)

def centroide(geom):
    """Centro aproximado de un polígono, promediando sus vértices."""
    if not geom or 'type' not in geom:
        return None, None
    try:
        if geom['type'] == 'Polygon':
            anillos = [geom['coordinates'][0]]
        elif geom['type'] == 'MultiPolygon':
            anillos = [p[0] for p in geom['coordinates']]
        else:
            return None, None
        pts = [p for a in anillos for p in a]
        if not pts:
            return None, None
        return sum(p[1] for p in pts)/len(pts), sum(p[0] for p in pts)/len(pts)
    except (KeyError, IndexError, TypeError):
        return None, None

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

    # Ubigeo a texto de 6 dígitos (el Excel pierde el cero inicial)
    df['Ubigeo'] = df['Ubigeo'].astype(int).astype(str).str.zfill(6)

    # Coordenadas reales desde el GeoJSON
    geo = cargar_geojson()
    coords = {}
    for f in geo['features']:
        lat, lon = centroide(f.get('geometry'))
        if lat is not None:
            coords[f['properties']['IDDIST']] = (lat, lon)

    df['Latitud'] = df['Ubigeo'].map(lambda u: coords.get(u, (None, None))[0])
    df['Longitud'] = df['Ubigeo'].map(lambda u: coords.get(u, (None, None))[1])

    return df

@st.cache_data
def cargar_sismos():
    df = pd.read_excel("datos-sismicos_Instrumental_1960-01-01_2026-07-31.xlsx")
    df = df.rename(columns={
        'latitud (º)': 'lat', 'longitud (º)': 'lon',
        'magnitud (M)': 'mag', 'profundidad (km)': 'prof'
    })
    return df.dropna(subset=['lat', 'lon', 'mag'])

datos = cargar_datos_oficiales()
sismos = cargar_sismos()
# ---------- PANELES ----------
tab1, tab2 = st.tabs(["🌊 Amenaza Hidrometeorológica (El Niño)", "🌋 Amenaza Sísmica"])

# ===== PANEL 1: EL NIÑO =====
with tab1:
    st.caption("Fuente: CENEPRED — escenarios de riesgo por movimientos en masa e inundaciones")
    col1, col2 = st.columns(2)

    with col1:
        st.write("### Distritos en riesgo")
        st.dataframe(datos[['Departamento', 'Distrito', 'Nivel_Riesgo',
                            'Poblacion_Expuesta', 'Colegios_Riesgo']])

        st.write("### Motor de Alerta (Gemma)")
        distrito_elegido = st.selectbox("Selecciona un distrito crítico:", datos['Distrito'])
        info = datos[datos['Distrito'] == distrito_elegido].iloc[0]

        st.warning(f"⚠️ {info['Distrito']}: Riesgo {info['Nivel_Riesgo']} · "
                   f"{int(info['Poblacion_Expuesta'])} personas expuestas")

        if st.button("Generar Alerta de Defensa Civil"):
            with st.spinner("Gemma procesando..."):
                prompt = (f"Eres Director de Defensa Civil de Perú. Hay riesgo nivel "
                          f"{info['Nivel_Riesgo']} por huaicos en {info['Distrito']} "
                          f"({info['Departamento']}). Hay {int(info['Poblacion_Expuesta'])} "
                          f"personas y {int(info['Colegios_Riesgo'])} colegios en peligro. "
                          f"Escribe un SMS de evacuación urgente de máximo 40 palabras.")
                respuesta = ollama.chat(model='gemma3:4b',
                                        messages=[{'role': 'user', 'content': prompt}])
                st.success(respuesta['message']['content'])

    with col2:
            st.write("### Mapa de vulnerabilidad")
            geo = cargar_geojson()

            # Nivel de riesgo a número, para colorear
            escala = {'B': 1, 'M': 2, 'A': 3, 'MA': 4}
            datos_mapa = datos.copy()
            datos_mapa['riesgo_num'] = datos_mapa['Nivel_Riesgo'].map(escala)

            mapa_nino = folium.Map(location=[-9.18, -75.01], zoom_start=5)

            folium.Choropleth(
                geo_data=geo,
                data=datos_mapa,
                columns=['Ubigeo', 'riesgo_num'],
                key_on='feature.properties.IDDIST',
                fill_color='YlOrRd',
                fill_opacity=0.7,
                line_opacity=0.3,
                nan_fill_color='transparent',
                nan_fill_opacity=0,
                legend_name='Nivel de riesgo (1=Bajo, 4=Muy Alto)'
            ).add_to(mapa_nino)

            # Marcador solo en los de riesgo Muy Alto
            for _, fila in datos_mapa[datos_mapa['Nivel_Riesgo'] == 'MA'].iterrows():
                if pd.notna(fila['Latitud']):
                    folium.CircleMarker(
                        [fila['Latitud'], fila['Longitud']],
                        radius=4, color='darkred', fill=True,
                        tooltip=f"{fila['Distrito']}: {int(fila['Poblacion_Expuesta'])} expuestos"
                    ).add_to(mapa_nino)

            st_folium(mapa_nino, width=600, height=450, key="mapa_nino")

# ===== PANEL 2: SÍSMICO =====
with tab2:
    st.caption("Fuente: IGP — catálogo sísmico instrumental 1960–2026")
    col3, col4 = st.columns([1, 2])

    with col3:
            magnitud = st.number_input(
                "Magnitud a consultar",
                min_value=0.0, max_value=9.0,
                value=7.0, step=0.1, format="%.1f"
            )

            solo_superficiales = st.checkbox(
                "Solo sismos superficiales (< 70 km)",
                help="Los sismos superficiales causan mayor daño en superficie"
            )

            # Coincidencia exacta con la magnitud ingresada
            sismos_filtrados = sismos[sismos['mag'].round(1) == round(magnitud, 1)]
            if solo_superficiales:
                sismos_filtrados = sismos_filtrados[sismos_filtrados['prof'] < 70]

            st.metric(f"Sismos de magnitud {magnitud:.1f}", f"{len(sismos_filtrados):,}")

            if len(sismos_filtrados) > 0:
                st.metric("Profundidad promedio", f"{sismos_filtrados['prof'].mean():.0f} km")

                st.write("**Registros**")
                tabla = sismos_filtrados[['fecha UTC', 'mag', 'prof']].copy()
                tabla.columns = ['Fecha', 'Magnitud', 'Profundidad (km)']
                st.dataframe(tabla.sort_values('Fecha', ascending=False), hide_index=True)
            else:
                st.info(f"No hay sismos de magnitud exacta {magnitud:.1f} con esos filtros.")
            st.divider()
            st.write("**Población expuesta**")
            radio_km = st.number_input("Radio de análisis (km)", 10, 300, 50, 10)

            if len(sismos_filtrados) > 0:
                dist_validos = datos.dropna(subset=['Latitud'])
                afectados = set()
                for _, s in sismos_filtrados.iterrows():
                    for _, d in dist_validos.iterrows():
                        # distancia aproximada en km
                        dx = (d['Longitud'] - s['lon']) * 111 * math.cos(math.radians(d['Latitud']))
                        dy = (d['Latitud'] - s['lat']) * 111
                        if math.hypot(dx, dy) <= radio_km:
                            afectados.add(d['Ubigeo'])

                exp = dist_validos[dist_validos['Ubigeo'].isin(afectados)]
                st.metric("Personas en distritos alcanzados",
                        f"{int(exp['Poblacion_Expuesta'].sum()):,}")
                st.metric("Distritos alcanzados", len(exp))
            

    with col4:
        st.write("### Mapa de calor sísmico")
        mapa_sismo = folium.Map(location=[-9.18, -75.01], zoom_start=5)
        if len(sismos_filtrados) > 0:
            HeatMap(
                data=sismos_filtrados[['lat', 'lon', 'mag']].values.tolist(),
                radius=12, blur=18, min_opacity=0.3
            ).add_to(mapa_sismo)
        st_folium(mapa_sismo, width=600, height=450, key="mapa_sismo")