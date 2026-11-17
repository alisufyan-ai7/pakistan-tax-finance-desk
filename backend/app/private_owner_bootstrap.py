"""P1W: one-owner atomic first enrollment with one-time recovery codes.

PRIVATE OPERATOR ceremony only. The caller must run inside a reviewed,
interactive administrative channel (never the public Railway preview). An
operator proof is *not* a second app user or a staff role; it is a separate
off-device Ed25519 key the one owner keeps for lost-phone recovery.

All writes succeed in a single transaction: no enrolled owner without a
one-time recovery kit. A valid replacement-device signing public key must
already be configured, but its private half MUST NOT be on the application.
No source data, provider grant or private HTTP endpoint is touched.
"""
from __future__ import annotations

import base64
import hmac
import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth_mfa import password_hash, totp_step
from .models import (
    OwnerPrivateIdentity, OwnerPrivateRecoveryState,
    OwnerPrivateRecoveryAudit, OwnerPrivateSession,
)
from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, _keys as owner_keys,
    _owner, _now, _row, _lock, _seal as seal_totp, _identity_mac,
)
from .private_owner_recovery import (
    PrivateOwnerRecoveryBlocked, _config as recovery_config,
    _DEFAULT_CODES, _TTL, _tag, _seal as seal_recovery,
    _row_mac as recovery_row_mac, _append as append_recovery,
)
from .private_owner_reenrollment import (
    PrivateOwnerReenrollmentBlocked, _public_key as require_offline_public_key,
)


class PrivateOwnerBootstrapBlocked(ValueError):
    """First private owner identity enrollment was denied."""


def enroll_single_owner_with_recovery(
    db: Session, *, owner_ref: str, password: str,
    totp_secret_base32: str, confirmed_totp_code: str,
    independently_verified_admin_session: bool = False,
    now_epoch: int | None = None,
) -> tuple[dict, tuple[str, ...]]:
    """Atomically enroll exactly one owner and return a recovery kit ONCE.

    The API receives only the confirmation code, never QR images or a browser
    recovery secret. The interactive caller must generate the TOTP seed with
    a cryptographic RNG and show it only over a private attended terminal.
    """
    if (os.getenv("P1W_ATOMIC_OWNER_BOOTSTRAP_ONLY") != "1"
        or os.getenv("P1W_G2_TERMINAL_CUSTODY_REVIEWED") != "1"
        or independently_verified_admin_session is not True):
        raise PrivateOwnerBootstrapBlocked("Owner's private terminal proof required")
    try:
        owner_enc, owner_mac, _, rec_enc, rec_mac = recovery_config(db)
        require_offline_public_key(db)
        if (type(password) is not str or not 16 <= len(password) <= 256
            or type(totp_secret_base32) is not str
            or type(confirmed_totp_code) is not str):
            raise PrivateOwnerBootstrapBlocked("Invalid owner enrollment proof")
        owner = _owner(owner_mac, owner_ref)
        now = _now(now_epoch)
        verified_step = totp_step(
            totp_secret_base32, confirmed_totp_code, now=now)
        if verified_step is None:
            raise PrivateOwnerBootstrapBlocked("New authenticator proof rejected")
        sealed = seal_totp(owner_enc, owner, totp_secret_base32)
        hashed = password_hash(password)
        # 8 * 160-bit one-time codes. Persist only independently keyed HMACs,
        # never plaintext recovery codes, as in the normal P1P issue path.
        raw = [base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
               for _ in range(_DEFAULT_CODES)]
        codes = tuple("-".join(value[i:i+4] for i in range(0, 32, 4))
                      for value in raw)
        tags = [_tag(rec_mac, "code", owner+":"+value) for value in raw]
        if len(set(tags)) != len(tags):
            raise PrivateOwnerBootstrapBlocked("Recovery code generation failed")
        bundle = {"issued": now, "code_hmacs": tags, "used_hmacs": []}
        try:
            _lock(db)
            if (_row(db) is not None
                or db.scalar(select(OwnerPrivateRecoveryState.owner_hmac).limit(1)) is not None
                or db.scalar(select(OwnerPrivateSession.token_hmac).limit(1)) is not None
                or db.scalar(select(OwnerPrivateRecoveryAudit.event_hmac).limit(1)) is not None):
                raise PrivateOwnerBootstrapBlocked("One owner already exists or storage is inconsistent")
            identity = OwnerPrivateIdentity(
                singleton_id=1, owner_hmac=owner,
                password_scrypt=hashed, totp_cipher=sealed,
                last_totp_step=verified_step, failures=0,
                window_started_epoch=now, locked_until_epoch=0,
                revision=1, row_hmac="",
            )
            identity.row_hmac = _identity_mac(owner_mac, identity)
            state = OwnerPrivateRecoveryState(
                owner_hmac=owner, revision=1, issued_epoch=now,
                expires_epoch=now+_TTL, pending=False,
                ciphertext=seal_recovery(rec_enc, owner, bundle), row_hmac="",
            )
            state.row_hmac = recovery_row_mac(rec_mac, state)
            db.add(identity)
            db.add(state)
            append_recovery(db, rec_mac, state, "ISSUED", "0"*64, now)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return ({
            "single_owner_enrolled": True,
            "owner_role": "owner",
            "human_user_count": 1,
            "recovery_codes_issued": len(codes),
            "recovery_kit_created_in_same_transaction": True,
            "operator_private_key_held_by_server": False,
            "password_persisted_plaintext": False,
            "totp_seed_persisted_plaintext": False,
            "recovery_codes_persisted_plaintext": False,
            "session_issued": False,
            "google_consent_established": False,
            "live_ingress_enabled": False,
            "real_financial_data_authorized": False,
        }, codes)
    except (PrivateOwnerBootstrapBlocked, PrivateOwnerIdentityBlocked,
            PrivateOwnerRecoveryBlocked, PrivateOwnerReenrollmentBlocked):
        db.rollback()
        raise PrivateOwnerBootstrapBlocked("Private one-owner enrollment denied") from None
    except Exception:
        db.rollback()
        raise PrivateOwnerBootstrapBlocked("Private one-owner enrollment failed") from None
