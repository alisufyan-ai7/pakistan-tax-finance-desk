"""G2: isolated ephemeral CI-only PostgreSQL least-privilege bootstrap.

DO NOT execute on Railway, owner DB, production, staging or a restore target.
This is deliberately locked to the fixed disposable synthetic_ci_db used by
GitHub backend-ci. It does not set Railway environment secrets or deploy users.
"""
from __future__ import annotations

import os
import re


class PreviewRoleBootstrapBlocked(ValueError):
    """Role provisioning refused outside the explicit ephemeral CI test DB."""


CI_DATABASE = "synthetic_ci_db"
CI_ROLE = "personal_cfo_preview_connectivity_ci"


def provision_synthetic_preview_role(admin_connection, *, password: str) -> dict:
    """Create one disposable LOGIN role with no financial-table privileges.

    Requires a freshly initialized ephemeral PostgreSQL18 CI database, connected
    as its CI administrator. No production DSN is ever permitted, regardless of
    owner consent passed to this function.
    """
    if os.getenv("APP_DATA_MODE") != "synthetic" or os.getenv("G2_EPHEMERAL_CI_ONLY") != "1":
        raise PreviewRoleBootstrapBlocked("Ephemeral synthetic CI role provisioning only")
    if (not isinstance(password, str)
        or not 24 <= len(password) <= 128
        or not re.fullmatch(r"[A-Za-z0-9_-]+", password)):
        raise PreviewRoleBootstrapBlocked("Invalid ephemeral role password policy")
    try:
        from psycopg import sql
        database = admin_connection.execute("SELECT current_database()").fetchone()[0]
        if database != CI_DATABASE:
            raise PreviewRoleBootstrapBlocked("Refusing non-CI PostgreSQL database")
        existing = admin_connection.execute("SELECT to_regrole(%s)", (CI_ROLE,)).fetchone()[0]
        if existing is not None:
            raise PreviewRoleBootstrapBlocked("Existing CI preview role will not be overwritten")
        with admin_connection.transaction():
            # Public TEMP is granted by default on Postgres. Revoke only in
            # disposable test DB; never apply this shared-role change live.
            admin_connection.execute(
                sql.SQL("REVOKE TEMPORARY ON DATABASE {} FROM PUBLIC").format(
                    sql.Identifier(CI_DATABASE)))
            admin_connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            admin_connection.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC")
            admin_connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                        "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}").format(
                    sql.Identifier(CI_ROLE), sql.Literal(password)))
            admin_connection.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(CI_DATABASE), sql.Identifier(CI_ROLE)))
            # SELECT 1 requires no application-table read grants.
    except PreviewRoleBootstrapBlocked:
        raise
    except Exception:
        raise PreviewRoleBootstrapBlocked("Ephemeral PostgreSQL privilege setup failed closed") from None
    return {
        "synthetic_only": True,
        "ephemeral_ci_role_provisioned": True,
        "live_railway_role_changed": False,
        "preview_can_access_finance_tables": False,
        "g2_release_accepted": False,
    }
