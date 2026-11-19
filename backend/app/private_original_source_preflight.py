"""P5A first genuine owner-original preflight: secure hashed bytes, no finance claims.

Reads an authenticated COMPLETE inventory of ONE pinned owner-private folder
with the separately consented content OAuth grant. Selects a bounded batch
BY SERVER ORDER (no user supplied file IDs or arbitrary Drive queries).
Validates each original before/after download and SHA-256 hashes actual bytes.
Returns only private owner-facing review status and HMAC receipts. NO content,
no transaction amounts, no original modification, no SQL financial import.

The work is deliberately a first step, NOT a bank statement parser; PDF,
image and non-normalized workbook source content remains "needs parser".
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
import re
from sqlalchemy.orm import Session

from .document_preflight import MAX_UPLOAD_BYTES, preflight_tabular
from .drive_folder_pages import _to_file
from .drive_inbox_planner import DRIVE_ID, _index, _version
from .private_content_grant_custody import (
    read_private_content_grant, store_private_content_grant,
)
from .private_drive_google_http import (
    _guard_network, _http_google, verify_owner_private_folder,
    list_private_owner_folder_page,
)
from .private_google_content_consent import (
    GOOGLE_CONTENT_READ_SCOPE, refresh_google_content_token,
)
from .private_owner_google_media_read import (
    read_pinned_google_source_once, _bounded_google_media,
)

_MAX_PAGES = 10
_MAX_SOURCES = 1000
_BATCH_SIZE = 3
_HEX = re.compile(r"^[a-f0-9]{64}$")
_OWNER = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class PrivateSourcePreflightBlocked(ValueError):
    """Private source hash preflight cannot safely proceed."""


def _guard(owner: str) -> None:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or not _OWNER.fullmatch(owner)
        or owner != os.getenv("P1W_OWNER_REF")
        or any(os.getenv(name) != "1" for name in (
            "P5A_ORIGINAL_HASH_PILOT",
            "P5A_G3_SINGLE_FOLDER_BYTES_REVIEWED",
            "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
            "P3A_G3_RESTRICTED_SCOPE_REVIEWED",
            "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
        ))
    ):
        raise PrivateSourcePreflightBlocked("Original-file read pilot not accepted")


def _inventory(access: str, *, config, transport: Callable):
    verify_owner_private_folder(
        access_token=access, config=config, transport=transport)
    result=[]
    seen_files=set()
    seen_cursors=set()
    cursor=None
    for _ in range(_MAX_PAGES):
        page=list_private_owner_folder_page(
            access_token=access, config=config,
            page_token=cursor, transport=transport)
        for raw in page["files"]:
            item=_to_file(raw)
            if (item.id in seen_files
                or item.parent_ids != (config.folder_id,)
                or item.trashed):
                raise PrivateSourcePreflightBlocked("Incomplete or unapproved original inventory")
            seen_files.add(item.id)
            result.append(item)
            if len(result)>_MAX_SOURCES:
                raise PrivateSourcePreflightBlocked("Original inventory exceeds private pilot bound")
        nxt=page.get("nextPageToken")
        if nxt is None:
            return tuple(sorted(result,key=lambda f:(f.name.casefold(),f.id)))
        if not isinstance(nxt,str) or nxt in seen_cursors or not 1<=len(nxt)<=1024:
            raise PrivateSourcePreflightBlocked("Original inventory pagination failed")
        seen_cursors.add(nxt)
        cursor=nxt
    raise PrivateSourcePreflightBlocked("Incomplete original inventory cannot be processed")


def preflight_original_owner_batch(
    *, session_factory: Callable[[],Session], owner_ref: str,
    batch_index: int, transport: Callable = _http_google,
    media_transport: Callable = _bounded_google_media,
) -> dict:
    """Read max 3 pinned originals per call; no source identities supplied by user.

    Return only statuses and source HMAC identity, never file bytes, account
    numbers, passwords or financial figures. Operator must first separately
    attest private ingestion and reviewed isolated parsers before money.
    """
    _guard(owner_ref)
    if (type(batch_index) is not int or not 0<=batch_index<=333
        or not callable(session_factory) or not callable(transport)
        or not callable(media_transport)):
        raise PrivateSourcePreflightBlocked("Approved bounded batch required")
    try:
        config=_guard_network()
        with session_factory() as db:
            refresh=read_private_content_grant(
                db,owner_ref=owner_ref,folder_id=config.folder_id,
                client_id=config.client_id)
        access, rotated=refresh_google_content_token(
            refresh_token=refresh,config=config,transport=transport)
        if rotated and rotated!=refresh:
            with session_factory() as db:
                store_private_content_grant(
                    db,owner_ref=owner_ref,folder_id=config.folder_id,
                    client_id=config.client_id,refresh_token=rotated,
                    verified_granted_scope=GOOGLE_CONTENT_READ_SCOPE)
        files=_inventory(access,config=config,transport=transport)
        start=batch_index*_BATCH_SIZE
        chosen=files[start:start+_BATCH_SIZE]
        results=[]
        for item in chosen:
            receipt={"source_hmac":_index("file",item.id),
                     "revision_hmac":_version(item),
                     "source_name":item.name}
            if item.size_bytes is None or item.size_bytes==0:
                results.append({**receipt,"state":"NEEDS_SIZE_REVIEW",
                                "byte_hash_verified":False})
                continue
            if item.size_bytes>MAX_UPLOAD_BYTES:
                results.append({**receipt,"state":"OVERSIZED_ISOLATED_REVIEW",
                                "byte_hash_verified":False})
                continue
            if not item.name.casefold().endswith(
                (".pdf",".csv",".xlsx",".png",".jpg",".jpeg")
            ):
                results.append({**receipt,"state":"UNSUPPORTED_FORMAT_REVIEW",
                                "byte_hash_verified":False})
                continue
            try:
                blob=read_pinned_google_source_once(
                    file_id=item.id,
                    expected_file_hmac=_index("file",item.id),
                    expected_revision_hmac=_version(item),
                    expected_name_hmac=_index("filename",item.name),
                    access_token=access,granted_scope=GOOGLE_CONTENT_READ_SCOPE,
                    metadata_transport=transport,
                    media_transport=media_transport)
                state="ORIGINAL_BYTES_HASH_VERIFIED"
                if blob.extension in (".csv",".xlsx"):
                    try:
                        preflight_tabular(blob.data,blob.extension)
                    except Exception:
                        state="ORIGINAL_HASH_VERIFIED_FORMAT_REVIEW"
                else:
                    state="ORIGINAL_HASH_VERIFIED_NEEDS_ISOLATED_PARSER"
                results.append({**receipt,
                    "state":state,
                    "byte_hash_verified":True,
                    "source_content_hmac":blob.content_hmac,
                    "byte_count":blob.byte_count})
            except Exception:
                results.append({**receipt,"state":"READ_OR_REVISION_REVIEW",
                                "byte_hash_verified":False})
        return {
            "contract":"personal_cfo_private_original_byte_preflight_v1",
            "approved_source_folder":True,
            "metadata_complete":True,
            "total_source_files":len(files),
            "batch_index":batch_index,
            "batch_size":_BATCH_SIZE,
            "next_batch":batch_index+1 if start+len(chosen)<len(files) else None,
            "results":results,
            "originals_modified":False,
            "source_bytes_returned_to_browser":False,
            "bytes_persisted":False,
            "source_hashes_persisted":False,
            "financial_figures_verified":False,
            "actual_bank_amounts_available":False,
            "real_pdf_parser_active":False,
        }
    except PrivateSourcePreflightBlocked:
        raise
    except Exception:
        raise PrivateSourcePreflightBlocked(
            "Private original source read unavailable; try again or review grant"
        ) from None
