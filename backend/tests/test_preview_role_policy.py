"""G2 preview DB role: fail closed on excessive PostgreSQL privilege."""
from types import SimpleNamespace
import pytest
from app.preview_role_policy import attest_synthetic_preview_role, RoleAttestationBlocked


class Result:
    def __init__(self, item):
        self.item = item
    def one_or_none(self):
        return self.item
    def scalar_one(self):
        return self.item
    def one(self):
        return self.item


class FakeConnection:
    dialect = SimpleNamespace(name="postgresql")
    def __init__(self, *, elevated=False, db_ddl=False, schema_ddl=False, accessible=0, tables=28):
        self.elevated = elevated
        self.db_ddl = db_ddl
        self.schema_ddl = schema_ddl
        self.accessible = accessible
        self.tables = tables
        self.calls = []
    def execute(self, query):
        sql = str(query)
        self.calls.append(sql)
        if "pg_catalog.pg_roles" in sql:
            return Result((self.elevated, False, False, False, False))
        if "has_database_privilege" in sql:
            return Result(self.db_ddl)
        if "has_schema_privilege" in sql:
            return Result(self.schema_ddl)
        if "pg_catalog.pg_class" in sql:
            return Result((self.tables, self.accessible))
        raise AssertionError("Unrecognized privilege SQL")


def test_dedicated_zero_access_preview_db_role_passes(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    conn = FakeConnection()
    report = attest_synthetic_preview_role(conn)
    assert report["preview_role_privileges"] == "NO_APP_TABLE_ACCESS"
    assert report["g2_full_security_accepted"] is False
    assert report["real_data_authorized"] is False
    assert len(conn.calls) == 4
    assert all("INSERT INTO" not in sql and "CREATE ROLE" not in sql for sql in conn.calls)


@pytest.mark.parametrize("kwargs", [
    {"elevated": True}, {"db_ddl": True}, {"schema_ddl": True},
    {"accessible": 1}, {"tables": 0}
])
def test_privileged_or_incomplete_db_role_denied(monkeypatch, kwargs):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    with pytest.raises(RoleAttestationBlocked):
        attest_synthetic_preview_role(FakeConnection(**kwargs))


def test_wrong_database_or_real_mode_denied(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(RoleAttestationBlocked):
        attest_synthetic_preview_role(FakeConnection())
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    conn=FakeConnection()
    conn.dialect=SimpleNamespace(name="sqlite")
    with pytest.raises(RoleAttestationBlocked):
        attest_synthetic_preview_role(conn)


def test_unexpected_database_exception_never_prints_connection_details(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    conn=FakeConnection()
    conn.execute=lambda query: (_ for _ in ()).throw(RuntimeError("password=fake-secret"))
    with pytest.raises(RoleAttestationBlocked) as error:
        attest_synthetic_preview_role(conn)
    assert "fake-secret" not in str(error.value)
