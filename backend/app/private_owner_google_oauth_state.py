"""P1R: single-use encrypted PostgreSQL PKCE attempts bound to owner MFA.

This is a real-compatible PRIVATE service component, deliberately unmounted.
Google authorization codes/refresh tokens are NOT exchanged or stored here.
The owner must have a valid authenticated 15-minute P1N session, with CSRF
for authorization start and SameSite=Lax for Google's top-level GET callback.

The attempt is consumed/committed BEFORE any external network exchange.
This module cannot activate the OAuth public route or bypass G2 release gates.
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

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .drive_google_oauth import (
    GOOGLE_METADATA_SCOPE, PERSONAL_CFO_RAILWAY_CALLBACK,
    begin_google_metadata_consent, private_google_configuration,
)
from .models import OwnerPrivateOAuthAttempt
from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, _keys as owner_keys, _owner, _mac as owner_mac,
    _session, _lock, _deny_private_recovery_hold, _now,
)

_STATE = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
_CODE = re.compile(r"^[A-Za-z0-9._~/-]{8,2048}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_PREFIX = "P1R1:"
_TTL = 600
_MAX_OUTSTANDING = 3
_MAX_RETAINED = 256


class PrivateOAuthStateBlocked(ValueError):
    """An OAuth attempt lacks independently approved private authorization."""


@dataclass(frozen=True)
class PrivateClaimedPKCE:
    verifier: str
    metadata_only: bool
    state_consumed_before_external_exchange: bool


def _key(name: str) -> bytes:
    try:
        value = base64.b64decode(os.environ.get(name, ""),
                                 altchars=b"-_", validate=True)
        if len(value) != 32:
            raise ValueError()
        return value
    except (TypeError, ValueError):
        raise PrivateOAuthStateBlocked("Separate private OAuth keys unavailable") from None


def _config(db: Session):
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1R_PRIVATE_OAUTH_STATE_ONLY") != "1"
        or os.getenv("P1R_G2_SESSION_OAUTH_REVIEWED") != "1"
        or os.getenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY") != "1"
        or db.bind is None
        or db.bind.dialect.name not in ("postgresql", "sqlite")
        or (db.bind.dialect.name == "sqlite"
            and os.getenv("P1R_SQLITE_FAKE_TEST_ONLY") != "1")):
        raise PrivateOAuthStateBlocked("Owner session OAuth state is disabled")
    try:
        cfg = private_google_configuration()
        if cfg.redirect_uri != PERSONAL_CFO_RAILWAY_CALLBACK:
            raise ValueError()
        enc, mac, session_mac = owner_keys(db)
        state_enc = _key("P1R_OAUTH_STATE_ENCRYPTION_KEY")
        state_mac = _key("P1R_OAUTH_STATE_HMAC_KEY")
        if len({enc, mac, session_mac, state_enc, state_mac}) != 5:
            raise ValueError()
        return cfg, state_enc, state_mac, mac, session_mac
    except Exception:
        raise PrivateOAuthStateBlocked("Private OAuth owner/keys unavailable") from None


def _tag(key: bytes, domain: str, value: str) -> str:
    return hmac.new(key, ("personal-cfo:p1r:" + domain + "\0" + value).encode("ascii"),
                    sha256).hexdigest()


def _cipher(key: bytes, row: OwnerPrivateOAuthAttempt, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(key).encrypt(
        nonce, raw, ("personal-cfo:p1r:" + row.state_hmac + ":" + row.owner_hmac).encode("ascii"))
    return _PREFIX + base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")


def _open(key: bytes, row: OwnerPrivateOAuthAttempt) -> dict:
    try:
        if (type(row.ciphertext) is not str
            or not row.ciphertext.startswith(_PREFIX)
            or len(row.ciphertext) > 2000):
            raise ValueError()
        blob = base64.b64decode(row.ciphertext[len(_PREFIX):], altchars=b"-_", validate=True)
        if not 28 <= len(blob) <= 1500:
            raise ValueError()
        value = json.loads(AESGCM(key).decrypt(
            blob[:12], blob[12:],
            ("personal-cfo:p1r:" + row.state_hmac + ":" + row.owner_hmac).encode("ascii")))
        if type(value) is not dict:
            raise ValueError()
        return value
    except Exception:
        raise PrivateOAuthStateBlocked("OAuth attempt ciphertext rejected") from None


def _row_mac(mac: bytes, row: OwnerPrivateOAuthAttempt) -> str:
    data = json.dumps({
        "state": row.state_hmac, "owner": row.owner_hmac,
        "session": row.session_hmac, "folder": row.folder_hmac,
        "client": row.client_hmac, "cipher": row.ciphertext,
        "issued": row.issued_epoch, "expires": row.expires_epoch,
        "status": row.status,
    }, sort_keys=True, separators=(",", ":"))
    return _tag(mac, "row", data)


def _verify(mac: bytes, row: OwnerPrivateOAuthAttempt) -> None:
    if (type(row.row_hmac) is not str or _HEX.fullmatch(row.row_hmac) is None
        or not hmac.compare_digest(row.row_hmac, _row_mac(mac, row))
        or row.expires_epoch - row.issued_epoch != _TTL):
        raise PrivateOAuthStateBlocked("OAuth attempt integrity verification failed")


def _owner_session(db: Session, mac: bytes, session_mac: bytes,
                   owner_ref: str, token: str, now: int,
                   *, csrf: str | None = None, mutation: bool = False):
    owner = _owner(mac, owner_ref)
    auth = _session(db, owner, session_mac, token, now,
                    csrf=csrf, mutation=mutation, for_update=True)
    _deny_private_recovery_hold(db, owner)
    return owner, auth


def begin_private_session_google_oauth(
    db: Session, *, owner_ref: str, session_token: str,
    csrf_token: str, now_epoch: int | None = None,
) -> str:
    """Return a Google authorization URL ONLY to a trusted private controller.

    The caller enforces exact TLS, Origin and POST; the URL MUST NOT be logged.
    """
    cfg, enc, mac, owner_key, session_key = _config(db)
    now = _now(now_epoch)
    try:
        _lock(db)
        owner, auth = _owner_session(db, owner_key, session_key, owner_ref,
                                    session_token, now, csrf=csrf_token, mutation=True)
        total = db.scalar(select(func.count()).select_from(OwnerPrivateOAuthAttempt))
        outstanding = db.scalar(select(func.count()).select_from(
            OwnerPrivateOAuthAttempt).where(
                OwnerPrivateOAuthAttempt.owner_hmac == owner,
                OwnerPrivateOAuthAttempt.status == "pending",
                OwnerPrivateOAuthAttempt.expires_epoch > now,
            ))
        if total >= _MAX_RETAINED or outstanding >= _MAX_OUTSTANDING:
            raise PrivateOAuthStateBlocked("Private OAuth start rate limit")
        pending = begin_google_metadata_consent(cfg)
        state_hmac = _tag(mac, "state", pending.state)
        row = OwnerPrivateOAuthAttempt(
            state_hmac=state_hmac, owner_hmac=owner,
            session_hmac=auth.token_hmac,
            folder_hmac=_tag(mac, "folder", cfg.folder_id),
            client_hmac=_tag(mac, "client", cfg.client_id),
            ciphertext="", issued_epoch=now, expires_epoch=now+_TTL,
            status="pending", row_hmac="",
        )
        row.ciphertext = _cipher(enc, row, {
            "verifier": pending.pkce_verifier,
            "client": cfg.client_id,
            "redirect": cfg.redirect_uri,
            "folder_hmac": cfg.folder_hmac,
            "scope": GOOGLE_METADATA_SCOPE,
            "session": auth.token_hmac,
        })
        row.row_hmac = _row_mac(mac, row)
        db.add(row)
        db.commit()
        return pending.authorization_url
    except (PrivateOAuthStateBlocked, PrivateOwnerIdentityBlocked):
        db.rollback()
        raise PrivateOAuthStateBlocked("Private session OAuth start denied") from None
    except Exception:
        db.rollback()
        raise PrivateOAuthStateBlocked("Private session OAuth start failed") from None


def consume_private_session_google_oauth(
    db: Session, *, owner_ref: str, session_token: str,
    state: str, code: str, now_epoch: int | None = None,
) -> PrivateClaimedPKCE:
    """One-time CAS-style commit before Google exchange, including worker races.

    Google's redirect uses GET with Secure HttpOnly SameSite=Lax cookie.
    A trusted controller must reject duplicate query keys and scrub response
    URLs; no raw code/state can be logged in any edge or upstream layer.
    """
    cfg, enc, mac, owner_key, session_key = _config(db)
    now = _now(now_epoch)
    if (type(state) is not str or _STATE.fullmatch(state) is None
        or type(code) is not str or _CODE.fullmatch(code) is None):
        raise PrivateOAuthStateBlocked("Google callback parameters denied")
    state_hmac = _tag(mac, "state", state)
    try:
        _lock(db)
        owner, auth = _owner_session(db, owner_key, session_key,
                                    owner_ref, session_token, now)
        row = db.scalar(select(OwnerPrivateOAuthAttempt).where(
            OwnerPrivateOAuthAttempt.state_hmac == state_hmac).with_for_update())
        if (row is None or row.status != "pending" or now >= row.expires_epoch
            or row.issued_epoch > now+30 or row.owner_hmac != owner
            or row.session_hmac != auth.token_hmac
            or row.folder_hmac != _tag(mac, "folder", cfg.folder_id)
            or row.client_hmac != _tag(mac, "client", cfg.client_id)):
            raise PrivateOAuthStateBlocked("Google callback expired or unbound")
        _verify(mac, row)
        payload = _open(enc, row)
        if (set(payload) != {"verifier", "client", "redirect",
                            "folder_hmac", "scope", "session"}
            or type(payload["verifier"]) is not str
            or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", payload["verifier"])
            or payload["client"] != cfg.client_id
            or payload["redirect"] != cfg.redirect_uri
            or payload["folder_hmac"] != cfg.folder_hmac
            or payload["scope"] != GOOGLE_METADATA_SCOPE
            or payload["session"] != auth.token_hmac):
            raise PrivateOAuthStateBlocked("Google callback scope/PKCE mismatch")
        verifier = payload["verifier"]
        row.status = "claimed"
        row.ciphertext = _cipher(enc, row, {"claimed": True})
        row.row_hmac = _row_mac(mac, row)
        db.commit()
        return PrivateClaimedPKCE(verifier, True, True)
    except (PrivateOAuthStateBlocked, PrivateOwnerIdentityBlocked):
        db.rollback()
        raise PrivateOAuthStateBlocked("Private session OAuth callback denied") from None
    except Exception:
        db.rollback()
        raise PrivateOAuthStateBlocked("Private session OAuth callback failed") from None
