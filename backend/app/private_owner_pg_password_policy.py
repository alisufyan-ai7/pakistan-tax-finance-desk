"""P1AE: prove private Postgres rejects a deliberately wrong password.

Runs only via owner-authenticated Railway SSH in synthetic private API.
Unlike psql -W, which unconditionally asks for a password, this proves the
server actually enforces password authentication from the API's network.

No HTTP endpoint, migrations, credential mutation, escrow read, MFA enrollment,
Google consent or real finance. Never print database URL/password/error.
"""
from __future__ import annotations

import hmac
import json
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from .private_owner_runtime_preflight import _inventory
from .private_owner_setup_cli import _operator_database_url

# A fixed publicly known invalid password, not a second user credential.
_INVALID_PASSWORD = "P1AE_invalid_password_probe_never_a_real_secret_2026"
_OPTIONS = "-c default_transaction_read_only=on -c statement_timeout=3500"


def _report(stage: str) -> dict:
    allowed = {
        "private_operator_scope",
        "restricted_database_url_policy",
        "positive_tls_owner_connection",
        "wrong_password_accepted",
        "wrong_password_rejection_unproven",
        "complete",
    }
    if stage not in allowed:
        stage = "wrong_password_rejection_unproven"
    return {
        "contract": "personal_cfo_owner_postgres_password_policy_v1",
        "result": "PASS" if stage == "complete" else "BLOCKED",
        "stage": stage,
        "same_private_tcp_host_checked": stage == "complete",
        "server_rejects_intentionally_wrong_password": stage == "complete",
        "read_only": True,
        "database_modified": False,
        "credentials_or_error_details_included": False,
        "owner_enrolled": False,
        "google_consent_activated": False,
        "real_financial_mode_activated": False,
    }


def _read_only_engine(url):
    return create_engine(
        url, poolclass=NullPool,
        connect_args={"connect_timeout": 5, "options": _OPTIONS},
    )


def _auth_failure(error: Exception) -> bool:
    """Accept only an explicit rejected-password response, never timeout/DNS."""
    orig = getattr(error, "orig", error)
    state = getattr(orig, "sqlstate", None)
    if state == "28P01":
        return True
    if state is not None:
        return False
    # psycopg/libpq may report the TLS authentication handshake as an
    # OperationalError without SQLSTATE. Only this exact symptom qualifies.
    message = str(orig).lower()
    return "password authentication failed for user" in message


def prove_private_postgres_password_enforcement() -> dict:
    try:
        _inventory()
    except Exception:
        return _report("private_operator_scope")
    try:
        valid_url = make_url(_operator_database_url())
        true_password = valid_url.password
        if (not true_password or hmac.compare_digest(
            true_password, _INVALID_PASSWORD)):
            raise ValueError()
    except Exception:
        return _report("restricted_database_url_policy")

    valid = None
    try:
        valid = _read_only_engine(valid_url)
        with valid.connect() as connection:
            identity = connection.execute(text(
                "SELECT current_database(), current_user, "
                "inet_client_addr() IS NOT NULL, "
                "(SELECT ssl FROM pg_catalog.pg_stat_ssl "
                " WHERE pid = pg_backend_pid()), "
                "current_setting('transaction_read_only')"
            )).one()
            if identity != (
                "personal_cfo_owner_auth", "personal_cfo_owner_credentials",
                True, True, "on",
            ):
                return _report("positive_tls_owner_connection")
    except Exception:
        return _report("positive_tls_owner_connection")
    finally:
        if valid is not None:
            valid.dispose()

    wrong = None
    try:
        # New engine/physical connection: cannot reuse the valid login.
        wrong_url = valid_url.set(password=_INVALID_PASSWORD)
        wrong = _read_only_engine(wrong_url)
        with wrong.connect() as connection:
            # If even a deliberate wrong password reaches SQL, fail CLOSED.
            connection.execute(text("SELECT 1"))
        return _report("wrong_password_accepted")
    except Exception as exc:
        if _auth_failure(exc):
            return _report("complete")
        return _report("wrong_password_rejection_unproven")
    finally:
        if wrong is not None:
            wrong.dispose()


def main() -> int:
    try:
        report = prove_private_postgres_password_enforcement()
    except Exception:
        report = _report("wrong_password_rejection_unproven")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
