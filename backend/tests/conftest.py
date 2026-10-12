import os

from cryptography.fernet import Fernet

os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-twilio-token")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.models.models import Base
from main import app


@pytest.fixture
def db_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture
def api(db_factory, monkeypatch):
    def override_get_db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.api.endpoints.webhooks.SessionLocal", db_factory)
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(api, email="owner@example.com", password="correct-horse", name="Barbershop"):
    response = api.post(
        "/api/v1/auth/register",
        json={"business_name": name, "email": email, "password": password, "timezone": "America/Sao_Paulo"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
