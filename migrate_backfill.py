"""
migrate_backfill.py
-------------------
Rulează o singură dată pentru a completa retroactiv coloanele:
  OreSoare, OrePloaie, WMO, ZiTip
pentru toate rândurile din baza de date care nu le au.

Folosire:
    python migrate_backfill.py

SAU dacă vrei să forțezi re-descărcarea pentru toate orașele/datele:
    python migrate_backfill.py --force
"""

import pandas as pd
import requests
import sys
import os
import time
from datetime import datetime, timedelta

FILE_DB = "baza_date.csv"
FORCE   = "--force" in sys.argv

# Codul WMO → Emoji + Descriere
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

ORASE_COORDS = {
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


def wmo_to_ziptype(code):
    if code is None:
        return ("❓", "Necunoscut")
    try:
        code = int(float(code))
    except (ValueError, TypeError):
        return ("❓", "Necunoscut")
    return WMO_CODES.get(code, ("🌡️", f"Cod {code}"))


def fetch_extra_columns(city_name, start_date, end_date, retries=3):
    """
    Descarcă sunshine_duration, precipitation_hours, weathercode
    pentru intervalul dat și returnează un DataFrame indexat pe dată.
    """
    coords = ORASE_COORDS.get(city_name)
    if not coords:
        return pd.DataFrame()

    lat, lon = coords["lat"], coords["lon"]
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&daily=sunshine_duration,precipitation_hours,weathercode"
        f"&timezone=Europe%2FBerlin"
    )

    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            d = r.json().get("daily", {})
            if not d or not d.get("time"):
                return pd.DataFrame()

            n      = len(d["time"])
            codes  = d.get("weathercode",       [None] * n)
            soare  = d.get("sunshine_duration",  [0]    * n)
            ploaie = d.get("precipitation_hours",[0]    * n)

            df = pd.DataFrame({
                "Data":      pd.to_datetime(d["time"]),
                "OreSoare":  [round(s / 3600, 1) if s is not None else 0.0 for s in soare],
                "OrePloaie": [round(p, 1)         if p is not None else 0.0 for p in ploaie],
                "WMO":       codes,
                "ZiTip":     [wmo_to_ziptype(c)[0] + " " + wmo_to_ziptype(c)[1] for c in codes],
            })
            return df.set_index("Data")

        except requests.exceptions.Timeout:
            print(f"      ⏳ Timeout (încercare {attempt+1}/{retries})...")
            time.sleep(5)
        except Exception as e:
            print(f"      ❌ Eroare: {e} (încercare {attempt+1}/{retries})")
            time.sleep(3)

    return pd.DataFrame()


def main():
    if not os.path.exists(FILE_DB) or os.path.getsize(FILE_DB) == 0:
        print("❌ baza_date.csv nu există sau e goală. Rulează mai întâi app.py --update_only")
        sys.exit(1)

    print("📂 Citesc baza de date...")
    df = pd.read_csv(FILE_DB)
    df["Data"] = pd.to_datetime(df["Data"])

    # Adăugăm coloanele dacă lipsesc complet
    for col in ["OreSoare", "OrePloaie", "WMO", "ZiTip"]:
        if col not in df.columns:
            df[col] = None

    df["OreSoare"]  = pd.to_numeric(df["OreSoare"],  errors="coerce")
    df["OrePloaie"] = pd.to_numeric(df["OrePloaie"], errors="coerce")

    # Identificăm rândurile care au nevoie de completare
    if FORCE:
        mask_incomplete = pd.Series([True] * len(df), index=df.index)
        print("⚡ Mod FORCE: re-descărcăm totul.")
    else:
        mask_incomplete = df["OreSoare"].isna() | df["WMO"].isna()

    n_total = mask_incomplete.sum()
    if n_total == 0:
        print("✅ Toate rândurile au deja coloanele completate. Nimic de făcut!")
        sys.exit(0)

    print(f"🔍 Găsite {n_total} rânduri fără OreSoare/WMO din {len(df)} total.\n")

    # Grupăm rândurile incomplete pe (Oras, an-luna) pentru a minimiza apelurile API
    # Fiecare apel API acoperă un interval continuu per oraș
    orase_de_procesat = df.loc[mask_incomplete, "Oras"].unique()
    print(f"🏙️  Orașe de procesat: {len(orase_de_procesat)}\n")

    total_actualizate = 0
    backup_facut = False

    for idx_oras, oras in enumerate(orase_de_procesat):
        # Găsim intervalul de date incomplete pentru acest oraș
        mask_oras = mask_incomplete & (df["Oras"] == oras)
        date_incomplete = df.loc[mask_oras, "Data"]

        if date_incomplete.empty:
            continue

        start_dt = date_incomplete.min().strftime("%Y-%m-%d")
        end_dt   = date_incomplete.max().strftime("%Y-%m-%d")

        print(f"[{idx_oras+1}/{len(orase_de_procesat)}] 🛰️  {oras}: {start_dt} → {end_dt} ({len(date_incomplete)} zile)...")

        df_extra = fetch_extra_columns(oras, start_dt, end_dt)

        if df_extra.empty:
            print(f"      ⚠️  Nu s-au primit date. Sărim peste {oras}.")
            continue

        # Actualizăm rândurile din df_principal
        n_before = total_actualizate
        for data_val in date_incomplete:
            if data_val in df_extra.index:
                row_extra = df_extra.loc[data_val]
                mask_row  = (df["Oras"] == oras) & (df["Data"] == data_val)

                df.loc[mask_row, "OreSoare"]  = row_extra["OreSoare"]
                df.loc[mask_row, "OrePloaie"] = row_extra["OrePloaie"]
                df.loc[mask_row, "WMO"]       = row_extra["WMO"]
                df.loc[mask_row, "ZiTip"]     = row_extra["ZiTip"]
                total_actualizate += 1

        n_actualizate_acum = total_actualizate - n_before
        print(f"      ✅ {n_actualizate_acum} rânduri actualizate.")

        # Salvăm progresul la fiecare oraș (în caz că se întrerupe)
        if not backup_facut:
            os.replace(FILE_DB, FILE_DB + ".bak")
            print(f"      📦 Backup creat: {FILE_DB}.bak")
            backup_facut = True

        df.to_csv(FILE_DB, index=False)
        print(f"      💾 Progres salvat. Total până acum: {total_actualizate}/{n_total}")

        # Pauză mică între orașe ca să nu supraîncărcăm API-ul
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"🎉 Migrare completă! {total_actualizate} rânduri actualizate din {n_total} necesare.")

    # Verificare finală
    incomplete_final = df["OreSoare"].isna().sum()
    if incomplete_final > 0:
        print(f"⚠️  Mai sunt {incomplete_final} rânduri fără OreSoare (posibil API indisponibil pentru acele date).")
    else:
        print(f"✅ Toate rândurile au OreSoare completat!")

    print(f"💾 Fișier final: {FILE_DB} ({len(df)} rânduri)")


if __name__ == "__main__":
    main()
