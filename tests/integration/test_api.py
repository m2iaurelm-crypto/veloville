"""Tests des parcours API essentiels avec TestClient."""

from datetime import UTC, date, datetime, timedelta

import jwt

from api.models import Incident, Station, Trajet
from api.securite import JWT_ALGORITHM, JWT_SECRET


def test_sante(client):
    response = client.get("/sante")

    assert response.status_code == 200
    assert response.json() == {"statut": "ok"}


def test_connexion_reussie_et_refusee(client, identifiants_test):
    identifiants = identifiants_test["exploitant"]
    response = client.post("/auth/login", json=identifiants)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"
    assert response.json()["role"] == "exploitant"
    claims = jwt.decode(
        response.json()["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM]
    )
    assert claims["sub"].isdigit()
    assert claims["role"] == "exploitant"
    assert claims["iat"] <= claims["exp"]

    refus = client.post(
        "/auth/login",
        json={"username": identifiants["username"], "password": "incorrect"},
    )
    assert refus.status_code == 401
    assert refus.json() == {"detail": "Identifiants invalides"}

    entree_invalide = client.post(
        "/auth/login",
        json={"username": "ab", "password": "court"},
    )
    assert entree_invalide.status_code == 422


def test_route_protegee_sans_jeton(client):
    response = client.get("/stations")

    assert response.status_code == 401


def test_route_protegee_avec_jeton_modifie(client, identifiants_test):
    """Un jeton dont la signature est altérée doit être refusé."""
    connexion = client.post("/auth/login", json=identifiants_test["exploitant"])
    parties = connexion.json()["access_token"].split(".")
    parties[2] = ("A" if parties[2][0] != "A" else "B") + parties[2][1:]
    jeton_modifie = ".".join(parties)

    response = client.get(
        "/stations", headers={"Authorization": f"Bearer {jeton_modifie}"}
    )

    assert response.status_code == 401


def test_route_protegee_avec_jeton_expire(client):
    """Un JWT signé mais expiré ne donne pas accès à une route protégée."""
    maintenant = datetime.now(UTC)
    jeton_expire = jwt.encode(
        {
            "sub": "1",
            "role": "exploitant",
            "iat": maintenant - timedelta(minutes=2),
            "exp": maintenant - timedelta(minutes=1),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/stations", headers={"Authorization": f"Bearer {jeton_expire}"}
    )

    assert response.status_code == 401


def test_direction_ne_peut_pas_modifier_un_incident(client, identifiants_test):
    identifiants = identifiants_test["direction"]
    connexion = client.post("/auth/login", json=identifiants)
    jeton = connexion.json()["access_token"]

    response = client.put(
        "/incidents/I2026-0001/statut",
        json={"statut": "en_cours"},
        headers={"Authorization": f"Bearer {jeton}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Acces reserve au role exploitant"}


def test_exploitant_peut_modifier_un_incident(client, identifiants_test, db_session):
    """Le rôle exploitant peut effectuer une transition autorisée."""
    incident = Incident(
        incident_id="SEC-TEST-01",
        date_signalement=datetime.now(),
        cible="velo",
        velo_id="V0001",
        station_id=None,
        type_incident="test",
        statut="ouvert",
        date_resolution=None,
        technicien=None,
    )
    db_session.add(incident)
    db_session.flush()

    connexion = client.post("/auth/login", json=identifiants_test["exploitant"])
    response = client.put(
        f"/incidents/{incident.incident_id}/statut",
        json={"statut": "en_cours"},
        headers={"Authorization": f"Bearer {connexion.json()['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["statut"] == "en_cours"
    assert db_session.get(Incident, incident.incident_id).statut == "en_cours"


def test_usager_ref_masque_a_direction_et_visible_a_exploitant(
    client, identifiants_test, db_session
):
    """Le pseudonyme est renvoyé à l'exploitant, pas à la direction."""
    db_session.add(
        Station(
            station_id="S999",
            nom="Station test",
            commune="Lille",
            capacite=20,
            latitude=50.63,
            longitude=3.05,
            date_mise_en_service=date(2020, 1, 1),
        )
    )
    db_session.add(
        Trajet(
            trajet_id="T999998",
            velo_id="V9999",
            depart_horodatage=datetime(2026, 8, 24, 12),
            station_depart="S999",
            station_arrivee=None,
            duree_secondes=600,
            type_usager="abonne",
            usager_ref="U1234ABCD",
        )
    )
    db_session.flush()
    for role in ("direction", "exploitant"):
        connexion = client.post("/auth/login", json=identifiants_test[role])
        response = client.get(
            "/trajets?taille_page=100",
            headers={"Authorization": f"Bearer {connexion.json()['access_token']}"},
        )
        assert response.status_code == 200
        usager_refs = [trajet["usager_ref"] for trajet in response.json()["resultats"]]
        assert usager_refs
        if role == "direction":
            assert all(usager_ref is None for usager_ref in usager_refs)
        else:
            assert any(usager_ref is not None for usager_ref in usager_refs)


def test_pagination_validation_et_reponses_indicateurs(client, identifiants_test):
    identifiants = identifiants_test["exploitant"]
    connexion = client.post("/auth/login", json=identifiants)
    headers = {"Authorization": f"Bearer {connexion.json()['access_token']}"}

    for chemin in ("/stations", "/trajets", "/incidents"):
        response = client.get(
            chemin, params={"page": 1, "taille_page": 10}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["page"] == 1
        assert response.json()["taille_page"] == 10
        assert response.json()["total"] >= len(response.json()["resultats"])

    assert client.get("/stations?page=0", headers=headers).status_code == 422
    assert client.get("/incidents?statut=invalide", headers=headers).status_code == 422
    assert (
        client.put(
            "/incidents/I2026-0001/statut",
            json={"statut": "ouvert"},
            headers=headers,
        ).status_code
        == 422
    )

    activite = client.get(
        "/indicateurs/activite-par-jour",
        params={"date_debut": "2026-08-24", "date_fin": "2026-08-30"},
        headers=headers,
    )
    stations = client.get("/indicateurs/stations-actives", headers=headers)
    incidents = client.get("/indicateurs/incidents-par-statut", headers=headers)

    assert activite.status_code == 200
    assert isinstance(activite.json()["donnees"], list)
    assert stations.status_code == 200
    assert isinstance(stations.json()["donnees"], list)
    assert incidents.status_code == 200
    assert "delai_moyen_resolution_heures" in incidents.json()
