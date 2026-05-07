import pandas as pd
import requests
import sys
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURARE ORASE (Nume standardizate pentru stabilitate) ---
ORASE_MCDO = {
    "Bucuresti": {"lat": 44.43, "lon": 26.10},
    "Cluj":      {"lat": 46.77, "lon": 23.62},
    "Timisoara": {"lat": 45.75, "lon": 21.21},
    "Iasi":      {"lat": 47.16, "lon": 27.60},
    "Brasov":    {"lat": 45.65, "lon": 25.61},
    "Constanta": {"lat": 44.17, "lon": 28.63},
    "Craiova":   {"lat": 44.33, "lon": 23.79},
    "Sibiu":     {"lat": 45.80, "lon": 24.15},
    "Oradea":    {"lat": 47.04, "lon": 21.91},
    "Ploiesti":  {"lat": 44.93, "lon": 26.03},
    "Pitesti":   {"lat": 44.85, "lon": 24.87},
    "Bacau":     {"lat": 46.57, "lon": 26.91},
    "Galati":    {"lat": 45.43, "lon": 28.05},
    "Braila":    {"lat": 45.27, "lon": 27.96},
    "Targu Mures": {"lat": 46.54, "lon": 24.56},
    "Arad":      {"lat": 46.18, "lon": 21.31},
    "Deva":      {"lat": 45.88, "lon": 22.91},
    "Ramnicu Valcea": {"lat": 45.10, "lon": 24.37},
    "Suceava":   {"lat": 47.65, "lon": 26.26},
    "Piatra Neamt": {"lat": 46.93, "lon": 26.37},
    "Targoviste": {"lat": 44.93, "lon": 25.46},
    "Slatina":   {"lat": 44.43, "lon": 24.37},
    "Drobeta Turnu Severin": {"lat": 44.63, "lon": 22.66},
    "Botosani":  {"lat": 47.74, "lon": 26.67},
    "Buzau":     {"lat": 45.15, "lon": 26.82},
    "Focsani":   {"lat": 45.70, "lon": 27.19},
    "Slobozia":  {"lat": 44.57, "lon": 27.37},
    "Tulcea":    {"lat": 45.18, "lon": 28.80},
    "Bistrita":  {"lat": 47.13, "lon": 24.50},
    "Alba Iulia": {"lat": 46.07, "lon": 23.58},
    "Dumbravita": {"lat": 45.80, "lon": 21.27},
    "Targu Jiu": {"lat": 45.04, "lon": 23.28},
    "Alexandria": {"lat": 43.97, "lon": 25.34},
}

FILE_DB = "baza_date.csv"

WMO_CODES = {
    0: ("☀️", "Senin"), 1: ("🌤️", "Majoritar senin"), 2: ("⛅", "Partial noros"), 
    3: ("☁️", "Noros"), 45: ("🌫️", "Ceata"), 51: ("🌦️", "Burnita"), 
    61: ("🌧️", "Ploaie slaba"), 63: ("🌧️", "Ploaie"), 71: ("🌨️", "Ninsoare"), 
    80: ("🌦️", "Averse"), 95: ("⛈️", "Furtuna")
}

def wmo_to_emoji(code):
    if code is None: return ("❓", "N/A")
    return WMO_CODES.get(int(code), ("🌡️", f"Cod {code}"))

def fetch_weather_data(city, lat, lon, start, end, is_archive=True):
    base = "archive-api" if is_archive else "api"
    type_req = "archive" if is_archive else "forecast"
    url = f"https://{base}.open-meteo.com/v1/{type_req}?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration,weathercode&timezone=Europe%2FBerlin"
    try:
        r = requests.get(url, timeout=15)
        d = r.json().get("daily", {})
        if not d or "time" not in d: return pd.DataFrame()
        return pd.DataFrame({
            "Data": d["time"], "Oras": city, "Max": d["temperature_2m_max"], "Min": d["temperature_2m_min"],
            "Precipitatii": d["precipitation_sum"], 
            "OreSoare": [round(s/3600, 1) for s in d.get("sunshine_duration", [0]*len(d["time"]))],
            "WMO": d.get("weathercode", [0]*len(d["time"])), "Vanzari": 0.0
        })
    except: return pd.DataFrame()

# --- LOGICA ROBOT (PENTRU GITHUB ACTIONS) ---
if "--update_only" in sys.argv:
    print("🤖 Robotul inteligent scaneaza baza de date...")
    df_ex = pd.read_csv(FILE_DB) if os.path.exists(FILE_DB) else pd.DataFrame()
    if not df_ex.empty: df_ex["Data"] = pd.to_datetime(df_ex["Data"])
    
    new_batches = []
    limit_date = (datetime.now() - timedelta(days=2)).date()

    for city, coords in ORASE_MCDO.items():
        # Verificam individual fiecare oras
        if not df_ex.empty and city in df_ex["Oras"].values:
            last_date = df_ex[df_ex["Oras"] == city]["Data"].max().date()
            start_dt = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            start_dt = "2023-01-01"
            print(f"🆕 Oras lipsa sau nou: {city}")

        end_dt = limit_date.strftime("%Y-%m-%d")
        
        if start_dt <= end_dt:
            print(f"🛰️ {city}: Descarc de la {start_dt}")
            batch = fetch_weather_data(city, coords["lat"], coords["lon"], start_dt, end_dt)
            if not batch.empty: new_batches.append(batch)
    
    if new_batches:
        df_new = pd.concat(new_batches)
        df_new["Data"] = pd.to_datetime(df_new["Data"])
        df_final = pd.concat([df_ex, df_new]).drop_duplicates(subset=["Data", "Oras"]).sort_values(["Oras", "Data"])
        df_final.to_csv(FILE_DB, index=False)
        print("✅ Datele au fost actualizate cu succes.")
    else: print("✅ Toate orasele sunt deja la zi.")
    sys.exit(0)

# --- INTERFATA STREAMLIT ---
st.set_page_config(layout="wide", page_title="Meteo McDo")
st.title("📊 Panou Monitorizare Meteo McDonald's")

if not os.path.exists(FILE_DB):
    st.error("⚠️ Fisierul de date nu a fost gasit!"); st.stop()

df = pd.read_csv(FILE_DB); df["Data"] = pd.to_datetime(df["Data"])

# Sidebar
st.sidebar.header("🔧 Configurare Vizualizare")
all_cities = sorted(df["Oras"].unique())
sel_oras = st.sidebar.multiselect("Selecteaza Orase:", all_cities, default=[all_cities[0]] if all_cities else [])
data_range = st.sidebar.date_input("Interval Calendaristic:", [df["Data"].min(), df["Data"].max()])

# Filtrare Date
mask = df["Oras"].isin(sel_oras)
if len(data_range) == 2:
    mask &= (df["Data"].dt.date >= data_range[0]) & (df["Data"].dt.date <= data_range[1])
df_view = df[mask].sort_values("Data")

# Componente Tab
t1, t2, t3, t4 = st.tabs(["📈 Evolutie Meteo", "⚖️ Comparatie Intervale", "🗺️ Restaurante", "📋 Date & Vanzari"])

with t1:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.line(df_view, x="Data", y="Max", color="Oras", title="Evolutie Temperaturi Maxime (°C)"), use_container_width=True)
    with col2:
        st.plotly_chart(px.bar(df_view, x="Data", y="Precipitatii", color="Oras", title="Precipitatii Zilnice (mm)"), use_container_width=True)

with t2:
    st.subheader("⚖️ Analiza Comparativa intre Perioade")
    if not sel_oras: st.warning("Selecteaza un oras din sidebar pentru comparatie."); st.stop()
    
    c1, c2 = st.columns(2)
    with c1: int_a = st.date_input("Perioada A (Referinta)", [df["Data"].min().date(), (df["Data"].min() + timedelta(days=6)).date()], key="ka")
    with c2: int_b = st.date_input("Perioada B (Comparatie)", [df["Data"].max().date() - timedelta(days=6), df["Data"].max().date()], key="kb")
    
    if len(int_a) == 2 and len(int_b) == 2:
        def get_summary(start, end, city):
            sub = df[(df["Oras"] == city) & (df["Data"].dt.date >= start) & (df["Data"].dt.date <= end)]
            if sub.empty: return None
            emoji = sub["WMO"].mode()[0] if not sub["WMO"].mode().empty else 0
            return {"max": sub["Max"].mean(), "prec": sub["Precipitatii"].sum(), "soare": sub["OreSoare"].mean(), "emoji": wmo_to_emoji(emoji)[0]}
        
        sum_a = get_summary(int_a[0], int_a[1], sel_oras[0])
        sum_b = get_summary(int_b[0], int_b[1], sel_oras[0])
        
        if sum_a and sum_b:
            st.markdown(### Rezultate Comparatie: {sel_oras[0]})
            comp_df = pd.DataFrame({
                "Indicator": ["Vreme Dominanta", "Medie Temp Max", "Total Precipitatii", "Medie Ore Soare"],
                "Perioada A": [sum_a['emoji'], f"{sum_a['max']:.1f}°C", f"{sum_a['prec']:.1f} mm", f"{sum_a['soare']:.1f} h"],
                "Perioada B": [sum_b['emoji'], f"{sum_b['max']:.1f}°C", f"{sum_b['prec']:.1f} mm", f"{sum_b['soare']:.1f} h"]
            })
            st.table(comp_df)

with t3:
    st.info("Harta afiseaza locatiile McDonald's conform coordonatelor din sistem.")
    # Aici poți reintroduce codul px.scatter_map din versiunile anterioare dacă dorești harta vizibilă

with t4:
    st.subheader("📋 Gestionare Date Manuale")
    st.caption("Modifica vanzarile mai jos si apasa butonul de salvare.")
    df_edit = df_view[["Data", "Oras", "Max", "Precipitatii", "Vanzari"]].copy()
    df_edit["Data"] = df_edit["Data"].dt.strftime('%Y-%m-%d')
    edited_data = st.data_editor(df_edit, hide_index=True, use_container_width=True)
    
    if st.button("💾 Salveaza Modificarile in Baza de Date"):
        df.set_index(["Data", "Oras"], inplace=True)
        edited_data["Data"] = pd.to_datetime(edited_data["Data"])
        df.update(edited_data.set_index(["Data", "Oras"]))
        df.reset_index().to_csv(FILE_DB, index=False)
        st.success("Modificarile au fost salvate cu succes!")
        st.rerun()
