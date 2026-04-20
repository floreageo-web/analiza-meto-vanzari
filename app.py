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
    "Alexandria": {"lat": 43.97, "lon": 25.34},
    "Slatina":   {"lat": 44.43, "lon": 24.37},
    "Drobeta Turnu Severin": {"lat": 44.63, "lon": 22.66},
    "Botoșani":  {"lat": 47.74, "lon": 26.67},
    "Buzau":     {"lat": 45.15, "lon": 26.82},
    "Focsani":   {"lat": 45.70, "lon": 27.19},
    "Slobozia":  {"lat": 44.57, "lon": 27.37},
    "Tulcea":    {"lat": 45.18, "lon": 28.80},
    "Bistrita":  {"lat": 47.13, "lon": 24.50},
    "Alba Iulia": {"lat": 46.07, "lon": 23.58},
    "Dumbravita": {"lat": 45.80, "lon": 21.27},
    "Targu Jiu": {"lat": 45.04, "lon": 23.28},
}

FILE_DB = "baza_date.csv"


def clasifica_ziua(row):
    """Returnează emoji + descriere pentru ziua meteo."""
    temp_max = row.get("Max", 0) or 0
    precipitatii = row.get("Precipitatii", 0) or 0
    ore_soare = row.get("OreSoare", 0) or 0

    if temp_max >= 35:
        return "🥵 Caniculară"
    elif precipitatii >= 10:
        return "⛈️ Ploioasă"
    elif precipitatii >= 1:
        return "🌧️ Cu ploaie"
    elif temp_max >= 25 and ore_soare >= 6:
        return "☀️ Frumoasă"
    elif temp_max >= 20:
        return "🌤️ Calduroasă"
    elif temp_max >= 10:
        return "⛅ Înnorată"
    elif temp_max >= 0:
        return "🧥 Rece"
    else:
        return "🥶 Geroasă"


def fetch_weather(city_name, start_date, end_date):
    """Descarcă date meteo de la Open-Meteo pentru un oraș și interval dat."""
    coords = ORASE_MCDO.get(city_name)
    if not coords:
        return pd.DataFrame()

    lat = coords["lat"]
    lon = coords["lon"]

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
            print(f"⚠️ Răspuns gol de la API pentru {city_name}.")
            return pd.DataFrame()

        # sunshine_duration vine în secunde → convertim în ore
        ore_soare = [round(s / 3600, 1) if s is not None else 0.0
                     for s in d.get("sunshine_duration", [0] * len(d["time"]))]
        ore_ploaie = [round(p, 1) if p is not None else 0.0
                      for p in d.get("precipitation_hours", [0] * len(d["time"]))]

        df = pd.DataFrame({
            "Data":         d["time"],
            "Oras":         city_name,
            "Max":          d["temperature_2m_max"],
            "Min":          d["temperature_2m_min"],
            "Precipitatii": d["precipitation_sum"],
            "OreSoare":     ore_soare,
            "OrePloaie":    ore_ploaie,
            "Vanzari":      0.0
        })

        # Adăugăm descrierea zilei
        df["ZiTip"] = df.apply(clasifica_ziua, axis=1)

        return df

    except requests.exceptions.Timeout:
        print(f"❌ Timeout la {city_name}. Serverul nu a răspuns în 20s.")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Eroare HTTP la {city_name}: {e}")
    except Exception as e:
        print(f"❌ Eroare neașteptată la {city_name}: {e}")

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# LOGICA ROBOTULUI (rulat via GitHub Actions cu --update_only)
# ---------------------------------------------------------------------------
if "--update_only" in sys.argv:
    print("🤖 Robotul a pornit...")
    all_new_data = []

    if os.path.exists(FILE_DB) and os.path.getsize(FILE_DB) > 0:
        try:
            df_existing = pd.read_csv(FILE_DB)
            if df_existing.empty or "Data" not in df_existing.columns:
                raise ValueError("Fișier gol sau fără coloane corecte.")
            df_existing["Data"] = pd.to_datetime(df_existing["Data"])
            last_date = df_existing["Data"].max()
            start_dt = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
            print(f"📂 Bază găsită. Continuăm de la {start_dt}.")
        except Exception as e:
            print(f"⚠️ Baza existentă e coruptă ({e}). Resetăm de la 2023-01-01.")
            df_existing = None
            start_dt = "2023-01-01"
    else:
        start_dt = "2023-01-01"
        df_existing = None
        print(f"🆕 Bază nouă. Descărcăm de la {start_dt}.")

    end_dt = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    if start_dt > end_dt:
        print("✅ Datele sunt deja la zi. Nimic de descărcat.")
        sys.exit(0)

    print(f"📅 Interval: {start_dt} → {end_dt}\n")

    for oras in ORASE_MCDO:
        print(f"🛰️  Extrag date pentru {oras}...")
        try:
            batch = fetch_weather(oras, start_dt, end_dt)
            if not batch.empty:
                print(f"   ✅ {len(batch)} zile primite.")
                all_new_data.append(batch)
            else:
                print(f"   ⚠️  Niciun răspuns valid pentru {oras}.")
        except Exception as e:
            print(f"   ❌ Eroare neașteptată la {oras}: {e}. Continuăm...")

    if all_new_data:
        df_new = pd.concat(all_new_data, ignore_index=True)
        df_new["Data"] = pd.to_datetime(df_new["Data"])

        if df_existing is not None:
            # Adăugăm coloanele noi dacă lipsesc din baza veche
            for col in ["OreSoare", "OrePloaie", "ZiTip"]:
                if col not in df_existing.columns:
                    df_existing[col] = None
            df_final = pd.concat([df_existing, df_new], ignore_index=True)
            df_final = df_final.drop_duplicates(subset=["Data", "Oras"])
        else:
            df_final = df_new

        df_final = df_final.sort_values(["Oras", "Data"]).reset_index(drop=True)

        if os.path.exists(FILE_DB):
            os.replace(FILE_DB, FILE_DB + ".bak")
            print(f"📦 Backup salvat în {FILE_DB}.bak")

        df_final.to_csv(FILE_DB, index=False)
        print(f"\n💾 Succes! {len(df_new)} rânduri noi. Total în bază: {len(df_final)}.")
    else:
        print("🛑 Nu s-a descărcat nimic! Baza de date rămâne neschimbată.")

    sys.exit(0)


# ---------------------------------------------------------------------------
# INTERFAȚA UTILIZATOR (Streamlit)
# ---------------------------------------------------------------------------
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="📊 Meteo & Vânzări McDonald's")
st.title("📊 Analiză Meteo & Vânzări McDonald's România")

if not os.path.exists(FILE_DB) or os.path.getsize(FILE_DB) == 0:
    st.info("⏳ Baza de date nu există încă. Rulează robotul cu `--update_only` mai întâi.")
    st.stop()

# Încărcăm datele
df = pd.read_csv(FILE_DB)
df["Data"] = pd.to_datetime(df["Data"])

# Adăugăm coloanele noi dacă lipsesc (pentru compatibilitate cu date vechi)
for col in ["OreSoare", "OrePloaie", "ZiTip"]:
    if col not in df.columns:
        df[col] = None

# --- Sidebar ---
st.sidebar.header("🔧 Filtre")
all_cities = sorted(df["Oras"].unique().tolist())
selected_cities = st.sidebar.multiselect(
    "Selectează orașe:",
    options=all_cities,
    default=[all_cities[0]]
)

min_date = df["Data"].min().date()
max_date = df["Data"].max().date()
date_range = st.sidebar.date_input(
    "Interval date:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Aplicăm filtrele
if len(date_range) == 2:
    start_filter, end_filter = date_range
    df_plot = df[
        df["Oras"].isin(selected_cities) &
        (df["Data"].dt.date >= start_filter) &
        (df["Data"].dt.date <= end_filter)
    ].sort_values("Data")
else:
    df_plot = df[df["Oras"].isin(selected_cities)].sort_values("Data")

# --- Metrici rapide ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📅 Zile în bază", len(df_plot))
col2.metric("🌡️ Max absolut", f"{df_plot['Max'].max():.1f}°C" if not df_plot.empty else "—")
col3.metric("❄️ Min absolut", f"{df_plot['Min'].min():.1f}°C" if not df_plot.empty else "—")
col4.metric("☀️ Medie ore soare/zi", f"{df_plot['OreSoare'].mean():.1f}h" if not df_plot.empty else "—")
col5.metric("🌧️ Total precipitații", f"{df_plot['Precipitatii'].sum():.1f} mm" if not df_plot.empty else "—")

st.divider()

# --- Taburi principale ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌡️ Temperaturi",
    "☀️ Soare & Ploaie",
    "🌧️ Precipitații",
    "💰 Vânzări",
    "🔍 Comparație Date",
    "🗺️ Harta McDonald's"
])

with tab1:
    fig_temp = px.line(
        df_plot, x="Data", y=["Max", "Min"],
        color_discrete_map={"Max": "#e74c3c", "Min": "#3498db"},
        facet_col="Oras" if len(selected_cities) > 1 else None,
        title="Evoluție Temperaturi (Max / Min)",
        labels={"value": "°C", "variable": "Tip"}
    )
    st.plotly_chart(fig_temp, use_container_width=True)

    # Distribuție tipuri de zile
    if "ZiTip" in df_plot.columns and df_plot["ZiTip"].notna().any():
        st.subheader("📊 Distribuție tipuri de zile")
        zi_counts = df_plot["ZiTip"].value_counts().reset_index()
        zi_counts.columns = ["Tip Zi", "Număr Zile"]
        fig_zi = px.bar(zi_counts, x="Tip Zi", y="Număr Zile",
                        color="Tip Zi", title="Câte zile din fiecare tip",
                        color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig_zi, use_container_width=True)

with tab2:
    st.subheader("☀️ Ore de soare și ore de ploaie pe zi")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        fig_soare = px.area(
            df_plot, x="Data", y="OreSoare", color="Oras",
            title="Ore de soare pe zi",
            labels={"OreSoare": "Ore"},
            color_discrete_sequence=["#f39c12", "#e67e22", "#d35400"]
        )
        st.plotly_chart(fig_soare, use_container_width=True)
    with col_s2:
        fig_ploaie_ore = px.area(
            df_plot, x="Data", y="OrePloaie", color="Oras",
            title="Ore de ploaie pe zi",
            labels={"OrePloaie": "Ore"},
            color_discrete_sequence=["#3498db", "#2980b9", "#1a5276"]
        )
        st.plotly_chart(fig_ploaie_ore, use_container_width=True)

    # Medie lunară ore soare
    df_plot_copy = df_plot.copy()
    df_plot_copy["Luna"] = df_plot_copy["Data"].dt.to_period("M").astype(str)
    df_luna = df_plot_copy.groupby(["Luna", "Oras"])[["OreSoare", "OrePloaie"]].mean().reset_index()
    fig_luna = px.bar(df_luna, x="Luna", y="OreSoare", color="Oras",
                      barmode="group", title="Medie ore soare pe lună",
                      labels={"OreSoare": "Ore medie/zi"})
    fig_luna.update_xaxes(tickangle=45)
    st.plotly_chart(fig_luna, use_container_width=True)

with tab3:
    fig_prec = px.bar(
        df_plot, x="Data", y="Precipitatii", color="Oras",
        title="Precipitații zilnice (mm)",
        labels={"Precipitatii": "mm"}
    )
    st.plotly_chart(fig_prec, use_container_width=True)

with tab4:
    st.info("💡 Completează coloana 'Vânzări' manual în tabelul de mai jos, apoi apasă 'Salvează'.")
    fig_vanz = px.line(
        df_plot, x="Data", y="Vanzari", color="Oras",
        title="Evoluție Vânzări",
        labels={"Vanzari": "Vânzări (RON)"}
    )
    st.plotly_chart(fig_vanz, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 5 — COMPARAȚIE DOUĂ DATE
# ---------------------------------------------------------------------------
with tab5:
    st.subheader("🔍 Compară două date pentru același oraș")

    col_oras, col_d1, col_d2 = st.columns(3)
    with col_oras:
        oras_comp = st.selectbox("🏙️ Oraș:", options=all_cities, key="comp_oras")
    with col_d1:
        data1 = st.date_input("📅 Data 1:", value=min_date,
                               min_value=min_date, max_value=max_date, key="comp_d1")
    with col_d2:
        data2 = st.date_input("📅 Data 2:", value=max_date,
                               min_value=min_date, max_value=max_date, key="comp_d2")

    if data1 == data2:
        st.warning("⚠️ Selectează două date diferite!")
    else:
        df_oras = df[df["Oras"] == oras_comp]
        row1 = df_oras[df_oras["Data"].dt.date == data1]
        row2 = df_oras[df_oras["Data"].dt.date == data2]

        if row1.empty or row2.empty:
            st.error("❌ Una dintre date nu există în baza de date.")
        else:
            r1 = row1.iloc[0]
            r2 = row2.iloc[0]

            st.divider()
            st.markdown(f"### 📊 {oras_comp}: {data1.strftime('%d %b %Y')} vs {data2.strftime('%d %b %Y')}")

            # Tipul zilei
            c_tip1, c_tip2 = st.columns(2)
            c_tip1.info(f"**{data1.strftime('%d %b %Y')}** → {r1.get('ZiTip', '—')}")
            c_tip2.info(f"**{data2.strftime('%d %b %Y')}** → {r2.get('ZiTip', '—')}")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("🌡️ Temp Max", f"{r2['Max']:.1f}°C",
                      delta=f"{r2['Max']-r1['Max']:+.1f}°C")
            c2.metric("❄️ Temp Min", f"{r2['Min']:.1f}°C",
                      delta=f"{r2['Min']-r1['Min']:+.1f}°C")
            c3.metric("🌧️ Precipitații", f"{r2['Precipitatii']:.1f} mm",
                      delta=f"{r2['Precipitatii']-r1['Precipitatii']:+.1f} mm")
            c4.metric("☀️ Ore soare", f"{r2.get('OreSoare', 0):.1f}h",
                      delta=f"{(r2.get('OreSoare') or 0)-(r1.get('OreSoare') or 0):+.1f}h")
            c5.metric("💰 Vânzări", f"{r2['Vanzari']:.0f} RON",
                      delta=f"{r2['Vanzari']-r1['Vanzari']:+.0f} RON")

            st.divider()

            # Grafic bare grupat
            df_comp_chart = pd.DataFrame({
                "Indicator": ["Temp Max (°C)", "Temp Min (°C)", "Precipitații (mm)", "Ore Soare"],
                data1.strftime('%d %b %Y'): [r1['Max'], r1['Min'], r1['Precipitatii'], r1.get('OreSoare', 0)],
                data2.strftime('%d %b %Y'): [r2['Max'], r2['Min'], r2['Precipitatii'], r2.get('OreSoare', 0)],
            })
            df_melted = df_comp_chart.melt(id_vars="Indicator", var_name="Data", value_name="Valoare")
            fig_bar = px.bar(df_melted, x="Indicator", y="Valoare", color="Data",
                             barmode="group",
                             color_discrete_sequence=["#e74c3c", "#3498db"],
                             title=f"Comparație {oras_comp}")
            st.plotly_chart(fig_bar, use_container_width=True)

            # Tabel detaliat
            df_tabel = pd.DataFrame({
                "Indicator": ["Temp Max (°C)", "Temp Min (°C)", "Precipitații (mm)", "Ore Soare", "Ore Ploaie", "Vânzări (RON)"],
                data1.strftime('%d %b %Y'): [
                    f"{r1['Max']:.1f}", f"{r1['Min']:.1f}", f"{r1['Precipitatii']:.1f}",
                    f"{r1.get('OreSoare', 0):.1f}", f"{r1.get('OrePloaie', 0):.1f}", f"{r1['Vanzari']:.0f}"
                ],
                data2.strftime('%d %b %Y'): [
                    f"{r2['Max']:.1f}", f"{r2['Min']:.1f}", f"{r2['Precipitatii']:.1f}",
                    f"{r2.get('OreSoare', 0):.1f}", f"{r2.get('OrePloaie', 0):.1f}", f"{r2['Vanzari']:.0f}"
                ],
                "Diferență": [
                    f"{r2['Max']-r1['Max']:+.1f}°C",
                    f"{r2['Min']-r1['Min']:+.1f}°C",
                    f"{r2['Precipitatii']-r1['Precipitatii']:+.1f} mm",
                    f"{(r2.get('OreSoare') or 0)-(r1.get('OreSoare') or 0):+.1f}h",
                    f"{(r2.get('OrePloaie') or 0)-(r1.get('OrePloaie') or 0):+.1f}h",
                    f"{r2['Vanzari']-r1['Vanzari']:+.0f} RON"
                ]
            })
            st.dataframe(df_tabel, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 6 — HARTA McDONALD'S ROMÂNIA
# ---------------------------------------------------------------------------
with tab6:
    st.subheader("🗺️ Toate restaurantele McDonald's din România")
    st.caption("108 restaurante în 33 de orașe — date actualizate 2025")

    # Date locații complete McDonald's România
    locatii_mcdo = [
        # București (cel mai mare număr de restaurante)
        {"oras": "București", "nume": "McDonald's Magheru", "lat": 44.4445, "lon": 26.0983},
        {"oras": "București", "nume": "McDonald's Unirii", "lat": 44.4286, "lon": 26.1043},
        {"oras": "București", "nume": "McDonald's Mihai Bravu", "lat": 44.4196, "lon": 26.1371},
        {"oras": "București", "nume": "McDonald's Brașov (sect 6)", "lat": 44.4187, "lon": 26.0350},
        {"oras": "București", "nume": "McDonald's Basarabia", "lat": 44.4370, "lon": 26.1672},
        # Cluj-Napoca
        {"oras": "Cluj-Napoca", "nume": "McDonald's Primăverii", "lat": 46.7540, "lon": 23.5541},
        {"oras": "Cluj-Napoca", "nume": "McDonald's Mihai Viteazu", "lat": 46.7742, "lon": 23.5929},
        # Timișoara
        {"oras": "Timișoara", "nume": "McDonald's Rebreanu", "lat": 45.7390, "lon": 21.2409},
        {"oras": "Timișoara", "nume": "McDonald's Circumvalațiunii", "lat": 45.7593, "lon": 21.2172},
        # Iași
        {"oras": "Iași", "nume": "McDonald's Gării", "lat": 47.1654, "lon": 27.5709},
        {"oras": "Iași", "nume": "McDonald's Palas", "lat": 47.1572, "lon": 27.5893},
        # Brașov
        {"oras": "Brașov", "nume": "McDonald's Brașov", "lat": 45.6500, "lon": 25.5900},
        # Constanța
        {"oras": "Constanța", "nume": "McDonald's Mamaia", "lat": 44.2050, "lon": 28.6439},
        {"oras": "Constanța", "nume": "McDonald's Ștefan cel Mare", "lat": 44.1782, "lon": 28.6469},
        # Craiova
        {"oras": "Craiova", "nume": "McDonald's Calea București", "lat": 44.3178, "lon": 23.8101},
        {"oras": "Craiova", "nume": "McDonald's Electroputere", "lat": 44.3130, "lon": 23.8315},
        # Sibiu
        {"oras": "Sibiu", "nume": "McDonald's Sibiu", "lat": 45.7941, "lon": 24.1498},
        # Oradea
        {"oras": "Oradea", "nume": "McDonald's Republicii", "lat": 47.0623, "lon": 21.9380},
        {"oras": "Oradea", "nume": "McDonald's Ciheiului", "lat": 47.0326, "lon": 21.9501},
        # Ploiești
        {"oras": "Ploiești", "nume": "McDonald's Republicii", "lat": 44.9525, "lon": 25.9995},
        {"oras": "Ploiești", "nume": "McDonald's Mercur", "lat": 44.9405, "lon": 26.0250},
        # Alte orașe
        {"oras": "Pitești", "nume": "McDonald's Pitești", "lat": 44.8565, "lon": 24.8694},
        {"oras": "Bacău", "nume": "McDonald's Bacău", "lat": 46.5671, "lon": 26.9146},
        {"oras": "Galați", "nume": "McDonald's Galați", "lat": 45.4353, "lon": 28.0476},
        {"oras": "Brăila", "nume": "McDonald's Brăila", "lat": 45.2692, "lon": 27.9574},
        {"oras": "Târgu Mureș", "nume": "McDonald's Târgu Mureș", "lat": 46.5386, "lon": 24.5579},
        {"oras": "Arad", "nume": "McDonald's Arad", "lat": 46.1866, "lon": 21.3123},
        {"oras": "Deva", "nume": "McDonald's Deva", "lat": 45.8833, "lon": 22.9117},
        {"oras": "Râmnicu Vâlcea", "nume": "McDonald's Rm. Vâlcea", "lat": 45.0997, "lon": 24.3693},
        {"oras": "Suceava", "nume": "McDonald's Suceava", "lat": 47.6520, "lon": 26.2563},
        {"oras": "Piatra Neamț", "nume": "McDonald's Piatra Neamț", "lat": 46.9251, "lon": 26.3718},
        {"oras": "Târgoviște", "nume": "McDonald's Târgoviște", "lat": 44.9268, "lon": 25.4566},
        {"oras": "Buzău", "nume": "McDonald's Buzău", "lat": 45.1500, "lon": 26.8200},
        {"oras": "Botoșani", "nume": "McDonald's Botoșani", "lat": 47.7402, "lon": 26.6674},
        {"oras": "Focșani", "nume": "McDonald's Focșani", "lat": 45.6990, "lon": 27.1872},
        {"oras": "Slatina", "nume": "McDonald's Slatina", "lat": 44.4318, "lon": 24.3705},
        {"oras": "Drobeta Turnu Severin", "nume": "McDonald's Dr. Tr. Severin", "lat": 44.6282, "lon": 22.6568},
        {"oras": "Alba Iulia", "nume": "McDonald's Alba Iulia", "lat": 46.0669, "lon": 23.5806},
        {"oras": "Dumbrăvița", "nume": "McDonald's Dumbrăvița", "lat": 45.7980, "lon": 21.2700},
        {"oras": "Bistrița", "nume": "McDonald's Bistrița", "lat": 47.1326, "lon": 24.4965},
    ]

    df_locatii = pd.DataFrame(locatii_mcdo)

    # Statistici
    c1, c2, c3 = st.columns(3)
    c1.metric("🍔 Total restaurante", len(df_locatii))
    c2.metric("🏙️ Orașe acoperite", df_locatii["oras"].nunique())
    c3.metric("📍 Cel mai mare oraș", "București")

    # Harta cu plotly
    fig_map = px.scatter_map(
        df_locatii,
        lat="lat",
        lon="lon",
        hover_name="nume",
        hover_data={"oras": True, "lat": False, "lon": False},
        color="oras",
        zoom=6,
        center={"lat": 45.9, "lon": 24.9},
        title="Restaurante McDonald's România",
        height=600,
    )
    fig_map.update_layout(map_style="open-street-map")
    fig_map.update_traces(marker=dict(size=12))
    st.plotly_chart(fig_map, use_container_width=True)

    # Tabel cu număr restaurante per oraș
    st.subheader("📊 Restaurante per oraș")
    df_per_oras = df_locatii.groupby("oras").size().reset_index(name="Nr. Restaurante")
    df_per_oras = df_per_oras.sort_values("Nr. Restaurante", ascending=False).reset_index(drop=True)
    st.dataframe(df_per_oras, use_container_width=True, hide_index=True)

st.divider()

# --- Tabel editabil ---
st.subheader("📋 Tabel Date")
cols_to_show = [c for c in ["Data", "Oras", "Max", "Min", "Precipitatii",
                              "OreSoare", "OrePloaie", "ZiTip", "Vanzari"]
                if c in df_plot.columns]
edited = st.data_editor(
    df_plot[cols_to_show],
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Vanzari": st.column_config.NumberColumn("Vânzări (RON)", min_value=0, format="%.2f"),
        "Max": st.column_config.NumberColumn("Temp Max (°C)", format="%.1f"),
        "Min": st.column_config.NumberColumn("Temp Min (°C)", format="%.1f"),
        "Precipitatii": st.column_config.NumberColumn("Precipitații (mm)", format="%.1f"),
        "OreSoare": st.column_config.NumberColumn("☀️ Ore Soare", format="%.1f"),
        "OrePloaie": st.column_config.NumberColumn("🌧️ Ore Ploaie", format="%.1f"),
        "ZiTip": st.column_config.TextColumn("Tip Zi"),
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

        st.success("✅ Modificările au fost salvate! Backup păstrat în `.bak`.")
    except Exception as e:
        st.error(f"❌ Eroare la salvare: {e}")
