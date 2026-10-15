import pandas as pd


def compter_doublons(df, colonne):
    return int(df[colonne].duplicated().sum())


def compter_vides(df):
    return df.isnull().sum()


def audit_stations(stations):
    print("--- AUDIT CSV STATIONS ---")
    print("Stations avec l'id dupliqué :", compter_doublons(stations, "station_id"))
    print("Lignes avec champ nul :\n", compter_vides(stations))
    print("Capacité <= 0 :", int((stations["capacite"] <= 0).sum()))
    print("Dates invalides :", int(pd.to_datetime(stations["date_mise_en_service"], errors="coerce").isna().sum()))


def audit_trajets(trajets, stations):
    stations_ids = set(stations["station_id"])
    print("\n--- AUDIT CSV TRAJETS ---")
    print("Trajets avec l'id dupliqué :", compter_doublons(trajets, "trajet_id"))
    print("Lignes avec champ nul :\n", compter_vides(trajets))
    print("duree_secondes <= 0 :", int((trajets["duree_secondes"] <= 0).sum()))
    print("Station de départ invalide :", int((~trajets["station_depart"].isin(stations_ids)).sum()))
    print(
        "Station d'arrivée invalide :",
        int((trajets["station_arrivee"].notnull() & ~trajets["station_arrivee"].isin(stations_ids)).sum()),
    )
    dates_non_standard = trajets[~trajets["depart_horodatage"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}")]
    print("Format de date hétérogène :", len(dates_non_standard), "lignes concernées")


def audit_incidents(incidents, stations):
    stations_ids = set(stations["station_id"])
    print("\n--- AUDIT CSV INCIDENTS ---")
    print("Incidents avec l'id dupliqué :", compter_doublons(incidents, "incident_id"))
    print("Lignes avec champ nul :\n", compter_vides(incidents))

    velo_erreurs = (incidents["cible"] == "velo") & (incidents["velo_id"].isnull() | incidents["station_id"].notnull())
    station_erreurs = (incidents["cible"] == "station") & (
        incidents["station_id"].isnull()
        | incidents["velo_id"].notnull()
        | ~incidents["station_id"].isin(stations_ids)
    )
    print("Cible velo erreurs :", int(velo_erreurs.sum()))
    print("Cible station erreurs :", int(station_erreurs.sum()))

    incidents = incidents.copy()
    incidents["dt_sig"] = pd.to_datetime(incidents["date_signalement"], errors="coerce")
    incidents["dt_res"] = pd.to_datetime(incidents["date_resolution"], errors="coerce")
    statut = incidents["statut"].str.lower()

    resolu_sans_date = (statut == "resolu") & incidents["date_resolution"].isnull()
    date_non_resolu = (statut != "resolu") & incidents["date_resolution"].notnull()
    date_incoherente = (statut == "resolu") & incidents["date_resolution"].notnull() & (incidents["dt_res"] < incidents["dt_sig"])

    print("Incident résolu sans date :", int(resolu_sans_date.sum()))
    print("Date de résolution présente alors que non résolu :", int(date_non_resolu.sum()))
    print("Date_resolution < date_signalement :", int(date_incoherente.sum()))

    technicien_absent = incidents["statut"].str.lower().isin(["en cours", "resolu"]) & incidents["technicien"].isnull()
    print("Technicien absent sur incident pris en charge :", int(technicien_absent.sum()), "lignes concernées")


stations = pd.read_csv("data/stations.csv")
trajets = pd.read_csv("data/trajets.csv")
incidents = pd.read_csv("data/incidents.csv")

audit_stations(stations)
audit_trajets(trajets, stations)
audit_incidents(incidents, stations)
