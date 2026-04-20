import streamlit as st
import pandas as pd
import requests
import sys
import os
from datetime import datetime, timedelta
import plotly.express as px

# --- CONFIGURARE ȘI DATE CONSTANTE ---
ORASE_MCDO = {
    "Bucuresti": {"lat": 44.43, "lon": 26.10},
    "Cluj": {"lat": 46.77, "lon": 23.62},
    "Timisoara": {"lat": 45.75, "lon": 21.21},
    "Iasi": {"lat": 47.16, "lon": 27.60},
    "Brasov": {"lat": 45.65, "lon": 25.61},
    "Constanta": {"lat": 44.17, "lon": 28.63},
    "Craiova": {"lat": 44.33, "lon": 23.79},
    "Sibiu": {"lat": 45.80, "lon": 24.15},
    "Oradea": {"lat": 47.04, "lon": 21.91},
    "Ploiesti": {"lat": 44.93, "lon": 26.03}
}

FILE_DB = "baza_date.csv"

def fetch_weather(city_name, start_date, end_date):
    lat = ORASE_MCDO[city_name]["lat"]
    lon = ORASE_MCDO[city_name]["lon"]
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&timezone=Europe%20%2FBerlin"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            d = r.json()["daily"]
            return pd.DataFrame({
                "Data": d["time"],
                "Oras": city_name,
                "Max": d["temperature_2m_max"],
                "Min": d["temperature_2m_min"],
                "Precipitatii": d["precipitation_sum"],
                "Vanzari": 0.0
            })
    except Exception as e:
        print(f"Eroare la {city_name}: {e}")
    return pd.DataFrame()

# --- LOGICA ROBOTULUI (GITHUB ACTIONS) ---
if "--update_only" in sys.argv:
    print("🤖 Robotul a pornit actualizarea...")
    
    if os.path.exists(FILE_DB):
        df_old = pd.read_csv(FILE_DB)
        last_date_str = df_old["Data"].max()
        start_dt = datetime.strptime(last_date_str, '%Y-%m-%d') + timedelta(days=1)
    else:
        df_old = pd.DataFrame()
        start_dt = datetime.now() - timedelta(days=1095) # 3 ani in urma

    end_dt = datetime.now() - timedelta(days=2) # Open-Meteo are nevoie de 2 zile pt arhiva
    
    if start_dt.strftime('%Y-%m-%d') <= end_dt.strftime('%Y-%m-%d'):
        new_batches = []
        for oras in ORASE_MCDO:
            print(f"Descarc date noi pentru {oras}...")
            batch = fetch_weather(oras, start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))
            new_batches.append(batch)
        
        if new_batches:
            df_new = pd.concat(new_batches)
            df_final = pd.concat([df_old, df_new]).drop_duplicates(subset=['Data', 'Oras'])
            df_final.to_csv(FILE_DB, index=False)
            print("✅ Baza de date a fost actualizată cu succes!")
    else:
        print("☀️ Datele sunt deja la zi.")
    sys.exit()

# --- INTERFAȚA UTILIZATOR (STREAMLIT) ---
st.set_page_config(layout="wide", page_title="Analiză Meteo & Vânzări")

st.title("📊 Sistem Intern de Analiză: Vreme vs Vânzări")

if not os.path.exists(FILE_DB):
    st.error("⚠️ Baza de date nu există. Robotul nu a rulat încă sau fișierul a fost șters.")
    if st.button("🚀 Pornește prima extracție manual (3 ani)"):
        st.info("Acest proces poate dura 1-2 minute. Te rog așteaptă...")
        # (Aici codul de fetch manual similar cu cel de robot)
else:
    df = pd.read_csv(FILE_DB)
    df["Data"] = pd.to_datetime(df["Data"])

    st.sidebar.header("Filtre Analiză")
    oras_sel = st.sidebar.multiselect("Selectează Orașe:", df["Oras"].unique(), default=[df["Oras"].unique()[0]])
    perioada = st.sidebar.date_input("Interval timp:", [df["Data"].min(), df["Data"].max()])

    # Filtrare
    mask = (df["Oras"].isin(oras_sel)) & (df["Data"] >= pd.Timestamp(perioada[0])) & (df["Data"] <= pd.Timestamp(perioada[1]))
    df_f = df.loc[mask].sort_values(by="Data", ascending=False)

    # Grafic
    st.subheader("📈 Evoluție Temperaturi Maxime")
    fig = px.line(df_f, x="Data", y="Max", color="Oras", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    # Tabel Editabil
    st.subheader("📝 Introducere Vânzări")
    st.caption("Introdu valorile de vânzări în coloana de mai jos. Acestea vor fi salvate local în sesiune.")
    edited_df = st.data_editor(df_f, use_container_width=True)

    if st.button("💾 Salvează modificările în Baza de Date"):
        # Actualizăm DF-ul principal cu datele editate
        df.set_index(['Data', 'Oras'], inplace=True)
        edited_df['Data'] = pd.to_datetime(edited_df['Data'])
        edited_df.set_index(['Data', 'Oras'], inplace=True)
        df.update(edited_df)
        df.reset_index(inplace=True)
        df.to_csv(FILE_DB, index=False)
        st.success("✅ Vânzările au fost salvate permanent!")

    # Descarcă raport
    st.download_button("📥 Descarcă Raport CSV", df_f.to_csv(index=False), "raport_analiza.csv")
