"""Routes des indicateurs métier."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Trajet
from api.schemas import (
    ReponseActivite,
    ReponseIncidentsParStatut,
    ReponseStationsActives,
)
from api.securite import utilisateur_courant
from api.services.indicateurs import (
    activite_par_jour,
    incidents_par_statut,
    stations_actives,
)

router = APIRouter(prefix="/indicateurs", tags=["indicateurs"])


@router.get("/activite-par-jour", response_model=ReponseActivite)
def obtenir_activite_par_jour(
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
    utilisateur=Depends(utilisateur_courant),
):
    if date_debut is None or date_fin is None:
        debut_connu, fin_connue = db.query(
            func.min(Trajet.depart_horodatage), func.max(Trajet.depart_horodatage)
        ).one()
        if debut_connu is None:
            return {"donnees": []}
        date_debut = date_debut or debut_connu.date()
        date_fin = date_fin or fin_connue.date()
    return {
        "donnees": activite_par_jour(db, date_debut, date_fin),
    }


@router.get("/stations-actives", response_model=ReponseStationsActives)
def obtenir_stations_actives(
    limite: int = Query(default=10, ge=1),
    db: Session = Depends(get_db),
    utilisateur=Depends(utilisateur_courant),
):
    return {"donnees": stations_actives(db, limite=limite)}


@router.get("/incidents-par-statut", response_model=ReponseIncidentsParStatut)
def obtenir_incidents_par_statut(
    db: Session = Depends(get_db),
    utilisateur=Depends(utilisateur_courant),
):
    return incidents_par_statut(db)
