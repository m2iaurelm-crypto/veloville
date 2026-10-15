import pandas as pd


def remove_duplicate_id(trajets_dataframe: pd.DataFrame) -> pd.DataFrame:
    return trajets_dataframe.drop_duplicates(subset="trajet_id", keep="first")


def remove_duree_invalide(trajets_dataframe: pd.DataFrame) -> pd.DataFrame:
    return trajets_dataframe[trajets_dataframe["duree_secondes"] > 0].copy()


def remove_station_inexistante(
    stations_dataframe: pd.DataFrame, trajets_dataframe: pd.DataFrame
) -> pd.DataFrame:
    stations_ids = set(stations_dataframe["station_id"])
    cond_depart_valide = trajets_dataframe["station_depart"].isin(stations_ids)
    cond_arrivee_valide = trajets_dataframe["station_arrivee"].isna() | trajets_dataframe["station_arrivee"].isin(stations_ids)
    return trajets_dataframe[cond_depart_valide & cond_arrivee_valide].copy()


def normaliser_format_date_trajets(trajets_dataframe: pd.DataFrame) -> pd.DataFrame:
    df = trajets_dataframe.copy()
    dates = pd.to_datetime(df["depart_horodatage"], errors="coerce")
    df["depart_horodatage"] = dates.dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def filtrer_incoherence_temporelle_incidents(
    incidents_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    signale = pd.to_datetime(incidents_dataframe["date_signalement"], errors="coerce")
    resolu = pd.to_datetime(incidents_dataframe["date_resolution"], errors="coerce")
    statut = incidents_dataframe["statut"].str.replace("_", " ").str.lower()
    invalides = statut.eq("resolu") & (resolu < signale)
    return incidents_dataframe.loc[~invalides].copy(), incidents_dataframe.loc[invalides].copy()


def normaliser_statut_incidents(incidents_dataframe: pd.DataFrame) -> pd.DataFrame:
    df = incidents_dataframe.copy()
    df["statut"] = df["statut"].str.replace(" ", "_").str.lower()
    return df


def identifier_techniciens_absents(incidents_dataframe: pd.DataFrame) -> pd.Series:
    statut = incidents_dataframe["statut"].str.replace("_", " ").str.lower()
    pris_en_charge = statut.isin(["en cours", "resolu"])
    return pris_en_charge & incidents_dataframe["technicien"].isna()


def nettoyer_valeurs_manquantes_trajets(trajets_df: pd.DataFrame) -> pd.DataFrame:
    df = trajets_df.copy()
    absentes = {"", "nan", "none", "null"}
    for colonne in ("station_arrivee", "velo_id", "type_usager", "usager_ref"):
        if colonne in df:
            df[colonne] = df[colonne].map(
                lambda valeur: (
                    None
                    if pd.isna(valeur)
                    or (isinstance(valeur, str) and valeur.strip().lower() in absentes)
                    else valeur
                )
            )
    return df
