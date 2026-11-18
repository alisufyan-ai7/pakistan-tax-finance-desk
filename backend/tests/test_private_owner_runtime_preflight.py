"""P1AA: source-safe preflight must fail closed before real MFA enrollment."""
from types import SimpleNamespace

import pytest

from app import private_owner_runtime_preflight as pf


class Result:
    def __init__(self, value):
        self.value = value
    def one(self):
        return self.value
    def scalar_one(self):
        return self.value


class FakeConnection:
    dialect = SimpleNamespace(name="postgresql")

    def __init__(self, *, ssl=True, readonly=True, role="personal_cfo_owner_credentials",
                 db="personal_cfo_owner_auth", tcp=True, populated=None):
        self.ssl = ssl
        self.readonly = readonly
        self.role = role
        self.db = db
        self.tcp = tcp
        self.populated = populated
        self.sql = []

    def execute(self, query):
        statement = str(query)
        self.sql.append(statement)
        if "current_database(), current_user" in statement:
            return Result((
                self.db, self.role, self.tcp, self.ssl,
                "on" if self.readonly else "off",
            ))
        if "SELECT EXISTS(SELECT 1 FROM public." in statement:
            return Result(
                self.populated is not None and
                self.populated in statement
            )
        pytest.fail("Unexpected query shape could expose data or mutate SQL")


@pytest.fixture(autouse=True)
def synthetic_env(monkeypatch):
    settings = {
        "APP_DATA_MODE": "synthetic",
        "PERSONAL_CFO_PRIVATE_PREVIEW": "enabled",
        "RAILWAY_PROJECT_NAME": "personal-cfo-dev-sandbox",
        "RAILWAY_ENVIRONMENT_NAME": "development",
        "RAILWAY_SERVICE_NAME": "personal-cfo-api-preview",
        "P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT": "1",
        "P1W_OWNER_REF": "SYNTHETIC_OWNER_REF_2026",
    }
    for i,name in enumerate(pf._KEY_NAMES):
        settings[name] = pf.base64.urlsafe_b64encode(bytes([i+1])*32).decode()
    settings["P1Q_OPERATOR_PUBLIC_KEY"] = pf.base64.urlsafe_b64encode(b"K"*32).decode()
    for name,value in settings.items():
        monkeypatch.setenv(name, value)


def test_private_owner_credentials_verified_without_leaking_or_mutating(monkeypatch):
    audited=[]
    monkeypatch.setattr(pf,"attest_private_credential_role",
                        lambda c:audited.append(c))
    conn=FakeConnection()
    result=pf.check_private_runtime(conn)
    assert audited==[conn]
    assert result["authenticated_tls_tcp_connection"]
    assert result["owner_security_tables_empty"]
    assert result["least_privilege_attestation_passed"]
    assert result["production_g2_accepted"] is False
    assert len(conn.sql)==7  # one TLS/role check plus six table empty checks
    assert not any("INSERT " in x.upper() or "UPDATE " in x.upper()
                   or "DELETE " in x.upper() or "CREATE " in x.upper()
                   for x in conn.sql)
    assert len(pf._inventory()["runtime_key_count"].__str__())==1


@pytest.mark.parametrize("db,role,tcp,ssl,readonly",[
    ("postgres","personal_cfo_owner_credentials",True,True,True),
    ("personal_cfo_owner_auth","postgres",True,True,True),
    ("personal_cfo_owner_auth","personal_cfo_owner_credentials",False,True,True),
    ("personal_cfo_owner_auth","personal_cfo_owner_credentials",True,False,True),
    ("personal_cfo_owner_auth","personal_cfo_owner_credentials",True,True,False),
])
def test_wrong_database_role_or_transport_blocks(monkeypatch,db,role,tcp,ssl,readonly):
    monkeypatch.setattr(pf,"attest_private_credential_role",
                        lambda _:pytest.fail("must not attest an untrusted role"))
    with pytest.raises(pf.PrivateOwnerRuntimePreflightBlocked):
        pf.check_private_runtime(
            FakeConnection(db=db,role=role,tcp=tcp,ssl=ssl,readonly=readonly))


def test_existing_owner_or_recovery_row_blocks_first_enrollment(monkeypatch):
    monkeypatch.setattr(pf,"attest_private_credential_role",lambda _:None)
    with pytest.raises(pf.PrivateOwnerRuntimePreflightBlocked):
        pf.check_private_runtime(FakeConnection(populated="owner_private_identities"))


@pytest.mark.parametrize("name,value", [
    ("APP_DATA_MODE","real"),
    ("PERSONAL_CFO_PRIVATE_PREVIEW","0"),
    ("RAILWAY_PROJECT_NAME","different-project"),
    ("RAILWAY_ENVIRONMENT_NAME","production"),
    ("RAILWAY_SERVICE_NAME","Postgres"),
    ("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT","0"),
    ("P1N_OWNER_ENCRYPTION_KEY","not-base64"),
    ("P1Q_OPERATOR_PUBLIC_KEY","garbled"),
    ("P1W_OWNER_REF","bad"),
])
def test_key_or_environment_gate_fails_closed(monkeypatch,name,value):
    monkeypatch.setenv(name,value)
    with pytest.raises(pf.PrivateOwnerRuntimePreflightBlocked):
        pf._inventory()


def test_key_domains_must_be_distinct(monkeypatch):
    monkeypatch.setenv(pf._KEY_NAMES[0],pf.base64.urlsafe_b64encode(b"Z"*32).decode())
    monkeypatch.setenv(pf._KEY_NAMES[1],pf.base64.urlsafe_b64encode(b"Z"*32).decode())
    with pytest.raises(pf.PrivateOwnerRuntimePreflightBlocked):
        pf._inventory()


def test_failed_sql_or_env_never_prints_secrets(monkeypatch,capsys):
    def error():
        raise RuntimeError("postgresql+psycopg://user:SECRET@private/owner_auth")
    monkeypatch.setattr(pf,"run_preflight",error)
    assert pf.main()==1
    captured=capsys.readouterr()
    assert "SECRET" not in captured.out+captured.err
    assert "postgresql://" not in captured.out+captured.err
