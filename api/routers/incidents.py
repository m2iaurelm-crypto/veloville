"""Routes de consultation et de mise à jour des incidents."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Incident
from api.schemas import ChangementStatut, IncidentLecture, PageIncidents
from api.securite import exiger_role, utilisateur_courant

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=PageIncidents)
def lister_incidents(
    statut: Literal["ouvert", "en_cours", "resolu"] | None = None,
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    utilisateur=Depends(utilisateur_courant),
):
    requete = db.query(Incident)
    if statut:
        requete = requete.filter(Incident.statut == statut)
    total = requete.count()
    resultats = (
        requete.order_by(Incident.date_signalement.desc())
        .offset((page - 1) * taille_page)
        .limit(taille_page)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "taille_page": taille_page,
        "resultats": resultats,
    }


@router.put("/{incident_id}/statut", response_model=IncidentLecture)
def modifier_statut_incident(
    incident_id: str,
    changement: ChangementStatut,
    db: Session = Depends(get_db),
    utilisateur=Depends(exiger_role("exploitant")),
):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident introuvable")

    transitions = {
        "ouvert": {"en_cours", "resolu"},
        "en_cours": {"resolu"},
    }
    if changement.statut not in transitions.get(incident.statut, set()):
        raise HTTPException(
            status_code=422, detail="Transition de statut non autorisee"
        )

    incident.statut = changement.statut
    if changement.statut == "resolu" and incident.date_resolution is None:
        incident.date_resolution = datetime.now()
    db.commit()
    db.refresh(incident)
    return incident
