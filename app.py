import pandas as pd
import requests
import sys
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURARE ---
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
    0:  ("☀️",  "Cer senin"),
    1:  ("🌤️", "Predominant senin"),
    2:  ("⛅",  "Parțial înnorat"),
    3:  ("☁️",  "Înnorat"),
    45: ("🌫️", "Ceață"),
    48: ("🌫️", "Ceață cu chiciură"),
    51: ("🌦️", "Burniță ușoară"),
    53: ("🌦️", "Burniță moderată"),
    55: ("🌧️", "Burniță densă"),
    61: ("🌧️", "Ploaie ușoară"),
    63: ("🌧️", "Ploaie moderată"),
    65: ("🌧️", "Ploaie abundentă"),
    71: ("🌨️", "Ninsoare ușoară"),
    73: ("🌨️", "Ninsoare moderată"),
    75: ("❄️",  "Ninsoare abundentă"),
    77: ("🌨️", "Grăunțe de zăpadă"),
    80: ("🌦️", "Averse ușoare"),
    81: ("🌧️", "Averse moderate"),
    82: ("⛈️", "Averse violente"),
    85: ("🌨️", "Averse de zăpadă"),
    86: ("❄️",  "Averse puternice de zăpadă"),
    95: ("⛈️", "Furtună"),
    96: ("⛈️", "Furtună cu grindină"),
    99: ("⛈️", "Furtună puternică cu grindină"),
}

def wmo_to_emoji(code):
    if code is None: return ("❓", "Necunoscut")
    return WMO_CODES.get(int(code), ("🌡️", f"Cod {code}"))

def safe_float(val, default=0.0):
    try:
        if pd.isna(val): return default
        return float(val)
    except: return default

# --- FUNCȚII FETCH (Robot & Prognoză) ---
def fetch_weather(city_name, start_date, end_date):
    coords = ORASE_MCDO.get(city_name)
    if not coords: return pd.DataFrame()
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={coords['lat']}&longitude={coords['lon']}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration,precipitation_hours,weathercode&timezone=Europe%2FBerlin"
    try:
        r = requests.get(url, timeout=20); r.raise_for_status()
        d = r.json().get("daily", {})
        if not d: return pd.DataFrame()
        n = len(d["time"])
        return pd.DataFrame({
            "Data": d["time"], "Oras": city_name, "Max": d["temperature_2m_max"], "Min": d["temperature_2m_min"],
            "Precipitatii": d["precipitation_sum"], "OreSoare": [round(s/3600,1) for s in d.get("sunshine_duration",[0]*n)],
            "OrePloaie": d.get("precipitation_hours",[0]*n), "WMO": d.get("weathercode",[0]*n),
            "ZiTip": [wmo_to_emoji(c)[0] + " " + wmo_to_emoji(c)[1] for c in d.get("weathercode",[0]*n)], "Vanzari": 0.0, "Tip": "arhiva"
        })
    except: return pd.DataFrame()

def fetch_forecast(city_name, forecast_days=7):
    coords = ORASE_MCDO.get(city_name)
    if not coords: return pd.DataFrame()
    url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration,precipitation_hours,weathercode,precipitation_probability_max&forecast_days={forecast_days}&timezone=Europe%2FBerlin"
    try:
        r = requests.get(url, timeout=20); r.raise_for_status()
        d = r.json().get("daily", {})
        if not d: return pd.DataFrame()
        n = len(d["time"])
        return pd.DataFrame({
            "Data": d["time"], "Oras": city_name, "Max": d["temperature_2m_max"], "Min": d["temperature_2m_min"],
            "Precipitatii": d["precipitation_sum"], "OreSoare": [round(s/3600,1) for s in d.get("sunshine_duration",[0]*n)],
            "OrePloaie": d.get("precipitation_hours",[0]*n), "ProbPloaie": d.get("precipitation_probability_max",[0]*n),
            "WMO": d.get("weathercode",[0]*n), "ZiTip": [wmo_to_emoji(c)[0] + " " + wmo_to_emoji(c)[1] for c in d.get("weathercode",[0]*n)], "Tip": "prognoza"
        })
    except: return pd.DataFrame()

# --- LOGICĂ ROBOT ---
if "--update_only" in sys.argv:
    print("🤖 Robotul a pornit..."); all_new_data = []
    if os.path.exists(FILE_DB):
        df_ex = pd.read_csv(FILE_DB); df_ex["Data"] = pd.to_datetime(df_ex["Data"])
        start_dt = (df_ex["Data"].max() + timedelta(days=1)).strftime("%Y-%m-%d")
    else: start_dt = "2023-01-01"; df_ex = None
    end_dt = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    if start_dt <= end_dt:
        for oras in ORASE_MCDO:
            batch = fetch_weather(oras, start_dt, end_dt)
            if not batch.empty: all_new_data.append(batch)
        if all_new_data:
            df_final = pd.concat([df_ex, pd.concat(all_new_data)] if df_ex is not None else all_new_data).drop_duplicates(subset=["Data", "Oras"])
            df_final.to_csv(FILE_DB, index=False); print("✅ Update reușit.")
    sys.exit(0)

# --- INTERFAȚĂ STREAMLIT ---
st.set_page_config(layout="wide", page_title="📊 Meteo & Vânzări")
st.title("📊 Analiză Comparativă Meteo & Vânzări")

if not os.path.exists(FILE_DB):
    st.warning("Baza de date lipsește!"); st.stop()

df = pd.read_csv(FILE_DB); df["Data"] = pd.to_datetime(df["Data"])
all_cities = sorted(df["Oras"].unique().tolist())

# --- Sidebar ---
st.sidebar.header("🔧 Filtre Generale")
selected_cities = st.sidebar.multiselect("Orașe:", all_cities, default=[all_cities[0]])
min_d, max_d = df["Data"].min().date(), df["Data"].max().date()
date_range = st.sidebar.date_input("Interval:", value=(min_d, max_d))

df_plot = df[df["Oras"].isin(selected_cities)]
if len(date_range) == 2:
    df_plot = df_plot[(df_plot["Data"].dt.date >= date_range[0]) & (df_plot["Data"].dt.date <= date_range[1])]

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🌡️ Temperaturi", "🔮 Prognoză", "🌧️ Precipitații", "💰 Vânzări", "⚖️ Comparație Intervale"])

# --- TAB 5: COMPARAȚIE INTERVALE (CERINȚA NOUĂ) ---
with tab5:
    st.subheader("⚖️ Compară două perioade de timp")
    st.caption("Exemplu: Compară prima săptămână din Mai 2024 cu prima săptămână din Mai 2025.")

    c_o, c_p1, c_p2 = st.columns([1, 2, 2])
    with c_o: 
        oras_comp = st.selectbox("Alege Orașul:", all_cities)
    with c_p1:
        interval_a = st.date_input("Perioada A:", value=(min_d, min_d + timedelta(days=6)), key="p_a")
    with c_p2:
        interval_b = st.date_input("Perioada B:", value=(max_d - timedelta(days=6), max_d), key="p_b")

    if len(interval_a) == 2 and len(interval_b) == 2:
        def get_stats(start, end, city):
            mask = (df["Oras"] == city) & (df["Data"].dt.date >= start) & (df["Data"].dt.date <= end)
            sub = df[mask]
            if sub.empty: return None
            # Calcul mediilor și sumelor
            m_max = sub["Max"].mean()
            m_min = sub["Min"].mean()
            t_prec = sub["Precipitatii"].sum()
            m_soare = sub["OreSoare"].mean()
            # Determinare Semn Dominant (cel mai frecvent emoji)
            sub["EmojiOnly"] = sub["ZiTip"].apply(lambda x: str(x).split()[0])
            dominant = sub["EmojiOnly"].mode()[0] if not sub["EmojiOnly"].mode().empty else "❓"
            return {"max": m_max, "min": m_min, "prec": t_prec, "soare": m_soare, "emoji": dominant, "count": len(sub)}

        s_a = get_stats(interval_a[0], interval_a[1], oras_comp)
        s_b = get_stats(interval_b[0], interval_b[1], oras_comp)

        if s_a and s_b:
            st.divider()
            cols = st.columns(2)
            cols[0].metric(f"Perioada A ({s_a['count']} zile)", f"{s_a['emoji']}")
            cols[1].metric(f"Perioada B ({s_b['count']} zile)", f"{s_b['emoji']}")

            # Tabel Comparativ
            res_data = {
                "Indicator": ["Semn Dominant", "Medie Temp Max", "Medie Temp Min", "Total Precipitații", "Medie Ore Soare"],
                "Perioada A": [s_a["emoji"], f"{s_a['max']:.1f}°C", f"{s_a['min']:.1f}°C", f"{s_a['prec']:.1f} mm", f"{s_a['soare']:.1f} h"],
                "Perioada B": [s_b["emoji"], f"{s_b['max']:.1f}°C", f"{s_b['min']:.1f}°C", f"{s_b['prec']:.1f} mm", f"{s_b['soare']:.1f} h"],
                "Diferență": ["-", f"{s_b['max']-s_a['max']:+.1f}", f"{s_b['min']-s_a['min']:+.1f}", f"{s_b['prec']-s_a['prec']:+.1f}", f"{s_b['soare']-s_a['soare']:+.1f}"]
            }
            st.table(pd.DataFrame(res_data))

            # Grafic comparativ
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(name="Perioada A", x=["Max", "Min"], y=[s_a["max"], s_a["min"]], marker_color='blue'))
            fig_comp.add_trace(go.Bar(name="Perioada B", x=["Max", "Min"], y=[s_b["max"], s_b["min"]], marker_color='orange'))
            st.plotly_chart(fig_comp)
        else:
            st.error("Nu există date pentru unul dintre intervale.")

# --- Restul Tab-urilor (Temperaturi, Prognoza, etc.) se completează similar cu codul tău original ---
with tab1:
    st.plotly_chart(px.line(df_plot, x="Data", y=["Max", "Min"], color="Oras", title="Evoluție Temperaturi"))
with tab2:
    o_p = st.selectbox("Prognoză pentru:", all_cities)
    df_p = fetch_forecast(o_p)
    if not df_p.empty:
        c_p = st.columns(len(df_p))
        for i, r in df_p.iterrows():
            c_p[i].markdown(f"**{r['Data'][5:]}**\n\n{wmo_to_emoji(r['WMO'])[0]}\n\n{r['Max']}°")
with tab3:
    st.plotly_chart(px.bar(df_plot, x="Data", y="Precipitatii", color="Oras", title="Precipitatii zilnice"))
with tab4:
    st.info("Completează vânzările în tabelul de jos și salvează.")

# --- TABEL EDITABIL ȘI SALVARE ---
st.divider()
st.subheader("📋 Editare Date & Vânzări")
edited_df = st.data_editor(df_plot[["Data", "Oras", "ZiTip", "Max", "Min", "Precipitatii", "Vanzari"]], use_container_width=True, hide_index=True)

if st.button("💾 Salvează în Baza de Date", type="primary"):
    df.set_index(["Data", "Oras"], inplace=True)
    e_copy = edited_df.set_index(["Data", "Oras"])
    df.update(e_copy)
    df.reset_index().to_csv(FILE_DB, index=False)
    st.success("Date salvate!")
