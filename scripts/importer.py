"""Fiabilise et importe les CSV de Veloville dans PostgreSQL.

Usage : python scripts/importer.py
"""

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg import sql

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_JOURNAL_PATH = PROJECT_ROOT / "docs" / "journal_rejets.csv"
JOURNAL_COLUMNS = ["fichier", "identifiant", "colonne", "valeur", "motif", "decision"]

sys.path.insert(0, str(PROJECT_ROOT))
from api.services.fiabilisation import (
    filtrer_incoherence_temporelle_incidents,
    identifier_techniciens_absents,
    normaliser_format_date_trajets,
    normaliser_statut_incidents,
    remove_duplicate_id,
    remove_duree_invalide,
    remove_station_inexistante,
)


def journaliser(
    journal: list[dict[str, str]],
    fichier: str,
    identifiant: Any,
    colonne: str,
    valeur: Any,
    motif: str,
    decision: str = "rejet",
) -> None:
    """Ajoute une ligne au journal de rejet ou de normalisation."""
    journal.append(
        {
            "fichier": fichier,
            "identifiant": "N/A" if pd.isna(identifiant) else str(identifiant),
            "colonne": colonne,
            "valeur": "NULL" if pd.isna(valeur) else str(valeur),
            "motif": motif,
            "decision": decision,
        }
    )


def _verifier_colonnes(df: pd.DataFrame, attendues: set[str], fichier: str) -> None:
    """Vérifie la présence des colonnes requises et lève une erreur sinon.

    Args:
            df: Tableau lu depuis un fichier CSV.
            attendues: Noms des colonnes nécessaires au traitement.
            fichier: Nom du fichier utilisé dans le message d'erreur.
    """
    manquantes = attendues - set(df.columns)
    if manquantes:
        raise ValueError(
            f"Colonnes manquantes dans {fichier} : {', '.join(sorted(manquantes))}"
        )


def _valeur_sql(valeur: Any) -> Any:
    """Convertit une valeur pandas en valeur native ou NULL compatible SQL."""
    if pd.isna(valeur) or (
        isinstance(valeur, str)
        and valeur.strip().lower() in {"", "nan", "none", "null", "<na>"}
    ):
        return None
    if isinstance(valeur, pd.Timestamp):
        return valeur.to_pydatetime()
    return valeur.item() if hasattr(valeur, "item") else valeur


def _preparer_lignes(df: pd.DataFrame, colonnes: list[str]) -> list[tuple[Any, ...]]:
    """Convertit les lignes Pandas en tuples adaptés à psycopg."""
    valeurs = df[colonnes].astype(object).where(pd.notna(df[colonnes]), None)
    return [
        tuple(_valeur_sql(value) for value in ligne)
        for ligne in valeurs.itertuples(index=False, name=None)
    ]


def _inserer_lignes(
    curseur, table: str, df: pd.DataFrame, colonnes: list[str], cle: str
) -> None:
    champs = sql.SQL(", ").join(map(sql.Identifier, colonnes))
    parametres = sql.SQL(", ").join(sql.Placeholder() for _ in colonnes)
    requete = sql.SQL(
        "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO NOTHING"
    ).format(sql.Identifier(table), champs, parametres, sql.Identifier(cle))
    curseur.executemany(requete, _preparer_lignes(df, colonnes))


def _charger_stations(
    stations: pd.DataFrame, journal: list[dict[str, str]]
) -> pd.DataFrame:
    """Nettoie les stations, rejette les champs invalides et les doublons.

    Les anomalies détectées sont ajoutées au journal; le DataFrame nettoyé est
    retourné pour servir de référentiel aux trajets et aux incidents.
    """
    fichier = "stations.csv"
    stations = stations.copy()
    for colonne in ("capacite", "latitude", "longitude"):
        stations[colonne] = pd.to_numeric(stations[colonne], errors="coerce")
    stations["date_mise_en_service"] = pd.to_datetime(
        stations["date_mise_en_service"], errors="coerce"
    )
    obligatoires = [
        "station_id",
        "nom",
        "commune",
        "capacite",
        "latitude",
        "longitude",
        "date_mise_en_service",
    ]
    invalides = stations[stations[obligatoires].isna().any(axis=1)]
    for _, ligne in invalides.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["station_id"],
            "champs obligatoires",
            "NULL",
            "Champ obligatoire manquant ou invalide",
        )
    stations = stations.drop(index=invalides.index)
    doublons = stations[stations.duplicated(subset="station_id", keep="first")]
    for _, ligne in doublons.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["station_id"],
            "station_id",
            ligne["station_id"],
            "Doublon sur l'identifiant station_id",
        )
    return stations.drop_duplicates(subset="station_id", keep="first").copy()


def _charger_trajets(
    trajets: pd.DataFrame,
    stations: pd.DataFrame,
    journal: list[dict[str, str]],
) -> pd.DataFrame:
    """Fiabilise les trajets et journalise chaque ligne rejetée."""
    fichier = "trajets.csv"
    trajets = trajets.copy()
    trajets["duree_secondes"] = pd.to_numeric(
        trajets["duree_secondes"], errors="coerce"
    )
    doublons = trajets[trajets.duplicated("trajet_id", keep="first")]
    for _, ligne in doublons.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["trajet_id"],
            "trajet_id",
            ligne["trajet_id"],
            "Doublon strict sur l'identifiant trajet_id",
        )
    trajets_dates = normaliser_format_date_trajets(remove_duplicate_id(trajets))
    trajets_dates["depart_horodatage"] = pd.to_datetime(
        trajets_dates["depart_horodatage"], errors="coerce"
    )
    invalides = trajets_dates[trajets_dates["depart_horodatage"].isna()]
    for _, ligne in invalides.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["trajet_id"],
            "depart_horodatage",
            ligne["depart_horodatage"],
            "Horodatage de départ absent ou invalide",
        )
    trajets_dates = trajets_dates.drop(index=invalides.index)
    trajets_durees = remove_duree_invalide(trajets_dates)
    invalides = trajets_dates.loc[~trajets_dates.index.isin(trajets_durees.index)]
    for _, ligne in invalides.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["trajet_id"],
            "duree_secondes",
            ligne["duree_secondes"],
            "Durée de trajet absente, négative ou nulle (RG4)",
        )
    valides = remove_station_inexistante(stations, trajets_durees)
    invalides = trajets_durees.loc[~trajets_durees.index.isin(valides.index)]
    for _, ligne in invalides.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["trajet_id"],
            "station_depart / station_arrivee",
            f"dep: {ligne['station_depart']}, arr: {ligne['station_arrivee']}",
            "Station de départ ou d'arrivée inexistante dans le référentiel (RG2/RG3)",
        )
    obligatoires = [
        "trajet_id",
        "velo_id",
        "depart_horodatage",
        "station_depart",
        "duree_secondes",
        "type_usager",
    ]
    invalides = valides[valides[obligatoires].isna().any(axis=1)]
    for _, ligne in invalides.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["trajet_id"],
            "champs obligatoires",
            "NULL",
            "Champ obligatoire manquant",
        )
    return valides.drop(index=invalides.index).copy()


def _charger_incidents(
    incidents: pd.DataFrame,
    stations: pd.DataFrame,
    journal: list[dict[str, str]],
) -> pd.DataFrame:
    """Fiabilise les incidents et journalise chaque rejet ou avertissement."""
    fichier = "incidents.csv"
    doublons = incidents[incidents.duplicated("incident_id", keep="first")]
    for _, ligne in doublons.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["incident_id"],
            "incident_id",
            ligne["incident_id"],
            "Doublon sur l'identifiant incident_id",
        )
    uniques = incidents.drop_duplicates(subset="incident_id", keep="first")
    incidents_valides, rejetes_dates = filtrer_incoherence_temporelle_incidents(uniques)
    for _, ligne in rejetes_dates.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["incident_id"],
            "date_resolution / date_signalement",
            f"sig: {ligne['date_signalement']}, res: {ligne['date_resolution']}",
            "Date de résolution antérieure à la date de signalement (RG8)",
        )
    incidents = normaliser_statut_incidents(incidents_valides)
    for colonne in ("date_signalement", "date_resolution"):
        incidents[colonne] = pd.to_datetime(incidents[colonne], errors="coerce")
    requis = ["incident_id", "date_signalement", "cible", "type_incident", "statut"]
    invalides = incidents[incidents[requis].isna().any(axis=1)]
    for _, ligne in invalides.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["incident_id"],
            "champs obligatoires",
            "NULL",
            "Champ obligatoire manquant ou invalide",
        )
    incidents = incidents.drop(index=invalides.index)
    invalides = incidents[~incidents["statut"].isin({"ouvert", "en_cours", "resolu"})]
    for _, ligne in invalides.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["incident_id"],
            "statut",
            ligne["statut"],
            "Statut non reconnu par le schéma de la base",
        )
    incidents = incidents.drop(index=invalides.index)

    stations_connues = set(stations["station_id"])
    cible_station = incidents["cible"].str.lower().eq("station")
    cible_velo = incidents["cible"].str.lower().eq("velo")
    station_invalide = cible_station & (
        incidents["station_id"].isna()
        | ~incidents["station_id"].isin(stations_connues)
        | incidents["velo_id"].notna()
    )
    velo_invalide = cible_velo & (
        incidents["velo_id"].isna() | incidents["station_id"].notna()
    )
    cible_invalide = ~(cible_station | cible_velo)
    invalides_cible = incidents[station_invalide | velo_invalide | cible_invalide]
    for _, ligne in invalides_cible.iterrows():
        journaliser(
            journal,
            fichier,
            ligne["incident_id"],
            "cible / station_id / velo_id",
            f"{ligne['cible']} / {ligne['station_id']} / {ligne['velo_id']}",
            "Cible ou référence d'incident incohérente",
        )
    incidents = incidents.drop(index=invalides_cible.index).copy()
    techniciens_absents = identifier_techniciens_absents(incidents)
    for _, ligne in incidents[techniciens_absents].iterrows():
        journaliser(
            journal,
            fichier,
            ligne["incident_id"],
            "technicien",
            "NULL",
            "Technicien absent sur un incident pris en charge (RG8)",
            "normalisation_avertissement",
        )
    return incidents


def executer_importation(
    dossier: Path = DEFAULT_DATA_DIR,
    journal_path: Path = DEFAULT_JOURNAL_PATH,
) -> None:
    """Fiabilise les CSV, écrit le journal et insère les données dans PostgreSQL.

    Les tables sont alimentées dans l'ordre des dépendances de clés étrangères.
    Les conflits de clés primaires sont ignorés pour rendre l'import rejouable.
    """
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("La variable DATABASE_URL est absente du fichier .env")
    database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

    colonnes = {
        "stations.csv": {
            "station_id",
            "nom",
            "commune",
            "capacite",
            "latitude",
            "longitude",
            "date_mise_en_service",
        },
        "trajets.csv": {
            "trajet_id",
            "velo_id",
            "depart_horodatage",
            "station_depart",
            "station_arrivee",
            "duree_secondes",
            "type_usager",
            "usager_ref",
        },
        "incidents.csv": {
            "incident_id",
            "date_signalement",
            "cible",
            "velo_id",
            "station_id",
            "type_incident",
            "statut",
            "date_resolution",
            "technicien",
        },
    }
    sources = {fichier: pd.read_csv(dossier / fichier) for fichier in colonnes}
    for fichier, dataframe in sources.items():
        _verifier_colonnes(dataframe, colonnes[fichier], fichier)

    journal: list[dict[str, str]] = []
    stations = _charger_stations(sources["stations.csv"], journal)
    trajets = _charger_trajets(sources["trajets.csv"], stations, journal)
    incidents = _charger_incidents(sources["incidents.csv"], stations, journal)

    journal_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(journal, columns=JOURNAL_COLUMNS).to_csv(
        journal_path, index=False, encoding="utf-8"
    )

    tables = (
        (
            "station",
            stations,
            [
                "station_id",
                "nom",
                "commune",
                "capacite",
                "latitude",
                "longitude",
                "date_mise_en_service",
            ],
            "station_id",
        ),
        (
            "trajet",
            trajets,
            [
                "trajet_id",
                "velo_id",
                "depart_horodatage",
                "station_depart",
                "station_arrivee",
                "duree_secondes",
                "type_usager",
                "usager_ref",
            ],
            "trajet_id",
        ),
        (
            "incident",
            incidents,
            [
                "incident_id",
                "date_signalement",
                "cible",
                "velo_id",
                "station_id",
                "type_incident",
                "statut",
                "date_resolution",
                "technicien",
            ],
            "incident_id",
        ),
    )
    with psycopg.connect(database_url) as connexion, connexion.cursor() as curseur:
        for table, dataframe, champs, cle in tables:
            _inserer_lignes(curseur, table, dataframe, champs, cle)

    print(
        f"Import terminé : {len(stations)} stations, {len(trajets)} trajets, "
        f"{len(incidents)} incidents; {len(journal)} rejets/avertissements."
    )
    print(f"Journal : {journal_path}")


if __name__ == "__main__":
    executer_importation()
