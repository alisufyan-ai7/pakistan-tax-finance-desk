"""P1W: restricted technical SQL role is NOT a second human account."""
from pathlib import Path

ROOT=Path(__file__).parents[2]
ROLE=ROOT/"ops/one_owner_credential_role.review.sql"

def test_credential_role_review_plan_is_nonlogin_and_finance_denied():
    sql=ROLE.read_text()
    assert "SOURCE REVIEW PLAN ONLY" in sql
    assert "NOLOGIN" in sql
    assert "NOINHERIT" in sql
    assert "NOCREATEDB" in sql and "NOCREATEROLE" in sql
    assert "NOBYPASSRLS" in sql and "NOSUPERUSER" in sql
    assert "GRANT SELECT, INSERT, UPDATE ON TABLE" in sql
    assert "REVOKE ALL PRIVILEGES ON ALL TABLES" in sql
    assert "REVOKE ALL PRIVILEGES ON ALL SEQUENCES" in sql
    for name in (
        "owner_private_identities","owner_private_sessions",
        "owner_private_recovery_states","owner_private_recovery_audit",
        "owner_google_metadata_grants","owner_private_oauth_attempts"
    ):
        assert "public."+name in sql
    for forbidden in (
        "public.accounts", "public.transactions", "public.historical_filings",
        "public.documents", "GRANT ALL", "ALTER ROLE personal_cfo_owner_credentials LOGIN",
        "PASSWORD '", "DROP TABLE", "TRUNCATE TABLE",
    ):
        assert forbidden not in sql
