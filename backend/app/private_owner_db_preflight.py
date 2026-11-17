"""P1X: read-only Personal CFO owner credential schema/role preflight.

Run inside the EXISTING private Railway API container using authenticated
Railway SSH; no public database proxy or new service is required:

  railway ssh --project <approved-project-id> --environment development \
      --service personal-cfo-api-preview -- python -m app.private_owner_db_preflight

This command inspects *catalog metadata only*. It does not inspect owner
identity, financial records, OAuth grants or secrets, and never runs DDL.
It reports whether the six tables and restricted technical SQL role exist.
A result cannot itself authorize MFA enrollment or live Google consent.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from .private_credential_role_policy import PRIVATE_TABLES

_HEAD = "0022_private_oauth_attempts"
_PROJECT = "personal-cfo-dev-sandbox"
_ENV = "development"
_SERVICE = "personal-cfo-api-preview"
_ROLE = "personal_cfo_owner_credentials"

_TABLE_NAMES = tuple(sorted(PRIVATE_TABLES))

_CHECK_TABLES = text(
    "SELECT " + ", ".join(
        f"(to_regclass('public.{name}') IS NOT NULL)"
        for name in (*_TABLE_NAMES, "alembic_version")
    )
)
_CHECK_VERSION_ACCESS = text(
    "SELECT CASE WHEN to_regclass('public.alembic_version') IS NOT NULL "
    "THEN has_table_privilege(current_user, "
    "to_regclass('public.alembic_version'), 'SELECT') "
    "ELSE FALSE END"
)
_CHECK_ROLE = text(
    "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, "
    "rolreplication, rolbypassrls, rolinherit "
    "FROM pg_catalog.pg_roles WHERE rolname='personal_cfo_owner_credentials'"
)
_GET_VERSION = text("SELECT version_num FROM public.alembic_version")
_READ_ONLY = text("SHOW transaction_read_only")


class PrivateOwnerPreflightBlocked(ValueError):
    """Private, synthetic-only read-only credential preflight is unavailable."""


def _private_url() -> str:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("PERSONAL_CFO_PRIVATE_PREVIEW") != "enabled"
        or os.getenv("RAILWAY_PROJECT_NAME") != _PROJECT
        or os.getenv("RAILWAY_ENVIRONMENT_NAME") != _ENV
        or os.getenv("RAILWAY_SERVICE_NAME") != _SERVICE
    ):
        raise PrivateOwnerPreflightBlocked("Wrong private project or data mode")
    raw = os.getenv("DATABASE_URL", "")
    try:
        parsed = make_url(raw)
        if (
            parsed.drivername not in ("postgresql", "postgresql+psycopg")
            or not parsed.host
            or not parsed.host.lower().endswith(".railway.internal")
            or parsed.port not in (None, 5432)
            or not parsed.database
        ):
            raise ValueError()
    except Exception:
        raise PrivateOwnerPreflightBlocked(
            "Approved private PostgreSQL connection unavailable"
        ) from None
    # Return only to the local SQLAlchemy connection call, never output DSN.
    return raw


def _public_key_is_configured() -> bool:
    supplied = os.getenv("P1Q_OPERATOR_PUBLIC_KEY", "")
    try:
        raw = base64.b64decode(supplied, altchars=b"-_", validate=True)
        return len(raw) == 32
    except (ValueError, binascii.Error, TypeError):
        return False


def inspect_private_owner_catalog(connection) -> dict:
    """Inspect catalog metadata on an enforced read-only transaction.

    The supplied connection is expected to be the restricted synthetic
    Railway preview connection. No sensitive row is queried or returned.
    """
    if connection.dialect.name != "postgresql":
        raise PrivateOwnerPreflightBlocked("PostgreSQL-only private preflight")
    if connection.execute(_READ_ONLY).scalar_one() != "on":
        raise PrivateOwnerPreflightBlocked("Read-only database mode not enforced")

    present = connection.execute(_CHECK_TABLES).one()
    if len(present) != len(_TABLE_NAMES) + 1:
        raise PrivateOwnerPreflightBlocked("Credential schema census inconclusive")
    if any(type(x) is not bool for x in present):
        raise PrivateOwnerPreflightBlocked("Credential schema result indeterminate")
    tables = dict(zip(_TABLE_NAMES, present[:-1]))
    has_alembic = present[-1]
    can_read_revision = (
        bool(connection.execute(_CHECK_VERSION_ACCESS).scalar_one())
        if has_alembic else False
    )
    revision = (
        connection.execute(_GET_VERSION).scalar_one_or_none()
        if can_read_revision else None
    )
    role = connection.execute(_CHECK_ROLE).one_or_none()
    if role is not None and (len(role) != 7 or
                            any(type(value) is not bool for value in role)):
        raise PrivateOwnerPreflightBlocked("Credential-role state inconclusive")

    return {
        "project": _PROJECT,
        "environment": _ENV,
        "service": _SERVICE,
        "enforced_read_only": True,
        "no_schema_or_row_write": True,
        "credential_tables_present": sum(tables.values()),
        "credential_tables_expected": len(_TABLE_NAMES),
        "missing_credential_tables": [name for name, ok in tables.items() if not ok],
        "alembic_table_present": has_alembic,
        "migration_revision_readable": can_read_revision,
        "migration_at_current_head": (
            revision == _HEAD if can_read_revision else None
        ),
        "role_present": role is not None,
        "role_can_login": role[0] if role is not None else None,
        "role_has_admin_flags": (
            any(role[1:6]) if role is not None else None
        ),
        "role_inheritance_enabled": role[6] if role is not None else None,
        "role_privileges_attested": False,
        "owner_enrollment_status": "not_inspected",
        "google_consent_status": "not_inspected",
        "production_approval": False,
    }


def run_preflight() -> dict:
    url = _private_url()
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 4,
            "options": "-c default_transaction_read_only=on -c statement_timeout=3500",
        },
    )
    try:
        with engine.connect() as conn:
            report = inspect_private_owner_catalog(conn)
        report["offline_public_recovery_key_configured"] = _public_key_is_configured()
        return report
    finally:
        engine.dispose()


def main() -> int:
    try:
        print(json.dumps(run_preflight(), indent=2, sort_keys=True))
        return 0
    except PrivateOwnerPreflightBlocked:
        print("Private owner preflight denied; no database writes were attempted",
              file=sys.stderr)
    except Exception:
        # No connection string, database name, SQL exceptions or user data.
        print("Private owner preflight unavailable; no database writes were attempted",
              file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
