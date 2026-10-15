"""Schémas Pydantic des entrées et sorties de l'API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModeleLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StationLecture(ModeleLecture):
    station_id: str = Field(min_length=1, max_length=10)
    nom: str = Field(min_length=1, max_length=100)
    commune: str = Field(min_length=1, max_length=100)
    capacite: int = Field(ge=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    date_mise_en_service: date


class TrajetLecture(ModeleLecture):
    trajet_id: str = Field(min_length=1, max_length=12)
    velo_id: str = Field(min_length=1, max_length=8)
    depart_horodatage: datetime
    station_depart: str = Field(min_length=1, max_length=10)
    station_arrivee: str | None = Field(max_length=10)
    duree_secondes: int = Field(gt=0)
    type_usager: str = Field(min_length=1, max_length=50)
    usager_ref: str | None = Field(max_length=50)


class IncidentLecture(ModeleLecture):
    incident_id: str = Field(min_length=1, max_length=12)
    date_signalement: datetime
    cible: Literal["station", "velo"]
    velo_id: str | None = Field(max_length=8)
    station_id: str | None = Field(max_length=10)
    type_incident: str = Field(min_length=1, max_length=50)
    statut: Literal["ouvert", "en_cours", "resolu"]
    date_resolution: datetime | None
    technicien: str | None = Field(max_length=100)


class Pagination(BaseModel):
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    taille_page: int = Field(ge=1, le=100)


class PageStations(Pagination):
    resultats: list[StationLecture] = Field(max_length=100)


class PageTrajets(Pagination):
    resultats: list[TrajetLecture] = Field(max_length=100)


class PageIncidents(Pagination):
    resultats: list[IncidentLecture] = Field(max_length=100)


class Connexion(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)


class ReponseConnexion(BaseModel):
    access_token: str = Field(min_length=1)
    token_type: Literal["bearer"] = "bearer"
    role: Literal["exploitant", "direction"]


class ChangementStatut(BaseModel):
    statut: Literal["en_cours", "resolu"]


class ActiviteJour(BaseModel):
    jour: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    nb_trajets: int = Field(ge=1)


class ReponseActivite(BaseModel):
    donnees: list[ActiviteJour]


class StationActive(BaseModel):
    station_id: str = Field(min_length=1, max_length=10)
    nom: str = Field(min_length=1, max_length=100)
    nb_departs: int = Field(ge=0)
    nb_arrivees: int = Field(ge=0)


class ReponseStationsActives(BaseModel):
    donnees: list[StationActive]


class IncidentParStatut(BaseModel):
    statut: Literal["ouvert", "en_cours", "resolu"]
    nb_incidents: int = Field(gt=0)


class ReponseIncidentsParStatut(BaseModel):
    donnees: list[IncidentParStatut] = Field(max_length=3)
    delai_moyen_resolution_heures: float | None = Field(ge=0)
