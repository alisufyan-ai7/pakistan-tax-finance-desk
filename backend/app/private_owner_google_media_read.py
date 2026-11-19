"""P3A: read-only pinned-folder Google blob reader; unmounted pending OAuth G3.

This is a real-network-compatible, *independent* component. It is NOT an
activated endpoint or permission upgrade. Existing metadata-only consent
MUST NOT be used here. A separate, explicitly accepted Google content grant
must pass the verified granted_scope from the authenticated token exchange.

No Drive-wide list, writes, rename, delete, Google PDF parser, disk storage,
financial SQL mutation, or response containing source bytes is implemented.
Read credentials/tokens never enter logs, front-end code, or GitHub.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, Request, build_opener
from collections.abc import Callable

from .document_preflight import MAX_UPLOAD_BYTES
from .drive_folder_pages import _to_file
from .drive_inbox_planner import DRIVE_ID, DriveFile, _index, _version
from .drive_google_oauth import DriveOAuthConfig
from .private_drive_google_http import (
    _NoRedirects, _http_google, _guard_network, verify_owner_private_folder,
)

_CONTENT_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
_GOOGLE_FILES = "https://www.googleapis.com/drive/v3/files/"
_METADATA_FIELDS = "id,name,mimeType,parents,size,modifiedTime,md5Checksum,trashed,capabilities(canDownload)"
_HASH = re.compile(r"^[a-f0-9]{64}$")
_ALLOWED_EXT = (".csv", ".xlsx", ".pdf", ".png", ".jpg", ".jpeg")
_ALLOWED_MIME = {
    ".csv": ("text/csv","application/csv","application/vnd.ms-excel"),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    ".pdf": ("application/pdf",),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
}


class PrivateSourceMediaBlocked(ValueError):
    """Google original-byte read blocked with redacted failure."""


@dataclass(frozen=True)
class PrivateSourceBlob:
    """Internal-only ephemeral bytes, NEVER returned by a public endpoint."""
    data: bytes
    sha256: str
    content_hmac: str
    file_hmac: str
    revision_hmac: str
    extension: str
    byte_count: int


def _gate(*, granted_scope: str) -> DriveOAuthConfig:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P3A_PRIVATE_SOURCE_MEDIA_ENABLED") != "1"
        or os.getenv("P3A_G3_RESTRICTED_SCOPE_REVIEWED") != "1"
        or os.getenv("P3A_OWNER_CONTENT_CONSENT_ACCEPTED") != "1"
        or granted_scope != _CONTENT_SCOPE
    ):
        raise PrivateSourceMediaBlocked("Read-only Google content consent not approved")
    try:
        return _guard_network()
    except Exception:
        raise PrivateSourceMediaBlocked("Private Google content network not approved") from None


def _meta_url(file_id: str) -> str:
    return _GOOGLE_FILES + file_id + "?" + urlencode({
        "fields": _METADATA_FIELDS, "supportsAllDrives": "false",
    })


def _media_url(file_id: str) -> str:
    return _GOOGLE_FILES + file_id + "?" + urlencode({
        "alt": "media", "supportsAllDrives": "false",
    })


def _bounded_google_media(method: str, url: str, token: str) -> bytes:
    """Fixed-host, no-redirect HTTPS bytes transport; no generic HTTP client.

    Only callable by the already-gated owner reader. Size bound applies to
    downloaded data, not just Content-Length. Errors never include provider
    response body, URL, owner identity, token, or filenames.
    """
    if (method != "GET" or type(url) is not str
        or not re.fullmatch(
            r"https://www\.googleapis\.com/drive/v3/files/[A-Za-z0-9_-]{10,200}"
            r"\?alt=media&supportsAllDrives=false", url)
        or type(token) is not str or not 20 <= len(token) <= 8192
        or any(ch in token for ch in "\r\n\x00")):
        raise PrivateSourceMediaBlocked("Unapproved Google document request")
    try:
        opener = build_opener(HTTPSHandler(), _NoRedirects())
        request = Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/octet-stream",
            "Cache-Control": "no-store",
            "User-Agent": "PersonalCFO-PrivateSourceRead/1",
        }, method="GET")
        with opener.open(request, timeout=12) as response:
            if response.status != 200:
                raise ValueError()
            header = response.headers.get("Content-Length")
            if header is not None and (
                not header.isdecimal() or int(header) > MAX_UPLOAD_BYTES
            ):
                raise ValueError()
            payload = response.read(MAX_UPLOAD_BYTES + 1)
            if (header is not None and len(payload) != int(header)
                or not 0 < len(payload) <= MAX_UPLOAD_BYTES):
                raise ValueError()
            return payload
    except (ValueError, HTTPError, URLError, TimeoutError, OSError,
            PrivateSourceMediaBlocked):
        raise PrivateSourceMediaBlocked("Approved original-byte read unavailable") from None


def _file(
    raw: object, *, file_id: str, folder_id: str,
    expected_file_hmac: str, expected_revision_hmac: str,
) -> tuple[DriveFile, str]:
    if type(raw) is not dict or set(raw) != {
        "id","name","mimeType","parents","size","modifiedTime",
        "md5Checksum","trashed","capabilities",
    } or raw.get("capabilities") != {"canDownload": True}:
        raise PrivateSourceMediaBlocked("Original source metadata rejected")
    try:
        file = _to_file({k:v for k,v in raw.items() if k!="capabilities"})
        if (file.id != file_id
            or file.parent_ids != (folder_id,)
            or file.trashed is not False
            or file.size_bytes is None
            or not 0 < file.size_bytes <= MAX_UPLOAD_BYTES
            or "." not in file.name
            or _HASH.fullmatch(expected_file_hmac) is None
            or _HASH.fullmatch(expected_revision_hmac) is None
            or not hmac.compare_digest(_index("file", file_id), expected_file_hmac)
            or not hmac.compare_digest(_version(file), expected_revision_hmac)):
            raise ValueError()
        extension = "." + file.name.casefold().rsplit(".", 1)[-1]
        if extension not in _ALLOWED_EXT or file.mime_type not in _ALLOWED_MIME[extension]:
            raise ValueError()
        return file, extension
    except Exception:
        raise PrivateSourceMediaBlocked("Pinned original-file provenance mismatch") from None


def read_pinned_google_source_once(
    *, file_id: str, expected_file_hmac: str, expected_revision_hmac: str,
    access_token: str, granted_scope: str,
    metadata_transport: Callable = _http_google,
    media_transport: Callable = _bounded_google_media,
    folder_verifier: Callable = verify_owner_private_folder,
) -> PrivateSourceBlob:
    """Return a bounded source into PRIVATE memory, with two revision checks.

    Source IDs/HMAC receipts MUST originate in an independently authenticated
    complete inventory, NOT a URL or owner browser payload. This reader cannot
    itself verify OAuth refresh-token custody, source consent, anti-malware
    isolation or parser acceptance; it must remain unmounted until those gates
    are independently attested. No persistence or public JSON return.
    """
    config = _gate(granted_scope=granted_scope)
    if (type(file_id) is not str or DRIVE_ID.fullmatch(file_id) is None
        or type(access_token) is not str or not 20 <= len(access_token) <= 8192
        or any(c in access_token for c in "\r\n\x00")):
        raise PrivateSourceMediaBlocked("Approved file and credential required")
    try:
        folder_verifier(access_token=access_token, config=config,
                        transport=metadata_transport)
        url = _meta_url(file_id)
        first = metadata_transport("GET", url, None, access_token)
        file, extension = _file(
            first, file_id=file_id, folder_id=config.folder_id,
            expected_file_hmac=expected_file_hmac,
            expected_revision_hmac=expected_revision_hmac,
        )
        blob = media_transport("GET", _media_url(file_id), access_token)
        if type(blob) is not bytes or len(blob) != file.size_bytes:
            raise PrivateSourceMediaBlocked("Original bytes do not match approved version")
        # Detect changes between the authorization/metadata and media fetch.
        second = metadata_transport("GET", url, None, access_token)
        confirmed, extension_again = _file(
            second, file_id=file_id, folder_id=config.folder_id,
            expected_file_hmac=expected_file_hmac,
            expected_revision_hmac=expected_revision_hmac,
        )
        if confirmed != file or extension_again != extension:
            raise PrivateSourceMediaBlocked("Original source changed while reading")
        digest = sha256(blob).hexdigest()
        return PrivateSourceBlob(
            data=blob, sha256=digest, content_hmac=_index("source-sha256", digest),
            file_hmac=expected_file_hmac, revision_hmac=expected_revision_hmac,
            extension=extension, byte_count=len(blob),
        )
    except Exception:
        raise PrivateSourceMediaBlocked(
            "Private source requires scope, provenance and immutable-version review"
        ) from None
