"""P1AA: read-only operational check BEFORE first owner MFA enrollment.

Run via an owner-authenticated Railway SSH connection *only after* the private
API was deliberately redeployed with the seven previously configured owner
variables (without applying the separately staged Google OAuth secret).

  railway ssh --project <approved-project> --environment development \
    --service personal-cfo-api-preview -- \
    env P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1 \
    python -m app.private_owner_runtime_preflight

Never mounts HTTP, runs migration/DDL, enables a role, creates identities,
looks at financial records, or emits sensitive SQL rows/DSNs/key material.
It verifies current private credentials/TLS and empty six-table custody before
the attended user-generated password/TOTP ceremony. This reports readiness
to attempt enrollment, NOT permission to deploy a public OAuth callback.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
import sys

from sqlalchemy import create_engine, text

from .private_owner_setup_cli import _operator_database_url
from .private_credential_role_policy import (
    PRIVATE_TABLES, attest_private_credential_role,
)

_KEY_NAMES = (
    "P1N_OWNER_ENCRYPTION_KEY",
    "P1N_OWNER_IDENTITY_HMAC_KEY",
    "P1N_OWNER_SESSION_HMAC_KEY",
    "P1P_OWNER_RECOVERY_ENCRYPTION_KEY",
    "P1P_OWNER_RECOVERY_HMAC_KEY",
)
_OTHER = ("P1Q_OPERATOR_PUBLIC_KEY", "P1W_OWNER_REF")
_TARGET = (
    "personal-cfo-dev-sandbox", "development", "personal-cfo-api-preview",
)
_OWNER = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class PrivateOwnerRuntimePreflightBlocked(ValueError):
    """The private, read-only first-enrollment preflight is not acceptable."""


def _read_key(value: str) -> bytes:
    try:
        raw = base64.b64decode(value, altchars=b"-_", validate=True)
        if len(raw) != 32:
            raise ValueError()
        return raw
    except (ValueError, binascii.Error, TypeError):
        raise PrivateOwnerRuntimePreflightBlocked("Private key inventory invalid") from None


def _inventory() -> dict:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("PERSONAL_CFO_PRIVATE_PREVIEW") != "enabled"
        or tuple(os.getenv(n) for n in (
            "RAILWAY_PROJECT_NAME", "RAILWAY_ENVIRONMENT_NAME", "RAILWAY_SERVICE_NAME",
        )) != _TARGET
        or os.getenv("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT") != "1"
    ):
        raise PrivateOwnerRuntimePreflightBlocked("Private operator preflight denied")
    keys = tuple(_read_key(os.getenv(n, "")) for n in _KEY_NAMES)
    if len(set(keys)) != len(keys):
        raise PrivateOwnerRuntimePreflightBlocked("Runtime key domains not independent")
    _read_key(os.getenv("P1Q_OPERATOR_PUBLIC_KEY", ""))
    if not _OWNER.fullmatch(os.getenv("P1W_OWNER_REF", "")):
        raise PrivateOwnerRuntimePreflightBlocked("Opaque single-owner reference invalid")
    return {
        "runtime_key_count": len(keys),
        "independent_runtime_key_domains": True,
        "offline_operator_public_key_available": True,
        "one_owner_reference_configured": True,
    }


def check_private_runtime(connection) -> dict:
    """Inspect exact role, TLS, six source tables, and empty custody rows."""
    if connection.dialect.name != "postgresql":
        raise PrivateOwnerRuntimePreflightBlocked("PostgreSQL-only")
    row = connection.execute(text(
        "SELECT current_database(), current_user, inet_client_addr() IS NOT NULL,"
        " (SELECT ssl FROM pg_catalog.pg_stat_ssl WHERE pid=pg_backend_pid()),"
        " current_setting('transaction_read_only')"
    )).one()
    if (
        len(row) != 5
        or row[0] != "personal_cfo_owner_auth"
        or row[1] != "personal_cfo_owner_credentials"
        or row[2] is not True
        or row[3] is not True
        or row[4] != "on"
    ):
        raise PrivateOwnerRuntimePreflightBlocked("Private TLS SQL authority not accepted")
    attest_private_credential_role(connection)

    # This initial-enrollment check never returns row data or even row counts.
    # Only perform a SELECT on six fixed security tables approved for this role.
    for name in sorted(PRIVATE_TABLES):
        result = connection.execute(text(
            f"SELECT EXISTS(SELECT 1 FROM public.{name} LIMIT 1)"
        )).scalar_one()
        if result is not False:
            raise PrivateOwnerRuntimePreflightBlocked(
                "Owner custody store is not empty; refuse first-run enrollment")
    return {
        "authenticated_tls_tcp_connection": True,
        "isolated_credential_database": True,
        "least_privilege_attestation_passed": True,
        "owner_security_tables_empty": True,
        "no_sql_writes_performed": True,
        "owner_enrolled_by_this_check": False,
        "google_consent_performed": False,
        "real_financial_data_enabled": False,
        "production_g2_accepted": False,
    }


def run_preflight() -> dict:
    # Check the local environment before constructing or connecting to a URL.
    inventory = _inventory()
    # The URL parser rejects an administrator, financial or non-TLS DSN.
    url = _operator_database_url()
    engine = create_engine(
        url, pool_pre_ping=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=3500",
        },
    )
    try:
        with engine.connect() as conn:
            return {**inventory, **check_private_runtime(conn)}
    finally:
        engine.dispose()


def main() -> int:
    try:
        print(json.dumps(run_preflight(), sort_keys=True, indent=2))
        return 0
    except Exception:
        # Never emit the PostgreSQL URL, private values, SQL queries, or
        # original exception, even when a backend driver exposes them.
        print("Private owner first-enrollment preflight unavailable or denied",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
