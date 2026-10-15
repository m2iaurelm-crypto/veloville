"""Authentification JWT et contrôle des rôles."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Utilisateur

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
bearer = HTTPBearer(auto_error=False)


def creer_jeton(utilisateur: Utilisateur) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET n'est pas configuré")
    maintenant = datetime.now(UTC)
    expiration = maintenant + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    return jwt.encode(
        {
            "sub": str(utilisateur.id_utilisateur),
            "role": utilisateur.role,
            "iat": maintenant,
            "exp": expiration,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def utilisateur_courant(
    identifiants: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Utilisateur:
    if not identifiants or not JWT_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Jeton invalide ou absent",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        contenu = jwt.decode(
            identifiants.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
        utilisateur_id = int(contenu["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Jeton invalide ou absent",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(
            status_code=401,
            detail="Jeton invalide ou absent",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return utilisateur


def exiger_role(role_attendu: str):
    def verifier_role(
        utilisateur: Utilisateur = Depends(utilisateur_courant),
    ) -> Utilisateur:
        if utilisateur.role != role_attendu:
            raise HTTPException(
                status_code=403, detail="Acces reserve au role exploitant"
            )
        return utilisateur

    return verifier_role
