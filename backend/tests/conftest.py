import os
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("OWNER_PASSWORD", "local-test-password-123456")
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as c:
        c.auth = ("owner", "local-test-password-123456")
        yield c

@pytest.fixture
def account(client):
    r = client.post("/api/accounts", json={"name": "Synthetic Account", "institution": "Example Bank", "currency": "PKR"})
    assert r.status_code == 201, r.text
    return r.json()["id"]
