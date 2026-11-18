"""P1AP: owner-only, on-demand one-folder metadata review snapshot.

No original file media/download or move/delete/write. No persistent index or
background scheduler is claimed: only a bounded validated snapshot returned to
an independently authenticated private owner UI. No direct public route.

A real PostgreSQL P1M encrypted grant must exist first. The caller enforces
P1Q owner session/CSRF and rate limits; this function never trusts a browser-
supplied folder, owner, page token or refresh token.
"""
from __future__ import annotations

from collections.abc import Callable
import os
import re
from time import time

from sqlalchemy.orm import Session

from .drive_folder_pages import _to_file
from .drive_inbox_planner import _format, DriveInboxBlocked
from .private_drive_google_http import (
    _guard_network, _http_google, list_private_owner_folder_page,
    refresh_google_access_token, verify_owner_private_folder,
)
from .private_metadata_grant_custody import (
    read_private_metadata_grant, store_private_metadata_grant,
)

_MAX_PAGES = 10
_MAX_FILES = 1000
_HEX = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class PrivateMetadataSnapshotBlocked(ValueError):
    """Untrusted, partial, unauthorized or oversized Google metadata snapshot."""


def _release_guard(owner_ref: str) -> None:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1AP_OWNER_FOLDER_METADATA_REVIEW_ONLY") != "1"
        or os.getenv("P1AP_G2_AUTHENTICATED_METADATA_UI_REVIEWED") != "1"
        or os.getenv("P1AN_GOOGLE_METADATA_RUNTIME") != "1"
        or os.getenv("P1AL_G2_EXACT_OAUTH_REVIEWED") != "1"
        or os.getenv("P1M_PRIVATE_METADATA_CUSTODY_ONLY") != "1"
        or os.getenv("P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED") != "1"
        or os.getenv("P1C_GOOGLE_NETWORK_ENABLED") != "1"
        or not isinstance(owner_ref, str)
        or _HEX.fullmatch(owner_ref) is None
        or owner_ref != os.getenv("P1W_OWNER_REF")
    ):
        raise PrivateMetadataSnapshotBlocked(
            "Owner metadata preview not independently accepted"
        )


def scan_one_owner_folder_metadata(
    *, session_factory: Callable[[], Session], owner_ref: str,
    transport: Callable = _http_google,
    now_epoch: int | None = None,
) -> dict:
    """Return one complete verified metadata snapshot, never raw Drive IDs.

    If any Google page is incomplete, duplicated, malformed or outside the
    pinned folder, the entire result is discarded. Nothing is persisted here.
    """
    _release_guard(owner_ref)
    if not callable(session_factory) or not callable(transport):
        raise PrivateMetadataSnapshotBlocked("Private metadata transport invalid")
    if now_epoch is not None and (
        type(now_epoch) is not int or not 1_500_000_000 <= now_epoch <= 4_000_000_000
    ):
        raise PrivateMetadataSnapshotBlocked("Private metadata clock invalid")
    try:
        config = _guard_network()
        with session_factory() as db:
            refresh = read_private_metadata_grant(
                db, owner_ref=owner_ref, folder_id=config.folder_id,
                client_id=config.client_id,
            )
        access, rotated_refresh = refresh_google_access_token(
            refresh_token=refresh, config=config, transport=transport,
        )
        # Verify identity and private folder *after* refresh and before list.
        verify_owner_private_folder(
            access_token=access, config=config, transport=transport,
        )
        if rotated_refresh and rotated_refresh != refresh:
            with session_factory() as db:
                store_private_metadata_grant(
                    db, owner_ref=owner_ref, folder_id=config.folder_id,
                    client_id=config.client_id, refresh_token=rotated_refresh,
                )
        items = []
        seen_ids = set()
        seen_cursors = set()
        cursor = None
        for _ in range(_MAX_PAGES):
            raw = list_private_owner_folder_page(
                access_token=access, config=config,
                page_token=cursor, transport=transport,
            )
            for value in raw["files"]:
                file = _to_file(value)
                if (
                    file.id in seen_ids or config.folder_id not in file.parent_ids
                    or file.trashed
                ):
                    raise PrivateMetadataSnapshotBlocked(
                        "Unexpected duplicate or unapproved folder file"
                    )
                seen_ids.add(file.id)
                classification, category = _format(file)
                items.append({
                    "display_name": file.name,
                    "virtual_collection": category,
                    "review_status": classification,
                    "size_bytes": file.size_bytes,
                    "modified_time": file.modified_time.isoformat(),
                    "original_content_imported": False,
                    "financial_claims_verified": False,
                })
                if len(items) > _MAX_FILES:
                    raise PrivateMetadataSnapshotBlocked(
                        "One-folder metadata inventory exceeds safe bound"
                    )
            next_cursor = raw.get("nextPageToken")
            if next_cursor is None:
                items.sort(key=lambda v: (v["virtual_collection"], v["display_name"].casefold(),
                                          v["modified_time"]))
                return {
                    "contract": "personal_cfo_owner_metadata_review_preview_v1",
                    "connection": "APPROVED_METADATA_GRANT_USED",
                    "folder": "ONE_OWNER_APPROVED_FOLDER",
                    "snapshot_complete": True,
                    "metadata_checked_at_epoch": int(time()) if now_epoch is None else now_epoch,
                    "items": items,
                    "total": len(items),
                    "snapshot_persisted": False,
                    "background_sync_active": False,
                    "source_bytes_downloaded": False,
                    "financial_claims_verified": False,
                    "real_financial_data_enabled": False,
                }
            if (
                type(next_cursor) is not str
                or not 1 <= len(next_cursor) <= 1024
                or next_cursor in seen_cursors
            ):
                raise PrivateMetadataSnapshotBlocked(
                    "Google metadata pagination cursor invalid"
                )
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        raise PrivateMetadataSnapshotBlocked(
            "Google metadata pagination incomplete"
        )
    except PrivateMetadataSnapshotBlocked:
        raise
    except Exception:
        # Never leak raw names, tokens, provider messages or OAuth codes.
        raise PrivateMetadataSnapshotBlocked(
            "Owner metadata snapshot unavailable; no data imported"
        ) from None
