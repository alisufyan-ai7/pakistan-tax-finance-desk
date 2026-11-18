"""P2B: single-owner, one-folder, purely deterministic Drive metadata change plan.

This is an *unmounted* synthetic-only planner, not a provider connection or
durable schedule. Nothing modifies originals or financial records. A complete
approved-folder snapshot is mandatory before calculating missing items. All
file/name/revision keys leaving this boundary are HMAC-blinded. Drive MD5 is
a weak *hint*, never an independently computed SHA-256 content hash.
"""
from __future__ import annotations

from collections import Counter
import hmac
import os
import re

from .drive_inbox_planner import (
    DriveFile, DriveInboxBlocked, DRIVE_ID, MAX_ITEMS, _index, _version,
)

_HEX = re.compile(r"^[a-f0-9]{64}$")
_REQUIRED = frozenset({
    "revision_hmac", "name_hmac", "content_hint_hmac", "present",
})
_STAGES = (
    "new", "unchanged", "name_changed_needs_review",
    "content_hint_changed_needs_sha256",
    "metadata_changed_needs_review", "missing_in_source",
)


class PrivateDriveRevisionBlocked(ValueError):
    """Untrusted source inventory; never emit partial metadata state."""


def _previous(previous: object) -> dict[str, dict]:
    if previous is None:
        return {}
    if type(previous) is not dict or len(previous) > MAX_ITEMS:
        raise PrivateDriveRevisionBlocked("Bounded prior manifest required")
    result = {}
    for key, value in previous.items():
        if (type(key) is not str or _HEX.fullmatch(key) is None
            or type(value) is not dict or set(value) != _REQUIRED
            or type(value["present"]) is not bool
            or any(type(value[n]) is not str or _HEX.fullmatch(value[n]) is None
                   for n in ("revision_hmac", "name_hmac",
                             "content_hint_hmac"))):
            raise PrivateDriveRevisionBlocked("Prior manifest schema invalid")
        result[key] = dict(value)
    return result


def plan_complete_owner_folder_revision(
    *, folder_id: str, files: tuple[DriveFile, ...],
    previous: dict[str, dict] | None = None,
    snapshot_complete: bool,
    approved_synthetic_fixture: bool,
) -> dict:
    """Produce source-blinded new/unchanged/rename/revision/missing transitions.

    Caller MUST use only an already-authenticated, complete, single-approved
    folder response and atomically persist a returned manifest in a future
    explicitly reviewed encrypted store. Repeated identical scans are
    deterministic; source deletions remain historical missing records.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or approved_synthetic_fixture is not True
        or type(snapshot_complete) is not bool or not snapshot_complete
        or type(folder_id) is not str or DRIVE_ID.fullmatch(folder_id) is None
        or type(files) is not tuple or len(files) > MAX_ITEMS
        or any(not isinstance(item, DriveFile) for item in files)):
        raise PrivateDriveRevisionBlocked("Complete approved synthetic folder snapshot required")
    try:
        pinned = os.getenv("DRIVE_ALLOWED_FOLDER_HMAC", "")
        calculated = _index("folder", folder_id)
        if (_HEX.fullmatch(pinned) is None
            or not hmac.compare_digest(pinned, calculated)):
            raise ValueError()
        known = _previous(previous)
        manifest = {}
        changes = []
        for file in files:
            if (folder_id not in file.parent_ids or file.trashed
                or any(parent != folder_id for parent in file.parent_ids)):
                raise ValueError()
            blind_id = _index("file", file.id)
            if blind_id in manifest:
                raise ValueError()
            version = _version(file)
            name = _index("filename", file.name)
            # Size/MD5/MIME are provider hints, not proof of byte identity.
            hint = _index("provider-content-hint", "|".join([
                file.mime_type, str(file.size_bytes), file.md5_checksum or "",
            ]))
            old = known.get(blind_id)
            if old is None or not old["present"]:
                stage = "new"
            elif old["content_hint_hmac"] != hint:
                stage = "content_hint_changed_needs_sha256"
            elif old["name_hmac"] != name:
                stage = "name_changed_needs_review"
            elif old["revision_hmac"] != version:
                stage = "metadata_changed_needs_review"
            else:
                stage = "unchanged"
            entry = {
                "revision_hmac": version,
                "name_hmac": name,
                "content_hint_hmac": hint,
                "present": True,
            }
            manifest[blind_id] = entry
            changes.append({"file_hmac": blind_id, "stage": stage})
        for blind_id in sorted(set(known) - set(manifest)):
            old = known[blind_id]
            manifest[blind_id] = {**old, "present": False}
            # Do not classify an already-missing historical record as
            # newly deleted on every replay; no source evidence is erased.
            changes.append({
                "file_hmac": blind_id,
                "stage": "missing_in_source",
            })
        changes.sort(key=lambda row: (row["file_hmac"], row["stage"]))
        counts = Counter(c["stage"] for c in changes)
        return {
            "contract": "personal_cfo_synthetic_private_revision_plan_v1",
            "snapshot_complete": True,
            "total_current_files": len(files),
            "prior_record_count": len(known),
            "stage_counts": {stage: counts[stage] for stage in _STAGES},
            "next_manifest": manifest,
            "transitions": changes,
            "content_sha256_computed": False,
            "provider_md5_is_content_proof": False,
            "original_files_mutated": False,
            "financial_data_authorized": False,
            "durable_index_written": False,
            "background_sync_running": False,
            "provider_network_used": False,
        }
    except PrivateDriveRevisionBlocked:
        raise
    except (ValueError, TypeError, KeyError, DriveInboxBlocked):
        raise PrivateDriveRevisionBlocked(
            "Untrusted Drive revision snapshot; no partial changes"
        ) from None
