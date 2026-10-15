import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDES = float(os.getenv("API_TIMEOUT_SECONDES", "5"))


class ErreurApi(Exception):
    pass


def _requete(
    methode: str,
    chemin: str,
    jeton: str | None = None,
    params: dict[str, Any] | None = None,
    donnees: dict[str, Any] | None = None,
) -> Any:
    entetes = {"Authorization": f"Bearer {jeton}"} if jeton else {}
    try:
        reponse = requests.request(
            methode,
            f"{API_URL}{chemin}",
            params=params,
            json=donnees,
            headers=entetes,
            timeout=API_TIMEOUT_SECONDES,
        )
    except requests.RequestException as erreur:
        raise ErreurApi("API injoignable. Vérifiez que le service est démarré.") from erreur

    if not reponse.ok:
        try:
            message = reponse.json().get("detail")
        except (ValueError, AttributeError):
            message = None
        raise ErreurApi(str(message or "La requête a échoué."))
    if not reponse.content:
        return None
    return reponse.json()


def se_connecter(username: str, password: str) -> dict[str, Any]:
    return _requete(
        "POST", "/auth/login", donnees={"username": username, "password": password}
    )


def verifier_api() -> None:
    _requete("GET", "/sante")


def lister_stations(
    jeton: str, commune: str = "", page: int = 1, taille_page: int = 20
) -> dict[str, Any]:
    return _requete(
        "GET",
        "/stations",
        jeton,
        {"commune": commune or None, "page": page, "taille_page": taille_page},
    )


def lister_trajets(
    jeton: str,
    date_debut: str | None = None,
    date_fin: str | None = None,
    page: int = 1,
    taille_page: int = 20,
) -> dict[str, Any]:
    return _requete(
        "GET",
        "/trajets",
        jeton,
        {
            "date_debut": date_debut,
            "date_fin": date_fin,
            "page": page,
            "taille_page": taille_page,
        },
    )


def lister_incidents(
    jeton: str, statut: str = "Tous", page: int = 1, taille_page: int = 20
) -> dict[str, Any]:
    return _requete(
        "GET",
        "/incidents",
        jeton,
        {
            "statut": None if statut == "Tous" else statut,
            "page": page,
            "taille_page": taille_page,
        },
    )


def modifier_statut_incident(
    jeton: str, incident_id: str, statut: str
) -> dict[str, Any]:
    return _requete(
        "PUT",
        f"/incidents/{quote(incident_id, safe='')}/statut",
        jeton,
        donnees={"statut": statut},
    )


def activite_par_jour(jeton: str, date_debut: str, date_fin: str) -> dict[str, Any]:
    return _requete(
        "GET",
        "/indicateurs/activite-par-jour",
        jeton,
        {"date_debut": date_debut, "date_fin": date_fin},
    )


def stations_actives(jeton: str, limite: int = 10) -> dict[str, Any]:
    return _requete("GET", "/indicateurs/stations-actives", jeton, {"limite": limite})


def incidents_par_statut(jeton: str) -> dict[str, Any]:
    return _requete("GET", "/indicateurs/incidents-par-statut", jeton)
