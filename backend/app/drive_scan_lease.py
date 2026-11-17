"""P1J: fake-only transactional scan leases and last-good HMAC receipt.

No cron, Drive HTTP, real Google identity, original bytes, credential vault
or real-data mode. Caller runs an approved fictional complete-page scan;
a success heartbeat is accepted ONLY with an integrity-checked committed
DriveInboxCheckpoint receipt, including an idempotent complete replay.
"""
from __future__ import annotations

import hmac
import os
import secrets
import re
from time import time

from sqlalchemy import select,text
from sqlalchemy.orm import Session

from .drive_inbox_planner import DriveInboxBlocked, DRIVE_ID, _index
from .drive_inbox_store import _load
from .models import DriveScanLease

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{40,128}$")


def _now(value: int | None) -> int:
    epoch = int(time()) if value is None else value
    if type(epoch) is not int or not 1_500_000_000 <= epoch <= 4_000_000_000:
        raise DriveInboxBlocked("Invalid synthetic scan clock")
    return epoch


def _guard(db: Session, folder_id: str) -> str:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("DRIVE_FAKE_TRANSPORT_ONLY") != "1"
        or os.getenv("P1J_FAKE_SCAN_LEASE_ONLY") != "1"
        or type(folder_id) is not str or DRIVE_ID.fullmatch(folder_id) is None
        or db.bind is None or db.bind.dialect.name not in {"sqlite", "postgresql"}
        or (db.bind.dialect.name == "sqlite"
            and os.getenv("P1J_SQLITE_TEST_ONLY") != "1")):
        raise DriveInboxBlocked("Unapproved synthetic Drive lease")
    folder_hmac = _index("folder", folder_id)
    allowed = os.getenv("DRIVE_ALLOWED_FOLDER_HMAC", "")
    if (_HEX64.fullmatch(allowed) is None
        or not hmac.compare_digest(folder_hmac, allowed)):
        raise DriveInboxBlocked("Unapproved synthetic Drive lease folder")
    return folder_hmac


def _lock(db: Session, folder_hmac: str) -> None:
    if db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:tag))"),
                   {"tag": folder_hmac})


def _row(db: Session, folder_hmac: str) -> DriveScanLease | None:
    return db.scalar(select(DriveScanLease).where(
        DriveScanLease.folder_hmac == folder_hmac
    ).with_for_update())


def acquire_fake_scan_lease(db: Session, *, folder_id: str,
                            now_epoch: int | None = None,
                            ttl_seconds: int = 300) -> str:
    """Lease is ONE worker at a time, even if the row did not yet exist.

    Return the random secret ONLY to the private synthetic test runner;
    SQL-visible value is an HMAC. No public API ever uses this module.
    """
    folder = _guard(db, folder_id)
    now = _now(now_epoch)
    if type(ttl_seconds) is not int or not 15 <= ttl_seconds <= 900:
        raise DriveInboxBlocked("Unapproved scan lease duration")
    try:
        _lock(db, folder)
        row = _row(db, folder)
        if row is None:
            row = DriveScanLease(
                folder_hmac=folder, lease_hmac=None, lease_expires_epoch=0,
                last_success_epoch=None, last_source_hmac=None,
                last_receipt_hmac=None,
                last_scan_number=0, last_attempt_epoch=None,
                last_outcome="never", failure_count=0, permission_revoked=False,
            )
            db.add(row)
            db.flush()
        if (row.permission_revoked
            or (row.lease_hmac is not None and row.lease_expires_epoch > now)
            or (row.last_attempt_epoch is not None and now < row.last_attempt_epoch)):
            db.rollback()
            raise DriveInboxBlocked("Scan lease unavailable or access revoked")
        raw = secrets.token_urlsafe(32)
        row.lease_hmac = _index("lease-token", raw)
        row.lease_expires_epoch = now + ttl_seconds
        db.commit()
        return raw
    except DriveInboxBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise DriveInboxBlocked("Synthetic scan lease could not be issued") from None


def finish_fake_scan_lease(db: Session, *, folder_id: str,
                           lease_token: str,
                           outcome: str,
                           complete_receipt: dict | None = None,
                           now_epoch: int | None = None) -> dict:
    """Finalize with a committed, authenticated inventory, never a partial page.

    A failed or revoked provider attempt cannot overwrite the latest accepted
    complete snapshot, even after lease expiry, restart or worker crash.
    """
    folder = _guard(db, folder_id)
    now = _now(now_epoch)
    if (type(lease_token) is not str or _TOKEN.fullmatch(lease_token) is None
        or outcome not in {"success", "retryable", "denied"}):
        raise DriveInboxBlocked("Invalid synthetic scan lease completion")
    try:
        _lock(db, folder)
        row = _row(db, folder)
        if (row is None or row.lease_hmac is None
            or not hmac.compare_digest(row.lease_hmac, _index("lease-token",lease_token))
            or not row.lease_expires_epoch > now
            or (row.last_attempt_epoch is not None and now < row.last_attempt_epoch)
            or row.permission_revoked):
            db.rollback()
            raise DriveInboxBlocked("Expired, replayed or mismatched scan lease")
        if outcome == "success":
            if (type(complete_receipt) is not dict
                or complete_receipt.get("complete_folder_scan") is not True
                or complete_receipt.get("google_oauth_connected_to_pwa") is not False
                or complete_receipt.get("source_content_imported") is not False
                or complete_receipt.get("reconciliation_ready") is not False
                or type(complete_receipt.get("scan_number")) is not int
                or type(complete_receipt.get("tracked_sources")) is not int
                or complete_receipt.get("tracked_sources") < 0):
                raise DriveInboxBlocked("Complete fake scan receipt required")
            checkpoint, _, saved_state = _load(db, folder)
            if (checkpoint is None
                or checkpoint.scan_number != complete_receipt["scan_number"]
                or len(saved_state) != complete_receipt["tracked_sources"]
                or checkpoint.scan_number < row.last_scan_number
                or _HEX64.fullmatch(checkpoint.source_snapshot_hmac) is None):
                raise DriveInboxBlocked("Fake scan receipt not backed by complete index")
            row.last_success_epoch = now
            row.last_scan_number = checkpoint.scan_number
            row.last_source_hmac = checkpoint.source_snapshot_hmac
            row.failure_count = 0
        else:
            if complete_receipt is not None:
                raise DriveInboxBlocked("Failed scan cannot carry a success receipt")
            row.failure_count = min(row.failure_count+1,100)
        row.last_attempt_epoch = now
        row.last_outcome = outcome
        row.permission_revoked = outcome == "denied"
        row.lease_hmac = None
        row.lease_expires_epoch = 0
        db.commit()
        return {"synthetic_only":True,"outcome":outcome,
                "last_complete_scan_preserved":True,
                "background_job_started":False,
                "google_drive_connected":False,
                "real_financial_records_imported":False}
    except DriveInboxBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise DriveInboxBlocked("Fake scan completion not committed") from None


def fake_scan_lease_status(db: Session, *, folder_id: str,
                           now_epoch: int | None = None) -> dict:
    """Read private synthetic status; no owner IDs, filenames or token."""
    folder = _guard(db, folder_id)
    now = _now(now_epoch)
    try:
        row = db.get(DriveScanLease, folder)
        if row is None:
            return {"synthetic_only":True,"last_success_epoch":None,
                    "last_scan_number":0,"permission_state":"NEVER_SCANNED",
                    "lease_active":False,"heartbeat_is_real":False,
                    "background_job_started":False,"google_drive_connected":False}
        return {"synthetic_only":True,
                "last_success_epoch":row.last_success_epoch,
                "last_scan_number":row.last_scan_number,
                "permission_state": "REAUTHORIZATION_REQUIRED" if row.permission_revoked
                    else "FICTIONAL_TEST_ONLY",
                "lease_active":bool(row.lease_hmac and row.lease_expires_epoch>now),
                "heartbeat_is_real":False,
                "background_job_started":False,
                "google_drive_connected":False}
    finally:
        db.rollback()
