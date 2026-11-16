"""G1 A8: actual SQL savepoint/rollback on isolated synthetic restored clone.

This is NOT an authoritative financial cutover or table retirement: the
simulated read-authority pointer is a PostgreSQL TEMP table, not application
configuration. No persistent writes or live service changes are permitted.
Requires an authentic already-created encrypted snapshot and independently
verified restored/source-candidate parity. Even success reports G1 BLOCKED.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path

from .g1c_candidate import _guards
from .g1c_preflight import preflight_postgres_source
from .g1c_projection import inspect_restored_sealed_candidate
from .pg_recovery import MAX_FILE, _table_names


class SyntheticCutoverRehearsalBlocked(ValueError):
    """A8 clone-only rehearsal lacks authenticated recovery or safe rollback."""


def rehearse_synthetic_clone_switch(
    backup_file: str | Path, *, candidate_receipt: dict,
    inject_failure_at: str | None = None,
) -> dict:
    """Perform DB savepoint rehearsal on a dedicated disposable restore clone.

    `candidate_receipt` alone is never accepted as evidence: independently
    re-hash the protected backup bytes and re-verify every sealed source row
    against the original protected preflight before touching even a temp table.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("CI", "").lower() != "true"
        or os.getenv("G1_A8_EPHEMERAL_CI_ONLY") != "1"):
        raise SyntheticCutoverRehearsalBlocked(
            "Only explicit ephemeral synthetic CI restore-clone rehearsal allowed"
        )
    if inject_failure_at not in (None, "after_legacy", "after_switch", "before_rollback"):
        raise SyntheticCutoverRehearsalBlocked("Unknown rehearsal failure phase")
    if type(candidate_receipt) is not dict or not all(
        candidate_receipt.get(key) is True for key in (
            "synthetic_only", "independent_restore_verified",
            "full_source_row_parity_verified", "original_database_untouched",
            "candidate_on_restored_clone_only", "legacy_plaintext_still_present",
        )
    ) or candidate_receipt.get("active_ledger_cutover") is not False:
        raise SyntheticCutoverRehearsalBlocked("Missing authenticated source/backup receipt")
    path = Path(backup_file)
    if not path.is_file() or path.is_symlink() or not 33 <= path.stat().st_size <= MAX_FILE:
        raise SyntheticCutoverRehearsalBlocked("Missing or oversized encrypted backup")
    # Re-read the exact snapshot bytes, not a digest supplied by the caller.
    snapshot_hash = sha256(path.read_bytes()).hexdigest()
    if snapshot_hash != candidate_receipt.get("encrypted_snapshot_sha256"):
        raise SyntheticCutoverRehearsalBlocked("Encrypted backup changed after restore")
    try:
        source_dsn, target_dsn = _guards()
        from psycopg.conninfo import conninfo_to_dict
        target_name = conninfo_to_dict(target_dsn).get("dbname", "")
        if target_name != "synthetic_restore_candidate":
            raise SyntheticCutoverRehearsalBlocked("Unexpected non-disposable clone target")
        before = preflight_postgres_source()
        inspected = inspect_restored_sealed_candidate()
        if (before["source_graph_consistent"] is not True
            or before["source_integrity_hmac"] != candidate_receipt.get("legacy_source_hmac")
            or inspected["full_source_row_parity_verified"] is not True
            or inspected["original_source_integrity_hmac"] != candidate_receipt.get("legacy_source_hmac")
            or inspected["authenticated_mirror_count"] != candidate_receipt.get("sealed_source_rows")
            or inspected["active_ledger_cutover"] is not False
            or inspected["canonical_operational_store_ready"] is not False):
            raise SyntheticCutoverRehearsalBlocked("Independently verified source/clone parity missing")
        import psycopg
        with psycopg.connect(target_dsn, autocommit=True) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                conn.execute("SET LOCAL lock_timeout='3s'")
                _table_names(conn)
                # pg_temp state cannot become application authority. It is
                # physically inaccessible to other connections, and auto-drops.
                conn.execute(
                    "CREATE TEMP TABLE cfo_a8_rehearsal_state ("
                    "id integer PRIMARY KEY CHECK (id=1),"
                    "mode text NOT NULL CHECK (mode IN ('legacy','sealed_candidate'))"
                    ") ON COMMIT DROP"
                )
                conn.execute(
                    "INSERT INTO pg_temp.cfo_a8_rehearsal_state(id,mode) VALUES (1,'legacy')"
                )
                if inject_failure_at == "after_legacy":
                    raise SyntheticCutoverRehearsalBlocked("Injected A8 after legacy phase")
                conn.execute("SAVEPOINT cfo_a8_simulated_switch")
                conn.execute(
                    "UPDATE pg_temp.cfo_a8_rehearsal_state "
                    "SET mode='sealed_candidate' WHERE id=1 AND mode='legacy'"
                )
                if conn.execute(
                    "SELECT mode FROM pg_temp.cfo_a8_rehearsal_state WHERE id=1"
                ).fetchone() != ("sealed_candidate",):
                    raise SyntheticCutoverRehearsalBlocked("Temporary clone switch failed")
                if conn.execute(
                    "SELECT COUNT(*) FROM canonical_source_mirrors"
                ).fetchone()[0] != inspected["authenticated_mirror_count"]:
                    raise SyntheticCutoverRehearsalBlocked("Restored candidate drift during rehearsal")
                if inject_failure_at == "after_switch":
                    raise SyntheticCutoverRehearsalBlocked("Injected A8 after temporary switch")
                # This is a database ROLLBACK TO SAVEPOINT, not a Python flag.
                conn.execute("ROLLBACK TO SAVEPOINT cfo_a8_simulated_switch")
                if conn.execute(
                    "SELECT mode FROM pg_temp.cfo_a8_rehearsal_state WHERE id=1"
                ).fetchone() != ("legacy",):
                    raise SyntheticCutoverRehearsalBlocked("Temporary authority rollback failed")
                if inject_failure_at == "before_rollback":
                    raise SyntheticCutoverRehearsalBlocked("Injected A8 before final commit")
                conn.execute("RELEASE SAVEPOINT cfo_a8_simulated_switch")
            # After commit, the temp table was automatically dropped.
            if conn.execute(
                "SELECT to_regclass('pg_temp.cfo_a8_rehearsal_state')"
            ).fetchone()[0] is not None:
                raise SyntheticCutoverRehearsalBlocked("Temporary authority state survived commit")
        after = preflight_postgres_source()
        rechecked = inspect_restored_sealed_candidate()
        if (after["source_integrity_hmac"] != before["source_integrity_hmac"]
            or after["table_counts"] != before["table_counts"]
            or rechecked["authenticated_mirror_count"] != inspected["authenticated_mirror_count"]
            or rechecked["original_source_integrity_hmac"] != inspected["original_source_integrity_hmac"]):
            raise SyntheticCutoverRehearsalBlocked("Source or restored candidate changed during rehearsal")
    except SyntheticCutoverRehearsalBlocked:
        raise
    except Exception:
        raise SyntheticCutoverRehearsalBlocked("Clone rehearsal failed closed") from None

    return {
        "synthetic_only": True,
        "ephemeral_restore_clone_only": True,
        "encrypted_backup_bytes_rehashed": True,
        "independently_verified_source_mirror_parity": True,
        "sql_temp_pointer_switched": True,
        "sql_savepoint_rollback_verified": True,
        "temporary_pointer_dropped_on_commit": True,
        "original_source_untouched": True,
        "restored_candidate_rows_untouched": True,
        "active_application_financial_authority_switched": False,
        "legacy_plaintext_retired": False,
        "real_data_authorized": False,
        "g1_release_accepted": False,
    }
