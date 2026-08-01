# 🚨 Centinela GRD: Sistema Multi-Amenaza Híbrido (Edge AI)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/Ollama_Gemma_2B-000000?style=for-the-badge&logo=Ollama&logoColor=white)](https://ollama.ai)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

**Centinela GRD** es una plataforma de Gestión del Riesgo de Desastres (GRD) diseñada para el contexto peruano. Combina datos oficiales del estado (CENEPRED, IGP) con telemetría en tiempo real y el poder de **Gemma 2B operando 100% offline (Edge AI)**. 

Desarrollado para garantizar la toma de decisiones críticas y la emisión de alertas de evacuación incluso cuando las telecomunicaciones e internet colapsan durante una emergencia.

---

## 🎯 El Problema
Durante desastres de gran magnitud (sismos severos, Fenómeno El Niño), la infraestructura de internet es la primera en caer. Los Centros de Operaciones de Emergencia (COEN) quedan a ciegas, con datos técnicos difíciles de interpretar y sin herramientas para generar alertas rápidas y comprensibles para la población.

## 💡 Nuestra Solución
Un dashboard táctico e interactivo de dos módulos que funciona como un **"Modo Supervivencia"**:
1. **Multi-Amenaza:** Monitoreo simultáneo de riesgos Hidrometeorológicos y Sísmicos.
2. **Offline-First:** La Inteligencia Artificial (Gemma 2B) corre localmente en el equipo. Si se pierde la conexión a la API del clima, el sistema utiliza promedios históricos y simuladores de sensores IoT.
3. **Agente Especializado:** Un asistente conversacional que analiza la vulnerabilidad y las lagunas sísmicas de cada distrito basándose estrictamente en catálogos oficiales.
4. **Traducción Táctica:** Convierte datos crudos (coordenadas, mm/h, magnitudes) en mensajes SMS de evacuación claros, urgentes y en lenguaje natural.

---

## 🚀 Funcionalidades Principales

### 🌧️ Módulo Hidrometeorológico
*   **Telemetría en Vivo y Fallback Local:** Consumo de la API de Open-Meteo con un switch para simular caídas de internet y pasar a datos locales.
*   **Generador Autónomo de Alertas:** Si los sensores superan el umbral de peligro, Gemma redacta protocolos de evacuación instantáneos.
*   **Distribución por QR:** Generación de códigos QR al instante para compartir la alerta en el centro de mando.

### 🌋 Módulo Sísmico y Lagunas
*   **Análisis de Impacto Radial:** Calcula la población exacta expuesta en un radio kilométrico tras simular un sismo histórico.
*   **Detección de Silencio Sísmico:** Algoritmo que cruza el catálogo del IGP (1960-2026) para identificar cuántos años lleva un distrito sin liberar energía sísmica importante.
*   **Mapas de Calor Geoespaciales:** Renderizado interactivo con Folium para identificar las zonas rojas de vulnerabilidad.

### 🤖 Agente RAG Oficial
*   **Chatbot Contextual:** Asistente IA que responde preguntas cruzando la base de datos de CENEPRED (viviendas, colegios y hospitales en riesgo) y el historial sísmico del distrito consultado.

---

## ⚙️ Arquitectura y Tecnologías
*   **Frontend / UI:** Streamlit, Streamlit-Folium.
*   **Motor Lógico y Datos:** Pandas, Numpy, Math, JSON.
*   **Inteligencia Artificial:** Ollama (Modelo: `gemma:2b`).
*   **Mapas y Geoespacial:** Folium, GeoJSON.

---

## 🛠️ Instalación y Uso (Local)

Para ejecutar este proyecto en tu máquina local para la evaluación, sigue estos pasos:

### 1. Requisitos Previos
*   Tener **Python 3.9+** instalado.
*   Instalar [Ollama](https://ollama.ai/) en tu computadora.

### 2. Descargar el Modelo IA
Abre tu terminal y ejecuta el siguiente comando para descargar el modelo local de Google Gemma:
```bash
ollama run gemma:2b
