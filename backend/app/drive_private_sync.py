"""P1B: bounded retry-safe one-folder Drive metadata sync orchestration.

This consumes only a private synthetic injected transport in public CI. The
future owner-authorized Google HTTP adapter must pass *only* a pinned-folder
files.list request, refreshed short-lived access token, and validated pages.
No raw names, token, URL or provider error goes into a status/exception/log.

Atomicity: no inventory write until every Google Drive page is complete.
A failed scan does not remove the last authenticated inventory or cursor.
The previous snapshot is retained when provider access is lost. No financial
data is imported and an untrusted Google filename never proves any FBR claim.
"""
from __future__ import annotations

from collections.abc import Callable
import os
from typing import Any

from sqlalchemy.orm import Session

from .drive_inbox_planner import DriveInboxBlocked
from .drive_folder_pages import collect_synthetic_drive_folder
from .drive_inbox_store import (
    apply_synthetic_drive_snapshot, read_synthetic_drive_review_queue,
)


class DriveProviderFailure(RuntimeError):
    def __init__(self, status: int):
        self.status = status
        super().__init__("Redacted private Drive metadata request failed")


_RETRYABLE = frozenset((429, 500, 502, 503, 504))


def scan_private_synthetic_folder(
    db: Session, *, folder_id: str,
    get_page: Callable[[dict[str, Any]], dict[str, Any]],
    synthetic_authorization_approved: bool,
    on_retry: Callable[[int], None] | None = None,
) -> dict:
    """Complete-batch delivery: bounded retries then one atomic index commit.

    A genuine production connector requires independent owner consent,
    restricted-scope Google OAuth verification, MFA, encrypted refresh token
    custody, private environment approval and a separate real-mode gate.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("DRIVE_FAKE_TRANSPORT_ONLY") != "1"
        or synthetic_authorization_approved is not True
        or not callable(get_page)):
        raise DriveInboxBlocked("Unapproved Google Drive synchronization")
    attempt_counter = 0

    def with_retries(params: dict[str, Any]) -> dict[str, Any]:
        nonlocal attempt_counter
        for retry_index in range(3):
            attempt_counter += 1
            try:
                return get_page(dict(params))
            except DriveProviderFailure as failure:
                if failure.status not in _RETRYABLE or retry_index == 2:
                    raise DriveInboxBlocked("Google metadata unavailable; last inventory preserved") from None
                if on_retry is not None:
                    # A production scheduler can apply bounded exponential backoff.
                    # CI does not sleep, leak response bodies or loop indefinitely.
                    on_retry(retry_index + 1)
            except Exception:
                raise DriveInboxBlocked("Google metadata unavailable; last inventory preserved") from None
        raise DriveInboxBlocked("Google metadata unavailable; last inventory preserved")

    try:
        complete_files = collect_synthetic_drive_folder(
            folder_id=folder_id, list_page=with_retries)
    except DriveInboxBlocked:
        # The caller has not committed *any* new inventory before completion.
        db.rollback()
        raise
    saved = apply_synthetic_drive_snapshot(
        db, folder_id=folder_id, files=complete_files,
        snapshot_complete=True, approved_synthetic_fixture=True,
    )
    return {
        **saved,
        "metadata_page_attempts": attempt_counter,
        "complete_folder_scan": True,
        "source_index_saved_atomically": not saved["idempotent_replay"],
        "google_oauth_connected_to_pwa": False,
        "source_content_imported": False,
        "reconciliation_ready": False,
    }


def safe_owner_inbox_status(db: Session, *, folder_id: str) -> dict:
    """Owner review data from sealed records only; no Google token/file bytes."""
    report = read_synthetic_drive_review_queue(db, folder_id=folder_id, limit=100)
    return {
        "contract": "personal_cfo_synthetic_document_inbox_v1",
        "synthetic_only": True,
        "source": "PRIVATE_SYNTHETIC_ENCRYPTED_INDEX",
        "connection": "NOT_LIVE_CONNECTED",
        "scan_number": report["scan_number"],
        "tracked": report["tracked_sources"],
        "visible": report["visible_sources"],
        "changed_needing_review": report["changed_sources_need_review"],
        "missing_needing_review": report["unavailable_sources_need_review"],
        "quarantined": report["quarantined_sources"],
        "possible_duplicates": report["possible_duplicates_need_review"],
        "review_queue": report["queue"],
        "source_evidence_certified": False,
        "owner_data_in_use": False,
        "requires_private_oauth_security_and_g3": True,
        "real_data_authorized": False,
    }
