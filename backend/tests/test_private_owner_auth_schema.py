"""P1Y: dedicated one-owner database has exactly six custody tables and no finance."""
import json
import re
from sqlalchemy import create_engine, inspect

from app.db import Base
from app import models  # noqa: F401
from app.private_credential_role_policy import PRIVATE_TABLES
from app.private_owner_auth_schema import (
    OWNER_AUTH_DB, OWNER_AUTH_SCHEMA_REV, OWNER_AUTH_TABLES,
    _tables, review_only_sql, schema_signature,
)


def test_compiler_emits_exact_six_private_tables_and_admin_only_version_receipt():
    script = review_only_sql()
    assert OWNER_AUTH_DB == "personal_cfo_owner_auth"
    assert OWNER_AUTH_SCHEMA_REV == "p1y_owner_auth_v1"
    assert set(OWNER_AUTH_TABLES) == PRIVATE_TABLES
    assert len(OWNER_AUTH_TABLES) == 6
    assert script.startswith("-- P1Y OWNER AUTH DDL REVIEW CANDIDATE ONLY;")
    assert script.count("CREATE TABLE") == 7
    assert script.count("CREATE INDEX") >= 2
    assert "IF current_database() <> 'personal_cfo_owner_auth'" in script
    assert "Owner schema target is not empty" in script
    assert "SET LOCAL search_path = public, pg_catalog" in script
    assert "CREATE TABLE public.owner_auth_schema_version" in script
    assert schema_signature() in script
    assert script.strip().endswith("COMMIT;")
    for name in OWNER_AUTH_TABLES:
        assert re.search(r"CREATE TABLE " + name + r"\s*\(", script)
    for financial in ("accounts", "transactions", "documents",
                      "historical_filings", "investment_positions"):
        assert "CREATE TABLE " + financial not in script
    for prohibited in ("DROP TABLE", "TRUNCATE", "CREATE ROLE", "GRANT ALL",
                       "P1C_GOOGLE_CLIENT_SECRET", "DATABASE_URL", "PASSWORD '"):
        assert prohibited not in script


def test_private_models_can_be_created_without_any_other_application_table():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        Base.metadata.create_all(connection, tables=_tables(), checkfirst=False)
        found = set(inspect(connection).get_table_names())
        assert found == set(OWNER_AUTH_TABLES)
        for name in OWNER_AUTH_TABLES:
            assert len(inspect(connection).get_columns(name)) > 1
    engine.dispose()


def test_role_plan_only_grants_six_private_tables_and_no_login():
    from pathlib import Path
    path = Path(__file__).parents[2] / "ops" / "owner_auth_isolated_role.review.sql"
    sql = path.read_text()
    assert sql.startswith("-- P1Y OWNER AUTH TECHNICAL ROLE")
    assert "IF current_database() <> 'personal_cfo_owner_auth'" in sql
    assert "owner_auth_schema_version" in sql
    assert "NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE" in sql
    assert "REVOKE ALL PRIVILEGES ON DATABASE personal_cfo_owner_auth FROM PUBLIC" in sql
    assert "GRANT CONNECT ON DATABASE personal_cfo_owner_auth" in sql
    assert "REVOKE CREATE ON SCHEMA public FROM PUBLIC" in sql
    assert "GRANT SELECT, INSERT, UPDATE ON TABLE" in sql
    for name in OWNER_AUTH_TABLES:
        assert "public." + name in sql
    assert "public.owner_auth_schema_version\n    TO personal_cfo_owner_credentials" not in sql
    assert "PASSWORD '" not in sql
    assert "GRANT ALL" not in sql
    assert "GRANT SELECT, INSERT, UPDATE ON TABLE\n    public.accounts" not in sql
