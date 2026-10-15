import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from api.services.indicateurs import (
    activite_par_jour,
    incidents_par_statut,
    stations_actives,
)

load_dotenv()


@pytest.fixture
def session():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Définir TEST_DATABASE_URL pour utiliser PostgreSQL en test")

    engine = create_engine(database_url)
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    test_session = Session(join_transaction_mode="create_savepoint")

    try:
        test_session.execute(text("DELETE FROM incident"))
        test_session.execute(text("DELETE FROM trajet"))
        test_session.execute(text("DELETE FROM station"))
        test_session.execute(
            text(
                """
                INSERT INTO station (
                    station_id, nom, commune, capacite, latitude, longitude,
                    date_mise_en_service
                )
                VALUES
                    ('S001', 'Lille - Gare', 'Lille', 20, 50.6301, 3.0572, '2023-01-01'),
                    ('S002', 'Lille - Mairie', 'Lille', 30, 50.6290, 3.0578, '2022-04-01'),
                    ('S003', 'Roubaix - Centre', 'Roubaix', 15, 50.6900, 3.1770, '2021-07-15')
                """
            )
        )
        test_session.execute(
            text(
                """
                INSERT INTO trajet (
                    trajet_id, velo_id, depart_horodatage, station_depart,
                    station_arrivee, duree_secondes, type_usager, usager_ref
                )
                VALUES
                    ('T000001', 'V0001', '2026-08-24 08:00:00', 'S001', 'S002', 1200, 'abonne', 'UABCDEF12'),
                    ('T000002', 'V0002', '2026-08-24 12:30:00', 'S001', NULL, 1800, 'occasionnel', NULL),
                    ('T000003', 'V0003', '2026-08-25 09:15:00', 'S002', 'S001', 1500, 'abonne', 'UABCDEF13'),
                    ('T000004', 'V0004', '2026-08-26 18:00:00', 'S003', NULL, 2100, 'occasionnel', NULL),
                    ('T000005', 'V0005', '2026-08-26 20:00:00', 'S003', 'S001', 600, 'abonne', 'UABCDEF14')
                """
            )
        )
        test_session.execute(
            text(
                """
                INSERT INTO incident (
                    incident_id, date_signalement, cible, velo_id, station_id,
                    type_incident, statut, date_resolution, technicien
                )
                VALUES
                    ('I2026-0001', '2026-08-24 09:00:00', 'station', NULL, 'S001', 'borne hors service', 'ouvert', NULL, NULL),
                    ('I2026-0002', '2026-08-25 10:00:00', 'velo', 'V0007', NULL, 'frein defectueux', 'en_cours', NULL, 'Dupont'),
                    ('I2026-0003', '2026-08-26 12:00:00', 'station', NULL, 'S002', 'eclairage HS', 'resolu', '2026-08-26 14:00:00', 'Martin'),
                    ('I2026-0004', '2026-08-27 08:00:00', 'velo', 'V0012', NULL, 'pneu creve', 'resolu', '2026-08-27 12:00:00', 'Martin')
                """
            )
        )

        yield test_session
    finally:
        test_session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def test_activite_par_jour(session):
    result = activite_par_jour(session, "2026-08-24", "2026-08-26")

    assert result == [
        {"jour": "2026-08-24", "nb_trajets": 2},
        {"jour": "2026-08-25", "nb_trajets": 1},
        {"jour": "2026-08-26", "nb_trajets": 2},
    ]


def test_stations_actives(session):
    result = stations_actives(session, limite=10)

    assert result == [
        {
            "station_id": "S001",
            "nom": "Lille - Gare",
            "nb_departs": 2,
            "nb_arrivees": 2,
        },
        {
            "station_id": "S002",
            "nom": "Lille - Mairie",
            "nb_departs": 1,
            "nb_arrivees": 1,
        },
        {
            "station_id": "S003",
            "nom": "Roubaix - Centre",
            "nb_departs": 2,
            "nb_arrivees": 0,
        },
    ]


def test_incidents_par_statut(session):
    result = incidents_par_statut(session)

    assert result["donnees"] == [
        {"statut": "ouvert", "nb_incidents": 1},
        {"statut": "en_cours", "nb_incidents": 1},
        {"statut": "resolu", "nb_incidents": 2},
    ]
    assert result["delai_moyen_resolution_heures"] == 3.0
