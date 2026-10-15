"""Routes de consultation des trajets."""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Trajet
from api.schemas import PageTrajets, TrajetLecture
from api.securite import utilisateur_courant

router = APIRouter(prefix="/trajets", tags=["trajets"])


@router.get("", response_model=PageTrajets)
def lister_trajets(
    date_debut: date | None = None,
    date_fin: date | None = None,
    station: str | None = None,
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    utilisateur=Depends(utilisateur_courant),
):
    requete = db.query(Trajet)
    if date_debut:
        requete = requete.filter(
            Trajet.depart_horodatage >= datetime.combine(date_debut, time.min)
        )
    if date_fin:
        lendemain = date_fin + timedelta(days=1)
        requete = requete.filter(
            Trajet.depart_horodatage < datetime.combine(lendemain, time.min)
        )
    if station:
        requete = requete.filter(
            or_(Trajet.station_depart == station, Trajet.station_arrivee == station)
        )

    total = requete.count()
    resultats = (
        requete.order_by(Trajet.depart_horodatage)
        .offset((page - 1) * taille_page)
        .limit(taille_page)
        .all()
    )
    if utilisateur.role == "direction":
        resultats = [
            TrajetLecture.model_validate(trajet).model_copy(update={"usager_ref": None})
            for trajet in resultats
        ]
    return {
        "total": total,
        "page": page,
        "taille_page": taille_page,
        "resultats": resultats,
    }
