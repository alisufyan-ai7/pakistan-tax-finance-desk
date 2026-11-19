"""P2D unmounted read-only source-byte boundary, synthetic-test fixtures ONLY.

Never calls Google, mutates originals, installs a worker, stores raw file
bytes or financial facts. A future reviewed drive.readonly OAuth grant must
authenticate one pinned owner folder, then feed its exact independently
re-fetched file metadata and bytes into a private isolated parser. Provider
MD5/version is a hint, never a substitute for independently hashed bytes.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
import os
import re

from .document_preflight import (
    MAX_UPLOAD_BYTES, PreflightError, preflight_tabular,
)
from .drive_inbox_planner import DriveFile, DRIVE_ID, _index

_MIME = {
    ".csv": ("text/csv", "application/csv", "application/vnd.ms-excel"),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    ".pdf": ("application/pdf",),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
}
_HEX = re.compile(r"^[a-f0-9]{64}$")


class PrivateDriveSourceReadBlocked(ValueError):
    """Untrusted or unsupported original-source byte proof."""


def preflight_synthetic_pinned_source_bytes(
    *, folder_id: str, file_id: str, metadata: DriveFile,
    content: bytes, approved_synthetic_fixture: bool,
) -> dict:
    """Require the exact pinned one-folder source with matching raw-byte size.

    The caller cannot supply a filename-derived authorization decision.
    Signature checks for PDFs/images are ONLY intake preflight and DO NOT
    certify their internal contents: isolated conversion remains mandatory.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("P2D_FAKE_ORIGINAL_CONTENT_ONLY") != "1"
        or approved_synthetic_fixture is not True
        or type(folder_id) is not str or not DRIVE_ID.fullmatch(folder_id)
        or type(file_id) is not str or not DRIVE_ID.fullmatch(file_id)
        or type(metadata) is not DriveFile
        or type(content) is not bytes
        or not 0 < len(content) <= MAX_UPLOAD_BYTES):
        raise PrivateDriveSourceReadBlocked("Private source content reading not authorized")
    try:
        approved = os.getenv("DRIVE_ALLOWED_FOLDER_HMAC","")
        folder_hmac = _index("folder",folder_id)
        if (_HEX.fullmatch(approved) is None
            or not hmac.compare_digest(approved,folder_hmac)
            or metadata.id != file_id or metadata.trashed
            or metadata.parent_ids != (folder_id,)
            or metadata.size_bytes != len(content)
            or "." not in metadata.name):
            raise ValueError()
        ext = "." + metadata.name.casefold().rsplit(".",1)[-1]
        if ext not in _MIME or metadata.mime_type not in _MIME[ext]:
            raise ValueError()
        if ext in (".csv",".xlsx"):
            preflight_tabular(content,ext)
            status="TABULAR_SIGNATURE_PREFLIGHT_ONLY"
        else:
            signs={
                ".pdf":b"%PDF-",
                ".png":b"\x89PNG\r\n\x1a\n",
                ".jpg":b"\xff\xd8\xff",
                ".jpeg":b"\xff\xd8\xff",
            }
            if not content.startswith(signs[ext]):
                raise ValueError()
            status="ISOLATED_BINARY_PARSER_NOT_YET_APPROVED"
        digest=sha256(content).hexdigest()
        return {
            "contract":"personal_cfo_synthetic_pinned_source_byte_proof_v1",
            "synthetic_only":True,
            "file_hmac":_index("file",file_id),
            "revision_hmac":_index("revision", "|".join((
                metadata.id,metadata.modified_time.isoformat(),
                str(metadata.size_bytes),metadata.md5_checksum or "",
                metadata.mime_type,
            ))),
            "byte_sha256":digest,
            "byte_sha256_hmac":_index("source-sha256",digest),
            "byte_length":len(content),
            "format":ext[1:],
            "preflight_status":status,
            "complete_source_proof":True,
            "provider_md5_proves_source_bytes":False,
            "originals_modified":False,
            "originals_downloaded_from_real_google":False,
            "real_finance_enabled":False,
            "financial_facts_verified":False,
            "provider_network_used":False,
            "private_encrypted_storage_committed":False,
        }
    except Exception:
        raise PrivateDriveSourceReadBlocked(
            "Source bytes require approved folder, signature and size review"
        ) from None
