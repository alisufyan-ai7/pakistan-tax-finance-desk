"""P1AI: source-only one-owner private ASGI factory, never a public route."""
import base64
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app import private_owner_login_service as candidate
from app.preview_api import create_preview_app

TARGET = "personal-cfo-api-preview"
OWNER = "SYNTHETIC_OWNER_SINGLE_LOGIN_TEST_2026"
GATEWAY = "SYNTHETIC_PRIVATE_GATEWAY_TEST_2026_" + "G" * 48


def config(monkeypatch):
    values = {
        "APP_DATA_MODE": "synthetic",
        "PERSONAL_CFO_PRIVATE_PREVIEW": "enabled",
        "RAILWAY_PROJECT_NAME": "personal-cfo-dev-sandbox",
        "RAILWAY_ENVIRONMENT_NAME": "development",
        "RAILWAY_SERVICE_NAME": TARGET,
        "P1AI_PRIVATE_OWNER_SERVICE_ONLY": "1",
        "P1AI_G2_RUNTIME_INDEPENDENTLY_REVIEWED": "1",
        "P1N_PRIVATE_OWNER_AUTH_ONLY": "1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED": "1",
        "P1Q_PRIVATE_HTTP_GATEWAY_ONLY": "1",
        "P1Q_G2_PRIVATE_INGRESS_REVIEWED": "1",
        "P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT": "1",
        "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN": GATEWAY,
        "P1W_OWNER_REF": OWNER,
    }
    key_names = (
        "P1N_OWNER_ENCRYPTION_KEY",
        "P1N_OWNER_IDENTITY_HMAC_KEY",
        "P1N_OWNER_SESSION_HMAC_KEY",
        "P1P_OWNER_RECOVERY_ENCRYPTION_KEY",
        "P1P_OWNER_RECOVERY_HMAC_KEY",
        "P1Q_OPERATOR_PUBLIC_KEY",
    )
    for k, v in values.items():
        monkeypatch.setenv(k, v)
    for i, k in enumerate(key_names):
        monkeypatch.setenv(k, base64.urlsafe_b64encode(
            bytes([i+1]) * 32).decode("ascii"))


class FakeResult:
    def __init__(self, one_value=None, scalar=None):
        self.one_value, self.scalar = one_value, scalar

    def one(self):
        return self.one_value

    def scalar_one(self):
        return self.scalar


class PrivateConn:
    dialect = SimpleNamespace(name="postgresql")

    def __init__(self, *, ssl=True, counts=(1, 1, 1)):
        self.ssl = ssl
        self.counts = counts
        self.sql = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query):
        sql = str(query)
        self.sql.append(sql)
        if sql == "SET TRANSACTION READ ONLY":
            return FakeResult()
        if "SELECT current_database()" in sql:
            return FakeResult(one_value=(
                "personal_cfo_owner_auth", "personal_cfo_owner_credentials",
                True, self.ssl, "on"))
        if "count(*) FROM public.owner_private_identities" in sql:
            return FakeResult(scalar=self.counts[0])
        if "count(*) FROM public.owner_private_recovery_states" in sql:
            return FakeResult(scalar=self.counts[1])
        if "count(*) FROM public.owner_private_recovery_audit" in sql:
            return FakeResult(scalar=self.counts[2])
        raise AssertionError("Unexpected private owner SQL")


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection
        self.disposed = False

    def connect(self):
        return self.connection

    def dispose(self):
        self.disposed = True


def test_unapproved_private_entrypoint_never_opens_database(monkeypatch):
    monkeypatch.delenv("P1AI_G2_RUNTIME_INDEPENDENTLY_REVIEWED", raising=False)
    def never_engine():
        raise AssertionError("No database should be used without G2 gates")
    monkeypatch.setattr(candidate, "_new_engine", never_engine)
    app = candidate.create_review_only_private_owner_login_service()
    with pytest.raises(candidate.PrivateOwnerLoginServiceBlocked):
        with TestClient(app):
            pass


@pytest.mark.parametrize("key,value", (
    ("APP_DATA_MODE", "real"),
    ("RAILWAY_SERVICE_NAME", "Postgres"),
    ("P1AI_PRIVATE_OWNER_SERVICE_ONLY", "0"),
    ("P1Q_G2_PRIVATE_INGRESS_REVIEWED", "0"),
    ("P1N_G2_OWNER_IDENTITY_REVIEWED", "0"),
    ("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", "bad"),
    ("P1W_OWNER_REF", ""),
))
def test_source_only_release_approval_and_escrow_gates(monkeypatch,key,value):
    config(monkeypatch)
    monkeypatch.setenv(key, value)
    with pytest.raises(candidate.PrivateOwnerLoginServiceBlocked):
        candidate._reviewed_private_configuration()


def test_isolated_private_login_factory_installs_only_three_auth_paths(monkeypatch):
    config(monkeypatch)
    connection = PrivateConn()
    engine = FakeEngine(connection)
    monkeypatch.setattr(candidate, "_new_engine", lambda: engine)
    monkeypatch.setattr(candidate, "attest_private_credential_role",
                        lambda connection: {"least_privilege": True})
    app = candidate.create_review_only_private_owner_login_service()
    assert {route.path for route in app.routes if route.path.startswith(
        "/internal/drive/")} == {
            "/internal/drive/auth/login",
            "/internal/drive/auth/session",
            "/internal/drive/auth/logout",
        }
    with TestClient(app) as client:
        # No credentials, no public gateway proof, no owner session.
        response = client.get("/internal/drive/auth/session")
        assert response.status_code == 403
        assert client.get("/api/drive/oauth/callback").status_code == 404
        assert client.get("/internal/drive/oauth/start").status_code == 404
        assert client.get("/internal/finance/ledger").status_code == 404
    assert engine.disposed
    assert any("SET TRANSACTION READ ONLY" in x for x in connection.sql)
    assert not any(
        "financial" in sql or "SELECT *" in sql
        for sql in connection.sql
    )
    assert not any(
        route.path.startswith("/internal/drive/auth/")
        for route in create_preview_app().routes
    )


@pytest.mark.parametrize("ssl,counts", [
    (False, (1, 1, 1)),
    (True, (0, 1, 1)),
    (True, (2, 1, 1)),
    (True, (1, 0, 1)),
    (True, (1, 1, 0)),
])
def test_tls_or_one_owner_recovery_mismatch_denies_startup(
    monkeypatch, ssl, counts
):
    config(monkeypatch)
    engine = FakeEngine(PrivateConn(ssl=ssl, counts=counts))
    monkeypatch.setattr(candidate, "_new_engine", lambda: engine)
    monkeypatch.setattr(candidate, "attest_private_credential_role",
                        lambda connection: {})
    app = candidate.create_review_only_private_owner_login_service()
    with pytest.raises(candidate.PrivateOwnerLoginServiceBlocked):
        with TestClient(app):
            pass
    assert engine.disposed
