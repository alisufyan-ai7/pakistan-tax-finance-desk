"""P1S: deny financial-table privileges even with read-only app flags."""
from types import SimpleNamespace

import pytest

from app.db import Base
from app import models  # noqa: F401
from app.private_credential_role_policy import (
    PRIVATE_TABLES, PrivateCredentialRoleBlocked, attest_private_credential_role,
)


class Result:
    def __init__(self, value):
        self.value = value
    def one_or_none(self):
        return self.value
    def one(self):
        return self.value
    def scalar_one(self):
        return self.value
    def all(self):
        return self.value


class FakePostgres:
    dialect = SimpleNamespace(name="postgresql")
    def __init__(self, *, role=None, db_create=False, schema=(True, False),
                 table_rights=None, seq_access=0, missing=None):
        self.role = (False, False, False, False, False, False, 0) if role is None else role
        self.db_create = db_create
        self.schema = schema
        self.seq_access = seq_access
        self.calls = []
        names = set(Base.metadata.tables) - set(missing or [])
        if not PRIVATE_TABLES <= set(Base.metadata.tables):
            raise AssertionError("Private tables must be registered in metadata")
        safe_private = (True, True, True, False, False, False,
                        False, True, True, True, False)
        no_rights = (False,) * 11
        table_rights = table_rights or {}
        self.tables = [
            (name,) + tuple(table_rights.get(
                name, safe_private if name in PRIVATE_TABLES else no_rights))
            for name in sorted(names)
        ]
    def execute(self, query):
        sql = str(query)
        self.calls.append(sql)
        if "P1S_ROLE" in sql:
            return Result(self.role)
        if "P1S_DB" in sql:
            return Result(self.db_create)
        if "P1S_SCHEMA" in sql:
            return Result(self.schema)
        if "P1S_TABLES" in sql:
            return Result(self.tables)
        if "P1S_SEQUENCES" in sql:
            return Result(self.seq_access)
        raise AssertionError("Unknown SQL query")


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT", "1")


def test_only_registered_private_tables_can_be_accessed():
    conn = FakePostgres()
    result = attest_private_credential_role(conn)
    assert result["candidate_credential_tables_attested"] == 6
    assert result["unexpected_table_privileges"] is False
    assert not result["production_g2_accepted"]
    assert len(conn.calls) == 5
    assert all("GRANT " not in sql and "INSERT INTO " not in sql
               for sql in conn.calls)


@pytest.mark.parametrize("mutation", [
    {"role": (True, False, False, False, False, False, 0)},
    {"role": (False, False, False, False, False, True, 0)},
    {"role": (False, False, False, False, False, False, 1)},
    {"db_create": True},
    {"schema": (True, True)},
    {"schema": (False, False)},
    {"seq_access": 1},
    {"missing": {"owner_private_recovery_audit"}},
    {"table_rights": {"accounts": (True,) + (False,) * 10}},
    {"table_rights": {"accounts": (False,) * 7 + (True,) + (False,) * 3}},
    {"table_rights": {"owner_google_metadata_grants": (True,) * 11}},
    {"table_rights": {"owner_private_sessions": (True, False, True) + (False,) * 8}},
])
def test_privilege_escalation_missing_table_and_bad_column_right_denied(mutation):
    with pytest.raises(PrivateCredentialRoleBlocked):
        attest_private_credential_role(FakePostgres(**mutation))


def test_wrong_mode_or_unapproved_candidate_denied(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(PrivateCredentialRoleBlocked):
        attest_private_credential_role(FakePostgres())
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.delenv("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT")
    with pytest.raises(PrivateCredentialRoleBlocked):
        attest_private_credential_role(FakePostgres())
    monkeypatch.setenv("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT", "1")
    conn = FakePostgres()
    conn.dialect = SimpleNamespace(name="sqlite")
    with pytest.raises(PrivateCredentialRoleBlocked):
        attest_private_credential_role(conn)


def test_sql_error_does_not_disclose_sensitive_exception_text():
    conn = FakePostgres()
    def broken(query):
        raise ValueError("password=some-private-railway-value")
    conn.execute = broken
    with pytest.raises(PrivateCredentialRoleBlocked) as exc:
        attest_private_credential_role(conn)
    assert "some-private-railway-value" not in str(exc.value)
