"""Routes de consultation des stations."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Station
from api.schemas import PageStations, StationLecture
from api.securite import utilisateur_courant

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=PageStations)
def lister_stations(
    commune: str | None = None,
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    utilisateur=Depends(utilisateur_courant),
):
    requete = db.query(Station)
    if commune:
        requete = requete.filter(Station.commune.ilike(commune))
    total = requete.count()
    resultats = (
        requete.order_by(Station.station_id)
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


@router.get("/{station_id}", response_model=StationLecture)
def obtenir_station(
    station_id: str,
    db: Session = Depends(get_db),
    utilisateur=Depends(utilisateur_courant),
):
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station introuvable")
    return station
