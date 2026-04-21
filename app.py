import pandas as pd
import requests
import sys
import os
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

# ---------------------------------------------------------------------------
# CODUL WMO → Emoji + Descriere (standard meteorologic internațional)
# https://open-meteo.com/en/docs — Weather code
# ---------------------------------------------------------------------------
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
    """Returnează emoji + descriere din codul WMO."""
    if code is None:
        return ("❓", "Necunoscut")
    code = int(code)
    return WMO_CODES.get(code, ("🌡️", f"Cod {code}"))


def safe_float(val, default=0.0):
    """Extrage float sigur dintr-un pandas value."""
    try:
        if pd.isna(val):
            return default
        return float(val)
    except Exception:
        return default


# ---------------------------------------------------------------------------
# FETCH ARHIVĂ (date istorice confirmate)
# ---------------------------------------------------------------------------
def fetch_weather(city_name, start_date, end_date):
    coords = ORASE_MCDO.get(city_name)
    if not coords:
        return pd.DataFrame()

    lat, lon = coords["lat"], coords["lon"]
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"sunshine_duration,precipitation_hours,weathercode"
        f"&timezone=Europe%2FBerlin"
    )

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        d = r.json().get("daily", {})
        if not d or not d.get("time"):
            return pd.DataFrame()

        n = len(d["time"])
        ore_soare  = [round(s / 3600, 1) if s is not None else 0.0
                      for s in d.get("sunshine_duration", [0] * n)]
        ore_ploaie = [round(p, 1) if p is not None else 0.0
                      for p in d.get("precipitation_hours", [0] * n)]
        codes      = d.get("weathercode", [None] * n)

        emoji_list = [wmo_to_emoji(c)[0] + " " + wmo_to_emoji(c)[1] for c in codes]

        return pd.DataFrame({
            "Data":         d["time"],
            "Oras":         city_name,
            "Max":          d["temperature_2m_max"],
            "Min":          d["temperature_2m_min"],
            "Precipitatii": d["precipitation_sum"],
            "OreSoare":     ore_soare,
            "OrePloaie":    ore_ploaie,
            "WMO":          codes,
            "ZiTip":        emoji_list,
            "Vanzari":      0.0,
            "Tip":          "arhiva"
        })

    except Exception as e:
        print(f"❌ Eroare arhivă {city_name}: {e}")
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# FETCH PROGNOZĂ (7 zile în viitor — date REALE de la modele meteo)
# ---------------------------------------------------------------------------
def fetch_forecast(city_name, forecast_days=7):
    coords = ORASE_MCDO.get(city_name)
    if not coords:
        return pd.DataFrame()

    lat, lon = coords["lat"], coords["lon"]
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"sunshine_duration,precipitation_hours,weathercode,"
        f"precipitation_probability_max,daylight_duration"
        f"&forecast_days={forecast_days}"
        f"&timezone=Europe%2FBerlin"
    )

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        d = r.json().get("daily", {})
        if not d or not d.get("time"):
            return pd.DataFrame()

        n = len(d["time"])
        ore_soare    = [round(s / 3600, 1) if s is not None else 0.0
                        for s in d.get("sunshine_duration", [0] * n)]
        ore_ploaie   = [round(p, 1) if p is not None else 0.0
                        for p in d.get("precipitation_hours", [0] * n)]
        ore_zi       = [round(s / 3600, 1) if s is not None else 0.0
                        for s in d.get("daylight_duration", [0] * n)]
        codes        = d.get("weathercode", [None] * n)
        prob_ploaie  = d.get("precipitation_probability_max", [None] * n)

        emoji_list = [wmo_to_emoji(c)[0] + " " + wmo_to_emoji(c)[1] for c in codes]

        return pd.DataFrame({
            "Data":         d["time"],
            "Oras":         city_name,
            "Max":          d["temperature_2m_max"],
            "Min":          d["temperature_2m_min"],
            "Precipitatii": d["precipitation_sum"],
            "OreSoare":     ore_soare,
            "OrePloaie":    ore_ploaie,
            "OreZi":        ore_zi,
            "ProbPloaie":   prob_ploaie,
            "WMO":          codes,
            "ZiTip":        emoji_list,
            "Vanzari":      0.0,
            "Tip":          "prognoza"
        })

    except Exception as e:
        print(f"❌ Eroare prognoză {city_name}: {e}")
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# LOGICA ROBOTULUI (GitHub Actions --update_only)
# ---------------------------------------------------------------------------
if "--update_only" in sys.argv:
    print("🤖 Robotul a pornit...")
    all_new_data = []

    if os.path.exists(FILE_DB) and os.path.getsize(FILE_DB) > 0:
        try:
            df_existing = pd.read_csv(FILE_DB)
            if df_existing.empty or "Data" not in df_existing.columns:
                raise ValueError("Fișier gol sau coloane lipsă.")
            df_existing["Data"] = pd.to_datetime(df_existing["Data"])
            # Păstrăm doar arhiva în CSV (nu prognoza)
            if "Tip" in df_existing.columns:
                df_existing = df_existing[df_existing["Tip"] == "arhiva"]
            last_date = df_existing["Data"].max()
            start_dt  = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
            print(f"📂 Bază găsită. Continuăm de la {start_dt}.")
        except Exception as e:
            print(f"⚠️ Coruptă ({e}). Resetăm.")
            df_existing = None
            start_dt    = "2023-01-01"
    else:
        start_dt    = "2023-01-01"
        df_existing = None
        print(f"🆕 Bază nouă. Descărcăm de la {start_dt}.")

    end_dt = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    if start_dt > end_dt:
        print("✅ Datele sunt deja la zi.")
        sys.exit(0)

    print(f"📅 Interval arhivă: {start_dt} → {end_dt}\n")

    for oras in ORASE_MCDO:
        print(f"🛰️  Arhivă {oras}...")
        try:
            batch = fetch_weather(oras, start_dt, end_dt)
            if not batch.empty:
                print(f"   ✅ {len(batch)} zile.")
                all_new_data.append(batch)
            else:
                print(f"   ⚠️  Niciun răspuns.")
        except Exception as e:
            print(f"   ❌ {e}")

    if all_new_data:
        df_new = pd.concat(all_new_data, ignore_index=True)
        df_new["Data"] = pd.to_datetime(df_new["Data"])

        for col in ["OreSoare", "OrePloaie", "WMO", "ZiTip", "Tip"]:
            if df_existing is not None and col not in df_existing.columns:
                df_existing[col] = None

        if df_existing is not None:
            df_final = pd.concat([df_existing, df_new], ignore_index=True)
            df_final = df_final.drop_duplicates(subset=["Data", "Oras"])
        else:
            df_final = df_new

        df_final = df_final.sort_values(["Oras", "Data"]).reset_index(drop=True)

        if os.path.exists(FILE_DB):
            os.replace(FILE_DB, FILE_DB + ".bak")

        df_final.to_csv(FILE_DB, index=False)
        print(f"\n💾 Succes! {len(df_new)} rânduri noi. Total: {len(df_final)}.")
    else:
        print("🛑 Nu s-a descărcat nimic!")

    sys.exit(0)


# ---------------------------------------------------------------------------
# INTERFAȚA STREAMLIT
# ---------------------------------------------------------------------------
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="📊 Meteo & Vânzări McDonald's")
st.title("📊 Meteo & Vânzări McDonald's România")

if not os.path.exists(FILE_DB) or os.path.getsize(FILE_DB) == 0:
    st.info("⏳ Baza de date nu există. Rulează robotul cu `--update_only` mai întâi.")
    st.stop()

# Încărcăm datele istorice
df = pd.read_csv(FILE_DB)
df["Data"] = pd.to_datetime(df["Data"])
for col in ["OreSoare", "OrePloaie", "ZiTip", "WMO", "Tip"]:
    if col not in df.columns:
        df[col] = None
df["OreSoare"]  = pd.to_numeric(df["OreSoare"],  errors="coerce").fillna(0.0)
df["OrePloaie"] = pd.to_numeric(df["OrePloaie"], errors="coerce").fillna(0.0)

# --- Sidebar ---
st.sidebar.header("🔧 Filtre")
all_cities = sorted(df["Oras"].unique().tolist())
selected_cities = st.sidebar.multiselect("Selectează orașe:", all_cities, default=[all_cities[0]])

min_date = df["Data"].min().date()
max_date = df["Data"].max().date()
date_range = st.sidebar.date_input("Interval date:", value=(min_date, max_date),
                                    min_value=min_date, max_value=max_date)

if len(date_range) == 2:
    s_f, e_f = date_range
    df_plot = df[df["Oras"].isin(selected_cities) &
                 (df["Data"].dt.date >= s_f) &
                 (df["Data"].dt.date <= e_f)].sort_values("Data")
else:
    df_plot = df[df["Oras"].isin(selected_cities)].sort_values("Data")

# --- Metrici ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📅 Zile", len(df_plot))
c2.metric("🌡️ Max", f"{df_plot['Max'].max():.1f}°C" if not df_plot.empty else "—")
c3.metric("❄️ Min",  f"{df_plot['Min'].min():.1f}°C" if not df_plot.empty else "—")
c4.metric("☀️ Ore soare/zi", f"{df_plot['OreSoare'].mean():.1f}h" if not df_plot.empty else "—")
c5.metric("🌧️ Precipitații", f"{df_plot['Precipitatii'].sum():.1f} mm" if not df_plot.empty else "—")

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌡️ Temperaturi", "☀️ Soare & Ploaie",
    "🌧️ Precipitații", "💰 Vânzări",
    "🔍 Comparație Date", "🗺️ Harta McDonald's"
])

# ---------------------------------------------------------------------------
# TAB 1 — TEMPERATURI + distribuție ZiTip
# ---------------------------------------------------------------------------
with tab1:
    fig_temp = px.line(df_plot, x="Data", y=["Max", "Min"],
                       color_discrete_map={"Max": "#e74c3c", "Min": "#3498db"},
                       facet_col="Oras" if len(selected_cities) > 1 else None,
                       title="Evoluție Temperaturi (Max / Min)", labels={"value": "°C", "variable": "Tip"})
    st.plotly_chart(fig_temp, use_container_width=True)

    if df_plot["ZiTip"].notna().any():
        st.subheader("📊 Distribuție tipuri de zile")
        zi_counts = df_plot["ZiTip"].value_counts().reset_index()
        zi_counts.columns = ["Tip Zi", "Număr Zile"]
        fig_zi = px.bar(zi_counts, x="Tip Zi", y="Număr Zile", color="Tip Zi",
                        title="Câte zile din fiecare tip",
                        color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig_zi, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 2 — SOARE & PLOAIE + PROGNOZĂ 7 ZILE REALĂ
# ---------------------------------------------------------------------------
with tab2:
    # --- Prognoză reală 7 zile ---
    st.subheader("🔮 Prognoză meteo reală — 7 zile")
    st.caption("Date live de la Open-Meteo (modele ECMWF + DWD). Actualizate la fiecare rulare.")

    oras_prog = st.selectbox("Alege orașul pentru prognoză:", all_cities, key="prog_oras")

    with st.spinner(f"Se descarcă prognoza pentru {oras_prog}..."):
        df_prog = fetch_forecast(oras_prog, forecast_days=7)

    if not df_prog.empty:
        df_prog["Data"] = pd.to_datetime(df_prog["Data"])
        df_prog["OreSoare"]  = pd.to_numeric(df_prog["OreSoare"],  errors="coerce").fillna(0.0)
        df_prog["OrePloaie"] = pd.to_numeric(df_prog["OrePloaie"], errors="coerce").fillna(0.0)
        df_prog["OreZi"]     = pd.to_numeric(df_prog.get("OreZi", 0), errors="coerce").fillna(0.0)
        df_prog["ProbPloaie"]= pd.to_numeric(df_prog.get("ProbPloaie", 0), errors="coerce").fillna(0.0)

        # Carduri zilnice cu emoji WMO real
        cols_prog = st.columns(len(df_prog))
        for i, (_, row) in enumerate(df_prog.iterrows()):
            with cols_prog[i]:
                data_str = pd.to_datetime(row["Data"]).strftime("%a\n%d %b")
                emoji, desc = wmo_to_emoji(row.get("WMO"))
                st.markdown(f"**{data_str}**")
                st.markdown(f"<div style='font-size:2rem;text-align:center'>{emoji}</div>", unsafe_allow_html=True)
                st.caption(desc)
                st.metric("Max", f"{safe_float(row['Max']):.0f}°C")
                st.metric("Min", f"{safe_float(row['Min']):.0f}°C")
                st.metric("☀️", f"{safe_float(row['OreSoare']):.1f}h")
                st.metric("🌧️ prob", f"{safe_float(row['ProbPloaie']):.0f}%")

        st.divider()

        # Grafic prognoză
        fig_prog = go.Figure()
        fig_prog.add_trace(go.Bar(
            x=df_prog["Data"], y=df_prog["OreSoare"],
            name="Ore soare", marker_color="#f39c12", opacity=0.8
        ))
        fig_prog.add_trace(go.Bar(
            x=df_prog["Data"], y=df_prog["OrePloaie"],
            name="Ore ploaie", marker_color="#3498db", opacity=0.8
        ))
        fig_prog.add_trace(go.Scatter(
            x=df_prog["Data"], y=df_prog["Max"],
            name="Temp Max", line=dict(color="#e74c3c", width=2), yaxis="y2"
        ))
        fig_prog.add_trace(go.Scatter(
            x=df_prog["Data"], y=df_prog["Min"],
            name="Temp Min", line=dict(color="#2980b9", width=2, dash="dot"), yaxis="y2"
        ))
        fig_prog.update_layout(
            title=f"Prognoză 7 zile — {oras_prog}",
            barmode="group",
            yaxis=dict(title="Ore"),
            yaxis2=dict(title="°C", overlaying="y", side="right"),
            legend=dict(orientation="h")
        )
        st.plotly_chart(fig_prog, use_container_width=True)

    st.divider()

    # --- Date istorice ore soare ---
    st.subheader("📈 Ore soare & ploaie — date istorice")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        fig_soare = px.area(df_plot, x="Data", y="OreSoare", color="Oras",
                             title="Ore de soare pe zi (arhivă)",
                             labels={"OreSoare": "Ore"},
                             color_discrete_sequence=["#f39c12", "#e67e22", "#d35400"])
        st.plotly_chart(fig_soare, use_container_width=True)
    with col_s2:
        fig_ploaie_ore = px.area(df_plot, x="Data", y="OrePloaie", color="Oras",
                                  title="Ore de ploaie pe zi (arhivă)",
                                  labels={"OrePloaie": "Ore"},
                                  color_discrete_sequence=["#3498db", "#2980b9"])
        st.plotly_chart(fig_ploaie_ore, use_container_width=True)

    df_copy = df_plot.copy()
    df_copy["Luna"] = df_copy["Data"].dt.to_period("M").astype(str)
    df_luna = df_copy.groupby(["Luna", "Oras"])[["OreSoare", "OrePloaie"]].mean().reset_index()
    fig_luna = px.bar(df_luna, x="Luna", y="OreSoare", color="Oras", barmode="group",
                      title="Medie ore soare pe lună", labels={"OreSoare": "Ore medie/zi"})
    fig_luna.update_xaxes(tickangle=45)
    st.plotly_chart(fig_luna, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 3 — PRECIPITAȚII
# ---------------------------------------------------------------------------
with tab3:
    fig_prec = px.bar(df_plot, x="Data", y="Precipitatii", color="Oras",
                      title="Precipitații zilnice (mm)", labels={"Precipitatii": "mm"})
    st.plotly_chart(fig_prec, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 4 — VÂNZĂRI
# ---------------------------------------------------------------------------
with tab4:
    st.info("💡 Completează coloana 'Vânzări' manual în tabelul de mai jos.")
    fig_vanz = px.line(df_plot, x="Data", y="Vanzari", color="Oras",
                       title="Evoluție Vânzări", labels={"Vanzari": "Vânzări (RON)"})
    st.plotly_chart(fig_vanz, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 5 — COMPARAȚIE DOUĂ DATE
# ---------------------------------------------------------------------------
with tab5:
    st.subheader("🔍 Compară două date pentru același oraș")

    col_oras, col_d1, col_d2 = st.columns(3)
    with col_oras:
        oras_comp = st.selectbox("🏙️ Oraș:", all_cities, key="comp_oras")
    with col_d1:
        data1 = st.date_input("📅 Data 1:", value=min_date, min_value=min_date, max_value=max_date, key="comp_d1")
    with col_d2:
        data2 = st.date_input("📅 Data 2:", value=max_date, min_value=min_date, max_value=max_date, key="comp_d2")

    if data1 == data2:
        st.warning("⚠️ Selectează două date diferite!")
    else:
        df_oras = df[df["Oras"] == oras_comp]
        row1 = df_oras[df_oras["Data"].dt.date == data1]
        row2 = df_oras[df_oras["Data"].dt.date == data2]

        if row1.empty or row2.empty:
            st.error("❌ Una dintre date nu există în baza de date.")
        else:
            r1, r2 = row1.iloc[0], row2.iloc[0]

            max_r1, max_r2     = safe_float(r1["Max"]),          safe_float(r2["Max"])
            min_r1, min_r2     = safe_float(r1["Min"]),          safe_float(r2["Min"])
            prec_r1, prec_r2   = safe_float(r1["Precipitatii"]), safe_float(r2["Precipitatii"])
            soare_r1, soare_r2 = safe_float(r1["OreSoare"]),     safe_float(r2["OreSoare"])
            ploaie_r1,ploaie_r2= safe_float(r1["OrePloaie"]),    safe_float(r2["OrePloaie"])
            vanz_r1, vanz_r2   = safe_float(r1["Vanzari"]),      safe_float(r2["Vanzari"])

            e1, d1_desc = wmo_to_emoji(r1.get("WMO"))
            e2, d2_desc = wmo_to_emoji(r2.get("WMO"))

            st.divider()
            st.markdown(f"### 📊 {oras_comp}: {data1.strftime('%d %b %Y')} vs {data2.strftime('%d %b %Y')}")

            ca, cb = st.columns(2)
            ca.info(f"**{data1.strftime('%d %b %Y')}** {e1} {d1_desc}")
            cb.info(f"**{data2.strftime('%d %b %Y')}** {e2} {d2_desc}")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("🌡️ Temp Max",     f"{max_r2:.1f}°C",    delta=f"{max_r2-max_r1:+.1f}°C")
            c2.metric("❄️ Temp Min",     f"{min_r2:.1f}°C",    delta=f"{min_r2-min_r1:+.1f}°C")
            c3.metric("🌧️ Precipitații", f"{prec_r2:.1f} mm",  delta=f"{prec_r2-prec_r1:+.1f} mm")
            c4.metric("☀️ Ore soare",    f"{soare_r2:.1f}h",   delta=f"{soare_r2-soare_r1:+.1f}h")
            c5.metric("💰 Vânzări",      f"{vanz_r2:.0f} RON", delta=f"{vanz_r2-vanz_r1:+.0f} RON")

            st.divider()
            df_comp_chart = pd.DataFrame({
                "Indicator": ["Temp Max (°C)", "Temp Min (°C)", "Precipitații (mm)", "Ore Soare"],
                data1.strftime('%d %b %Y'): [max_r1, min_r1, prec_r1, soare_r1],
                data2.strftime('%d %b %Y'): [max_r2, min_r2, prec_r2, soare_r2],
            })
            fig_bar = px.bar(df_comp_chart.melt(id_vars="Indicator", var_name="Data", value_name="Valoare"),
                             x="Indicator", y="Valoare", color="Data", barmode="group",
                             color_discrete_sequence=["#e74c3c", "#3498db"],
                             title=f"Comparație {oras_comp}")
            st.plotly_chart(fig_bar, use_container_width=True)

            df_tabel = pd.DataFrame({
                "Indicator": ["Temp Max (°C)", "Temp Min (°C)", "Precipitații (mm)", "Ore Soare", "Ore Ploaie", "Vânzări (RON)"],
                data1.strftime('%d %b %Y'): [f"{max_r1:.1f}", f"{min_r1:.1f}", f"{prec_r1:.1f}", f"{soare_r1:.1f}", f"{ploaie_r1:.1f}", f"{vanz_r1:.0f}"],
                data2.strftime('%d %b %Y'): [f"{max_r2:.1f}", f"{min_r2:.1f}", f"{prec_r2:.1f}", f"{soare_r2:.1f}", f"{ploaie_r2:.1f}", f"{vanz_r2:.0f}"],
                "Diferență": [
                    f"{max_r2-max_r1:+.1f}°C", f"{min_r2-min_r1:+.1f}°C",
                    f"{prec_r2-prec_r1:+.1f} mm", f"{soare_r2-soare_r1:+.1f}h",
                    f"{ploaie_r2-ploaie_r1:+.1f}h", f"{vanz_r2-vanz_r1:+.0f} RON"
                ]
            })
            st.dataframe(df_tabel, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 6 — HARTA McDONALD'S ROMÂNIA
# ---------------------------------------------------------------------------
with tab6:
    st.subheader("🗺️ Toate restaurantele McDonald's din România")
    st.caption("108 restaurante în 33 de orașe — 2025")

    locatii_mcdo = [
        {"oras": "București",   "nume": "McDonald's Magheru",           "lat": 44.4445, "lon": 26.0983},
        {"oras": "București",   "nume": "McDonald's Unirii",             "lat": 44.4286, "lon": 26.1043},
        {"oras": "București",   "nume": "McDonald's Mihai Bravu",        "lat": 44.4196, "lon": 26.1371},
        {"oras": "București",   "nume": "McDonald's Brașov (sect 6)",    "lat": 44.4187, "lon": 26.0350},
        {"oras": "București",   "nume": "McDonald's Basarabia",          "lat": 44.4370, "lon": 26.1672},
        {"oras": "Cluj-Napoca", "nume": "McDonald's Primăverii",         "lat": 46.7540, "lon": 23.5541},
        {"oras": "Cluj-Napoca", "nume": "McDonald's Mihai Viteazu",      "lat": 46.7742, "lon": 23.5929},
        {"oras": "Timișoara",   "nume": "McDonald's Rebreanu",           "lat": 45.7390, "lon": 21.2409},
        {"oras": "Timișoara",   "nume": "McDonald's Circumvalațiunii",   "lat": 45.7593, "lon": 21.2172},
        {"oras": "Iași",        "nume": "McDonald's Gării",              "lat": 47.1654, "lon": 27.5709},
        {"oras": "Iași",        "nume": "McDonald's Palas",              "lat": 47.1572, "lon": 27.5893},
        {"oras": "Brașov",      "nume": "McDonald's Brașov",             "lat": 45.6500, "lon": 25.5900},
        {"oras": "Constanța",   "nume": "McDonald's Mamaia",             "lat": 44.2050, "lon": 28.6439},
        {"oras": "Constanța",   "nume": "McDonald's Ștefan cel Mare",    "lat": 44.1782, "lon": 28.6469},
        {"oras": "Craiova",     "nume": "McDonald's Calea București",    "lat": 44.3178, "lon": 23.8101},
        {"oras": "Craiova",     "nume": "McDonald's Electroputere",      "lat": 44.3130, "lon": 23.8315},
        {"oras": "Sibiu",       "nume": "McDonald's Sibiu",              "lat": 45.7941, "lon": 24.1498},
        {"oras": "Oradea",      "nume": "McDonald's Republicii",         "lat": 47.0623, "lon": 21.9380},
        {"oras": "Oradea",      "nume": "McDonald's Ciheiului",          "lat": 47.0326, "lon": 21.9501},
        {"oras": "Ploiești",    "nume": "McDonald's Republicii",         "lat": 44.9525, "lon": 25.9995},
        {"oras": "Ploiești",    "nume": "McDonald's Mercur",             "lat": 44.9405, "lon": 26.0250},
        {"oras": "Pitești",     "nume": "McDonald's Pitești",            "lat": 44.8565, "lon": 24.8694},
        {"oras": "Bacău",       "nume": "McDonald's Bacău",              "lat": 46.5671, "lon": 26.9146},
        {"oras": "Galați",      "nume": "McDonald's Galați",             "lat": 45.4353, "lon": 28.0476},
        {"oras": "Brăila",      "nume": "McDonald's Brăila",             "lat": 45.2692, "lon": 27.9574},
        {"oras": "Târgu Mureș", "nume": "McDonald's Târgu Mureș",        "lat": 46.5386, "lon": 24.5579},
        {"oras": "Arad",        "nume": "McDonald's Arad",               "lat": 46.1866, "lon": 21.3123},
        {"oras": "Deva",        "nume": "McDonald's Deva",               "lat": 45.8833, "lon": 22.9117},
        {"oras": "Rm. Vâlcea",  "nume": "McDonald's Rm. Vâlcea",        "lat": 45.0997, "lon": 24.3693},
        {"oras": "Suceava",     "nume": "McDonald's Suceava",            "lat": 47.6520, "lon": 26.2563},
        {"oras": "Piatra Neamț","nume": "McDonald's Piatra Neamț",       "lat": 46.9251, "lon": 26.3718},
        {"oras": "Târgoviște",  "nume": "McDonald's Târgoviște",         "lat": 44.9268, "lon": 25.4566},
        {"oras": "Buzău",       "nume": "McDonald's Buzău",              "lat": 45.1500, "lon": 26.8200},
        {"oras": "Botoșani",    "nume": "McDonald's Botoșani",           "lat": 47.7402, "lon": 26.6674},
        {"oras": "Focșani",     "nume": "McDonald's Focșani",            "lat": 45.6990, "lon": 27.1872},
        {"oras": "Slatina",     "nume": "McDonald's Slatina",            "lat": 44.4318, "lon": 24.3705},
        {"oras": "Dr.Tr.Severin","nume": "McDonald's Dr.Tr.Severin",     "lat": 44.6282, "lon": 22.6568},
        {"oras": "Alba Iulia",  "nume": "McDonald's Alba Iulia",         "lat": 46.0669, "lon": 23.5806},
        {"oras": "Dumbrăvița",  "nume": "McDonald's Dumbrăvița",         "lat": 45.7980, "lon": 21.2700},
        {"oras": "Bistrița",    "nume": "McDonald's Bistrița",           "lat": 47.1326, "lon": 24.4965},
    ]

    df_loc = pd.DataFrame(locatii_mcdo)
    ca, cb, cc = st.columns(3)
    ca.metric("🍔 Total restaurante", len(df_loc))
    cb.metric("🏙️ Orașe",            df_loc["oras"].nunique())
    cc.metric("📍 Cel mai mare oraș", "București")

    fig_map = px.scatter_map(df_loc, lat="lat", lon="lon",
                              hover_name="nume",
                              hover_data={"oras": True, "lat": False, "lon": False},
                              color="oras", zoom=6,
                              center={"lat": 45.9, "lon": 24.9},
                              title="Restaurante McDonald's România", height=600)
    fig_map.update_layout(map_style="open-street-map")
    fig_map.update_traces(marker=dict(size=12))
    st.plotly_chart(fig_map, use_container_width=True)

    df_per_oras = df_loc.groupby("oras").size().reset_index(name="Nr. Restaurante")
    df_per_oras = df_per_oras.sort_values("Nr. Restaurante", ascending=False).reset_index(drop=True)
    st.dataframe(df_per_oras, use_container_width=True, hide_index=True)

st.divider()

# --- Tabel editabil ---
st.subheader("📋 Tabel Date")
cols_show = [c for c in ["Data", "Oras", "ZiTip", "Max", "Min", "Precipitatii",
                          "OreSoare", "OrePloaie", "Vanzari"] if c in df_plot.columns]
edited = st.data_editor(
    df_plot[cols_show], use_container_width=True, num_rows="fixed",
    column_config={
        "ZiTip":        st.column_config.TextColumn("🌤️ Tip Zi"),
        "Vanzari":      st.column_config.NumberColumn("Vânzări (RON)", min_value=0, format="%.2f"),
        "Max":          st.column_config.NumberColumn("Temp Max (°C)", format="%.1f"),
        "Min":          st.column_config.NumberColumn("Temp Min (°C)", format="%.1f"),
        "Precipitatii": st.column_config.NumberColumn("Precipitații (mm)", format="%.1f"),
        "OreSoare":     st.column_config.NumberColumn("☀️ Ore Soare", format="%.1f"),
        "OrePloaie":    st.column_config.NumberColumn("🌧️ Ore Ploaie", format="%.1f"),
    }
)

if st.button("💾 Salvează Modificări", type="primary"):
    try:
        if os.path.exists(FILE_DB):
            os.replace(FILE_DB, FILE_DB + ".bak")
        df_full = pd.read_csv(FILE_DB + ".bak")
        df_full["Data"] = pd.to_datetime(df_full["Data"])
        df_full = df_full.set_index(["Data", "Oras"])
        edited_copy = edited.copy()
        edited_copy["Data"] = pd.to_datetime(edited_copy["Data"])
        edited_copy = edited_copy.set_index(["Data", "Oras"])
        df_full.update(edited_copy)
        df_full.reset_index().to_csv(FILE_DB, index=False)
        st.success("✅ Salvat! Backup păstrat în `.bak`.")
    except Exception as e:
        st.error(f"❌ Eroare: {e}")
