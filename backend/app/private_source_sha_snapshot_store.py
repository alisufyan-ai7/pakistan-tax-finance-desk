"""P5I single-owner encrypted complete-source SHA candidate snapshot storage.

Never mounted into public or private live HTTP. Synthetic test fixture evidence
only until independent full database recovery, source auth, reader and G1/G3
release review. Source hashes are not financial facts.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import uuid
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .drive_inbox_planner import DRIVE_ID, DriveFile, _index, MAX_ITEMS
from .models import PrivateSourceShaSnapshot
from .private_source_sha_scan_plan import (
    PrivateSourceShaPlanBlocked, _previous,
    plan_complete_synthetic_source_sha_scan,
)

_OWNER = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_HEX = re.compile(r"^[a-f0-9]{64}$")

class PrivateSourceShaStoreBlocked(ValueError):
    """Cannot persist an untrusted or unrecoverable owner source snapshot."""

def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True)

def _guard(db: Session, *, owner_ref: str, folder_id: str) -> tuple[str,str]:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P5I_FAKE_SHA_STORE_ONLY") != "1"
        or os.getenv("P5I_SYNTHETIC_SHA_PLANNER_ONLY") != "1"
        or type(owner_ref) is not str or _OWNER.fullmatch(owner_ref) is None
        or owner_ref != os.getenv("P1W_OWNER_REF")
        or type(folder_id) is not str or DRIVE_ID.fullmatch(folder_id) is None
        or db.bind is None or db.bind.dialect.name not in ("sqlite","postgresql")):
        raise PrivateSourceShaStoreBlocked("Source SHA store disabled")
    try:
        owner = _index("p5i-owner", owner_ref)
        folder = _index("folder", folder_id)
        pin = os.getenv("DRIVE_ALLOWED_FOLDER_HMAC", "")
        if _HEX.fullmatch(pin) is None or not hmac.compare_digest(pin,folder):
            raise ValueError()
        return owner,folder
    except Exception:
        raise PrivateSourceShaStoreBlocked("Pinned owner folder invalid") from None

def _lock(db: Session, owner: str, folder: str):
    if db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:value))"),
                   {"value":owner+folder})

def _receipts(manifest: dict) -> tuple[str,str]:
    current = {k:v for k,v in manifest.items() if v["present"]}
    return (
        _index("p5i-complete-owner-sha-snapshot",_canonical(current)),
        _index("p5i-complete-owner-sha-state",_canonical(manifest)),
    )

def _loaded(row: PrivateSourceShaSnapshot | None, *, owner: str, folder: str) -> dict:
    if row is None:
        return {}
    try:
        if (row.owner_hmac != owner or row.folder_hmac != folder
            or type(row.scan_number) is not int or row.scan_number < 1
            or _HEX.fullmatch(row.snapshot_hmac) is None
            or _HEX.fullmatch(row.state_hmac) is None):
            raise ValueError()
        manifest = _previous(json.loads(row.payload_json))
        receipt,state = _receipts(manifest)
        if (not hmac.compare_digest(receipt,row.snapshot_hmac)
            or not hmac.compare_digest(state,row.state_hmac)):
            raise ValueError()
        return manifest
    except Exception:
        raise PrivateSourceShaStoreBlocked(
            "Encrypted source SHA snapshot integrity failed") from None

def _summary(*, manifest: dict, sequence: int, replay: bool,
             stage_counts: dict | None) -> dict:
    return {
        "contract":"personal_cfo_synthetic_encrypted_sha_snapshot_v1",
        "synthetic_only":True,
        "scan_number":sequence,
        "idempotent_replay":replay,
        "tracked_sources":len(manifest),
        "visible_sources":sum(v["present"] for v in manifest.values()),
        "missing_historical_sources":sum(not v["present"] for v in manifest.values()),
        "stage_counts":stage_counts,
        "manifest_ciphertext_persisted":True,
        "sha_proofs_preverified_by_trusted_caller":True,
        "planner_calculated_sha256":False,
        "original_drive_modified":False,
        "real_google_sync_active":False,
        "financial_values_verified":False,
    }

def persist_complete_synthetic_source_sha_snapshot(
    db: Session, *, owner_ref: str, folder_id: str,
    files: tuple[DriveFile,...], proof_receipts: tuple[dict,...],
    inventory_complete: bool, proofs_complete: bool,
    approved_synthetic_fixture: bool,
) -> dict:
    owner,folder=_guard(db,owner_ref=owner_ref,folder_id=folder_id)
    if (type(files) is not tuple or len(files)>MAX_ITEMS
        or type(proof_receipts) is not tuple):
        raise PrivateSourceShaStoreBlocked("Bounded complete owner SHA scan required")
    try:
        _lock(db,owner,folder)
        row=db.execute(select(PrivateSourceShaSnapshot).where(
            PrivateSourceShaSnapshot.owner_hmac==owner,
            PrivateSourceShaSnapshot.folder_hmac==folder,
        )).scalar_one_or_none()
        previous=_loaded(row,owner=owner,folder=folder)
        plan=plan_complete_synthetic_source_sha_scan(
            folder_id=folder_id,files=files,proof_receipts=proof_receipts,
            prior=previous,inventory_complete=inventory_complete,
            proofs_complete=proofs_complete,
            approved_synthetic_fixture=approved_synthetic_fixture,
        )
        next_manifest=plan["next_manifest"]
        receipt,state=_receipts(next_manifest)
        if row is not None and hmac.compare_digest(row.state_hmac,state):
            result=_summary(manifest=previous,sequence=row.scan_number,replay=True,
                            stage_counts=plan["stage_counts"])
            db.rollback()
            return result
        seq=1 if row is None else row.scan_number+1
        if row is None:
            row=PrivateSourceShaSnapshot(
                id=str(uuid.uuid4()),owner_hmac=owner,folder_hmac=folder,
                scan_number=seq,snapshot_hmac=receipt,state_hmac=state,
                payload_json=_canonical(next_manifest))
            db.add(row)
        else:
            row.scan_number=seq
            row.snapshot_hmac=receipt
            row.state_hmac=state
            row.payload_json=_canonical(next_manifest)
        db.commit()
        return _summary(manifest=next_manifest,sequence=seq,replay=False,
                        stage_counts=plan["stage_counts"])
    except (PrivateSourceShaPlanBlocked,PrivateSourceShaStoreBlocked):
        db.rollback()
        raise PrivateSourceShaStoreBlocked("Complete owner SHA snapshot rejected") from None
    except Exception:
        db.rollback()
        raise PrivateSourceShaStoreBlocked("Owner SHA snapshot commit unavailable") from None

def read_synthetic_source_sha_snapshot_status(
    db: Session, *, owner_ref: str, folder_id: str,
) -> dict:
    owner,folder=_guard(db,owner_ref=owner_ref,folder_id=folder_id)
    try:
        row=db.execute(select(PrivateSourceShaSnapshot).where(
            PrivateSourceShaSnapshot.owner_hmac==owner,
            PrivateSourceShaSnapshot.folder_hmac==folder,
        )).scalar_one_or_none()
        if row is None:
            raise ValueError()
        manifest=_loaded(row,owner=owner,folder=folder)
        return _summary(manifest=manifest,sequence=row.scan_number,replay=True,
                        stage_counts=None)
    except Exception:
        raise PrivateSourceShaStoreBlocked("No verified owner SHA snapshot available") from None
