"""P4B: content-only refresh grant sealed beside, never INTO, metadata authority.

Uses the existing encrypted owner-grant PostgreSQL table but a DIFFERENT
blind owner namespace and HKDF-derived AES-GCM, row-HMAC and identity keys.
No metadata row is replaced, read, rotated or revoked by this component.
Its ciphertext is separately bound to the fixed Google drive.readonly scope.

No new cloud provider or DB schema, owner recovery secrets or passwords:
existing reviewed P1M root keys supply distinct per-purpose subkeys. A
private authenticated callback MUST verify exact provider content scope and
approved single-folder ownership before storing any token. These functions
do not call Google, fetch originals or create a public endpoint.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import hmac
import json
import os
import re
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.orm import Session

from .models import OwnerGoogleMetadataGrant
from .private_metadata_grant_custody import (
    PrivateMetadataCustodyBlocked, _config as _metadata_config,
    _identities as _metadata_identities, _lock, _time,
)
from .drive_google_oauth import GOOGLE_METADATA_SCOPE

GOOGLE_CONTENT_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
_PREFIX = "P4C1:"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_SALT = b"personal-cfo:p4c:content-grant:v1:salt"


class PrivateContentGrantBlocked(ValueError):
    """No independently granted, authenticated read-only content credential."""


def _derive(material: bytes, purpose: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32,
        salt=_SALT, info=b"personal-cfo:p4c:v1:" + purpose,
    ).derive(material)


def _config(db: Session):
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P4B_PRIVATE_CONTENT_GRANT_CUSTODY") != "1"
        or os.getenv("P4B_G2_OWNER_CONTENT_GRANT_REVIEWED") != "1"
        or os.getenv("P4B_G3_EXACT_CONTENT_SCOPE_ATTESTED") != "1"):
        raise PrivateContentGrantBlocked("Private content-grant custody disabled")
    try:
        active, roots, row_mac = _metadata_config(db)
        keys = {k: _derive(v, b"content-aesgcm") for k,v in roots.items()}
        mac = _derive(row_mac, b"content-row-hmac")
        identity = _derive(row_mac, b"content-identity-hmac")
        if (len(set(keys.values())) != len(keys)
            or mac == identity or mac in keys.values()
            or identity in keys.values()):
            raise ValueError()
        return active, keys, mac, identity
    except Exception:
        raise PrivateContentGrantBlocked("Private content keys unavailable") from None


def _identity(key: bytes, *, owner_ref: str, folder_id: str,
              client_id: str) -> tuple[str,str,str]:
    try:
        return _metadata_identities(
            key, owner_ref=owner_ref, folder_id=folder_id, client_id=client_id,
        )
    except Exception:
        raise PrivateContentGrantBlocked("Content scope identities invalid") from None


def _aad(row: OwnerGoogleMetadataGrant) -> bytes:
    return (b"personal-cfo:p4c:drive.readonly:v1:"
        + row.owner_hmac.encode("ascii") + b":"
        + row.folder_hmac.encode("ascii") + b":"
        + row.client_hmac.encode("ascii") + b":"
        + GOOGLE_CONTENT_SCOPE.encode("ascii") + b":"
        + row.key_version.encode("ascii"))


def _tag(key: bytes, row: OwnerGoogleMetadataGrant) -> str:
    raw = json.dumps({
        "owner":row.owner_hmac,"folder":row.folder_hmac,
        "client":row.client_hmac,"key":row.key_version,
        "ciphertext":row.ciphertext,"revision":row.revision,
        "revoked":row.revoked,"updated":row.updated_epoch,
    }, sort_keys=True,separators=(",",":")).encode("ascii")
    return hmac.new(key,b"personal-cfo:p4c:row:v1:"+raw,sha256).hexdigest()


def _verify(key: bytes, row: OwnerGoogleMetadataGrant) -> None:
    if (type(row.owner_hmac) is not str or _HEX.fullmatch(row.owner_hmac) is None
        or type(row.folder_hmac) is not str or _HEX.fullmatch(row.folder_hmac) is None
        or type(row.client_hmac) is not str or _HEX.fullmatch(row.client_hmac) is None
        or not isinstance(row.row_hmac,str)
        or type(row.revision) is not int or row.revision < 1
        or not hmac.compare_digest(row.row_hmac,_tag(key,row))):
        raise PrivateContentGrantBlocked("Content grant authenticity rejected")


def _token(value: str) -> str:
    if (type(value) is not str or not 24 <= len(value) <= 4096
        or any(ord(c) < 33 or ord(c) > 126 for c in value)):
        raise PrivateContentGrantBlocked("Content grant token invalid")
    return value


def _seal(key: bytes, row: OwnerGoogleMetadataGrant, token: str) -> str:
    raw=_token(token).encode("ascii")
    nonce=secrets.token_bytes(12)
    encrypted=AESGCM(key).encrypt(nonce,raw,_aad(row))
    return _PREFIX+base64.urlsafe_b64encode(nonce+encrypted).decode("ascii")


def _open(keys: dict[str,bytes],row: OwnerGoogleMetadataGrant) -> str:
    try:
        if (row.key_version not in keys
            or type(row.ciphertext) is not str
            or not row.ciphertext.startswith(_PREFIX)
            or len(row.ciphertext)>6300):
            raise ValueError()
        blob=base64.b64decode(row.ciphertext[len(_PREFIX):],
                              altchars=b"-_",validate=True)
        if not 28 <= len(blob) <= 4300:
            raise ValueError()
        return _token(AESGCM(keys[row.key_version]).decrypt(
            blob[:12],blob[12:],_aad(row),
        ).decode("ascii"))
    except Exception:
        raise PrivateContentGrantBlocked("Content grant cannot be decrypted") from None


def _row(db: Session, owner_hmac: str):
    return db.get(OwnerGoogleMetadataGrant,owner_hmac,with_for_update=True)


def store_private_content_grant(
    db: Session, *, owner_ref: str, folder_id: str, client_id: str,
    refresh_token: str, verified_granted_scope: str,
    now_epoch: int | None = None,
) -> dict:
    """Never trust the claimed scope unless private provider exchange checked it.

    The caller must have consumed a matching one-use MFA-session PKCE
    attempt, authenticated Google's scope, and verified the pinned owner
    folder. This storage module alone cannot prove those events occurred.
    """
    if verified_granted_scope != GOOGLE_CONTENT_SCOPE:
        raise PrivateContentGrantBlocked("Google content-only consent missing")
    active,keys,mac,index=_config(db)
    owner,folder,client=_identity(
        index,owner_ref=owner_ref,folder_id=folder_id,client_id=client_id)
    _token(refresh_token)
    now=_time(now_epoch)
    try:
        _lock(db,owner)
        row=_row(db,owner)
        if row is None:
            row=OwnerGoogleMetadataGrant(
                owner_hmac=owner, folder_hmac=folder, client_hmac=client,
                ciphertext="",key_version=active,revision=1,revoked=False,
                updated_epoch=now,row_hmac="",
            )
            db.add(row)
        else:
            _verify(mac,row)
            if row.folder_hmac!=folder or row.client_hmac!=client:
                raise PrivateContentGrantBlocked("Content grant bound to another folder")
            row.revision+=1
        row.key_version=active
        row.revoked=False
        row.updated_epoch=now
        row.ciphertext=_seal(keys[active],row,refresh_token)
        row.row_hmac=_tag(mac,row)
        db.commit()
        return {
            "content_readonly_scope":True,
            "separate_content_crypto_namespace":True,
            "existing_metadata_grant_preserved":True,
            "encrypted_content_grant_committed":True,
            "revision":row.revision,
            "google_network_used":False,
            "original_document_bytes_downloaded":False,
            "financial_data_authorized":False,
        }
    except PrivateContentGrantBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateContentGrantBlocked("Content grant not stored") from None


def read_private_content_grant(
    db: Session, *, owner_ref: str, folder_id: str, client_id: str,
) -> str:
    """Opaque plaintext ONLY inside the trusted backend, never HTTP response."""
    _,keys,mac,index=_config(db)
    owner,folder,client=_identity(
        index,owner_ref=owner_ref,folder_id=folder_id,client_id=client_id)
    try:
        row=db.get(OwnerGoogleMetadataGrant,owner)
        if row is None:
            raise PrivateContentGrantBlocked("No approved content grant")
        _verify(mac,row)
        if row.revoked or row.folder_hmac!=folder or row.client_hmac!=client:
            raise PrivateContentGrantBlocked("No approved content grant")
        token=_open(keys,row)
        db.rollback()
        return token
    except PrivateContentGrantBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateContentGrantBlocked("Content grant unavailable") from None


def revoke_private_content_grant(
    db: Session, *, owner_ref: str, folder_id: str, client_id: str,
    now_epoch: int | None = None,
) -> dict:
    """Local revocation without touching metadata OAuth or provider originals."""
    _,_,mac,index=_config(db)
    owner,folder,client=_identity(
        index,owner_ref=owner_ref,folder_id=folder_id,client_id=client_id)
    now=_time(now_epoch)
    try:
        _lock(db,owner)
        row=_row(db,owner)
        if row is None:
            db.rollback()
            return {"content_grant_revoked_locally":True,
                    "provider_revoke_performed":False,"metadata_grant_changed":False}
        _verify(mac,row)
        if row.folder_hmac!=folder or row.client_hmac!=client:
            raise PrivateContentGrantBlocked("Wrong content grant identity")
        row.revoked=True
        row.revision+=1
        row.updated_epoch=now
        # Do not retain an accessible token after local revocation.
        row.ciphertext=_PREFIX+base64.urlsafe_b64encode(
            secrets.token_bytes(28)).decode("ascii")
        row.row_hmac=_tag(mac,row)
        db.commit()
        return {"content_grant_revoked_locally":True,
                "provider_revoke_performed":False,"metadata_grant_changed":False}
    except PrivateContentGrantBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateContentGrantBlocked("Content grant revocation unavailable") from None
