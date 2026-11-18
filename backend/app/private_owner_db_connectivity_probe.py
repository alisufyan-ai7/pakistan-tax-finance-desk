"""P1AC — isolated, read-only diagnosis for owner DB connection failures.

P1AB established that owner key inventory and the restricted DSN shape pass,
but PostgreSQL connection fails. This one-off private Railway SSH CLI checks:
driver -> private DNS -> TCP -> TLS-required PostgreSQL login/SELECT 1.
It never prints credentials, hostnames, database error messages or SQL rows.

Must never be mounted into FastAPI, run on startup, or used for public OAuth.
"""
from __future__ import annotations

import json
import os
import socket
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from .private_owner_runtime_preflight import _inventory
from .private_owner_setup_cli import _operator_database_url


_ALLOWED = frozenset({
    "runtime_scope_or_keys",
    "restricted_dsn_policy",
    "database_driver",
    "private_dns_resolution",
    "private_tcp_connectivity",
    "postgres_password_rejected",
    "postgres_auth_policy",
    "postgres_database_or_role_missing",
    "postgres_tls_connection",
    "postgres_connection_other",
    "complete",
})


def _report(stage: str) -> dict:
    if stage not in _ALLOWED:
        stage = "postgres_connection_other"
    return {
        "contract": "personal_cfo_owner_connectivity_probe_v1",
        "stage": stage,
        "result": "PASS" if stage == "complete" else "BLOCKED",
        "read_only": True,
        "sensitive_values_included": False,
        "owner_enrolled": False,
        "google_consent_activated": False,
        "database_modified": False,
    }


def _classify_pg_failure(error: Exception) -> str:
    """Only fixed classifications. Never return exception text/SQLSTATE."""
    orig = getattr(error, "orig", error)
    state = getattr(orig, "sqlstate", None)
    if state == "28P01":
        return "postgres_password_rejected"
    if state in ("28000", "42501"):
        return "postgres_auth_policy"
    if state in ("3D000", "42704"):
        return "postgres_database_or_role_missing"
    # libpq often raises OperationalError without a structured SQLSTATE.
    # Inspect the message only in-memory; never log or emit it.
    message = str(orig).lower()
    if "password authentication failed" in message:
        return "postgres_password_rejected"
    if "no pg_hba.conf entry" in message or "authentication rejected" in message:
        return "postgres_auth_policy"
    if "does not exist" in message and ("database" in message or "role" in message):
        return "postgres_database_or_role_missing"
    if any(needle in message for needle in (
        "ssl error", "ssl syscall", "server does not support ssl",
        "tls handshake", "certificate verify failed", "ssl is required",
    )):
        return "postgres_tls_connection"
    return "postgres_connection_other"


def probe() -> dict:
    """No DDL, migration, real-owner row reads, token exchange, or writes."""
    try:
        _inventory()
    except Exception:
        return _report("runtime_scope_or_keys")
    try:
        raw = _operator_database_url()
        url = make_url(raw)
    except Exception:
        return _report("restricted_dsn_policy")
    if (url.host is None or not url.host.endswith(".railway.internal")
        or url.port not in (None, 5432)
        or url.database != "personal_cfo_owner_auth"
        or url.username != "personal_cfo_owner_credentials"):
        return _report("restricted_dsn_policy")
    try:
        import psycopg  # noqa: F401 - ensure binary driver is installed
    except ImportError:
        return _report("database_driver")
    try:
        socket.getaddrinfo(url.host, url.port or 5432,
                           type=socket.SOCK_STREAM)
    except (OSError, ValueError):
        return _report("private_dns_resolution")
    try:
        with socket.create_connection(
            (url.host, url.port or 5432), timeout=4
        ):
            pass
    except (OSError, ValueError):
        return _report("private_tcp_connectivity")

    engine = None
    try:
        engine = create_engine(
            raw,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 5,
                "options": "-c default_transaction_read_only=on -c statement_timeout=3500",
            },
        )
        with engine.connect() as conn:
            # No owner/financial records, only a connection smoke check.
            if conn.scalar(text("SELECT 1")) != 1:
                return _report("postgres_connection_other")
    except (ImportError, ModuleNotFoundError):
        return _report("database_driver")
    except Exception as exc:
        return _report(_classify_pg_failure(exc))
    finally:
        if engine is not None:
            engine.dispose()
    return _report("complete")


def main() -> int:
    try:
        result = probe()
    except Exception:
        result = _report("postgres_connection_other")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
