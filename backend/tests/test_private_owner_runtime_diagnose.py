"""Fail-closed P1AB diagnostic: stage IDs only, no secrets or DB writes."""
import base64
from types import SimpleNamespace

import pytest
from app import private_owner_runtime_diagnose as d


class R:
    def __init__(self, data):
        self.data = data
    def one(self):
        return self.data
    def scalar_one(self):
        return self.data


class FakeDB:
    dialect = SimpleNamespace(name="postgresql")
    def __init__(self, *, populated=False, tls=True, role=True):
        self.populated=populated
        self.tls=tls
        self.role=role
        self.queries=[]
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self, query):
        q=str(query)
        self.queries.append(q)
        if q=="SET TRANSACTION READ ONLY":return R(None)
        if "current_database(), current_user" in q:
            return R(("personal_cfo_owner_auth",
                      "personal_cfo_owner_credentials" if self.role else "postgres",
                      True, self.tls, "on"))
        if q.startswith("SELECT EXISTS(SELECT 1 FROM public."):
            return R(self.populated)
        raise AssertionError("Unknown SQL is not permitted")


class Engine:
    def __init__(self, conn, fail=None):
        self.conn=conn
        self.fail=fail
        self.disposed=False
    def connect(self):
        if self.fail:
            raise ValueError("SQL password=DO_NOT_PRINT_OR_STORE")
        return self.conn
    def dispose(self):self.disposed=True


@pytest.fixture(autouse=True)
def env(monkeypatch):
    for k,v in {
        "APP_DATA_MODE":"synthetic",
        "PERSONAL_CFO_PRIVATE_PREVIEW":"enabled",
        "RAILWAY_PROJECT_NAME":"personal-cfo-dev-sandbox",
        "RAILWAY_ENVIRONMENT_NAME":"development",
        "RAILWAY_SERVICE_NAME":"personal-cfo-api-preview",
        "P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT":"1",
        "P1W_OWNER_REF":"synthetic-one-owner-2026",
        "P1Q_OPERATOR_PUBLIC_KEY":base64.urlsafe_b64encode(b"Z"*32).decode(),
    }.items():monkeypatch.setenv(k,v)
    for i,k in enumerate(d._KEY_NAMES):
        monkeypatch.setenv(k,base64.urlsafe_b64encode(bytes([i+1])*32).decode())
    monkeypatch.setattr(d,"_operator_database_url",lambda:"postgresql+psycopg://FAKE")
    monkeypatch.setattr(d,"attest_private_credential_role",lambda c:None)


def fake_engine(monkeypatch, connection, fail=None):
    eng=Engine(connection,fail)
    monkeypatch.setattr(d,"create_engine",lambda *a,**kw:eng)
    return eng


def test_sanitized_success_reads_only_the_six_approved_tables(monkeypatch):
    conn=FakeDB()
    engine=fake_engine(monkeypatch,conn)
    result=d.diagnose()
    assert result["result"]=="PASS"
    assert result["stage"]=="complete"
    assert result["owner_enrolled"] is False
    assert engine.disposed
    assert len(conn.queries)==8
    for q in conn.queries:
        assert not any(b in q.upper() for b in (
            "DROP TABLE", "CREATE TABLE", "DELETE FROM", "INSERT INTO",
            "UPDATE PUBLIC", "GRANT ", "ALTER ROLE", "TRUNCATE TABLE"))
    assert sum(q.startswith("SELECT EXISTS(SELECT 1 FROM public.")
               for q in conn.queries)==6


@pytest.mark.parametrize("variable,value,stage",[
    ("APP_DATA_MODE","real","environment_scope"),
    ("RAILWAY_SERVICE_NAME","Postgres","environment_scope"),
    ("RAILWAY_PROJECT_NAME","other","environment_scope"),
    ("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT","0","environment_scope"),
    ("P1N_OWNER_ENCRYPTION_KEY","garbage","key_inventory"),
    ("P1Q_OPERATOR_PUBLIC_KEY","not-base64","key_inventory"),
    ("P1W_OWNER_REF","bad","key_inventory"),
])
def test_fail_closed_at_configuration_stage(monkeypatch,variable,value,stage):
    monkeypatch.setenv(variable,value)
    output=d.diagnose()
    assert output["result"]=="BLOCKED"
    assert output["stage"]==stage


def test_duplicate_keys_rejected(monkeypatch):
    monkeypatch.setenv(d._KEY_NAMES[0],monkeypatch.getenv(d._KEY_NAMES[1])
                       if hasattr(monkeypatch,"getenv") else
                       base64.urlsafe_b64encode(b"\x02"*32).decode())
    assert d.diagnose()["stage"]=="key_inventory"


def test_restricted_dsn_policy_denial_is_not_a_secret_leak(monkeypatch):
    def bad():
        raise ValueError("SECRET=private postgresql://admin:XYZ@host")
    monkeypatch.setattr(d,"_operator_database_url",bad)
    outcome=d.diagnose()
    assert outcome["stage"]=="isolated_database_url_policy"
    assert "XYZ" not in str(outcome)


def test_database_connection_denial_is_sanitized(monkeypatch):
    engine=fake_engine(monkeypatch,FakeDB(),fail=True)
    outcome=d.diagnose()
    assert outcome["stage"]=="database_connection"
    assert "DO_NOT_PRINT" not in str(outcome)
    assert engine.disposed


@pytest.mark.parametrize("conn,expected",[
    (FakeDB(tls=False),"tls_identity_readonly"),
    (FakeDB(role=False),"tls_identity_readonly"),
    (FakeDB(populated=True),"owner_tables_not_empty_or_inaccessible"),
])
def test_fail_closed_for_transport_role_or_existing_owner(monkeypatch,conn,expected):
    fake_engine(monkeypatch,conn)
    assert d.diagnose()["stage"]==expected


def test_effective_role_audit_failure_is_a_single_bounded_stage(monkeypatch):
    def blocked(_):
        raise ValueError("private db host and password leak here")
    monkeypatch.setattr(d,"attest_private_credential_role",blocked)
    fake_engine(monkeypatch,FakeDB())
    outcome=d.diagnose()
    assert outcome["stage"]=="effective_role_permissions"
    assert "password" not in str(outcome)


def test_main_prints_no_secrets_on_unexpected_failure(monkeypatch,capsys):
    def fail():
        raise ValueError("REAL_SECRET DSN user:password@host")
    monkeypatch.setattr(d,"diagnose",fail)
    assert d.main()==1
    printed=capsys.readouterr()
    assert "REAL_SECRET" not in printed.out+printed.err
    assert "password" not in printed.out+printed.err
    assert "unexpected_failure" in printed.out
