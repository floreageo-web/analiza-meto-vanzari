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
    "Ploiesti":  {"lat": 44.93, "lon": 26.03}
}

FILE_DB = "baza_date.csv"


def fetch_weather(city_name, start_date, end_date):
    """Descarcă date meteo de la Open-Meteo pentru un oraș și interval dat."""
    lat = ORASE_MCDO[city_name]["lat"]
    lon = ORASE_MCDO[city_name]["lon"]

    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        f"&timezone=Europe%2FBerlin"
    )

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        d = r.json().get("daily", {})

        if not d or not d.get("time"):
            print(f"⚠️ Răspuns gol de la API pentru {city_name}.")
            return pd.DataFrame()

        return pd.DataFrame({
            "Data":         d["time"],
            "Oras":         city_name,
            "Max":          d["temperature_2m_max"],
            "Min":          d["temperature_2m_min"],
            "Precipitatii": d["precipitation_sum"],
            "Vanzari":      0.0
        })

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
st.title("📊 Analiză Meteo & Vânzări")

if not os.path.exists(FILE_DB) or os.path.getsize(FILE_DB) == 0:
    st.info("⏳ Baza de date nu există încă. Rulează robotul cu `--update_only` mai întâi.")
    st.stop()

# Încărcăm datele
df = pd.read_csv(FILE_DB)
df["Data"] = pd.to_datetime(df["Data"])

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
col1, col2, col3, col4 = st.columns(4)
col1.metric("📅 Zile în bază", len(df_plot))
col2.metric("🌡️ Max absolut", f"{df_plot['Max'].max():.1f}°C" if not df_plot.empty else "—")
col3.metric("❄️ Min absolut", f"{df_plot['Min'].min():.1f}°C" if not df_plot.empty else "—")
col4.metric("🌧️ Total precipitații", f"{df_plot['Precipitatii'].sum():.1f} mm" if not df_plot.empty else "—")

st.divider()

# --- Taburi principale ---
tab1, tab2, tab3, tab4 = st.tabs(["🌡️ Temperaturi", "🌧️ Precipitații", "💰 Vânzări", "🔍 Comparație Date"])

with tab1:
    fig_temp = px.line(
        df_plot, x="Data", y=["Max", "Min"],
        color_discrete_map={"Max": "#e74c3c", "Min": "#3498db"},
        facet_col="Oras" if len(selected_cities) > 1 else None,
        title="Evoluție Temperaturi (Max / Min)",
        labels={"value": "°C", "variable": "Tip"}
    )
    st.plotly_chart(fig_temp, use_container_width=True)

with tab2:
    fig_prec = px.bar(
        df_plot, x="Data", y="Precipitatii", color="Oras",
        title="Precipitații zilnice (mm)",
        labels={"Precipitatii": "mm"}
    )
    st.plotly_chart(fig_prec, use_container_width=True)

with tab3:
    st.info("💡 Completează coloana 'Vânzări' manual în tabelul de mai jos, apoi apasă 'Salvează'.")
    fig_vanz = px.line(
        df_plot, x="Data", y="Vanzari", color="Oras",
        title="Evoluție Vânzări",
        labels={"Vanzari": "Vânzări (RON)"}
    )
    st.plotly_chart(fig_vanz, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 4 — COMPARAȚIE DOUĂ DATE
# ---------------------------------------------------------------------------
with tab4:
    st.subheader("🔍 Compară două date pentru același oraș")
    st.caption("Selectează un oraș și două date diferite pentru a vedea diferențele meteo.")

    col_oras, col_d1, col_d2 = st.columns(3)

    with col_oras:
        oras_comp = st.selectbox("🏙️ Oraș:", options=all_cities, key="comp_oras")

    with col_d1:
        data1 = st.date_input(
            "📅 Data 1:",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            key="comp_d1"
        )

    with col_d2:
        data2 = st.date_input(
            "📅 Data 2:",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            key="comp_d2"
        )

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

            # --- Carduri cu delta ---
            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "🌡️ Temp Max",
                f"{r2['Max']:.1f}°C",
                delta=f"{r2['Max']-r1['Max']:+.1f}°C",
                help=f"Data 1: {r1['Max']:.1f}°C → Data 2: {r2['Max']:.1f}°C"
            )
            c2.metric(
                "❄️ Temp Min",
                f"{r2['Min']:.1f}°C",
                delta=f"{r2['Min']-r1['Min']:+.1f}°C",
                help=f"Data 1: {r1['Min']:.1f}°C → Data 2: {r2['Min']:.1f}°C"
            )
            c3.metric(
                "🌧️ Precipitații",
                f"{r2['Precipitatii']:.1f} mm",
                delta=f"{r2['Precipitatii']-r1['Precipitatii']:+.1f} mm",
                help=f"Data 1: {r1['Precipitatii']:.1f}mm → Data 2: {r2['Precipitatii']:.1f}mm"
            )
            c4.metric(
                "💰 Vânzări",
                f"{r2['Vanzari']:.0f} RON",
                delta=f"{r2['Vanzari']-r1['Vanzari']:+.0f} RON",
                help=f"Data 1: {r1['Vanzari']:.0f} RON → Data 2: {r2['Vanzari']:.0f} RON"
            )

            st.divider()

            # --- Grafic bara grupat ---
            df_comp_chart = pd.DataFrame({
                "Indicator": ["Temp Max (°C)", "Temp Min (°C)", "Precipitații (mm)"],
                data1.strftime('%d %b %Y'): [r1['Max'], r1['Min'], r1['Precipitatii']],
                data2.strftime('%d %b %Y'): [r2['Max'], r2['Min'], r2['Precipitatii']],
            })
            df_melted = df_comp_chart.melt(id_vars="Indicator", var_name="Data", value_name="Valoare")

            fig_bar = px.bar(
                df_melted, x="Indicator", y="Valoare", color="Data",
                barmode="group",
                color_discrete_sequence=["#e74c3c", "#3498db"],
                title=f"Comparație {oras_comp}",
                labels={"Valoare": "Valoare", "Indicator": ""}
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            # --- Tabel detaliat ---
            st.subheader("📋 Detalii complete")
            df_tabel = pd.DataFrame({
                "Indicator": ["Temp Max (°C)", "Temp Min (°C)", "Precipitații (mm)", "Vânzări (RON)"],
                data1.strftime('%d %b %Y'): [
                    f"{r1['Max']:.1f}", f"{r1['Min']:.1f}",
                    f"{r1['Precipitatii']:.1f}", f"{r1['Vanzari']:.0f}"
                ],
                data2.strftime('%d %b %Y'): [
                    f"{r2['Max']:.1f}", f"{r2['Min']:.1f}",
                    f"{r2['Precipitatii']:.1f}", f"{r2['Vanzari']:.0f}"
                ],
                "Diferență": [
                    f"{r2['Max']-r1['Max']:+.1f}°C",
                    f"{r2['Min']-r1['Min']:+.1f}°C",
                    f"{r2['Precipitatii']-r1['Precipitatii']:+.1f} mm",
                    f"{r2['Vanzari']-r1['Vanzari']:+.0f} RON"
                ]
            })
            st.dataframe(df_tabel, use_container_width=True, hide_index=True)

st.divider()

# --- Tabel editabil ---
st.subheader("📋 Tabel Date")
edited = st.data_editor(
    df_plot,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Vanzari": st.column_config.NumberColumn("Vânzări (RON)", min_value=0, format="%.2f"),
        "Max": st.column_config.NumberColumn("Temp Max (°C)", format="%.1f"),
        "Min": st.column_config.NumberColumn("Temp Min (°C)", format="%.1f"),
        "Precipitatii": st.column_config.NumberColumn("Precipitații (mm)", format="%.1f"),
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
