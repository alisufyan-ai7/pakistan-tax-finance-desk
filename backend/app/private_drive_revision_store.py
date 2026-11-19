"""P2B: encrypted, atomic, restart-safe *synthetic* source revision snapshots.

Only a complete, owner-pinned fake Drive page-set can advance the stored
manifest. Provider name, revision and MD5 hints are HMAC-blinded by the
planner, then AES-GCM sealed in one PostgreSQL row. This is not a live
Google synchronizer, SHA-256 proof or financial import.
"""
from __future__ import annotations

from collections import Counter
import hmac
import json
import os
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from .drive_inbox_planner import DRIVE_ID, MAX_ITEMS, DriveFile, _index
from .models import PrivateDriveRevisionSnapshot
from .private_drive_revision_manifest import (
    PrivateDriveRevisionBlocked, _previous,
    plan_complete_owner_folder_revision,
)

_HEX = re.compile(r"^[a-f0-9]{64}$")


def _canonical(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _guard(db: Session, folder_id: str) -> str:
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("DRIVE_FAKE_TRANSPORT_ONLY") != "1"
        or type(folder_id) is not str
        or DRIVE_ID.fullmatch(folder_id) is None
        or db.bind is None
        or db.bind.dialect.name not in ("postgresql", "sqlite")):
        raise PrivateDriveRevisionBlocked("Protected Drive revision storage disabled")
    folder_hmac = _index("folder", folder_id)
    pinned = os.getenv("DRIVE_ALLOWED_FOLDER_HMAC", "")
    if _HEX.fullmatch(pinned) is None or not hmac.compare_digest(pinned, folder_hmac):
        raise PrivateDriveRevisionBlocked("Unapproved private Drive source folder")
    return folder_hmac


def _lock(db: Session, folder_hmac: str) -> None:
    if db.bind.dialect.name == "sqlite":
        # Must run first on a fresh session; serializes even first-scan writers.
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:folder))"),
                   {"folder": folder_hmac})


def _state_receipt(manifest: dict[str, dict]) -> str:
    return _index("p2b-durable-private-revision-state", _canonical(manifest))


def _current_receipt(manifest: dict[str, dict]) -> str:
    visible = {k: v for k, v in manifest.items() if v["present"]}
    return _index("p2b-complete-private-source-snapshot", _canonical(visible))


def _loaded(row: PrivateDriveRevisionSnapshot | None, folder_hmac: str) -> dict[str, dict]:
    if row is None:
        return {}
    try:
        if (row.folder_hmac != folder_hmac
            or type(row.scan_number) is not int or row.scan_number < 1
            or _HEX.fullmatch(row.state_hmac) is None
            or _HEX.fullmatch(row.source_snapshot_hmac) is None):
            raise ValueError()
        manifest = _previous(json.loads(row.payload_json))
        if (not hmac.compare_digest(row.state_hmac, _state_receipt(manifest))
            or not hmac.compare_digest(row.source_snapshot_hmac,
                                      _current_receipt(manifest))):
            raise ValueError()
        return manifest
    except Exception:
        raise PrivateDriveRevisionBlocked(
            "Stored private Drive revision history failed authenticated integrity check"
        ) from None


def _summary(manifest: dict[str, dict], *, scan_number: int,
             replayed: bool, stages: dict[str, int] | None = None) -> dict:
    present = sum(v["present"] for v in manifest.values())
    return {
        "contract": "personal_cfo_synthetic_durable_drive_revisions_v1",
        "synthetic_only": True,
        "scan_number": scan_number,
        "idempotent_replay": replayed,
        "tracked_sources": len(manifest),
        "visible_sources": present,
        "missing_historical_sources": len(manifest)-present,
        "stage_counts": stages,
        "snapshot_persisted_encrypted": True,
        "source_content_sha256_computed": False,
        "google_provider_md5_is_content_proof": False,
        "source_originals_modified": False,
        "background_sync_active": False,
        "provider_network_used": False,
        "financial_data_authorized": False,
    }


def persist_complete_synthetic_revision_snapshot(
    db: Session, *, folder_id: str, files: tuple[DriveFile, ...],
    snapshot_complete: bool, approved_synthetic_fixture: bool,
) -> dict:
    """One transaction holds the entire fully verified manifest or nothing.

    A complete scan is required to flag disappearance. Missing old sources
    stay historical; no source file is ever renamed/moved/modified or deleted.
    """
    folder_hmac = _guard(db, folder_id)
    if (snapshot_complete is not True
        or approved_synthetic_fixture is not True
        or type(files) is not tuple or len(files) > MAX_ITEMS
        or any(not isinstance(file, DriveFile) for file in files)):
        raise PrivateDriveRevisionBlocked("A complete authorized fake folder scan is required")
    try:
        _lock(db, folder_hmac)
        row = db.get(PrivateDriveRevisionSnapshot, folder_hmac)
        previous = _loaded(row, folder_hmac)
        plan = plan_complete_owner_folder_revision(
            folder_id=folder_id, files=files, previous=previous,
            snapshot_complete=True, approved_synthetic_fixture=True,
        )
        manifest = plan["next_manifest"]
        source_receipt = _current_receipt(manifest)
        state_receipt = _state_receipt(manifest)
        if row is not None and hmac.compare_digest(row.source_snapshot_hmac,
                                                     source_receipt):
            result = _summary(previous, scan_number=row.scan_number,
                              replayed=True, stages=plan["stage_counts"])
            db.rollback()
            return result
        seq = 1 if row is None else row.scan_number+1
        if row is None:
            db.add(PrivateDriveRevisionSnapshot(
                folder_hmac=folder_hmac, scan_number=seq,
                source_snapshot_hmac=source_receipt, state_hmac=state_receipt,
                payload_json=_canonical(manifest),
            ))
        else:
            row.scan_number = seq
            row.source_snapshot_hmac = source_receipt
            row.state_hmac = state_receipt
            row.payload_json = _canonical(manifest)
        db.commit()
        return _summary(manifest, scan_number=seq, replayed=False,
                        stages=plan["stage_counts"])
    except PrivateDriveRevisionBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateDriveRevisionBlocked(
            "Private Drive revision snapshot could not be committed"
        ) from None


def read_synthetic_private_revision_status(
    db: Session, *, folder_id: str,
) -> dict:
    """Read authenticated counts only; never return raw IDs/names or SHA claims."""
    folder_hmac = _guard(db, folder_id)
    try:
        _lock(db, folder_hmac)
        row = db.get(PrivateDriveRevisionSnapshot, folder_hmac)
        if row is None:
            raise PrivateDriveRevisionBlocked("No completed private Drive revision scan")
        previous = _loaded(row, folder_hmac)
        return _summary(previous, scan_number=row.scan_number,
                        replayed=True, stages=None)
    except PrivateDriveRevisionBlocked:
        raise
    except Exception:
        raise PrivateDriveRevisionBlocked(
            "Private Drive revision status unavailable"
        ) from None
    finally:
        db.rollback()
