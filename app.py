import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

# Configurare orașe McDo
ORASE = {
    "Bucuresti": {"lat": 44.43, "lon": 26.10},
    "Cluj": {"lat": 46.77, "lon": 23.62},
    "Timisoara": {"lat": 45.75, "lon": 21.21},
    "Iasi": {"lat": 47.16, "lon": 27.60},
    "Brasov": {"lat": 45.65, "lon": 25.61}
}

def fetch_real_data(city_name, start_date, end_date):
    lat, lon = ORASE[city_name]["lat"], ORASE[city_name]["lon"]
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&timezone=Europe%20%2FBerlin"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            d = r.json()["daily"]
            return pd.DataFrame({
                "Data": pd.to_datetime(d["time"]),
                "Oras": city_name,
                "Max": d["temperature_2m_max"],
                "Min": d["temperature_2m_min"],
                "Precipitatii": d["precipitation_sum"],
                "Vanzari": 0.0
            })
    except:
        return pd.DataFrame()
    return pd.DataFrame()

st.title("🤖 Sistem Automat Meteo-Vânzări")

# Încercăm să încărcăm baza de date existentă
try:
    df = pd.read_csv("baza_date.csv")
    df["Data"] = pd.to_datetime(df["Data"])
    st.success("Baza de date încărcată cu succes.")
except:
    st.warning("Baza de date nu există. Inițializăm extragerea istorică (3 ani)...")
    df = pd.DataFrame()

# BUTON DE ACTUALIZARE AUTOMATĂ
if st.button("🔄 Actualizează Datele (Istoric + Azi)"):
    new_data_list = []
    # Dacă e prima dată, luăm de acum 3 ani, altfel doar de la ultima dată salvată
    last_date = df["Data"].max() if not df.empty else (datetime.now() - timedelta(days=1095))
    start_str = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
    end_str = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

    if start_str < end_str:
        for oras in ORASE:
            with st.spinner(f"Extrag date noi pentru {oras}..."):
                batch = fetch_real_data(oras, start_str, end_str)
                new_data_list.append(batch)
        
        if new_data_list:
            new_df = pd.concat(new_data_list)
            df = pd.concat([df, new_df]).drop_duplicates(subset=['Data', 'Oras'])
            df.to_csv("baza_date.csv", index=False)
            st.rerun()
    else:
        st.info("Datele sunt deja la zi.")

# INTERFAȚA DE ANALIZĂ
if not df.empty:
    st.subheader("Comparație și Introducere Vânzări")
    
    # Filtre
    oras_sel = st.multiselect("Alege orașele:", df["Oras"].unique(), default=df["Oras"].unique()[:2])
    
    # Tabel editabil
    df_filtered = df[df["Oras"].isin(oras_sel)].sort_values(by="Data", ascending=False)
    edited_df = st.data_editor(df_filtered, key="editor")
    
    # Salvare manuală a vânzărilor introduse
    if st.button("💾 Salvează Vânzările Introduse"):
        df.update(edited_df)
        df.to_csv("baza_date.csv", index=False)
        st.success("Vânzările au fost salvate în baza de date!")

    # Grafic
    fig = px.line(edited_df, x="Data", y="Max", color="Oras", title="Evoluție Temperaturi Maxime")
    st.plotly_chart(fig, use_container_width=True)
