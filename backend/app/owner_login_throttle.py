"""P1G: PostgreSQL-serialized, fixture-only owner MFA login throttle.

This is a PRIVATE, UNMOUNTED integration rehearsal, NOT a public login API or
approved production owner authentication. Identity and keys are fictional.
No real Google credential, financial document, service deployment or
provider access is permitted. A true G2 login requires separate threat audit.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import os
import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .auth_mfa import (
    check_password, claim_synthetic_totp_step, csrf_for_session,
    session_token, token_digest, totp_step,
)
from .cloud_drive_oauth_vault import _config
from .models import OwnerLoginThrottle, OwnerSession

ATTEMPTS = 5
WINDOW_SECONDS = 10 * 60
LOCK_SECONDS = 15 * 60
SESSION_SECONDS = 15 * 60
FAKE_USER = "synthetic-owner"


class OwnerThrottleBlocked(ValueError):
    """The owner could not be authenticated; secrets never enter the error."""


def _identity_key() -> bytes:
    try:
        key = base64.b64decode(
            os.getenv("P1G_FAKE_THROTTLE_KEY", ""), altchars=b"-_", validate=True
        )
    except (UnicodeError, ValueError):
        raise OwnerThrottleBlocked("Synthetic throttle key unavailable") from None
    if len(key) != 32:
        raise OwnerThrottleBlocked("Synthetic throttle key unavailable")
    return key


def _guard(db: Session) -> bytes:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1G_FAKE_LOGIN_THROTTLE_ONLY") != "1"
        or os.getenv("P1F_SYNTHETIC_OWNER_GATEWAY_ONLY") != "1"
        or db.bind is None or db.bind.dialect.name not in {"sqlite", "postgresql"}
        or (db.bind.dialect.name == "sqlite"
            and os.getenv("P1G_SQLITE_TEST_ONLY") != "1")):
        raise OwnerThrottleBlocked("Synthetic owner MFA not authorized")
    try:
        _config(db)
    except Exception:
        raise OwnerThrottleBlocked("Synthetic owner MFA not authorized") from None
    return _identity_key()


def _time(now_epoch: int | None) -> int:
    from time import time
    now = int(time()) if now_epoch is None else now_epoch
    if type(now) is not int or not 1_500_000_000 <= now <= 4_000_000_000:
        raise OwnerThrottleBlocked("Invalid synthetic login clock")
    return now


def _row_lock(db: Session, identity: str) -> None:
    if db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        # The advisory transaction lock serializes FIRST record creation as
        # well as subsequent SELECT FOR UPDATE, across Railway replicas.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:identity))"),
                   {"identity": identity})


def _fail(db: Session, row: OwnerLoginThrottle, now: int):
    if now - row.window_started_epoch >= WINDOW_SECONDS:
        row.window_started_epoch = now
        row.failures = 0
    row.failures += 1
    row.updated_epoch = now
    if row.failures >= ATTEMPTS:
        row.locked_until_epoch = now + LOCK_SECONDS
    db.commit()
    raise OwnerThrottleBlocked("Synthetic owner MFA rejected")


def issue_throttled_fake_owner_session(
    db: Session, *, username: str, password: str, totp_code: str,
    now_epoch: int | None = None,
) -> str:
    """Atomic password+TOTP+throttle+session rehearsal.

    A repeated TOTP code, wrong password/name and wrong OTP all count as a
    persistent failed attempt. Lockout is checked BEFORE expensive scrypt.
    Only one fictional owner identity; never a real browser login route.
    """
    key = _guard(db)
    now = _time(now_epoch)
    if (type(username) is not str or len(username) > 128
        or type(password) is not str or len(password) > 256
        or type(totp_code) is not str or len(totp_code) > 32):
        raise OwnerThrottleBlocked("Synthetic owner MFA rejected")
    identity = hmac.new(
        key, b"personal-cfo:p1g:synthetic-owner-only", sha256
    ).hexdigest()
    try:
        _row_lock(db, identity)
        row = db.scalar(select(OwnerLoginThrottle).where(
            OwnerLoginThrottle.owner_hmac == identity
        ).with_for_update())
        if row is None:
            row = OwnerLoginThrottle(
                owner_hmac=identity, failures=0, window_started_epoch=now,
                locked_until_epoch=0, updated_epoch=now,
            )
            db.add(row)
            db.flush()
        if row.locked_until_epoch > now:
            db.rollback()
            raise OwnerThrottleBlocked("Synthetic owner MFA rejected")
        if row.locked_until_epoch and now >= row.locked_until_epoch:
            row.locked_until_epoch = 0
            row.failures = 0
            row.window_started_epoch = now
        # The user is synthetic and fixed, never accepted from a real owner
        # account, and there is no public route to accept a password.
        stored = os.getenv("P1F_FAKE_OWNER_PASSWORD_SCRYPT", "")
        secret = os.getenv("P1F_FAKE_OWNER_TOTP_SECRET", "")
        password_ok = (
            hmac.compare_digest(username, FAKE_USER)
            and stored.startswith("scrypt-v1$")
            and len(password) >= 16
            and check_password(password, stored)
        )
        step = totp_step(secret, totp_code, now=now) if password_ok else None
        if step is None:
            _fail(db, row, now)
        if not claim_synthetic_totp_step(db, step):
            _fail(db, row, now)
        raw = session_token()
        created = datetime.fromtimestamp(now, timezone.utc)
        db.add(OwnerSession(
            token_sha256=token_digest(raw),
            csrf_sha256=token_digest(csrf_for_session(raw)),
            created_at=created,
            expires_at=created + timedelta(seconds=SESSION_SECONDS),
            revoked=False,
        ))
        row.failures = 0
        row.locked_until_epoch = 0
        row.window_started_epoch = now
        row.updated_epoch = now
        db.commit()
        return raw
    except OwnerThrottleBlocked:
        raise
    except Exception:
        db.rollback()
        raise OwnerThrottleBlocked("Synthetic owner MFA unavailable") from None


def fake_throttle_health(db: Session) -> dict:
    """Privacy-safe index status. Never return login attempts or owner names."""
    _guard(db)
    return {"synthetic_only": True, "durable_multiworker_contract": True,
            "hosted_owner_login_enabled": False,
            "owner_mfa_production_accepted": False,
            "google_drive_connected": False, "real_data_authorized": False}
