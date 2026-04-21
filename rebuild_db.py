"""
rebuild_db.py
-------------
Script de reconstrucție completă a bazei de date.
Descarcă date reale pentru TOATE cele 33 de orașe, din 2023-01-01 până azi.

Rulare:
    python rebuild_db.py

Caracteristici:
- Salvează progresul după fiecare oraș (poate fi reluat dacă se întrerupe)
- Nu re-descarcă un oraș dacă are deja date complete în fișierul de progres
- La final combină totul într-un singur baza_date.csv
"""

import pandas as pd
import requests
import os
import time
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# CONFIGURARE
# ---------------------------------------------------------------------------
ORASE_MCDO = {
    "Bucuresti":             {"lat": 44.43, "lon": 26.10},
    "Cluj":                  {"lat": 46.77, "lon": 23.62},
    "Timisoara":             {"lat": 45.75, "lon": 21.21},
    "Iasi":                  {"lat": 47.16, "lon": 27.60},
    "Brasov":                {"lat": 45.65, "lon": 25.61},
    "Constanta":             {"lat": 44.17, "lon": 28.63},
    "Craiova":               {"lat": 44.33, "lon": 23.79},
    "Sibiu":                 {"lat": 45.80, "lon": 24.15},
    "Oradea":                {"lat": 47.04, "lon": 21.91},
    "Ploiesti":              {"lat": 44.93, "lon": 26.03},
    "Pitesti":               {"lat": 44.85, "lon": 24.87},
    "Bacau":                 {"lat": 46.57, "lon": 26.91},
    "Galati":                {"lat": 45.43, "lon": 28.05},
    "Braila":                {"lat": 45.27, "lon": 27.96},
    "Targu Mures":           {"lat": 46.54, "lon": 24.56},
    "Arad":                  {"lat": 46.18, "lon": 21.31},
    "Deva":                  {"lat": 45.88, "lon": 22.91},
    "Ramnicu Valcea":        {"lat": 45.10, "lon": 24.37},
    "Suceava":               {"lat": 47.65, "lon": 26.26},
    "Piatra Neamt":          {"lat": 46.93, "lon": 26.37},
    "Targoviste":            {"lat": 44.93, "lon": 25.46},
    "Slatina":               {"lat": 44.43, "lon": 24.37},
    "Drobeta Turnu Severin": {"lat": 44.63, "lon": 22.66},
    "Botosani":              {"lat": 47.74, "lon": 26.67},
    "Buzau":                 {"lat": 45.15, "lon": 26.82},
    "Focsani":               {"lat": 45.70, "lon": 27.19},
    "Slobozia":              {"lat": 44.57, "lon": 27.37},
    "Tulcea":                {"lat": 45.18, "lon": 28.80},
    "Bistrita":              {"lat": 47.13, "lon": 24.50},
    "Alba Iulia":            {"lat": 46.07, "lon": 23.58},
    "Dumbravita":            {"lat": 45.80, "lon": 21.27},
    "Targu Jiu":             {"lat": 45.04, "lon": 23.28},
    "Alexandria":            {"lat": 43.97, "lon": 25.34},
}

START_DATE   = "2023-01-01"
FILE_DB      = "baza_date.csv"
FILE_PROGRES = "progres_rebuild.csv"   # fișier temporar de progres

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


def wmo_emoji(code):
    try:
        c = int(float(code)) if code is not None else None
    except (ValueError, TypeError):
        c = None
    e, d = WMO_CODES.get(c, ("❓", "Necunoscut"))
    return f"{e} {d}"


def fetch_oras(city_name, start_date, end_date, retries=4):
    """Descarcă toate coloanele pentru un oraș și un interval."""
    coords = ORASE_MCDO[city_name]
    lat, lon = coords["lat"], coords["lon"]

    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"sunshine_duration,precipitation_hours,weathercode"
        f"&timezone=Europe%2FBerlin"
    )

    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            d = r.json().get("daily", {})

            if not d or not d.get("time"):
                print(f"   ⚠️  Răspuns gol pentru {city_name}.")
                return pd.DataFrame()

            n      = len(d["time"])
            codes  = d.get("weathercode",        [None] * n)
            soare  = d.get("sunshine_duration",  [0]    * n)
            ploaie = d.get("precipitation_hours", [0]   * n)

            return pd.DataFrame({
                "Data":         pd.to_datetime(d["time"]),
                "Oras":         city_name,
                "Max":          d["temperature_2m_max"],
                "Min":          d["temperature_2m_min"],
                "Precipitatii": d["precipitation_sum"],
                "OreSoare":     [round(s / 3600, 1) if s is not None else 0.0 for s in soare],
                "OrePloaie":    [round(p, 1)         if p is not None else 0.0 for p in ploaie],
                "WMO":          codes,
                "ZiTip":        [wmo_emoji(c) for c in codes],
                "Vanzari":      0.0,
                "Tip":          "arhiva",
            })

        except requests.exceptions.Timeout:
            wait = 10 * (attempt + 1)
            print(f"   ⏳ Timeout (încercare {attempt+1}/{retries}). Aștept {wait}s...")
            time.sleep(wait)
        except requests.exceptions.HTTPError as e:
            print(f"   ❌ HTTP {e.response.status_code}. Aștept 15s...")
            time.sleep(15)
        except Exception as e:
            print(f"   ❌ Eroare: {e}. Aștept 5s...")
            time.sleep(5)

    return pd.DataFrame()


def main():
    end_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    print(f"🚀 Rebuild complet: {START_DATE} → {end_date}")
    print(f"🏙️  {len(ORASE_MCDO)} orașe de procesat\n")

    # Încărcăm progresul anterior dacă există
    if os.path.exists(FILE_PROGRES) and os.path.getsize(FILE_PROGRES) > 0:
        try:
            df_progres = pd.read_csv(FILE_PROGRES)
            df_progres["Data"] = pd.to_datetime(df_progres["Data"])
            orase_gata = set(df_progres["Oras"].unique())
            print(f"📂 Progres găsit: {len(orase_gata)} orașe deja descărcate: {sorted(orase_gata)}\n")
        except Exception:
            df_progres = pd.DataFrame()
            orase_gata = set()
    else:
        df_progres = pd.DataFrame()
        orase_gata = set()

    toate_datele = [df_progres] if not df_progres.empty else []
    erori = []

    for idx, oras in enumerate(ORASE_MCDO):
        if oras in orase_gata:
            print(f"[{idx+1:2d}/{len(ORASE_MCDO)}] ⏭️  {oras} — deja descărcat, sărim.")
            continue

        print(f"[{idx+1:2d}/{len(ORASE_MCDO)}] 🛰️  {oras}...")
        df_oras = fetch_oras(oras, START_DATE, end_date)

        if df_oras.empty:
            print(f"   ❌ EȘUAT pentru {oras}. Continuăm cu următorul.")
            erori.append(oras)
            continue

        print(f"   ✅ {len(df_oras)} zile descărcate.")
        toate_datele.append(df_oras)

        # Salvăm progresul după fiecare oraș reușit
        df_curent = pd.concat(toate_datele, ignore_index=True)
        df_curent.to_csv(FILE_PROGRES, index=False)
        print(f"   💾 Progres salvat ({sum(len(d) for d in toate_datele)} rânduri total)")

        # Pauză scurtă între requesturi
        time.sleep(0.3)

    # ---------------------------------------------------------------------------
    # FINAL — combinăm totul și scriem baza_date.csv
    # ---------------------------------------------------------------------------
    if not toate_datele:
        print("\n❌ Nu s-a descărcat nimic! Verifică conexiunea la internet.")
        return

    print("\n🔧 Combinăm datele finale...")
    df_final = pd.concat(toate_datele, ignore_index=True)
    df_final["Data"] = pd.to_datetime(df_final["Data"])

    # Dacă există vânzări introduse manual în CSV-ul vechi, le păstrăm
    if os.path.exists(FILE_DB) and os.path.getsize(FILE_DB) > 0:
        try:
            df_vechi = pd.read_csv(FILE_DB)
            df_vechi["Data"] = pd.to_datetime(df_vechi["Data"])
            vanzari_existente = df_vechi[df_vechi["Vanzari"] > 0][["Data", "Oras", "Vanzari"]]
            if not vanzari_existente.empty:
                print(f"   💰 Păstrăm {len(vanzari_existente)} înregistrări de vânzări introduse manual.")
                df_final = df_final.merge(
                    vanzari_existente.rename(columns={"Vanzari": "Vanzari_vechi"}),
                    on=["Data", "Oras"], how="left"
                )
                df_final["Vanzari"] = df_final["Vanzari_vechi"].fillna(df_final["Vanzari"])
                df_final.drop(columns=["Vanzari_vechi"], inplace=True)
        except Exception as e:
            print(f"   ⚠️  Nu am putut păstra vânzările vechi: {e}")

    # Deduplicare și sortare
    df_final = df_final.drop_duplicates(subset=["Data", "Oras"])
    df_final = df_final.sort_values(["Oras", "Data"]).reset_index(drop=True)

    # Backup CSV vechi
    if os.path.exists(FILE_DB):
        backup_name = FILE_DB + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.replace(FILE_DB, backup_name)
        print(f"   📦 Backup: {backup_name}")

    df_final.to_csv(FILE_DB, index=False)

    # Curățăm fișierul de progres
    if os.path.exists(FILE_PROGRES):
        os.remove(FILE_PROGRES)
        print(f"   🗑️  Fișier progres temporar șters.")

    # ---------------------------------------------------------------------------
    # RAPORT FINAL
    # ---------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"✅ REBUILD COMPLET!")
    print(f"   📊 Total rânduri: {len(df_final)}")
    print(f"   🏙️  Orașe: {df_final['Oras'].nunique()}")
    print(f"   📅 Interval: {df_final['Data'].min().date()} → {df_final['Data'].max().date()}")
    print(f"   ☀️  Rânduri cu OreSoare completat: {df_final['OreSoare'].notna().sum()}")
    print(f"   🌤️  Rânduri cu ZiTip completat:   {df_final['ZiTip'].notna().sum()}")

    if erori:
        print(f"\n⚠️  Orașe cu erori ({len(erori)}): {erori}")
        print(f"   Rulează din nou scriptul — orașele reușite sunt salvate și se sare peste ele.")
    else:
        print(f"\n🎉 Toate orașele au fost descărcate cu succes!")

    print(f"{'='*60}")


if __name__ == "__main__":
    main()
