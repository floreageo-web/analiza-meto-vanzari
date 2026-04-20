if "--update_only" in sys.argv:
    print("🤖 Robotul a pornit...")
    all_new_data = []
    
    # Alegem o dată de start fixă dacă vrem să umplem totul
    start_dt = "2023-01-01"
    end_dt = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    
    for oras in ORASE_MCDO:
        print(f"🛰️ Interoghez serverul meteo pentru {oras}...")
        batch = fetch_weather(oras, start_dt, end_dt)
        if not batch.empty:
            print(f"✅ Am primit {len(batch)} zile de date pentru {oras}.")
            all_new_data.append(batch)
        else:
            print(f"❌ Serverul nu a trimis date pentru {oras}.")

    if all_new_data:
        df_final = pd.concat(all_new_data)
        df_final.to_csv(FILE_DB, index=False)
        print(f"💾 Succes! Am salvat în total {len(df_final)} rânduri în {FILE_DB}.")
    else:
        print("🛑 EROARE: Nu s-a descărcat nimic!")
    sys.exit()
