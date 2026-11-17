"""P1X: read-only development Railway catalog preflight, no private row access."""
import base64
from types import SimpleNamespace

import pytest
from app import private_owner_db_preflight as pf


class Result:
    def __init__(self, value):
        self.value = value
    def one(self):
        return self.value
    def one_or_none(self):
        return self.value
    def scalar_one(self):
        return self.value
    def scalar_one_or_none(self):
        return self.value


class FakePostgres:
    dialect = SimpleNamespace(name="postgresql")

    def __init__(self, *, readonly=True, role=None, revision=None,
                 migration_present=False, revision_readable=False,
                 missing=None, bad_table_result=None):
        self.readonly = readonly
        self.role = role
        self.revision = revision
        self.migration_present = migration_present
        self.revision_readable = revision_readable
        self.missing = set(missing or [])
        self.bad_table_result = bad_table_result
        self.queries = []

    def execute(self, statement):
        query = str(statement)
        self.queries.append(query)
        if "SHOW transaction_read_only" in query:
            return Result("on" if self.readonly else "off")
        if "SELECT CASE WHEN to_regclass" in query:
            return Result(self.revision_readable)
        if "SELECT version_num FROM public.alembic_version" in query:
            return Result(self.revision)
        if "FROM pg_catalog.pg_roles" in query:
            return Result(self.role)
        if "SELECT (to_regclass(" in query:
            return Result(
                self.bad_table_result if self.bad_table_result is not None else
                tuple(name not in self.missing for name in pf._TABLE_NAMES) +
                (self.migration_present,))
        raise AssertionError("Unexpected potentially unsafe SQL")


@pytest.fixture(autouse=True)
def private_env(monkeypatch):
    settings = {
        "APP_DATA_MODE": "synthetic",
        "PERSONAL_CFO_PRIVATE_PREVIEW": "enabled",
        "RAILWAY_PROJECT_NAME": "personal-cfo-dev-sandbox",
        "RAILWAY_ENVIRONMENT_NAME": "development",
        "RAILWAY_SERVICE_NAME": "personal-cfo-api-preview",
        "DATABASE_URL": "postgresql+psycopg://fake:synthetic@postgres.railway.internal:5432/synthetic_ci",
        "P1Q_OPERATOR_PUBLIC_KEY": base64.urlsafe_b64encode(b"X"*32).decode(),
    }
    for key, value in settings.items():
        monkeypatch.setenv(key, value)


def test_absent_schema_does_not_claim_real_enrollment_or_migration():
    db = FakePostgres()
    result = pf.inspect_private_owner_catalog(db)
    assert result["credential_tables_present"] == 6
    assert result["alembic_table_present"] is False
    assert result["migration_at_current_head"] is None
    assert result["role_present"] is False
    assert result["role_privileges_attested"] is False
    assert result["production_approval"] is False
    assert result["owner_enrollment_status"] == "not_inspected"
    assert not any(
        any(x in sql.upper() for x in ("INSERT INTO", "UPDATE ", "DELETE FROM",
                                      "CREATE ", "DROP TABLE", "ALTER TABLE"))
        for sql in db.queries
    )


def test_exact_head_and_no_privilege_claim_despite_role_existence():
    role = (False, False, False, False, False, False, False)
    db = FakePostgres(role=role, revision=pf._HEAD,
                      migration_present=True, revision_readable=True)
    result = pf.inspect_private_owner_catalog(db)
    assert result["credential_tables_present"] == 6
    assert result["migration_at_current_head"] is True
    assert result["role_present"] is True
    assert result["role_can_login"] is False
    assert result["role_has_admin_flags"] is False
    assert result["role_privileges_attested"] is False
    assert result["no_schema_or_row_write"] is True


def test_role_is_not_implicitly_approved_even_if_login_active():
    role = (True, False, True, False, False, False, True)
    db = FakePostgres(role=role, migration_present=True, revision_readable=False)
    result = pf.inspect_private_owner_catalog(db)
    assert result["role_can_login"] is True
    assert result["role_has_admin_flags"] is True
    assert result["role_inheritance_enabled"] is True
    assert result["migration_at_current_head"] is None
    assert not any("SELECT version_num" in q for q in db.queries)


@pytest.mark.parametrize("bad", [
    {"readonly":False},
    {"bad_table_result":(False,)},
    {"bad_table_result":("maybe",)*7},
])
def test_non_read_only_or_invalid_catalog_is_rejected(bad):
    with pytest.raises(pf.PrivateOwnerPreflightBlocked):
        pf.inspect_private_owner_catalog(FakePostgres(**bad))


@pytest.mark.parametrize("change", [
    ("APP_DATA_MODE","real"),
    ("PERSONAL_CFO_PRIVATE_PREVIEW","disabled"),
    ("RAILWAY_PROJECT_NAME","unrelated-project"),
    ("RAILWAY_ENVIRONMENT_NAME","production"),
    ("RAILWAY_SERVICE_NAME","Postgres"),
    ("DATABASE_URL","postgresql://fake:secret@127.0.0.1/test"),
    ("DATABASE_URL","sqlite:////tmp/data.db"),
])
def test_only_existing_private_development_api_database_is_accepted(monkeypatch, change):
    monkeypatch.setenv(*change)
    with pytest.raises(pf.PrivateOwnerPreflightBlocked):
        pf._private_url()


def test_public_key_is_validated_without_ever_echoing_value(monkeypatch):
    assert pf._public_key_is_configured() is True
    monkeypatch.setenv("P1Q_OPERATOR_PUBLIC_KEY","this-is-not-a-public-key")
    assert pf._public_key_is_configured() is False


def test_errors_are_sanitized_and_do_not_print_database_credentials(monkeypatch,capsys):
    def blocked():
        raise ValueError("postgresql://private:secret@private.host/owner")
    monkeypatch.setattr(pf,"run_preflight",blocked)
    result = pf.main()
    captured = capsys.readouterr()
    assert result == 1
    assert not captured.out
    assert "secret" not in captured.err
    assert "postgresql://" not in captured.err
