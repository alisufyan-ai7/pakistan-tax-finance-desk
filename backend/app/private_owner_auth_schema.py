"""P1Y: isolated six-table owner-identity schema in existing PostgreSQL cluster.

Does NOT run during app startup, migration upgrade, Railway deployments, or
CI against a live database. Generates a reviewable SQL file containing no
secret. An authenticated database administrator applies it manually to an
EMPTY, separately named database inside the existing Railway Postgres service.

This avoids creating all 36 financial tables or faking Alembic version 0022
in the current synthetic preview database. The owner's dedicated schema has
an independent, administrator-only version receipt, inaccessible to the
runtime owner-credential role. Future revisions require their own migration.
"""
from __future__ import annotations

from hashlib import sha256
import json

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex

from .db import Base
from . import models  # noqa: F401 register six private models

OWNER_AUTH_DB = "personal_cfo_owner_auth"
OWNER_AUTH_SCHEMA_REV = "p1y_owner_auth_v1"
OWNER_AUTH_TABLES = tuple(sorted({
    "owner_google_metadata_grants",
    "owner_private_identities",
    "owner_private_sessions",
    "owner_private_recovery_states",
    "owner_private_recovery_audit",
    "owner_private_oauth_attempts",
}))


def _tables():
    if len(OWNER_AUTH_TABLES) != 6 or not set(OWNER_AUTH_TABLES) <= set(Base.metadata.tables):
        raise RuntimeError("Private owner schema inventory has changed")
    return [Base.metadata.tables[name] for name in OWNER_AUTH_TABLES]


def schema_signature() -> str:
    """Deterministic source-based review signature, not a live DB attestation."""
    schema = []
    for table in _tables():
        schema.append({
            "table": table.name,
            "columns": [(c.name, str(c.type), c.primary_key, c.nullable)
                        for c in table.columns],
            "checks": sorted(str(c.sqltext) for c in table.constraints
                             if c.__class__.__name__ == "CheckConstraint"),
            "indexes": sorted((idx.name, tuple(c.name for c in idx.columns))
                              for idx in table.indexes),
        })
    return sha256(json.dumps(schema, sort_keys=True).encode("utf-8")).hexdigest()


def review_only_sql() -> str:
    """Emit PostgreSQL18 DDL with a database name and empty-schema guard.

    No SQL is executed and no connection, password, environment key, or
    financial data is consulted. The output is operator-reviewed before use.
    """
    dialect = postgresql.dialect()
    lines = [
        "-- P1Y OWNER AUTH DDL REVIEW CANDIDATE ONLY; DO NOT AUTO-DEPLOY.",
        "-- Admin only, separately created personal_cfo_owner_auth database.",
        "-- This SQL is intentionally non-idempotent and fails on an existing table.",
        "BEGIN;",
        "SET LOCAL lock_timeout = '5s';",
        "SET LOCAL statement_timeout = '30s';",
        r"""DO $owner_auth_guard$
BEGIN
    IF current_database() <> 'personal_cfo_owner_auth' THEN
        RAISE EXCEPTION 'Owner schema target database mismatch';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r','p','v','m','f','S')
    ) THEN
        RAISE EXCEPTION 'Owner schema target is not empty';
    END IF;
END
$owner_auth_guard$;""",
    ]
    for table in _tables():
        lines.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        for index in sorted(table.indexes, key=lambda x: x.name):
            lines.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    lines.extend([
        "CREATE TABLE public.owner_auth_schema_version ("
        " singleton_id INTEGER PRIMARY KEY CHECK (singleton_id=1),"
        " revision VARCHAR(48) NOT NULL,"
        " model_signature VARCHAR(64) NOT NULL);",
        ("INSERT INTO public.owner_auth_schema_version "
         "(singleton_id, revision, model_signature) VALUES "
         f"(1, '{OWNER_AUTH_SCHEMA_REV}', '{schema_signature()}');"),
        "COMMIT;",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    print(review_only_sql())
