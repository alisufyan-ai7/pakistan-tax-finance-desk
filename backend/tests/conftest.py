import os
import base64
import json
import pytest
from fastapi.testclient import TestClient
# Public synthetic fixture key; test code only, never use in actual application.
# Set BEFORE importing main, which instantiates a local demonstration app.
os.environ.setdefault("LEDGER_FIELD_KEYS_JSON", json.dumps({
    "synthetic_test": base64.urlsafe_b64encode(b"S" * 32).decode("ascii")
}))
os.environ.setdefault("LEDGER_FIELD_ACTIVE_KEY", "synthetic_test")
# Public fixture HMAC (not a credential): intentionally different from AES + bank dedup.
os.environ.setdefault("PRIVATE_EVENT_HMAC_KEY", base64.urlsafe_b64encode(b"P" * 32).decode("ascii"))
os.environ.setdefault("CONFIDENTIAL_BANK_HMAC_KEY", base64.urlsafe_b64encode(b"C" * 32).decode("ascii"))
os.environ.setdefault("LEDGER_DEDUP_HMAC_KEY", base64.urlsafe_b64encode(b"D" * 32).decode("ascii"))
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
