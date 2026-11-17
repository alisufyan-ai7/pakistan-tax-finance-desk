"""P1: durable, one-folder AES-GCM synthetic Drive document-review queue.

No Google network calls, file downloads, source content, real owner ingestion,
OAuth tokens, scheduler or app financial-authority switch. All persisted
source-specific review fields are AES-GCM protected; SQL-visible identities are
domain-separated HMACs and synthetic scan counters only. Caller MUST supply
a complete, bounded owner-approved fake-source snapshot. Real mode fails closed.
"""
from __future__ import annotations

from collections import Counter
import hmac
import json
import os
import re
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .drive_inbox_planner import (
    DRIVE_ID, MAX_ITEMS, DriveFile, DriveInboxBlocked, _index,
    plan_synthetic_drive_inbox,
)
from .models import DriveInboxCheckpoint, DriveInboxItem

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_QUEUE = 100
_KEYS = {
    "file_hmac", "revision_hmac", "collection_hint", "review_status", "stage",
    "visible", "possible_duplicate_unverified", "source_content_processed",
    "source_financial_claims_verified", "original_touched_by_app",
}


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _guard(db: Session, folder_id: str) -> str:
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("DRIVE_FAKE_TRANSPORT_ONLY") != "1"
        or not isinstance(folder_id, str)
        or DRIVE_ID.fullmatch(folder_id) is None
        or db.bind is None
        or db.bind.dialect.name not in ("postgresql", "sqlite")):
        raise DriveInboxBlocked("Private Drive ingress is disabled; synthetic DB only")
    folder_hmac = _index("folder", folder_id)
    allowed = os.getenv("DRIVE_ALLOWED_FOLDER_HMAC", "")
    if (_HEX64.fullmatch(allowed) is None
        or not hmac.compare_digest(folder_hmac, allowed)):
        raise DriveInboxBlocked("Source folder does not match private pinned permission")
    return folder_hmac


def _lock(db: Session, folder_hmac: str) -> None:
    if db.bind.dialect.name == "sqlite":
        # Must be first DB command in fresh session. Serializes synthetic writers.
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        # Serialize first-scan creation too; FOR UPDATE alone cannot lock absent row.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:folder))"),
                   {"folder": folder_hmac})


def _state_tag(state: dict[str, dict]) -> str:
    return _index("persisted-state", _canonical(
        [[key, state[key]] for key in sorted(state)]
    ))


def _source_tag(indexed_rows: list[dict]) -> str:
    return _index("complete-source-snapshot", _canonical(
        sorted((row["file_hmac"], row["revision_hmac"]) for row in indexed_rows)
    ))


def _unpack(row: DriveInboxItem, folder_hmac: str) -> dict:
    try:
        state = json.loads(row.payload_json)
        if (type(state) is not dict or set(state) != _KEYS
            or row.folder_hmac != folder_hmac
            or state["file_hmac"] != row.file_hmac
            or state["revision_hmac"] != row.revision_hmac
            or _HEX64.fullmatch(row.file_hmac) is None
            or _HEX64.fullmatch(row.revision_hmac) is None
            or type(state["visible"]) is not bool
            or type(state["possible_duplicate_unverified"]) is not bool
            or state["source_content_processed"] is not False
            or state["source_financial_claims_verified"] is not False
            or state["original_touched_by_app"] is not False
            or type(state["collection_hint"]) is not str
            or type(state["review_status"]) is not str
            or type(state["stage"]) is not str):
            raise ValueError()
        return state
    except Exception:
        raise DriveInboxBlocked("Encrypted Drive index state could not be authenticated") from None


def _load(db: Session, folder_hmac: str):
    checkpoint = db.scalar(select(DriveInboxCheckpoint).where(
        DriveInboxCheckpoint.folder_hmac == folder_hmac).with_for_update())
    rows = db.scalars(select(DriveInboxItem).where(
        DriveInboxItem.folder_hmac == folder_hmac
    ).limit(MAX_ITEMS + 1)).all()
    if len(rows) > MAX_ITEMS or (checkpoint is None and rows):
        raise DriveInboxBlocked("Incomplete or unbounded saved Drive index")
    state = {}
    ids = set()
    for row in rows:
        if row.file_hmac in ids:
            raise DriveInboxBlocked("Duplicate encrypted Drive inventory identity")
        ids.add(row.file_hmac)
        state[row.file_hmac] = _unpack(row, folder_hmac)
    if checkpoint is not None and (
        type(checkpoint.scan_number) is not int or checkpoint.scan_number < 1
        or _HEX64.fullmatch(checkpoint.source_snapshot_hmac) is None
        or _HEX64.fullmatch(checkpoint.state_hmac) is None
        or not hmac.compare_digest(checkpoint.state_hmac, _state_tag(state))
    ):
        raise DriveInboxBlocked("Protected Drive scan or review state has been altered")
    return checkpoint, rows, state


def _summary(state: dict[str, dict], scan_number: int, *, replayed: bool) -> dict:
    stages = Counter(v["stage"] for v in state.values())
    return {
        "synthetic_only": True, "scan_number": scan_number, "idempotent_replay": replayed,
        "tracked_sources": len(state),
        "visible_sources": sum(v["visible"] for v in state.values()),
        "unavailable_sources_need_review": stages["not_visible_needs_review"],
        "changed_sources_need_review": sum(v["stage"] in (
            "changed_needs_reverification", "returned_needs_reverification"
        ) for v in state.values()),
        "quarantined_sources": sum(v["review_status"].startswith("quarantined")
                                   for v in state.values()),
        "possible_duplicates_need_review": sum(
            bool(v["possible_duplicate_unverified"]) for v in state.values()),
        "originals_moved_or_deleted": False,
        "document_content_downloaded_or_parsed": False,
        "real_financial_claims_verified": False,
        "background_sync_active": False,
        "google_oauth_connected_to_pwa": False,
        "ledger_mutated": False,
        "real_data_authorized": False,
    }


def apply_synthetic_drive_snapshot(
    db: Session, *, folder_id: str, files: tuple[DriveFile, ...],
    snapshot_complete: bool, approved_synthetic_fixture: bool,
) -> dict:
    """Commit a complete metadata snapshot atomically; preserve missing sources.

    Handles first-index, replay, changed versions, duplicate candidates and
    no-longer-visible files. Inaccessible originals are **retained and flagged**,
    not deleted; never updates an unrelated folder or financial record.
    """
    folder_hmac = _guard(db, folder_id)
    if (snapshot_complete is not True or approved_synthetic_fixture is not True
        or type(files) is not tuple or len(files) > MAX_ITEMS
        or any(not isinstance(f, DriveFile) for f in files)):
        raise DriveInboxBlocked("Unverified or incomplete Drive metadata snapshot")
    try:
        _lock(db, folder_hmac)
        checkpoint, old_rows, previous = _load(db, folder_hmac)
        known = {key: state["revision_hmac"] for key, state in previous.items()}
        plan = plan_synthetic_drive_inbox(
            folder_id=folder_id, files=files, known_versions=known,
            snapshot_complete=True, approved_synthetic_fixture=True,
        )
        source_mac = _source_tag(plan["indexed_rows"])
        if checkpoint is not None and hmac.compare_digest(
            checkpoint.source_snapshot_hmac, source_mac
        ):
            report = _summary(previous, checkpoint.scan_number, replayed=True)
            db.rollback()
            return report
        state = {}
        for item in plan["indexed_rows"]:
            file_hmac = item["file_hmac"]
            status = item["stage"]
            if (file_hmac in previous and not previous[file_hmac]["visible"]):
                status = "returned_needs_reverification"
            state[file_hmac] = {
                "file_hmac": file_hmac,
                "revision_hmac": item["revision_hmac"],
                "collection_hint": item["collection_hint"],
                "review_status": item["review_status"],
                "stage": status,
                "visible": True,
                "possible_duplicate_unverified": item["possible_duplicate_unverified"],
                "source_content_processed": False,
                "source_financial_claims_verified": False,
                "original_touched_by_app": False,
            }
        for file_hmac, old_state in previous.items():
            if file_hmac not in state:
                state[file_hmac] = {
                    **old_state,
                    "visible": False,
                    "stage": "not_visible_needs_review",
                    "review_status": "source_inaccessible_or_removed",
                    "source_content_processed": False,
                    "source_financial_claims_verified": False,
                    "original_touched_by_app": False,
                }
        if len(state) > MAX_ITEMS:
            raise DriveInboxBlocked("Review queue too large for full integrity proof")
        rows_by_id = {row.file_hmac: row for row in old_rows}
        for file_hmac, value in state.items():
            row = rows_by_id.get(file_hmac)
            if row is None:
                db.add(DriveInboxItem(
                    id=str(uuid.uuid4()), folder_hmac=folder_hmac,
                    file_hmac=file_hmac, revision_hmac=value["revision_hmac"],
                    payload_json=_canonical(value),
                ))
            else:
                if (row.revision_hmac != value["revision_hmac"]
                    or previous[file_hmac] != value):
                    row.revision_hmac = value["revision_hmac"]
                    row.payload_json = _canonical(value)
        seq = 1 if checkpoint is None else checkpoint.scan_number + 1
        state_mac = _state_tag(state)
        if checkpoint is None:
            db.add(DriveInboxCheckpoint(
                folder_hmac=folder_hmac, scan_number=seq,
                source_snapshot_hmac=source_mac, state_hmac=state_mac,
            ))
        else:
            checkpoint.scan_number = seq
            checkpoint.source_snapshot_hmac = source_mac
            checkpoint.state_hmac = state_mac
        db.commit()
        return _summary(state, seq, replayed=False)
    except DriveInboxBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise DriveInboxBlocked("Protected Drive scan could not be committed atomically") from None


def read_synthetic_drive_review_queue(
    db: Session, *, folder_id: str, limit: int = _MAX_QUEUE,
) -> dict:
    """Authenticated HMAC-only queue, with no names, links or source bytes."""
    folder_hmac = _guard(db, folder_id)
    if type(limit) is not int or not 1 <= limit <= _MAX_QUEUE:
        raise DriveInboxBlocked("Invalid review queue bound")
    try:
        _lock(db, folder_hmac)
        checkpoint, _, state = _load(db, folder_hmac)
        if checkpoint is None:
            raise DriveInboxBlocked("No complete approved Drive inventory")
        priority = {
            "not_visible_needs_review": 0,
            "returned_needs_reverification": 1,
            "changed_needs_reverification": 2,
            "new": 3,
            "unchanged": 4,
        }
        ordered = sorted(
            state.values(),
            key=lambda v: (
                0 if v["review_status"].startswith("quarantined") else 1,
                priority.get(v["stage"], 9), v["file_hmac"],
            ),
        )
        rows = [{
            "file_hmac": v["file_hmac"],
            "review_status": v["review_status"],
            "stage": v["stage"],
            "virtual_collection": v["collection_hint"],
            "visible": v["visible"],
            "possible_duplicate_unverified": v["possible_duplicate_unverified"],
        } for v in ordered[:limit]]
        result = {
            **_summary(state, checkpoint.scan_number, replayed=True),
            "queue": rows, "queue_truncated": len(state) > limit,
            "integrity_checked": True,
        }
        db.rollback()
        return result
    except DriveInboxBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise DriveInboxBlocked("Protected Drive review queue unavailable") from None
