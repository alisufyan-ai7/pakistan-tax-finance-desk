"""A5a: authenticate a sealed PostgreSQL candidate and project its SOURCE facts.

READ-ONLY and synthetic-only. New code never queries plaintext legacy finance
tables on the RESTORED candidate, nor starts a live authoritative bank ledger.
Full source census is independently compared with the original source via the
existing source preflight. No raw source financial data appears in the receipt.
"""
from __future__ import annotations

from datetime import date, datetime
import json
import os

from sqlalchemy import Date, DateTime

from .db import Base
from . import models  # noqa: F401
from .g1c_preflight import (
    SOURCE_COLUMNS, MAX_ROWS, G1CPreflightBlocked,
    _tag, _verified_envelopes, analyze_source_rows, preflight_postgres_source,
)
from .ledger_crypto import unseal
from .pg_recovery import _connection_config, _table_names


class SealedProjectionBlocked(ValueError):
    """Encrypted candidate cannot be authenticated against original source."""


def _cast_value(table: str, column: str, val):
    if val is None:
        return None
    type_ = Base.metadata.tables[table].columns[column].type
    if isinstance(type_, DateTime):
        if not isinstance(val, str):
            raise SealedProjectionBlocked("Invalid candidate datetime")
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            raise SealedProjectionBlocked("Invalid candidate datetime") from None
    if isinstance(type_, Date):
        if not isinstance(val, str):
            raise SealedProjectionBlocked("Invalid candidate date")
        try:
            return date.fromisoformat(val)
        except ValueError:
            raise SealedProjectionBlocked("Invalid candidate date") from None
    return val


def verify_sealed_candidate_rows(
    encrypted_mirrors: list[tuple[str, str]], expected_receipt: dict,
) -> dict:
    """Authenticate/decode every sealed row then recompute complete-source HMAC.

    DATE and TIMESTAMP fields have typed reconstruction because the source
    candidate mirror uses exact JSON textual serialisation for PG types.
    Rejects surplus/unexpected/missing rows, content tampering, replay identity
    conflict and source/owner/account/year-parity deviation.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise SealedProjectionBlocked("Real canonical projections prohibited")
    if not isinstance(encrypted_mirrors, list) or not encrypted_mirrors or len(encrypted_mirrors) > MAX_ROWS:
        raise SealedProjectionBlocked("Empty/oversized sealed candidate, refusing partial projection")
    if not isinstance(expected_receipt, dict) or expected_receipt.get("migration_performed") is not False:
        raise SealedProjectionBlocked("Missing independent original-source preflight receipt")
    expected_tables = set(SOURCE_COLUMNS) - {"canonical_source_mirrors"}
    rows = {table: [] for table in SOURCE_COLUMNS}
    seen = set()
    for index, token in encrypted_mirrors:
        if not isinstance(index, str) or len(index) != 64 or index in seen:
            raise SealedProjectionBlocked("Duplicate/malformed candidate source identity")
        seen.add(index)
        try:
            decoded = json.loads(unseal(token, "canonical_source_mirrors.payload_json"))
        except Exception:
            raise SealedProjectionBlocked("Sealed candidate authentication failed") from None
        if not isinstance(decoded, dict) or set(decoded) != {"table", "source_row"}:
            raise SealedProjectionBlocked("Unknown sealed candidate record shape")
        table, raw = decoded["table"], decoded["source_row"]
        if table not in expected_tables or not isinstance(raw, dict) or set(raw) != set(SOURCE_COLUMNS[table]):
            raise SealedProjectionBlocked("Unknown canonical source table or columns")
        pk = [col.name for col in Base.metadata.tables[table].primary_key.columns]
        if _tag(b"candidate-source-key", [table, [raw[c] for c in pk]]) != index:
            raise SealedProjectionBlocked("Encrypted candidate source HMAC mismatch")
        rows[table].append({key: _cast_value(table, key, value) for key,value in raw.items()})
    try:
        _verified_envelopes(rows)
        report = analyze_source_rows(rows)
    except Exception:
        raise SealedProjectionBlocked("Reconstructed candidate source graph invalid") from None
    if (not report["source_graph_consistent"] or
        report["source_integrity_hmac"] != expected_receipt.get("source_integrity_hmac") or
        report["year_owner_account_direction_hmac"] !=
        expected_receipt.get("year_owner_account_direction_hmac") or
        any(report["table_counts"][name] != expected_receipt.get("table_counts",{}).get(name)
            for name in SOURCE_COLUMNS) or
        len(seen) != sum(report["table_counts"][name] for name in expected_tables)):
        raise SealedProjectionBlocked("Full candidate source/account/year parity failed")
    return {
        "synthetic_only": True, "read_only": True,
        "authenticated_mirror_count": len(seen),
        "original_source_integrity_hmac": report["source_integrity_hmac"],
        "year_owner_account_direction_hmac": report["year_owner_account_direction_hmac"],
        "full_source_row_parity_verified": True,
        "source_table_count": len(expected_tables),
        "active_ledger_cutover": False,
        "canonical_operational_store_ready": False,
        "legacy_plaintext_still_present": True,
        "fbr_ready": False, "tax_due_minor": None,
    }


def inspect_restored_sealed_candidate() -> dict:
    """Read only sealed rows in restored synthetic PG18 clone, not plaintext SQL.

    Original source independently inspected with READ ONLY PG preflight. This
    inspection makes NO original/candidate writes and is NOT an API endpoint.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise SealedProjectionBlocked("Real canonical projections prohibited")
    expected = preflight_postgres_source()
    if not expected["source_graph_consistent"]:
        raise SealedProjectionBlocked("Original source graph has blocking anomalies")
    dsn, _ = _connection_config("PG_SNAPSHOT_RESTORE_DSN", restore=True)
    try:
        import psycopg
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                _table_names(conn)
                count = conn.execute("SELECT COUNT(*) FROM canonical_source_mirrors").fetchone()[0]
                if count > MAX_ROWS:
                    raise SealedProjectionBlocked("Candidate source row count exceeds limit")
                mirrors = conn.execute(
                    "SELECT source_hmac, payload_json FROM canonical_source_mirrors "
                    "ORDER BY source_hmac"
                ).fetchall()
                result = verify_sealed_candidate_rows(mirrors, expected)
        after = preflight_postgres_source()
        if (after["source_integrity_hmac"] != expected["source_integrity_hmac"] or
            after["table_counts"] != expected["table_counts"]):
            raise SealedProjectionBlocked("Original source changed while inspecting sealed clone")
        return result
    except SealedProjectionBlocked:
        raise
    except Exception:
        raise SealedProjectionBlocked("Verified sealed candidate inspection failed closed") from None
