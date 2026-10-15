"""Tests unitaires des fonctions pures de fiabilisation."""

import pandas as pd

from api.services.fiabilisation import (
    filtrer_incoherence_temporelle_incidents,
    identifier_techniciens_absents,
    nettoyer_valeurs_manquantes_trajets,
    normaliser_format_date_trajets,
    normaliser_statut_incidents,
    remove_duplicate_id,
    remove_duree_invalide,
    remove_station_inexistante,
)


def test_remove_duplicate_id_rejette_la_seconde_occurrence():
    trajets = pd.DataFrame({"trajet_id": ["T1", "T1", "T2"]})

    resultat = remove_duplicate_id(trajets)

    assert resultat["trajet_id"].tolist() == ["T1", "T2"]
    assert len(trajets) == 3


def test_remove_duree_invalide_conserve_les_durees_positives():
    trajets = pd.DataFrame({"duree_secondes": [60, 0, -5]})

    resultat = remove_duree_invalide(trajets)

    assert resultat["duree_secondes"].tolist() == [60]


def test_remove_station_inexistante_rejette_les_references_inconnues():
    stations = pd.DataFrame({"station_id": ["S1", "S2"]})
    trajets = pd.DataFrame(
        {
            "trajet_id": ["T1", "T2", "T3"],
            "station_depart": ["S1", "S9", "S2"],
            "station_arrivee": ["S2", "S1", "S9"],
        }
    )

    resultat = remove_station_inexistante(stations, trajets)

    assert resultat["trajet_id"].tolist() == ["T1"]


def test_normaliser_format_date_trajets_convertit_le_format_francais():
    trajets = pd.DataFrame({"depart_horodatage": ["24/08/2026 08:30:00"]})

    resultat = normaliser_format_date_trajets(trajets)

    assert resultat.loc[0, "depart_horodatage"] == "2026-08-24 08:30:00"


def test_filtrer_incoherence_temporelle_rejette_resolution_anterieure():
    incidents = pd.DataFrame(
        {
            "incident_id": ["I1", "I2"],
            "statut": ["resolu", "ouvert"],
            "date_signalement": ["2026-08-24 10:00:00", "2026-08-24 10:00:00"],
            "date_resolution": ["2026-08-24 09:00:00", "2026-08-24 08:00:00"],
        }
    )

    valides, rejetes = filtrer_incoherence_temporelle_incidents(incidents)

    assert valides["incident_id"].tolist() == ["I2"]
    assert rejetes["incident_id"].tolist() == ["I1"]


def test_normaliser_statut_incidents_normalise_casse_et_espaces():
    incidents = pd.DataFrame({"statut": ["Ouvert", "EN COURS", "RESOLU"]})

    resultat = normaliser_statut_incidents(incidents)

    assert resultat["statut"].tolist() == ["ouvert", "en_cours", "resolu"]


def test_identifier_techniciens_absents_signale_les_incidents_pris_en_charge():
    incidents = pd.DataFrame(
        {
            "statut": ["ouvert", "en_cours", "resolu", "resolu"],
            "technicien": [None, None, "Martin", None],
        }
    )

    resultat = identifier_techniciens_absents(incidents)

    assert resultat.tolist() == [False, True, False, True]


def test_nettoyer_valeurs_manquantes_trajets_convertit_les_champs_optionnels():
    trajets = pd.DataFrame(
        {
            "station_arrivee": ["nan"],
            "velo_id": ["V1"],
            "type_usager": [""],
            "usager_ref": [None],
        }
    )

    resultat = nettoyer_valeurs_manquantes_trajets(trajets)

    assert resultat.loc[0, "station_arrivee"] is None
    assert resultat.loc[0, "velo_id"] == "V1"
    assert resultat.loc[0, "type_usager"] is None
    assert resultat.loc[0, "usager_ref"] is None
