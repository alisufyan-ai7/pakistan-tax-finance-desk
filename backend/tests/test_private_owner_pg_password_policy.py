"""P1AE synthetic-only proofs of password authentication and failure gates."""
from types import SimpleNamespace

import pytest

from app import private_owner_pg_password_policy as pg


CORRECT = ("postgresql+psycopg://personal_cfo_owner_credentials:"
           "SYNTHETIC_only_a_valid_password_2026"
           "@postgres-ade30e25.railway.internal:5432/"
           "personal_cfo_owner_auth?sslmode=require")


class Result:
    def __init__(self, value):
        self.value = value
    def one(self):
        return self.value


class Connection:
    def __init__(self, *, allowed=True):
        self.allowed = allowed
        self.sql = []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, query):
        q = str(query)
        self.sql.append(q)
        if "current_database(), current_user" in q:
            return Result(("personal_cfo_owner_auth",
                           "personal_cfo_owner_credentials",
                           True, True, "on"))
        if q == "SELECT 1":
            return Result(1)
        pytest.fail("Unreviewed SQL executed")


class Engine:
    def __init__(self, connection=None, error=None):
        self.conn = connection or Connection()
        self.error = error
        self.disposed = False
    def connect(self):
        if self.error is not None:
            raise self.error
        return self.conn
    def dispose(self):
        self.disposed = True


class FakeDBError(Exception):
    def __init__(self, state=None, message=""):
        self.sqlstate = state
        super().__init__(message)


@pytest.fixture(autouse=True)
def private_operator(monkeypatch):
    monkeypatch.setattr(pg, "_inventory", lambda: {})
    monkeypatch.setattr(pg, "_operator_database_url", lambda: CORRECT)


def setup_engines(monkeypatch, wrong_error, *, successful_wrong=False):
    valid = Engine()
    invalid = Engine(error=None if successful_wrong else wrong_error)
    records = []
    def engine(url):
        records.append(url)
        return valid if len(records) == 1 else invalid
    monkeypatch.setattr(pg, "_read_only_engine", engine)
    return valid, invalid, records


def test_explicit_wrong_password_rejection_is_required_and_secrets_never_printed(
    monkeypatch
):
    v,w,records = setup_engines(
        monkeypatch,
        FakeDBError(state="28P01", message="PASSWORD SECRET_SERVER_IP"),
    )
    report = pg.prove_private_postgres_password_enforcement()
    assert report["result"] == "PASS"
    assert report["server_rejects_intentionally_wrong_password"] is True
    assert report["same_private_tcp_host_checked"] is True
    assert report["read_only"]
    assert not report["owner_enrolled"]
    assert not report["database_modified"]
    assert v.disposed and w.disposed
    assert len(records) == 2
    assert records[0].host == records[1].host
    assert records[0].database == records[1].database
    assert records[0].username == records[1].username
    assert records[0].query["sslmode"] == records[1].query["sslmode"] == "require"
    assert records[0].password == "SYNTHETIC_only_a_valid_password_2026"
    assert records[1].password == pg._INVALID_PASSWORD
    assert "SECRET_SERVER_IP" not in str(report)
    assert "SYNTHETIC_only_a_valid_password_2026" not in str(report)


def test_wrong_password_that_authenticates_fails_closed(monkeypatch):
    v,w,records = setup_engines(
        monkeypatch, wrong_error=None, successful_wrong=True)
    report = pg.prove_private_postgres_password_enforcement()
    assert report["result"] == "BLOCKED"
    assert report["stage"] == "wrong_password_accepted"
    assert not report["server_rejects_intentionally_wrong_password"]
    assert v.disposed and w.disposed


@pytest.mark.parametrize("error", [
    FakeDBError(state="08001", message="private network unreachable secret"),
    FakeDBError(state=None, message="connection timed out, SECRET"),
    FakeDBError(state=None, message="no pg_hba.conf entry, hidden network"),
    FakeDBError(state="28000", message="permission denied"),
])
def test_network_or_policy_error_is_not_password_auth_proof(monkeypatch, error):
    setup_engines(monkeypatch, error)
    report = pg.prove_private_postgres_password_enforcement()
    assert report["result"] == "BLOCKED"
    assert report["stage"] == "wrong_password_rejection_unproven"
    assert str(error) not in str(report)


def test_libpq_password_failure_without_sqlstate_can_still_prove_rejection(monkeypatch):
    setup_engines(monkeypatch,
                  FakeDBError(message="FATAL: password authentication failed for user \"personal_cfo_owner_credentials\""))
    assert pg.prove_private_postgres_password_enforcement()["result"] == "PASS"


def test_fail_closed_before_network_when_scope_denied(monkeypatch):
    def err():
        raise RuntimeError("key=CONFIDENTIAL")
    monkeypatch.setattr(pg, "_inventory", err)
    monkeypatch.setattr(pg,"_read_only_engine",
                        lambda _:pytest.fail("do not touch SQL"))
    report=pg.prove_private_postgres_password_enforcement()
    assert report["stage"]=="private_operator_scope"
    assert "CONFIDENTIAL" not in str(report)


def test_failed_dsn_guard_exits_without_connect(monkeypatch):
    monkeypatch.setattr(pg,"_operator_database_url",
                        lambda:"postgresql://admin:secret@public.example/finance")
    # A bare make_url still succeeds, but this is an internal _operator_database_url
    # mock. The actual helper validates username/DB/TLS before returning.
    def reject():
        raise ValueError("secret")
    monkeypatch.setattr(pg,"_operator_database_url",reject)
    monkeypatch.setattr(pg,"_read_only_engine",
                        lambda _:pytest.fail("do not touch SQL"))
    assert pg.prove_private_postgres_password_enforcement()["stage"] == (
        "restricted_database_url_policy"
    )


def test_failed_positive_tls_identity_does_not_test_wrong_password(monkeypatch):
    engine = Engine(error=FakeDBError(None,"TLS failure with PASSWORD"))
    calls=[]
    monkeypatch.setattr(pg,"_read_only_engine",
                        lambda url: calls.append(url) or engine)
    report=pg.prove_private_postgres_password_enforcement()
    assert report["stage"] == "positive_tls_owner_connection"
    assert len(calls)==1
    assert engine.disposed


def test_main_errors_are_sanitized(monkeypatch,capsys):
    monkeypatch.setattr(pg, "prove_private_postgres_password_enforcement",
                        lambda: (_ for _ in ()).throw(
                            RuntimeError("postgresql://secret:password@hidden")))
    assert pg.main() == 1
    output = capsys.readouterr()
    assert "password@hidden" not in output.out+output.err
    assert "wrong_password_rejection_unproven" in output.out


def test_read_only_engine_is_new_no_pool_with_timeouts(monkeypatch):
    calls=[]
    monkeypatch.setattr(pg,"create_engine",lambda url,**kw: calls.append((url,kw)))
    pg._read_only_engine("a-synthetic-url")
    assert calls[0][1]["poolclass"] is pg.NullPool
    opts=calls[0][1]["connect_args"]
    assert opts["connect_timeout"] == 5
    assert "default_transaction_read_only=on" in opts["options"]
