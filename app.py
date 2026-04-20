import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="Meteo & Sales ROI")

# Lista orașe cu McDonald's
ORASE = {
    "București": {"lat": 44.4323, "lon": 26.1063},
    "Cluj-Napoca": {"lat": 46.7712, "lon": 23.6236},
    "Timișoara": {"lat": 45.7489, "lon": 21.2087},
    "Iași": {"lat": 47.1585, "lon": 27.6014},
    "Brașov": {"lat": 45.6486, "lon": 25.6061},
    "Constanța": {"lat": 44.1733, "lon": 28.6383},
    "Craiova": {"lat": 44.3302, "lon": 23.7949},
    "Sibiu": {"lat": 45.7983, "lon": 24.1256},
    "Oradea": {"lat": 47.0465, "lon": 21.9189},
    "Ploiești": {"lat": 44.9333, "lon": 26.0333}
}

@st.cache_data(ttl=86400)
def get_weather_data(city_name, start_date, end_date):
    try:
        lat = ORASE[city_name]["lat"]
        lon = ORASE[city_name]["lon"]
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&timezone=Europe%20%2FBerlin"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()["daily"]
            df = pd.DataFrame({
                "Data": pd.to_datetime(data["time"]),
                "Oraș": city_name,
                "Temp Max": data["temperature_2m_max"],
                "Temp Min": data["temperature_2m_min"],
                "Precipitații (mm)": data["precipitation_sum"],
                "Cod Meteo": data["weathercode"]
            })
            return df
    except:
        return pd.DataFrame()
    return pd.DataFrame()

st.title("🌦️ Corelație Vreme vs Vânzări")

st.sidebar.header("Setări Analiză")
selected_cities = st.sidebar.multiselect("Alege orașele:", list(ORASE.keys()), default=["București"])
start_d = st.sidebar.date_input("De la data:", datetime.now() - timedelta(days=365))
end_d = st.sidebar.date_input("Până la data:", datetime.now() - timedelta(days=2))

if st.sidebar.button("Extrage Datele"):
    with st.spinner('Se descarcă datele meteo...'):
        all_data = []
        for city in selected_cities:
            city_df = get_weather_data(city, start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d'))
            if not city_df.empty:
                all_data.append(city_df)
        
        if all_data:
            full_df = pd.concat(all_data)
            full_df["Vânzări (Manual)"] = 0.0
            st.session_state['master_data'] = full_df
        else:
            st.error("Nu am putut descărca datele. Verifică perioada selectată.")

if 'master_data' in st.session_state and not st.session_state['master_data'].empty:
    df_to_show = st.session_state['master_data']
    
    st.subheader("Grafic Comparativ Temperaturi")
    fig = px.line(df_to_show, x="Data", y="Temp Max", color="Oraș", markers=True)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Introducere Date Vânzări")
    edited_df = st.data_editor(df_to_show)
    
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descarcă Tabelul", data=csv, file_name="analiza_meteo.csv", mime="text/csv")
else:
    st.info("👈 Folosește meniul din stânga pentru a alege orașele și apasă pe 'Extrage Datele'.")
