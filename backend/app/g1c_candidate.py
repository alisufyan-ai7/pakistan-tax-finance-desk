"""G1-c synthetic PostgreSQL backup-first *sealed candidate*, not live cutover.

Explicitly invoked offline. Verifies original source, creates encrypted full-DB
backup, independently restores into pre-migrated EMPTY synthetic_restore_*
database, proves source equality, then seals every physical source row (including
review flags, tax filing revisions and loan/cash/asset links) into a separate,
non-authoritative canonical_source_mirrors table on the RESTORED clone.

No legacy source table is rewritten, no real data or production DSN is accepted.
Cannot be invoked by app GET/startup and has no live finance read/write switch.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import uuid

from .db import Base
from . import models  # noqa: F401
from .g1c_preflight import (
    G1CPreflightBlocked, SOURCE_COLUMNS, MAX_ROWS, _canonical, _tag,
    analyze_source_rows, preflight_postgres_source,
)
from .ledger_crypto import keyring, seal, unseal
from .pg_recovery import (
    _guard, _connection_config, create_pg_snapshot, restore_pg_snapshot,
)
from .private_events import _index_key


class G1CCandidateBlocked(ValueError):
    """No verified immutable/recoverable synthetic candidate can be produced."""


def _guards() -> tuple[str, str]:
    """Check all requirements before writing a backup or touching candidate."""
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise G1CCandidateBlocked("No real-source canonical migration permitted")
    backup_key = _guard()
    hmac_key = _index_key()
    _, ledger_keys = keyring()
    if hmac_key == backup_key or hmac_key in ledger_keys.values():
        raise G1CCandidateBlocked("HMAC, AES and backup keys must be independent")
    source, src_name = _connection_config("PG_G1C_SOURCE_DSN", restore=False)
    snapshot, snap_name = _connection_config("PG_SNAPSHOT_SOURCE_DSN", restore=False)
    target, tgt_name = _connection_config("PG_SNAPSHOT_RESTORE_DSN", restore=True)
    if source != snapshot or src_name != snap_name or src_name == tgt_name:
        raise G1CCandidateBlocked("Encrypted backup must originate from exact preflight source")
    if target == source:
        raise G1CCandidateBlocked("Original database cannot be the candidate target")
    return source, target


def _non_mirror_tables() -> list[str]:
    expected = set(SOURCE_COLUMNS)
    if expected != set(Base.metadata.tables) or "canonical_source_mirrors" not in expected:
        raise G1CCandidateBlocked("Unknown source or mirror table inventory")
    # Full restored-clone parity includes opaque ciphertext from the
    # synthetic-only cloud vault. These are NOT financial authority/claims.
    return sorted(expected - {"canonical_source_mirrors"})


def _copy_all_as_sealed_candidate(dsn: str, expected_receipt: dict,
                                   *, inject_failure_after_rows: int | None = None) -> dict:
    """Transactional clone-only mirror write and full authenticated parity check."""
    import psycopg
    from psycopg import sql

    tables = _non_mirror_tables()
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.transaction():
                # Serializable snapshot and explicit locks prevent a concurrent
                # synthetic writer from silently changing an evidence row midcopy.
                conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                conn.execute("SET LOCAL lock_timeout = '4s'")
                conn.execute("SET TIME ZONE 'UTC'")
                rows: dict[str, list[dict]] = {}
                total = 0
                for table in sorted(SOURCE_COLUMNS):
                    conn.execute(sql.SQL("LOCK TABLE {} IN SHARE MODE").format(
                        sql.Identifier("public", table)))
                for table in sorted(SOURCE_COLUMNS):
                    count = conn.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                        sql.Identifier("public", table))).fetchone()[0]
                    total += count
                    if total > MAX_ROWS:
                        raise G1CCandidateBlocked("Source scan limit exceeded, refusing incomplete copy")
                    cols = SOURCE_COLUMNS[table]
                    primary = [c.name for c in Base.metadata.tables[table].primary_key.columns]
                    query = sql.SQL("SELECT {} FROM {} ORDER BY {}").format(
                        sql.SQL(",").join(sql.Identifier(c) for c in cols),
                        sql.Identifier("public", table),
                        sql.SQL(",").join(sql.Identifier(c) for c in primary),
                    )
                    with conn.cursor() as cur:
                        cur.execute(query)
                        rows[table] = [dict(zip(cols, item)) for item in cur.fetchall()]
                if rows["canonical_source_mirrors"]:
                    raise G1CCandidateBlocked("Candidate already contains sealed rows")
                restored_report = analyze_source_rows(rows)
                if (not restored_report["source_graph_consistent"] or
                    restored_report["source_integrity_hmac"] != expected_receipt["source_integrity_hmac"] or
                    restored_report["year_owner_account_direction_hmac"] !=
                    expected_receipt["year_owner_account_direction_hmac"] or
                    restored_report["table_counts"] != expected_receipt["table_counts"]):
                    raise G1CCandidateBlocked("Restored clone source census changed before copy")
                if not sum(len(rows[t]) for t in tables):
                    raise G1CCandidateBlocked("Empty synthetic source graph not a candidate")
                expected: dict[str, dict] = {}
                created = 0
                for table in tables:
                    pk = [c.name for c in Base.metadata.tables[table].primary_key.columns]
                    for row in rows[table]:
                        identity = [table, [row[c] for c in pk]]
                        fingerprint = _tag(b"candidate-source-key", identity)
                        if fingerprint in expected:
                            raise G1CCandidateBlocked("Duplicate keyed source identity")
                        payload = {"table": table, "source_row": row}
                        encoded = _canonical(payload).decode("ascii")
                        expected[fingerprint] = json.loads(encoded)
                        conn.execute(
                            "INSERT INTO canonical_source_mirrors "
                            "(id,source_hmac,payload_json,created_at) "
                            "VALUES (%s,%s,%s,CURRENT_TIMESTAMP)",
                            (str(uuid.uuid4()), fingerprint,
                             seal(encoded, "canonical_source_mirrors.payload_json")),
                        )
                        created += 1
                        if inject_failure_after_rows is not None and created >= inject_failure_after_rows:
                            raise G1CCandidateBlocked("Injected candidate rollback before commit")
                # Authenticate/decrypt fresh SQL rows and prove EVERY field value
                # round-trips; any surplus/duplicate/omitted row blocks commit.
                found: dict[str, dict] = {}
                for h, ciphertext in conn.execute(
                    "SELECT source_hmac, payload_json FROM canonical_source_mirrors"
                ).fetchall():
                    try:
                        decoded = json.loads(unseal(ciphertext, "canonical_source_mirrors.payload_json"))
                    except Exception:
                        raise G1CCandidateBlocked("Candidate AES-GCM authentication failed") from None
                    if h in found or h not in expected or decoded != expected[h]:
                        raise G1CCandidateBlocked("Candidate full source row parity failed")
                    found[h] = decoded
                if len(found) != len(expected) or set(found) != set(expected):
                    raise G1CCandidateBlocked("Candidate missing source records")
        return {
            "sealed_source_rows": created,
            "table_count": len(tables),
            "full_source_row_parity_verified": True,
            "transactional_candidate_write": True,
            "ciphertext_only_candidate_payloads": True,
        }
    except G1CCandidateBlocked:
        raise
    except Exception:
        raise G1CCandidateBlocked("Candidate copy failed closed with transactional rollback") from None


def create_verified_sealed_candidate(backup_file: str | Path,
                                     *, inject_failure_after_rows: int | None = None) -> dict:
    """Run full synthetic source -> encrypted backup -> verified restore -> mirror.

    The caller prepares an *EMPTY already-Alembic-migrated* independent restore
    database and a NEW backup file path. On failures, original source is never
    written; backup and restored evidence are preserved for separate diagnosis.
    """
    source, target = _guards()
    first = preflight_postgres_source()
    if not first["source_graph_consistent"]:
        raise G1CCandidateBlocked("Legacy graph contains blocking source anomalies")
    if first["table_counts"]["canonical_source_mirrors"]:
        raise G1CCandidateBlocked("Original database already contains a prior candidate mirror")
    backup = create_pg_snapshot(backup_file)
    if not backup["encrypted"] or not backup["verified_read_snapshot"]:
        raise G1CCandidateBlocked("Encrypted source backup could not be verified")
    second = preflight_postgres_source()
    if (first["source_integrity_hmac"] != second["source_integrity_hmac"] or
        first["table_counts"] != second["table_counts"]):
        raise G1CCandidateBlocked("Source changed during encrypted backup, original left untouched")
    restore = restore_pg_snapshot(backup_file)
    if not restore["full_row_parity_verified"] or not restore["independent_target"]:
        raise G1CCandidateBlocked("Independent restored backup full-row verification failed")
    restored = preflight_postgres_source(restored_candidate=True)
    if (not restored["source_graph_consistent"] or
        first["source_integrity_hmac"] != restored["source_integrity_hmac"] or
        first["year_owner_account_direction_hmac"] != restored["year_owner_account_direction_hmac"]):
        raise G1CCandidateBlocked("Independent restored source does not match original")
    result = _copy_all_as_sealed_candidate(
        target, first, inject_failure_after_rows=inject_failure_after_rows
    )
    final = preflight_postgres_source()  # proof original remains unchanged
    if final["source_integrity_hmac"] != first["source_integrity_hmac"]:
        raise G1CCandidateBlocked("Original source changed during candidate construction")
    return {
        "synthetic_only": True,
        "encrypted_snapshot_sha256": backup["ciphertext_sha256"],
        "independent_restore_verified": True,
        "legacy_source_hmac": first["source_integrity_hmac"],
        "year_owner_account_direction_hmac": first["year_owner_account_direction_hmac"],
        "original_database_untouched": True,
        "candidate_on_restored_clone_only": True,
        "active_ledger_cutover": False,
        "legacy_plaintext_still_present": True,
        "complete_g1": False,
        "real_data_authorized": False,
        "fbr_ready": False,
        **result,
    }
