"""P1E: separately keyed, durable *synthetic-only* cloud OAuth custody.

A transactional multi-worker PostgreSQL design rehearsal, not live Google OAuth.
It NEVER accepts an authentic Google client/folder/refresh token. It never
opens a browser route, contacts Google, deploys keys, or authorizes real records.
The public Railway preview must not import this module.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
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

from .drive_google_oauth import (
    DriveOAuthConfig, PendingGoogleConsent, GOOGLE_METADATA_SCOPE,
    PERSONAL_CFO_RAILWAY_CALLBACK, private_google_configuration,
)
from .models import DriveCloudOAuthAttempt, DriveCloudOAuthGrant

_STATE_RE = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
_VERIFIER_RE = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
_PREFIX = "CFOC1:"
_TTL_SECONDS = 600
_MAX_PENDING = 8
_FAKE_REFRESH_PREFIX = "SYNTHETIC_FAKE_REFRESH_"


class CloudOAuthCustodyBlocked(ValueError):
    """Refuse unsafe, missing, expired, replayed or tampered custody."""


@dataclass(frozen=True)
class CloudClaimedAttempt:
    pkce_verifier: str
    folder_hmac: str
    client_id: str
    redirect_uri: str


def _key(name: str) -> bytes:
    try:
        raw = base64.b64decode(
            os.environ.get(name, ""), altchars=b"-_", validate=True
        )
    except (ValueError, UnicodeError):
        raise CloudOAuthCustodyBlocked("Private cloud custody keys unavailable") from None
    if len(raw) != 32:
        raise CloudOAuthCustodyBlocked("Private cloud custody keys unavailable")
    return raw


def _config(db: Session) -> tuple[DriveOAuthConfig, bytes, bytes]:
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY") != "1"
        or os.getenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY") != "1"
        or os.getenv("P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY") != "1"):
        raise CloudOAuthCustodyBlocked("Cloud OAuth custody not enabled")
    if db.bind is None or db.bind.dialect.name not in ("postgresql", "sqlite"):
        raise CloudOAuthCustodyBlocked("Approved transactional database required")
    if db.bind.dialect.name == "sqlite" and os.getenv("P1E_SQLITE_TEST_ONLY") != "1":
        raise CloudOAuthCustodyBlocked("SQLite allowed only in isolated tests")
    try:
        cfg = private_google_configuration()
    except Exception:
        raise CloudOAuthCustodyBlocked("Private Google config is not accepted") from None
    # Crucially: a deployed copy of this rehearsal must NEVER accept a real
    # owner OAuth credential, even if someone accidentally sets its feature flag.
    if (cfg.redirect_uri != PERSONAL_CFO_RAILWAY_CALLBACK
        or not cfg.folder_id.startswith("SYNTHETIC_")
        or not cfg.client_id.startswith("000000000000-syntheticdev.")):
        raise CloudOAuthCustodyBlocked("Only fictional OAuth fixtures are allowed")
    enc = _key("P1E_FAKE_CLOUD_VAULT_KEY")
    mac = _key("P1E_FAKE_CLOUD_INDEX_KEY")
    if hmac.compare_digest(enc, mac):
        raise CloudOAuthCustodyBlocked("Use separately isolated fake custody keys")
    return cfg, enc, mac


def _time(now_epoch: int | None) -> int:
    now = int(time.time()) if now_epoch is None else now_epoch
    if type(now) is not int or not 1_500_000_000 <= now <= 4_000_000_000:
        raise CloudOAuthCustodyBlocked("Invalid cloud consent clock")
    return now


def _tag(key: bytes, state: str) -> str:
    return hmac.new(key, ("personal-cfo:p1e:state:" + state).encode(), sha256).hexdigest()


def _seal(key: bytes, purpose: str, record: dict) -> str:
    nonce = secrets.token_bytes(12)
    raw = json.dumps(record, separators=(",", ":"), sort_keys=True).encode()
    cipher = AESGCM(key).encrypt(nonce, raw, ("p1e-cloud-oauth:" + purpose).encode())
    return _PREFIX + base64.urlsafe_b64encode(nonce + cipher).decode("ascii")


def _unseal(key: bytes, purpose: str, value: str) -> dict:
    try:
        if not isinstance(value, str) or not value.startswith(_PREFIX):
            raise ValueError()
        blob = base64.b64decode(value[len(_PREFIX):], altchars=b"-_", validate=True)
        if len(blob) < 28:
            raise ValueError()
        plain = AESGCM(key).decrypt(
            blob[:12], blob[12:], ("p1e-cloud-oauth:" + purpose).encode()
        )
        result = json.loads(plain)
        if type(result) is not dict:
            raise ValueError()
        return result
    except Exception:
        raise CloudOAuthCustodyBlocked("Sealed cloud state failed authentication") from None


def _lock(db: Session, folder_hmac: str) -> None:
    if db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        # Also serializes first insert, when SELECT FOR UPDATE has no row.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:scope))"),
                   {"scope": folder_hmac})


def remember_fake_cloud_attempt(
    db: Session, *, pending: PendingGoogleConsent, now_epoch: int | None = None,
) -> dict:
    cfg, key, mac = _config(db)
    now = _time(now_epoch)
    if (not isinstance(pending, PendingGoogleConsent)
        or not isinstance(pending.state, str)
        or not _STATE_RE.fullmatch(pending.state)
        or not isinstance(pending.pkce_verifier, str)
        or not _VERIFIER_RE.fullmatch(pending.pkce_verifier)
        or not hmac.compare_digest(pending.folder_hmac, cfg.folder_hmac)):
        raise CloudOAuthCustodyBlocked("Untrusted fake cloud OAuth attempt")
    state_hmac = _tag(mac, pending.state)
    value = {
        "pkce_verifier": pending.pkce_verifier,
        "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri,
        "folder_hmac": cfg.folder_hmac,
    }
    try:
        _lock(db, cfg.folder_hmac)
        db.query(DriveCloudOAuthAttempt).filter(
            DriveCloudOAuthAttempt.expires_epoch <= now
        ).delete(synchronize_session=False)
        # Serialized count prevents unbounded pending attempts across workers.
        count = db.query(DriveCloudOAuthAttempt).filter_by(
            folder_hmac=cfg.folder_hmac, status="pending"
        ).count()
        if count >= _MAX_PENDING:
            raise CloudOAuthCustodyBlocked("Too many pending fake cloud consents")
        db.add(DriveCloudOAuthAttempt(
            state_hmac=state_hmac, folder_hmac=cfg.folder_hmac,
            payload_cipher=_seal(key, "attempt:" + state_hmac, value),
            expires_epoch=now + _TTL_SECONDS, status="pending",
        ))
        db.commit()
        return {"fake_attempt_sealed": True, "expires_in_seconds": _TTL_SECONDS,
                "live_google_connection": False}
    except Exception as exc:
        db.rollback()
        if isinstance(exc, CloudOAuthCustodyBlocked):
            raise
        raise CloudOAuthCustodyBlocked("Fake cloud consent could not be persisted") from None


def claim_fake_cloud_attempt(
    db: Session, *, state: str, now_epoch: int | None = None,
) -> CloudClaimedAttempt:
    cfg, key, mac = _config(db)
    now = _time(now_epoch)
    if not isinstance(state, str) or not _STATE_RE.fullmatch(state):
        raise CloudOAuthCustodyBlocked("Expired, invalid or replayed cloud consent")
    state_hmac = _tag(mac, state)
    try:
        _lock(db, cfg.folder_hmac)
        row = db.scalar(select(DriveCloudOAuthAttempt).where(
            DriveCloudOAuthAttempt.state_hmac == state_hmac,
            DriveCloudOAuthAttempt.folder_hmac == cfg.folder_hmac,
        ).with_for_update())
        if row is None or row.status != "pending" or now >= row.expires_epoch:
            raise CloudOAuthCustodyBlocked("Expired, invalid or replayed cloud consent")
        value = _unseal(key, "attempt:" + state_hmac, row.payload_cipher)
        if (set(value) != {"pkce_verifier", "client_id", "redirect_uri", "folder_hmac"}
            or value["client_id"] != cfg.client_id
            or value["redirect_uri"] != cfg.redirect_uri
            or value["folder_hmac"] != cfg.folder_hmac
            or not isinstance(value["pkce_verifier"], str)
            or not _VERIFIER_RE.fullmatch(value["pkce_verifier"])):
            raise CloudOAuthCustodyBlocked("Cloud consent bound to another identity")
        verifier = value["pkce_verifier"]
        row.status = "claimed"
        row.payload_cipher = _seal(key, "attempt:" + state_hmac, {"claimed": True})
        db.commit()
        return CloudClaimedAttempt(verifier, cfg.folder_hmac, cfg.client_id, cfg.redirect_uri)
    except Exception as exc:
        db.rollback()
        if isinstance(exc, CloudOAuthCustodyBlocked):
            raise
        raise CloudOAuthCustodyBlocked("Fake cloud consent could not be claimed") from None


def seal_fake_cloud_grant(
    db: Session, *, refresh_token: str, now_epoch: int | None = None,
) -> None:
    cfg, key, _ = _config(db)
    now = _time(now_epoch)
    if (not isinstance(refresh_token, str)
        or not refresh_token.startswith(_FAKE_REFRESH_PREFIX)
        or not 32 <= len(refresh_token) <= 256
        or any(c in refresh_token for c in "\r\n\x00")):
        raise CloudOAuthCustodyBlocked("Genuine Google grants are prohibited in this rehearsal")
    record = {"client_id": cfg.client_id, "folder_hmac": cfg.folder_hmac,
              "scope": GOOGLE_METADATA_SCOPE, "refresh_token": refresh_token}
    try:
        _lock(db, cfg.folder_hmac)
        row = db.get(DriveCloudOAuthGrant, cfg.folder_hmac)
        cipher = _seal(key, "grant:" + cfg.folder_hmac, record)
        if row is None:
            db.add(DriveCloudOAuthGrant(
                folder_hmac=cfg.folder_hmac, payload_cipher=cipher,
                granted_epoch=now, revoked=False,
            ))
        else:
            row.payload_cipher, row.granted_epoch, row.revoked = cipher, now, False
        db.commit()
    except Exception:
        db.rollback()
        raise CloudOAuthCustodyBlocked("Fake cloud grant was not stored") from None


def read_fake_cloud_grant(db: Session) -> str:
    cfg, key, _ = _config(db)
    row = db.get(DriveCloudOAuthGrant, cfg.folder_hmac)
    if row is None or row.revoked:
        raise CloudOAuthCustodyBlocked("No active fake cloud grant")
    payload = _unseal(key, "grant:" + cfg.folder_hmac, row.payload_cipher)
    if (set(payload) != {"client_id", "folder_hmac", "scope", "refresh_token"}
        or payload["client_id"] != cfg.client_id
        or payload["folder_hmac"] != cfg.folder_hmac
        or payload["scope"] != GOOGLE_METADATA_SCOPE
        or not isinstance(payload["refresh_token"], str)
        or not payload["refresh_token"].startswith(_FAKE_REFRESH_PREFIX)):
        raise CloudOAuthCustodyBlocked("Fake cloud grant identity or scope mismatched")
    return payload["refresh_token"]


def disconnect_fake_cloud_grant(db: Session) -> None:
    cfg, key, _ = _config(db)
    try:
        _lock(db, cfg.folder_hmac)
        row = db.get(DriveCloudOAuthGrant, cfg.folder_hmac)
        if row is not None:
            row.payload_cipher = _seal(key, "grant:" + cfg.folder_hmac, {"revoked": True})
            row.revoked = True
        db.commit()
    except Exception:
        db.rollback()
        raise CloudOAuthCustodyBlocked("Fake cloud disconnect failed") from None


def cloud_connection_status() -> dict:
    """Never report a production Google connection from synthetic custody."""
    return {"google_drive_app_connected": False,
            "cloud_oauth_handler_live": False,
            "scheduled_real_drive_sync_enabled": False,
            "real_document_import_enabled": False,
            "financial_reconciliation_enabled": False}
