"""P1M: isolated Postgres-backed Google *metadata-only* grant custody.

Real-compatible opaque refresh-grant envelopes, deliberately NOT imported by
app.preview_api or any public route. This module does NOT initiate OAuth,
authenticate the owner, issue Google requests, install keys or certify G2.
The staged P1C_GOOGLE_CLIENT_SECRET is never read by this module.

The distinct P1M security switches are default-off. The operator must obtain
independent owner MFA/recovery, DB role, key-backup and ingress review BEFORE
deploying such a private service. Tests use fabricated token strings only.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import hmac
import json
import os
import re
import secrets
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .drive_google_oauth import GOOGLE_METADATA_SCOPE
from .models import OwnerGoogleMetadataGrant

_KEY_ID = re.compile(r"^cfo-google-key-v[1-9][0-9]{0,2}$")
_OWNER_REF = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
_CLIENT = re.compile(r"^[A-Za-z0-9._-]{12,220}\.apps\.googleusercontent\.com$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_PREFIX = "P1M1:"
_MAX_TOKEN = 4096


class PrivateMetadataCustodyBlocked(ValueError):
    """A private Google metadata grant cannot be authenticated or accessed."""


def _bytes(encoded: str) -> bytes:
    try:
        value = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (UnicodeError, ValueError, TypeError):
        raise PrivateMetadataCustodyBlocked("Private metadata key unavailable") from None
    if len(value) != 32:
        raise PrivateMetadataCustodyBlocked("Private metadata key unavailable")
    return value


def _config(db: Session) -> tuple[str, dict[str, bytes], bytes]:
    # Explicit separate private owner metadata mode. Do NOT change G1 real
    # financial data mode, reuse fake P1E keys or accept SQLite on Railway.
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1M_PRIVATE_METADATA_CUSTODY_ONLY") != "1"
        or os.getenv("P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED") != "1"
        or db.bind is None
        or db.bind.dialect.name not in ("postgresql", "sqlite")
        or (db.bind.dialect.name == "sqlite"
            and os.getenv("P1M_SQLITE_FAKE_TEST_ONLY") != "1")):
        raise PrivateMetadataCustodyBlocked("Private Google metadata custody disabled")
    try:
        encoded = json.loads(os.environ.get("P1M_METADATA_ENCRYPTION_KEYS_JSON", ""))
        active = os.environ.get("P1M_METADATA_ACTIVE_KEY_ID", "")
        if (type(encoded) is not dict or not 2 <= len(encoded) <= 5
            or _KEY_ID.fullmatch(active) is None or active not in encoded):
            raise ValueError()
        keys = {}
        for name, value in encoded.items():
            if type(name) is not str or _KEY_ID.fullmatch(name) is None or type(value) is not str:
                raise ValueError()
            keys[name] = _bytes(value)
        mac = _bytes(os.environ.get("P1M_METADATA_ROW_HMAC_KEY", ""))
        if len(set(keys.values())) != len(keys) or mac in keys.values():
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise PrivateMetadataCustodyBlocked("Dedicated private metadata keys not accepted") from None
    return active, keys, mac


def _identity(key: bytes, domain: str, value: str) -> str:
    return hmac.new(
        key, ("personal-cfo:p1m:v1:" + domain + "\0" + value).encode("ascii"), sha256
    ).hexdigest()


def _identities(mac: bytes, *, owner_ref: str, folder_id: str, client_id: str) -> tuple[str, str, str]:
    if (type(owner_ref) is not str or _OWNER_REF.fullmatch(owner_ref) is None
        or type(folder_id) is not str or _DRIVE_ID.fullmatch(folder_id) is None
        or type(client_id) is not str or _CLIENT.fullmatch(client_id) is None):
        raise PrivateMetadataCustodyBlocked("Private owner/folder/client binding invalid")
    return (_identity(mac, "owner", owner_ref),
            _identity(mac, "folder", folder_id),
            _identity(mac, "client", client_id))


def _time(value: int | None) -> int:
    now = int(time.time()) if value is None else value
    if type(now) is not int or not 1_500_000_000 <= now <= 4_000_000_000:
        raise PrivateMetadataCustodyBlocked("Invalid private custody clock")
    return now


def _aad(owner: str, folder: str, client: str, version: str) -> bytes:
    return (
        "personal-cfo:p1m:metadata-only:v1:" + owner + ":" + folder
        + ":" + client + ":" + GOOGLE_METADATA_SCOPE + ":" + version
    ).encode("ascii")


def _token(value: str) -> str:
    # No fake-specific prefix in the implementation: real compatible opaque
    # token. CI tests MUST supply fictional strings, never Google grants.
    if (type(value) is not str or not 24 <= len(value) <= _MAX_TOKEN
        or any(ord(c) < 33 or ord(c) > 126 for c in value)):
        raise PrivateMetadataCustodyBlocked("Invalid private offline grant")
    return value


def _seal(key: bytes, version: str, owner: str, folder: str, client: str,
          refresh_token: str) -> str:
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(key).encrypt(nonce, _token(refresh_token).encode("ascii"),
                                    _aad(owner, folder, client, version))
    return _PREFIX + base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")


def _unseal(keys: dict[str, bytes], row: OwnerGoogleMetadataGrant) -> str:
    try:
        if (row.key_version not in keys or type(row.ciphertext) is not str
            or not row.ciphertext.startswith(_PREFIX)
            or len(row.ciphertext) > 6300):
            raise ValueError()
        blob = base64.b64decode(row.ciphertext[len(_PREFIX):], altchars=b"-_", validate=True)
        if not 28 <= len(blob) <= 4200:
            raise ValueError()
        plain = AESGCM(keys[row.key_version]).decrypt(
            blob[:12], blob[12:],
            _aad(row.owner_hmac, row.folder_hmac, row.client_hmac, row.key_version),
        )
        return _token(plain.decode("ascii"))
    except Exception:
        raise PrivateMetadataCustodyBlocked("Private offline grant cannot be authenticated") from None


def _row_mac(mac: bytes, row: OwnerGoogleMetadataGrant) -> str:
    raw = json.dumps({
        "owner": row.owner_hmac, "folder": row.folder_hmac,
        "client": row.client_hmac, "key": row.key_version,
        "ciphertext": row.ciphertext, "revision": row.revision,
        "revoked": row.revoked, "updated": row.updated_epoch,
    }, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hmac.new(mac, b"personal-cfo:p1m:row:v1:" + raw, sha256).hexdigest()


def _verify(mac: bytes, row: OwnerGoogleMetadataGrant) -> None:
    if (type(row.revision) is not int or row.revision < 1
        or not _HEX.fullmatch(row.owner_hmac)
        or not _HEX.fullmatch(row.folder_hmac)
        or not _HEX.fullmatch(row.client_hmac)
        or not isinstance(row.row_hmac, str)
        or not hmac.compare_digest(_row_mac(mac, row), row.row_hmac)):
        raise PrivateMetadataCustodyBlocked("Private metadata grant row corrupted")


def _lock(db: Session, identity: str) -> None:
    if db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:identity))"),
                   {"identity": identity})


def _row(db: Session, owner: str) -> OwnerGoogleMetadataGrant | None:
    return db.scalar(select(OwnerGoogleMetadataGrant).where(
        OwnerGoogleMetadataGrant.owner_hmac == owner
    ).with_for_update())


def store_private_metadata_grant(
    db: Session, *, owner_ref: str, folder_id: str, client_id: str,
    refresh_token: str, now_epoch: int | None = None,
) -> dict:
    """Persist authenticated ciphertext, never original credentials in SQL.

    PRIVATE caller must independently verify owner MFA and exact OAuth state
    BEFORE calling. This module cannot authenticate a browser or Google.
    """
    active, keys, mac = _config(db)
    owner, folder, client = _identities(
        mac, owner_ref=owner_ref, folder_id=folder_id, client_id=client_id)
    _token(refresh_token)
    now = _time(now_epoch)
    try:
        _lock(db, owner)
        row = _row(db, owner)
        if row is None:
            row = OwnerGoogleMetadataGrant(
                owner_hmac=owner, folder_hmac=folder, client_hmac=client,
                ciphertext="", key_version=active, revision=1, revoked=False,
                updated_epoch=now, row_hmac="",
            )
            db.add(row)
            db.flush()
        else:
            _verify(mac, row)
            if row.folder_hmac != folder or row.client_hmac != client:
                raise PrivateMetadataCustodyBlocked("Owner grant bound to different folder/client")
            row.revision += 1
        row.ciphertext = _seal(keys[active], active, owner, folder, client, refresh_token)
        row.key_version = active
        row.revoked = False
        row.updated_epoch = now
        row.row_hmac = _row_mac(mac, row)
        db.commit()
        return {"metadata_only": True, "sealed_in_private_database": True,
                "revision": row.revision, "connected_to_google": False,
                "original_bytes_authorized": False, "real_finance_authorized": False}
    except PrivateMetadataCustodyBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateMetadataCustodyBlocked("Private metadata grant not stored") from None


def read_private_metadata_grant(
    db: Session, *, owner_ref: str, folder_id: str, client_id: str,
) -> str:
    """Return plaintext ONLY inside trusted private process, never to browser."""
    _, keys, mac = _config(db)
    owner, folder, client = _identities(
        mac, owner_ref=owner_ref, folder_id=folder_id, client_id=client_id)
    try:
        row = db.get(OwnerGoogleMetadataGrant, owner)
        if row is None:
            raise PrivateMetadataCustodyBlocked("Private owner metadata grant unavailable")
        _verify(mac, row)
        if row.revoked or row.folder_hmac != folder or row.client_hmac != client:
            raise PrivateMetadataCustodyBlocked("Private owner metadata grant unavailable")
        result = _unseal(keys, row)
        db.rollback()
        return result
    except PrivateMetadataCustodyBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateMetadataCustodyBlocked("Private metadata grant unavailable") from None


def rotate_private_metadata_grant(
    db: Session, *, owner_ref: str, folder_id: str, client_id: str,
    now_epoch: int | None = None,
) -> dict:
    """Atomic rewrap to current active key. The operator separately backs up keys."""
    active, keys, mac = _config(db)
    owner, folder, client = _identities(
        mac, owner_ref=owner_ref, folder_id=folder_id, client_id=client_id)
    now = _time(now_epoch)
    try:
        _lock(db, owner)
        row = _row(db, owner)
        if row is None:
            raise PrivateMetadataCustodyBlocked("Private grant unavailable for key rotation")
        _verify(mac, row)
        if row.revoked or row.folder_hmac != folder or row.client_hmac != client:
            raise PrivateMetadataCustodyBlocked("Private grant unavailable for key rotation")
        if row.key_version == active or keys[row.key_version] == keys[active]:
            raise PrivateMetadataCustodyBlocked("Distinct active key generation required")
        plain = _unseal(keys, row)
        row.ciphertext = _seal(keys[active], active, owner, folder, client, plain)
        row.key_version = active
        row.revision += 1
        row.updated_epoch = now
        row.row_hmac = _row_mac(mac, row)
        db.commit()
        return {"metadata_only": True, "ciphertext_rotated": True,
                "revision": row.revision, "old_key_removed_from_configuration": False,
                "independent_recovery_test_passed": False, "real_google_connection": False}
    except PrivateMetadataCustodyBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateMetadataCustodyBlocked("Private grant rotation failed") from None


def revoke_private_metadata_grant(
    db: Session, *, owner_ref: str, folder_id: str, client_id: str,
    now_epoch: int | None = None,
) -> dict:
    """Immediately blank local ciphertext; provider revocation is separate."""
    _, _, mac = _config(db)
    owner, folder, client = _identities(
        mac, owner_ref=owner_ref, folder_id=folder_id, client_id=client_id)
    now = _time(now_epoch)
    try:
        _lock(db, owner)
        row = _row(db, owner)
        if row is None:
            raise PrivateMetadataCustodyBlocked("Private owner metadata grant unavailable")
        _verify(mac, row)
        if row.folder_hmac != folder or row.client_hmac != client:
            raise PrivateMetadataCustodyBlocked("Private owner metadata grant unavailable")
        row.ciphertext = ""
        row.revoked = True
        row.revision += 1
        row.updated_epoch = now
        row.row_hmac = _row_mac(mac, row)
        db.commit()
        return {"metadata_only": True, "local_ciphertext_erased": True,
                "provider_token_revoked": False, "real_finance_authorized": False}
    except PrivateMetadataCustodyBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateMetadataCustodyBlocked("Private grant revocation failed") from None
