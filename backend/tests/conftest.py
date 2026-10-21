import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://hitassesnet:devpass@localhost:5432/hitassesnet_test")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "AdminPass12345")

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app import security


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    security._hits.clear()
    with TestClient(app) as c:  # el lifespan crea tablas y el admin inicial
        yield c


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture()
def admin(client):
    return _login(client, "admin@test.local", "AdminPass12345")


@pytest.fixture()
def vendedor(client, admin):
    r = client.post("/api/users", headers=admin, json={"email": "socio@test.local", "name": "Socio Valle", "password": "SocioPass12345", "role": "vendedor"})
    assert r.status_code == 201, r.text
    return _login(client, "socio@test.local", "SocioPass12345")
