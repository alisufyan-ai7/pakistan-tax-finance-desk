"""P1AB — bounded, no-secret diagnostic of owner MFA preflight.

The existing P1AA preflight fails closed but reports only a generic error.
This CLI identifies WHICH read-only guard denied enrollment, without dumping
credentials, database exceptions, owners, table contents or private variables.

Use only through authenticated Railway SSH to the existing private synthetic
API with a one-off P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1 environment switch.
This is NOT a G2 bypass, migration, owner enrollment or Google connection.
"""
from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine, text

from .private_owner_runtime_preflight import (
    _KEY_NAMES, _OWNER, _TARGET, _inventory, _read_key,
)
from .private_owner_setup_cli import _operator_database_url
from .private_credential_role_policy import (
    PRIVATE_TABLES, attest_private_credential_role,
)


def _result(stage: str, ok: bool) -> dict:
    return {
        "contract": "personal_cfo_private_owner_preflight_diagnostic_v1",
        "result": "PASS" if ok else "BLOCKED",
        "stage": stage,
        "read_only": True,
        "credential_values_included": False,
        "sql_rows_included": False,
        "owner_enrolled": False,
        "google_consent_activated": False,
    }


def _environment_guard() -> None:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("PERSONAL_CFO_PRIVATE_PREVIEW") != "enabled"
        or tuple(os.getenv(k) for k in (
            "RAILWAY_PROJECT_NAME", "RAILWAY_ENVIRONMENT_NAME",
            "RAILWAY_SERVICE_NAME",
        )) != _TARGET
        or os.getenv("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT") != "1"
    ):
        raise ValueError("operator scope")

def _key_guard() -> None:
    keys = tuple(_read_key(os.getenv(k, "")) for k in _KEY_NAMES)
    if len(set(keys)) != len(keys):
        raise ValueError("independent key domains required")
    _read_key(os.getenv("P1Q_OPERATOR_PUBLIC_KEY", ""))
    if _OWNER.fullmatch(os.getenv("P1W_OWNER_REF", "")) is None:
        raise ValueError("invalid owner ref")


def diagnose() -> dict:
    """Never return raw exception text, DSN details or sensitive row content."""
    try:
        _environment_guard()
    except Exception:
        return _result("environment_scope", False)
    try:
        _key_guard()
        # Re-check the original implementation too; do not diverge.
        _inventory()
    except Exception:
        return _result("key_inventory", False)
    try:
        url = _operator_database_url()
    except Exception:
        return _result("isolated_database_url_policy", False)

    engine = None
    try:
        engine = create_engine(
            url, pool_pre_ping=True,
            connect_args={
                "connect_timeout": 5,
                "options":
                    "-c default_transaction_read_only=on -c statement_timeout=3500",
            },
        )
        with engine.connect() as connection:
            try:
                if connection.dialect.name != "postgresql":
                    raise ValueError()
                connection.execute(text("SET TRANSACTION READ ONLY"))
                authority = connection.execute(text(
                    "SELECT current_database(), current_user,"
                    " inet_client_addr() IS NOT NULL,"
                    " (SELECT ssl FROM pg_catalog.pg_stat_ssl"
                    " WHERE pid=pg_backend_pid()),"
                    " current_setting('transaction_read_only')"
                )).one()
                if (
                    len(authority) != 5
                    or authority[0] != "personal_cfo_owner_auth"
                    or authority[1] != "personal_cfo_owner_credentials"
                    or authority[2] is not True
                    or authority[3] is not True
                    or authority[4] != "on"
                ):
                    raise ValueError()
            except Exception:
                return _result("tls_identity_readonly", False)
            try:
                attest_private_credential_role(connection)
            except Exception:
                return _result("effective_role_permissions", False)
            try:
                for table in sorted(PRIVATE_TABLES):
                    exists = connection.execute(text(
                        f"SELECT EXISTS(SELECT 1 FROM public.{table} LIMIT 1)"
                    )).scalar_one()
                    if exists is not False:
                        raise ValueError()
            except Exception:
                return _result("owner_tables_not_empty_or_inaccessible", False)
    except Exception:
        return _result("database_connection", False)
    finally:
        if engine is not None:
            engine.dispose()

    return _result("complete", True)


def main() -> int:
    # A result code is *not* approval to bypass the original P1AA check.
    try:
        outcome = diagnose()
    except Exception:
        outcome = _result("unexpected_failure", False)
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
