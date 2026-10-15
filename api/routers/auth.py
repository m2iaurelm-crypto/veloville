"""Routes d'authentification."""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Utilisateur
from api.schemas import Connexion, ReponseConnexion
from api.securite import creer_jeton

router = APIRouter(prefix="/auth", tags=["authentification"])


@router.post("/login", response_model=ReponseConnexion)
def connexion(donnees: Connexion, db: Session = Depends(get_db)) -> ReponseConnexion:
    utilisateur = db.query(Utilisateur).filter_by(username=donnees.username).first()
    mot_de_passe_valide = False
    if utilisateur:
        try:
            mot_de_passe_valide = bcrypt.checkpw(
                donnees.password.encode("utf-8"),
                utilisateur.mot_de_passe_hash.encode("utf-8"),
            )
        except ValueError:
            mot_de_passe_valide = False

    if not utilisateur or not mot_de_passe_valide:
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    return ReponseConnexion(
        access_token=creer_jeton(utilisateur),
        role=utilisateur.role,
    )
