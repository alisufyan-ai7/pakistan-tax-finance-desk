"""Google Drive v3 one-folder metadata page contract (synthetic fake transport).

No HTTP client, refresh token, credential, scheduler, drive-wide search or
real data. Caller must supply a trusted, owner-authorized private connector.
A complete paginated snapshot is required before indexing anything. All
file names and IDs stay in process; only HMAC redacted plans leave this layer.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Any
import os

from .drive_inbox_planner import (
    DRIVE_ID, DriveFile, DriveInboxBlocked, MAX_ITEMS, plan_synthetic_drive_inbox,
)

FIELDS = "nextPageToken,incompleteSearch,files(id,name,mimeType,parents,size,modifiedTime,md5Checksum,trashed)"
PAGE_SIZE = 100


def _to_file(raw: dict[str, Any]) -> DriveFile:
    if type(raw) is not dict:
        raise DriveInboxBlocked("Unexpected provider file metadata")
    allowed = {"id", "name", "mimeType", "parents", "size", "modifiedTime", "md5Checksum", "trashed"}
    if set(raw) - allowed:
        raise DriveInboxBlocked("Unexpected provider fields")
    try:
        size = raw.get("size")
        if size is not None:
            if type(size) is not str or not size.isdecimal():
                raise ValueError("Bad size")
            size = int(size)
        return DriveFile.model_validate({
            "id": raw["id"], "name": raw["name"],
            "mime_type": raw["mimeType"], "parent_ids": tuple(raw["parents"]),
            "size_bytes": size, "modified_time": raw["modifiedTime"],
            "md5_checksum": raw.get("md5Checksum"),
            "trashed": raw.get("trashed", False),
        })
    except Exception:
        raise DriveInboxBlocked("Unrecognized provider metadata") from None


def collect_synthetic_drive_folder(
    *, folder_id: str, list_page: Callable[[dict[str, Any]], dict],
    max_pages: int = 10,
) -> tuple[DriveFile, ...]:
    """Client-side pagination. NEVER quietly index a partial search result.

    `list_page` must be a synthetic fake in public CI. Production Drive OAuth
    and polling require private approvals, privacy/security acceptance and
    a separately implemented, reviewable credential holder.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("DRIVE_FAKE_TRANSPORT_ONLY") != "1"
        or not isinstance(folder_id, str) or not DRIVE_ID.fullmatch(folder_id)
        or type(max_pages) is not int or not 1 <= max_pages <= 10
        or not callable(list_page)):
        raise DriveInboxBlocked("Authenticated synthetic-only Drive transport required")
    files = []
    seen_tokens: set[str] = set()
    token: str | None = None
    for _ in range(max_pages):
        params: dict[str, Any] = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "pageSize": PAGE_SIZE,
            "fields": FIELDS,
            "spaces": "drive",
            "corpora": "user",
        }
        if token:
            params["pageToken"] = token
        try:
            data = list_page(dict(params))
        except Exception:
            raise DriveInboxBlocked("Drive folder metadata unavailable") from None
        if (type(data) is not dict or data.get("incompleteSearch", False) is not False
            or type(data.get("files")) is not list
            or len(data["files"]) > PAGE_SIZE):
            raise DriveInboxBlocked("Truncated or malformed Drive metadata search")
        for raw in data["files"]:
            file = _to_file(raw)
            if folder_id not in file.parent_ids:
                raise DriveInboxBlocked("Drive query returned outside-folder file")
            files.append(file)
            if len(files) > MAX_ITEMS:
                raise DriveInboxBlocked("Drive folder snapshot exceeds current safe limit")
        next_token = data.get("nextPageToken")
        if next_token is None:
            return tuple(files)
        if (type(next_token) is not str or not 1 <= len(next_token) <= 1024
            or next_token in seen_tokens):
            raise DriveInboxBlocked("Drive pagination loop or malformed cursor")
        seen_tokens.add(next_token)
        token = next_token
    raise DriveInboxBlocked("Incomplete Drive pagination cannot be indexed")


def plan_synthetic_folder_from_pages(
    *, folder_id: str, list_page: Callable[[dict[str, Any]], dict],
    known_versions: dict[str, str] | None = None,
) -> dict:
    """No side effects. Index *only after* the complete folder was listed."""
    files = collect_synthetic_drive_folder(folder_id=folder_id,list_page=list_page)
    return plan_synthetic_drive_inbox(
        folder_id=folder_id, files=files,
        known_versions=known_versions,snapshot_complete=True,
        approved_synthetic_fixture=True,
    )
