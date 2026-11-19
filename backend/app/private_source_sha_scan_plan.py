"""P5I pure fixture-only plan for a *fully* SHA-verified one-folder inventory.

This composes blinded P5A-like proof receipts and a complete metadata snapshot.
It does NOT fetch Google, read raw bytes, commit SQL, retain PDF content, or
verify the cryptographic SHA itself (the pinned byte-reader must do that).
It is not a released manifest, scheduler, reconciliation or finance endpoint.
"""
from __future__ import annotations

from collections import Counter
import hmac
import os
import re

from .drive_inbox_planner import DRIVE_ID, MAX_ITEMS, DriveFile, _index, _version

_HEX = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = frozenset({"revision_hmac", "name_hmac", "content_hmac", "present"})
_RECEIPT = frozenset({
    "source_hmac", "revision_hmac", "source_content_hmac",
    "byte_hash_verified",
})
_STAGES = (
    "new", "reappeared_needs_review", "content_changed_needs_review",
    "revision_changed_needs_review", "renamed_needs_review", "unchanged",
    "missing_in_source", "still_missing",
)


class PrivateSourceShaPlanBlocked(ValueError):
    """A partial, unpinned or unverified inventory cannot advance source state."""


def _previous(value: object) -> dict[str, dict]:
    if value is None:
        return {}
    if type(value) is not dict or len(value) > MAX_ITEMS:
        raise PrivateSourceShaPlanBlocked("Prior source manifest invalid")
    copy = {}
    for ident, entry in value.items():
        if (type(ident) is not str or _HEX.fullmatch(ident) is None
            or type(entry) is not dict or set(entry) != _FIELDS
            or type(entry["present"]) is not bool
            or any(type(entry[k]) is not str or _HEX.fullmatch(entry[k]) is None
                   for k in ("revision_hmac", "name_hmac", "content_hmac"))):
            raise PrivateSourceShaPlanBlocked("Prior source receipt malformed")
        copy[ident] = dict(entry)
    return copy


def plan_complete_synthetic_source_sha_scan(
    *, folder_id: str, files: tuple[DriveFile, ...],
    proof_receipts: tuple[dict, ...], prior: dict | None = None,
    inventory_complete: bool, proofs_complete: bool,
    approved_synthetic_fixture: bool,
) -> dict:
    """Atomically *plan* a snapshot using only complete owner-approved fake proofs.

    An unreadable/password-protected/oversized source must be resolved or
    quarantined by a future separately reviewed storage workflow. This strict
    pilot does not skip it: partial evidence cannot replace a last-good scan.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("P5I_SYNTHETIC_SHA_PLANNER_ONLY") != "1"
        or approved_synthetic_fixture is not True
        or inventory_complete is not True or proofs_complete is not True
        or type(folder_id) is not str or DRIVE_ID.fullmatch(folder_id) is None
        or type(files) is not tuple or len(files) > MAX_ITEMS
        or type(proof_receipts) is not tuple
        or len(proof_receipts) != len(files)
        or any(type(f) is not DriveFile for f in files)):
        raise PrivateSourceShaPlanBlocked("Complete approved fake source proof required")
    try:
        approved = os.getenv("DRIVE_ALLOWED_FOLDER_HMAC", "")
        calculated = _index("folder", folder_id)
        if _HEX.fullmatch(approved) is None or not hmac.compare_digest(
            approved, calculated
        ):
            raise ValueError()
        old = _previous(prior)
        proofs = {}
        for p in proof_receipts:
            if (type(p) is not dict or set(p) != _RECEIPT
                or p["byte_hash_verified"] is not True
                or any(type(p[k]) is not str or _HEX.fullmatch(p[k]) is None
                       for k in ("source_hmac", "revision_hmac",
                                 "source_content_hmac"))
                or p["source_hmac"] in proofs):
                raise ValueError()
            proofs[p["source_hmac"]] = p

        current = {}
        transitions = []
        for f in files:
            if (f.trashed or f.parent_ids != (folder_id,)
                or f.size_bytes is None or f.size_bytes <= 0):
                raise ValueError()
            ident = _index("file", f.id)
            if ident in current or ident not in proofs:
                raise ValueError()
            receipt = proofs[ident]
            revision = _version(f)
            if not hmac.compare_digest(receipt["revision_hmac"], revision):
                raise ValueError()
            name = _index("filename", f.name)
            item = {
                "revision_hmac": revision,
                "name_hmac": name,
                "content_hmac": receipt["source_content_hmac"],
                "present": True,
            }
            previous = old.get(ident)
            if previous is None:
                stage = "new"
            elif not previous["present"]:
                stage = "reappeared_needs_review"
            elif not hmac.compare_digest(previous["content_hmac"], item["content_hmac"]):
                stage = "content_changed_needs_review"
            elif previous["revision_hmac"] != revision:
                stage = "revision_changed_needs_review"
            elif previous["name_hmac"] != name:
                stage = "renamed_needs_review"
            else:
                stage = "unchanged"
            current[ident] = item
            transitions.append({"source_hmac": ident, "stage": stage})
        if set(proofs) != set(current):
            raise ValueError()
        for ident in set(old) - set(current):
            previous = old[ident]
            current[ident] = {**previous, "present": False}
            transitions.append({
                "source_hmac": ident,
                "stage": "missing_in_source" if previous["present"] else "still_missing",
            })
        transitions.sort(key=lambda row: (row["source_hmac"], row["stage"]))
        counts = Counter(row["stage"] for row in transitions)
        return {
            "contract": "personal_cfo_synthetic_complete_sha_plan_v1",
            "synthetic_only": True,
            "completed_plan": True,
            "idempotent_replay": prior is not None and current == old,
            "visible_sources": len(files),
            "tracked_sources": len(current),
            "stage_counts": {stage: counts[stage] for stage in _STAGES},
            "next_manifest": current,
            "transitions": transitions,
            "proofs_accepted_from_separate_hash_reader": True,
            "planner_computed_source_sha256": False,
            "source_hashes_persisted": False,
            "background_sync_active": False,
            "originals_modified": False,
            "financial_values_verified": False,
            "provider_network_used": False,
        }
    except PrivateSourceShaPlanBlocked:
        raise
    except (ValueError, TypeError, KeyError, AttributeError):
        raise PrivateSourceShaPlanBlocked(
            "Source hash evidence incomplete, stale, or untrusted"
        ) from None
