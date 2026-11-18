"""P1N: private owner MFA enrollment/login/session core, NOT a public API.

Unlike synthetic-owner fixtures, this models a genuine single-owner password
and TOTP under dedicated encrypted custody. No real owner credentials may be
used in public CI; no public routes, secret read from staged Railway variables,
recovery bypass, OAuth token exchange or financial source read exist here.

Operational G2 enrollment/key backup/recovery and trusted TLS proxy MUST be
independently accepted before a private server may invoke these functions.
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
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from .auth_mfa import password_hash, check_password, totp_step
from .models import OwnerPrivateIdentity, OwnerPrivateSession

_NAME = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_BASE32 = re.compile(r"^[A-Z2-7]{32,104}$")
_PIN = re.compile(r"^[0-9]{6}$")
_B64 = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_TTL = 15 * 60
_WINDOW = 10 * 60
_LOCK = 15 * 60
_FAILS = 5
_PREFIX = "P1N1:"


class PrivateOwnerIdentityBlocked(ValueError):
    """Owner authentication or its separately reviewed custody was denied."""


@dataclass(frozen=True)
class PrivateOwnerSessionProof:
    cookie_token: str
    csrf_token: str
    expires_epoch: int


def _key(name: str) -> bytes:
    try:
        value = base64.b64decode(os.environ.get(name, ""),
                                 altchars=b"-_", validate=True)
    except (ValueError, UnicodeError):
        raise PrivateOwnerIdentityBlocked("Private identity key unavailable") from None
    if len(value) != 32:
        raise PrivateOwnerIdentityBlocked("Private identity key unavailable")
    return value


def _keys(db: Session) -> tuple[bytes, bytes, bytes]:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1N_PRIVATE_OWNER_AUTH_ONLY") != "1"
        or os.getenv("P1N_G2_OWNER_IDENTITY_REVIEWED") != "1"
        or db.bind is None
        or db.bind.dialect.name not in ("postgresql", "sqlite")
        or (db.bind.dialect.name == "sqlite"
            and os.getenv("P1N_SQLITE_FAKE_TEST_ONLY") != "1")):
        raise PrivateOwnerIdentityBlocked("Production owner identity is not enabled")
    keys=tuple(_key(key) for key in (
        "P1N_OWNER_ENCRYPTION_KEY", "P1N_OWNER_IDENTITY_HMAC_KEY",
        "P1N_OWNER_SESSION_HMAC_KEY",
    ))
    if len(set(keys)) != 3:
        raise PrivateOwnerIdentityBlocked("Separate owner key domains required")
    return keys


def _owner(mac: bytes, owner_ref: str) -> str:
    if type(owner_ref) is not str or _NAME.fullmatch(owner_ref) is None:
        raise PrivateOwnerIdentityBlocked("Owner identity is invalid")
    return hmac.new(mac, b"personal-cfo:p1n:owner\0"+owner_ref.encode("ascii"),
                    sha256).hexdigest()


def _mac(key: bytes, domain: bytes, raw: str) -> str:
    return hmac.new(key, b"personal-cfo:p1n:" + domain + b"\0"
                    + raw.encode("ascii"), sha256).hexdigest()


def _now(epoch: int | None) -> int:
    value=int(time.time()) if epoch is None else epoch
    if type(value) is not int or not 1_500_000_000 <= value <= 4_000_000_000:
        raise PrivateOwnerIdentityBlocked("Owner authentication clock unavailable")
    return value


def _identity_mac(key: bytes, row: OwnerPrivateIdentity) -> str:
    raw=json.dumps({
        "owner_hmac":row.owner_hmac,
        "password_scrypt":row.password_scrypt,
        "totp_cipher":row.totp_cipher,
        "last_step":row.last_totp_step,
        "failures":row.failures,
        "window_started":row.window_started_epoch,
        "locked_until":row.locked_until_epoch,
        "revision":row.revision,
    },separators=(",",":"),sort_keys=True).encode("ascii")
    return hmac.new(key,b"personal-cfo:p1n:identity-row\0"+raw,sha256).hexdigest()


def _verify_identity(key: bytes, row: OwnerPrivateIdentity) -> None:
    if (type(row.owner_hmac) is not str or _HEX.fullmatch(row.owner_hmac) is None
        or not 0 <= row.failures <= 100
        or row.revision < 1
        or type(row.row_hmac) is not str
        or not hmac.compare_digest(_identity_mac(key,row),row.row_hmac)):
        raise PrivateOwnerIdentityBlocked("Owner identity integrity failed")


def _seal(key: bytes, owner: str, secret: str) -> str:
    if type(secret) is not str or _BASE32.fullmatch(secret) is None:
        raise PrivateOwnerIdentityBlocked("Invalid private TOTP setup")
    try:
        raw=base64.b32decode(secret,casefold=False)
    except (ValueError, UnicodeError):
        raise PrivateOwnerIdentityBlocked("Invalid private TOTP setup") from None
    if not 20 <= len(raw) <= 64:
        raise PrivateOwnerIdentityBlocked("Invalid private TOTP setup")
    nonce=secrets.token_bytes(12)
    value=AESGCM(key).encrypt(nonce, secret.encode("ascii"),
                             ("personal-cfo:p1n:totp:"+owner).encode("ascii"))
    return _PREFIX+base64.urlsafe_b64encode(nonce+value).decode("ascii")


def _unseal(key: bytes, row: OwnerPrivateIdentity) -> str:
    try:
        if (type(row.totp_cipher) is not str
            or not row.totp_cipher.startswith(_PREFIX)
            or len(row.totp_cipher)>240):
            raise ValueError()
        blob=base64.b64decode(row.totp_cipher[len(_PREFIX):],
                              altchars=b"-_",validate=True)
        if not 28 <= len(blob) <= 180:
            raise ValueError()
        result=AESGCM(key).decrypt(
            blob[:12],blob[12:],
            ("personal-cfo:p1n:totp:"+row.owner_hmac).encode("ascii")
        ).decode("ascii")
        if _BASE32.fullmatch(result) is None:
            raise ValueError()
        return result
    except Exception:
        raise PrivateOwnerIdentityBlocked("Encrypted owner MFA unavailable") from None


def _lock(db: Session) -> None:
    if db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext('personal-cfo:p1n:one-owner'))"))


def _row(db: Session) -> OwnerPrivateIdentity | None:
    return db.scalar(select(OwnerPrivateIdentity).where(
        OwnerPrivateIdentity.singleton_id == 1).with_for_update())


def enroll_private_owner(
    db: Session, *, owner_ref: str, password: str, totp_secret_base32: str,
    now_epoch: int | None=None, verified_offline_bootstrap: bool=False,
) -> dict:
    """One irreversible initial enrollment; no web onboarding endpoint.

    Caller must verify offline owner authority and present an approved secure
    MFA setup channel; a boolean alone is insufficient without default-off
    private G2 environment keys and a dedicated database role.
    """
    enc, mac, _ = _keys(db)
    if verified_offline_bootstrap is not True:
        raise PrivateOwnerIdentityBlocked("Independently verified owner enrollment required")
    owner=_owner(mac,owner_ref)
    now=_now(now_epoch)
    if type(password) is not str or not 16 <= len(password) <= 256:
        raise PrivateOwnerIdentityBlocked("Approved owner password length required")
    sealed=_seal(enc,owner,totp_secret_base32)
    hashed=password_hash(password)
    try:
        _lock(db)
        if _row(db) is not None:
            raise PrivateOwnerIdentityBlocked("A private owner is already enrolled")
        row=OwnerPrivateIdentity(
            singleton_id=1,owner_hmac=owner,password_scrypt=hashed,
            totp_cipher=sealed,last_totp_step=-1,failures=0,
            window_started_epoch=now,locked_until_epoch=0,revision=1,row_hmac="",
        )
        row.row_hmac=_identity_mac(mac,row)
        db.add(row)
        db.commit()
        return {
            "private_metadata_owner_enrolled":True,
            "owner_password_stored_in_plaintext":False,
            "totp_secret_stored_in_plaintext":False,
            "recovery_independently_accepted":False,
            "public_login_route_enabled":False,
            "real_google_connection_established":False,
            "real_finance_authorized":False,
        }
    except PrivateOwnerIdentityBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateOwnerIdentityBlocked("Private owner enrollment failed") from None


def _failed(db: Session,row: OwnerPrivateIdentity,mac: bytes,now: int) -> None:
    if now - row.window_started_epoch >= _WINDOW:
        row.window_started_epoch=now
        row.failures=0
    row.failures+=1
    if row.failures>=_FAILS:
        row.locked_until_epoch=now+_LOCK
    row.revision+=1
    row.row_hmac=_identity_mac(mac,row)
    db.commit()
    raise PrivateOwnerIdentityBlocked("Owner MFA rejected")


def _deny_private_recovery_hold(db: Session, owner: str) -> None:
    # The new recovery record is independently encrypted and authenticated.
    # Any absent recovery key, tampered audit or pending redemption FAILS CLOSED.
    from .models import OwnerPrivateRecoveryState
    if db.get(OwnerPrivateRecoveryState,owner) is None:
        return
    from .private_owner_recovery import (
        PrivateOwnerRecoveryBlocked,private_recovery_hold_active,
    )
    try:
        if private_recovery_hold_active(db,owner_hmac=owner):
            raise PrivateOwnerIdentityBlocked("Owner MFA recovery is pending")
    except PrivateOwnerRecoveryBlocked:
        raise PrivateOwnerIdentityBlocked("Owner MFA recovery attestation unavailable") from None


def issue_private_owner_session(
    db: Session, *, owner_ref: str, password: str, totp_code: str,
    now_epoch: int | None=None,
) -> PrivateOwnerSessionProof:
    """Atomic cross-worker password+TOTP+lockout+one-time step+cookie mint."""
    enc,mac,session_mac=_keys(db)
    owner=_owner(mac,owner_ref)
    now=_now(now_epoch)
    if (type(password) is not str or len(password)>256
        or type(totp_code) is not str or _PIN.fullmatch(totp_code) is None):
        raise PrivateOwnerIdentityBlocked("Owner MFA rejected")
    try:
        _lock(db)
        row=_row(db)
        if row is None or row.owner_hmac != owner:
            raise PrivateOwnerIdentityBlocked("Owner MFA rejected")
        _verify_identity(mac,row)
        _deny_private_recovery_hold(db,owner)
        if row.locked_until_epoch>now:
            raise PrivateOwnerIdentityBlocked("Owner MFA rejected")
        if row.locked_until_epoch and now>=row.locked_until_epoch:
            row.locked_until_epoch=0
            row.failures=0
            row.window_started_epoch=now
        if not check_password(password,row.password_scrypt):
            _failed(db,row,mac,now)
        secret=_unseal(enc,row)
        step=totp_step(secret,totp_code,now=now)
        if step is None or step<=row.last_totp_step:
            _failed(db,row,mac,now)
        raw=secrets.token_urlsafe(36)
        csrf=secrets.token_urlsafe(36)
        created=OwnerPrivateSession(
            token_hmac=_mac(session_mac,b"session",raw),owner_hmac=owner,
            csrf_hmac=_mac(session_mac,b"csrf",csrf),issued_epoch=now,
            expires_epoch=now+_TTL,revoked=False,
        )
        db.add(created)
        row.last_totp_step=step
        row.failures=0
        row.locked_until_epoch=0
        row.window_started_epoch=now
        row.revision+=1
        row.row_hmac=_identity_mac(mac,row)
        db.commit()
        return PrivateOwnerSessionProof(raw,csrf,now+_TTL)
    except PrivateOwnerIdentityBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateOwnerIdentityBlocked("Owner MFA authentication failed") from None


def _session(db: Session,owner: str, session_key: bytes, token: str,
             now: int, *, csrf: str | None=None, mutation: bool=False,
             for_update: bool=False) -> OwnerPrivateSession:
    if type(token) is not str or _B64.fullmatch(token) is None:
        raise PrivateOwnerIdentityBlocked("Owner session required")
    q=select(OwnerPrivateSession).where(
        OwnerPrivateSession.token_hmac==_mac(session_key,b"session",token))
    if for_update:
        q=q.with_for_update()
    row=db.scalar(q)
    if (row is None or row.owner_hmac!=owner or row.revoked
        or row.issued_epoch>now+30
        or row.expires_epoch<=now or row.expires_epoch-row.issued_epoch>_TTL):
        raise PrivateOwnerIdentityBlocked("Owner session required")
    if mutation and (type(csrf) is not str or _B64.fullmatch(csrf) is None
                     or not hmac.compare_digest(
                         row.csrf_hmac,_mac(session_key,b"csrf",csrf))):
        raise PrivateOwnerIdentityBlocked("Owner mutation CSRF denied")
    return row


def verify_private_owner_session(
    db: Session, *, owner_ref: str, token: str,
    csrf: str | None=None, mutation: bool=False,
    now_epoch: int | None=None,
) -> dict:
    """Private-only session verification; no HTTP cookie or proxy trust here."""
    _,mac,session_mac=_keys(db)
    owner=_owner(mac,owner_ref)
    now=_now(now_epoch)
    try:
        _session(db,owner,session_mac,token,now,csrf=csrf,mutation=mutation)
        _deny_private_recovery_hold(db,owner)
        db.rollback()
        return {"private_owner_mfa_session_valid":True,
                "google_consent_authorized_by_session_alone":False,
                "public_oauth_callback_enabled":False}
    except PrivateOwnerIdentityBlocked:
        db.rollback()
        raise



def renew_private_owner_session_csrf(
    db: Session, *, owner_ref: str, token: str,
    now_epoch: int | None = None,
) -> dict:
    """Reissue a session CSRF proof after OAuth's full-page round trip.

    A Secure HttpOnly SameSite=Lax session cookie survives Google's redirect,
    but the existing nonpersistent browser CSRF proof is lost on navigation.
    Reissue a *different* proof only after verifying that cookie, under the
    same persistent SQL advisory lock and recovery hold. A cross-site caller
    cannot read the same-origin no-store JSON response, and no CSRF proof is
    placed in a cookie, URL, log or localStorage.
    """
    _, mac, session_mac = _keys(db)
    owner = _owner(mac, owner_ref)
    now = _now(now_epoch)
    try:
        _lock(db)
        row = _session(db, owner, session_mac, token, now, for_update=True)
        _deny_private_recovery_hold(db, owner)
        csrf = secrets.token_urlsafe(36)
        row.csrf_hmac = _mac(session_mac, b"csrf", csrf)
        db.commit()
        return {"private_owner_mfa_session_valid": True,
                "csrf_token": csrf,
                "google_consent_authorized_by_session_alone": False}
    except PrivateOwnerIdentityBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateOwnerIdentityBlocked(
            "Private session CSRF reissue unavailable") from None


def revoke_private_owner_session(
    db: Session, *, owner_ref: str, token: str, csrf: str,
    now_epoch: int | None=None,
) -> dict:
    _,mac,session_mac=_keys(db)
    owner=_owner(mac,owner_ref)
    now=_now(now_epoch)
    try:
        _lock(db)
        row=_session(db,owner,session_mac,token,now,csrf=csrf,
                     mutation=True,for_update=True)
        row.revoked=True
        db.commit()
        return {"owner_session_revoked":True,
                "google_provider_grant_revoked":False}
    except PrivateOwnerIdentityBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateOwnerIdentityBlocked("Owner session could not be revoked") from None


def inspect_private_recovery_availability() -> dict:
    """Fail-closed: recovery enrollment/reset requires separate reviewed work."""
    return {"real_mfa_recovery_available":False,
            "owner_lost_device_self_service_enabled":False,
            "authenticator_reset_permitted":False,
            "operator_recovery_review_required":True,
            "production_oauth_activation_approved":False}
