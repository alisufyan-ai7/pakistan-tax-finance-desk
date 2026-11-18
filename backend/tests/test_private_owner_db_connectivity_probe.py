"""P1AC: no-sensitive-output owner DB connectivity triage tests."""
from types import SimpleNamespace
import socket

import pytest
from app import private_owner_db_connectivity_probe as probe


URL = ("postgresql+psycopg://personal_cfo_owner_credentials:"
       "SYNTHETIC_NOT_A_REAL_PASSWORD_2026"
       "@postgres.railway.internal:5432/personal_cfo_owner_auth?sslmode=require")


class FakeConnection:
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def scalar(self, query):
        assert str(query) == "SELECT 1"
        return 1


class FakeEngine:
    def __init__(self, error=None):
        self.error = error
        self.disposed = False
    def connect(self):
        if self.error:
            raise self.error
        return FakeConnection()
    def dispose(self):
        self.disposed = True


class SocketConnection:
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


@pytest.fixture(autouse=True)
def private_synthetic(monkeypatch):
    monkeypatch.setattr(probe, "_inventory", lambda: {})
    monkeypatch.setattr(probe, "_operator_database_url", lambda: URL)
    monkeypatch.setattr(probe.socket, "getaddrinfo",
                        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM,
                                          6, "", ("127.0.0.1", 5432))])
    monkeypatch.setattr(probe.socket, "create_connection",
                        lambda *a, **k: SocketConnection())


def test_pass_uses_only_private_host_and_select_one(monkeypatch):
    seen = []
    eng = FakeEngine()
    def engine(url, **kwargs):
        seen.append((url, kwargs))
        return eng
    monkeypatch.setattr(probe, "create_engine", engine)
    result = probe.probe()
    assert result["result"] == "PASS"
    assert result["stage"] == "complete"
    assert not result["owner_enrolled"]
    assert not result["google_consent_activated"]
    assert not result["database_modified"]
    assert eng.disposed
    assert seen[0][0] == URL
    assert seen[0][1]["connect_args"]["options"].startswith(
        "-c default_transaction_read_only=on")
    assert "SELECT" not in str(result)
    assert "SYNTHETIC_NOT_A_REAL_PASSWORD" not in str(result)


def test_missing_inventory_or_restricted_dsn_denied(monkeypatch):
    monkeypatch.setattr(probe, "_inventory",
                        lambda: (_ for _ in ()).throw(ValueError("secret-token")))
    assert probe.probe()["stage"] == "runtime_scope_or_keys"
    monkeypatch.setattr(probe, "_inventory", lambda: {})
    monkeypatch.setattr(probe, "_operator_database_url",
                        lambda: "postgresql+psycopg://postgres:fake@localhost/finance")
    assert probe.probe()["stage"] == "restricted_dsn_policy"


def test_dns_and_tcp_failures_are_bounded(monkeypatch):
    monkeypatch.setattr(probe.socket, "getaddrinfo",
                        lambda *a, **k: (_ for _ in ()).throw(
                            socket.gaierror("private host AND SECRET")))
    assert probe.probe()["stage"] == "private_dns_resolution"
    monkeypatch.setattr(probe.socket, "getaddrinfo",
                        lambda *a, **k: [(0, 0, 0, "", (0, 0))])
    monkeypatch.setattr(probe.socket, "create_connection",
                        lambda *a, **k: (_ for _ in ()).throw(
                            ConnectionRefusedError("SECRET password")))
    assert probe.probe()["stage"] == "private_tcp_connectivity"


@pytest.mark.parametrize("state,message,stage", [
    ("28P01", "password authentication failed for user secret", "postgres_password_rejected"),
    ("28000", "no pg_hba.conf entry and hidden host", "postgres_auth_policy"),
    ("3D000", "database does not exist", "postgres_database_or_role_missing"),
    (None, "password authentication failed for user", "postgres_password_rejected"),
    (None, "no pg_hba.conf entry hidden IP", "postgres_auth_policy"),
    (None, "SSL SYSCALL error: hidden password", "postgres_tls_connection"),
    (None, "unknown driver failure including SECRET", "postgres_connection_other"),
])
def test_pg_error_classes_are_fixed_and_never_leak_secrets(
    monkeypatch, state, message, stage
):
    error = RuntimeError("outer SECRET")
    error.orig = SimpleNamespace(sqlstate=state, __str__=lambda: message)
    # SimpleNamespace does not override __str__; use a real object.
    class SourceError(Exception):
        sqlstate = state
    error.orig = SourceError(message)
    eng = FakeEngine(error)
    monkeypatch.setattr(probe, "create_engine", lambda *a, **k: eng)
    result = probe.probe()
    assert result["stage"] == stage
    assert result["result"] == "BLOCKED"
    assert "SECRET" not in str(result)
    assert message not in str(result)
    assert eng.disposed


def test_create_engine_missing_driver(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ModuleNotFoundError("psycopg private SECRET")
    monkeypatch.setattr(probe, "create_engine", unavailable)
    assert probe.probe()["stage"] == "database_driver"


def test_main_suppresses_all_unexpected_failures(monkeypatch, capsys):
    monkeypatch.setattr(probe, "probe", lambda: (_ for _ in ()).throw(
        ValueError("postgresql://USER:REALPASSWORD@hidden")))
    assert probe.main() == 1
    displayed = capsys.readouterr().out
    assert "REALPASSWORD" not in displayed
    assert "postgresql://" not in displayed
    assert "postgres_connection_other" in displayed
