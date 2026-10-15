"""Fixtures pytest utilisant une session PostgreSQL isolée par transaction."""

import os
import secrets
from pathlib import Path

import bcrypt
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
if len(os.getenv("JWT_SECRET", "").encode("utf-8")) < 32:
    os.environ["JWT_SECRET"] = secrets.token_hex(32)

from api.database import get_db
from api.main import app
from api.models import Utilisateur


@pytest.fixture
def db_session():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Définir TEST_DATABASE_URL pour lancer les tests d'intégration")
    if database_url == os.getenv("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL ne doit pas viser la base applicative")

    engine_test = create_engine(database_url, pool_pre_ping=True)
    connexion = engine_test.connect()
    transaction = connexion.begin()
    session_test = sessionmaker(bind=connexion, autoflush=False, expire_on_commit=False)
    session = session_test(join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connexion.close()
        engine_test.dispose()


@pytest.fixture
def client(db_session):
    def remplacer_get_db():
        yield db_session

    app.dependency_overrides[get_db] = remplacer_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def identifiants_test(db_session):
    mot_de_passe = secrets.token_urlsafe(24)
    identifiants = {}
    for role in ("exploitant", "direction"):
        username = f"test-{role}-{secrets.token_hex(6)}"
        hash_mot_de_passe = bcrypt.hashpw(
            mot_de_passe.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        db_session.add(
            Utilisateur(
                username=username,
                mot_de_passe_hash=hash_mot_de_passe,
                role=role,
            )
        )
        identifiants[role] = {"username": username, "password": mot_de_passe}
    db_session.flush()
    return identifiants
