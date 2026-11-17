"""Single-folder Google Drive inbox: SYNTHETIC metadata-only ingestion planner.

Owner drops everything into ONE private inbox. The app does the virtual
organization; it does not move/delete/rename originals. No financial
classification is considered authoritative until a separately approved
private parser verifies original bytes and account/year/source provenance.

This module NEVER communicates with Google, downloads files, runs OCR,
handles OAuth, sets a schedule or mutates the legacy financial ledger.
A Drive connection and private processor must be independently authorized.
"""
from __future__ import annotations

import base64
from collections import Counter
from datetime import datetime
from hashlib import sha256
import hmac
import os
from pathlib import PurePosixPath
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

MAX_ITEMS = 1000
MAX_BYTES_PER_FILE = 60 * 1024 * 1024
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
_MD5 = re.compile(r"^[a-f0-9]{32}$")
_ALLOWED_TYPES = {
    ".pdf": {"application/pdf"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".csv": {"text/csv", "application/csv", "application/vnd.ms-excel"},
    ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"}, ".png": {"image/png"},
}
_COLLECTIONS = (
    "bank_statements", "tax_returns", "wealth_statements",
    "accountant_working", "investments", "loans_and_cash",
    "bills_and_receipts", "screenshots_and_correspondence", "unclassified",
)


class DriveInboxBlocked(ValueError):
    """Untrusted or unapproved source of file metadata."""


class DriveFile(BaseModel):
    """Precisely bounded Drive v3 file metadata, never raw source contents."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=10, max_length=200)
    name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=3, max_length=120)
    parent_ids: tuple[str, ...] = ()
    size_bytes: StrictInt | None = Field(default=None, ge=0, le=1_000_000_000)
    modified_time: datetime
    md5_checksum: str | None = None
    trashed: bool = False

    @model_validator(mode="after")
    def validate_drive_metadata(self):
        if (not DRIVE_ID.fullmatch(self.id)
            or not self.parent_ids or len(self.parent_ids) > 20
            or any(not DRIVE_ID.fullmatch(p) for p in self.parent_ids)
            or not self.name.strip() or "\x00" in self.name
            or self.modified_time.tzinfo is None
            or (self.md5_checksum is not None
                and not _MD5.fullmatch(self.md5_checksum))):
            raise ValueError("Invalid or incomplete Drive metadata")
        return self


def _key() -> bytes:
    raw = os.getenv("DRIVE_INDEX_HMAC_KEY", "")
    try:
        decoded = base64.b64decode(raw, altchars=b"-_", validate=True)
    except (ValueError, UnicodeError):
        raise DriveInboxBlocked("Drive index key unavailable") from None
    if len(decoded) != 32:
        raise DriveInboxBlocked("Drive index key unavailable")
    return decoded


def _index(domain: str, value: str) -> str:
    return hmac.new(_key(), ("personal-cfo:drive-inbox:v1:" + domain + ":" + value).encode("utf-8"),
                    sha256).hexdigest()


def _hint(name: str) -> str:
    """Untrusted filename-based *suggestion*, never a fact or bank account."""
    value = name.lower().replace("-", " ").replace("_", " ")
    if any(word in value for word in ("accountant", "working paper", "draft calculation")):
        return "accountant_working"
    if "wealth" in value and any(word in value for word in ("fbr", "iris", "tax")):
        return "wealth_statements"
    if any(word in value for word in ("fbr", "iris", "tax return", "return 202")):
        return "tax_returns"
    if any(word in value for word in ("statement", "bank", "account activity")):
        return "bank_statements"
    if any(word in value for word in ("investment", "broker", "mutual fund", "portfolio", "dividend")):
        return "investments"
    if any(word in value for word in ("loan", "cash receipt", "advance")):
        return "loans_and_cash"
    if any(word in value for word in ("invoice", "utility bill", "payment receipt", "rent")):
        return "bills_and_receipts"
    if any(word in value for word in ("whatsapp", "screenshot", "chat", "image")):
        return "screenshots_and_correspondence"
    return "unclassified"


def _format(file: DriveFile) -> tuple[str, str]:
    # No use of raw file paths for actual filesystem operations.
    filename = file.name.casefold()
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if file.mime_type == "application/vnd.google-apps.folder":
        return "skip_folder", "unclassified"
    if file.trashed:
        return "source_trashed_review", "unclassified"
    if not ext or ext not in _ALLOWED_TYPES or file.mime_type not in _ALLOWED_TYPES[ext]:
        return "quarantined_unsupported_format", "unclassified"
    if file.size_bytes is None or file.size_bytes < 1:
        return "needs_size_or_content_review", "unclassified"
    if file.size_bytes > MAX_BYTES_PER_FILE:
        return "quarantined_oversized", "unclassified"
    category = _hint(file.name)
    return ("needs_type_review" if category == "unclassified"
            else "awaiting_private_document_verification"), category


def _version(file: DriveFile) -> str:
    # Drive MD5 is weak and may be absent; NEVER treat this as SHA256 source proof.
    return _index("revision", "|".join([
        file.id, file.modified_time.isoformat(), str(file.size_bytes),
        file.md5_checksum or "", file.mime_type,
    ]))


def plan_synthetic_drive_inbox(
    *, folder_id: str, files: tuple[DriveFile, ...],
    known_versions: dict[str, str] | None = None, snapshot_complete: bool,
    approved_synthetic_fixture: bool,
) -> dict:
    """Fail closed unless a complete bounded one-folder synthetic page is known.

    'known_versions': private keyed file ID -> private keyed revision, from a
    previously committed source-index snapshot. Caller persists only after
    successful full validation; this library never commits or imports bytes.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or approved_synthetic_fixture is not True
        or not DRIVE_ID.fullmatch(folder_id)
        or snapshot_complete is not True or type(files) is not tuple
        or len(files) > MAX_ITEMS or any(not isinstance(x, DriveFile) for x in files)):
        raise DriveInboxBlocked("Only complete bounded synthetic Drive snapshot is accepted")
    known = known_versions or {}
    if (type(known) is not dict
        or any(not isinstance(k, str) or not isinstance(v, str)
               or not re.fullmatch(r"[0-9a-f]{64}", k)
               or not re.fullmatch(r"[0-9a-f]{64}", v)
               for k, v in known.items())):
        raise DriveInboxBlocked("Incomplete or unauthenticated prior index")
    seen = set()
    checksums = {}
    rows = []
    for file in files:
        # Do not sweep other Drive folders, even if OAuth user sees them.
        if folder_id not in file.parent_ids:
            raise DriveInboxBlocked("Source file is outside approved inbox")
        identity = _index("file", file.id)
        if identity in seen:
            raise DriveInboxBlocked("Repeated Drive file ID in same snapshot")
        seen.add(identity)
        revision = _version(file)
        status, collection = _format(file)
        prev = known.get(identity)
        if prev == revision:
            stage = "unchanged"
        elif prev:
            stage = "changed_needs_reverification"
        else:
            stage = "new"
        possible_duplicate = False
        if file.md5_checksum and file.size_bytes:
            # Conservative candidate only: MD5 collisions and copies exist.
            weak = _index("possible-md5", f"{file.size_bytes}:{file.md5_checksum}")
            possible_duplicate = weak in checksums
            checksums[weak] = identity
        rows.append({
            "file_hmac": identity,
            "revision_hmac": revision,
            "stage": stage,
            "collection_hint": collection,
            "review_status": status,
            "possible_duplicate_unverified": possible_duplicate,
            "original_kept_in_inbox": True,
            "source_content_processed": False,
            "source_financial_claims_verified": False,
        })
    status_counts = Counter(row["review_status"] for row in rows)
    stage_counts = Counter(row["stage"] for row in rows)
    categories = Counter(row["collection_hint"] for row in rows)
    return {
        "synthetic_only": True, "one_drop_folder": True,
        "snapshot_complete": True, "originals_never_moved_or_deleted": True,
        "count": len(rows), "new_count": stage_counts["new"],
        "changed_count": stage_counts["changed_needs_reverification"],
        "unchanged_count": stage_counts["unchanged"],
        "quarantined_count": sum(v for k, v in status_counts.items() if k.startswith("quarantined")),
        "duplicate_candidates_needing_review": sum(
            bool(row["possible_duplicate_unverified"]) for row in rows),
        "virtual_collection_counts": {name: categories[name] for name in _COLLECTIONS},
        "indexed_rows": rows,
        "original_content_downloaded": False,
        "drive_oauth_connected": False,
        "background_monitor_started": False,
        "ledger_mutated": False,
        "owner_tax_or_fbr_filing_verified": False,
        "real_data_authorized": False,
    }
