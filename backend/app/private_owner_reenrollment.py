"""P1Q: offline-signed, single-use replacement TOTP enrollment after recovery hold.

This is a PRIVATE operator workflow, not a public API or owner self-service.
The recovery code and password were verified before the hold was created.
A separately held Ed25519 signing key must authorize the precise replacement
TOTP seed and current authenticated recovery-state revision. The application
receives ONLY the operator public key. It cannot issue its own authorization.

No real owner credentials, Google grant, or source document is used by CI.
No private route mounts this workflow; G2 operational review remains required.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import hmac
import json
import os
import re

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .auth_mfa import check_password, totp_step
from .models import (
    OwnerGoogleMetadataGrant, OwnerPrivateRecoveryState, OwnerPrivateSession,
)
from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, _keys as owner_keys, _owner, _lock, _row,
    _verify_identity, _identity_mac, _seal as seal_totp, _unseal as unseal_totp,
    _now, _PIN,
)
from .private_owner_recovery import (
    PrivateOwnerRecoveryBlocked, _config as recovery_config,
    _verify as verify_recovery, _seal as seal_recovery,
    _row_mac as recovery_row_mac, _append as append_recovery,
)

_ATTESTATION_DOMAIN = b"personal-cfo:p1q:offline-reenrollment:v1\0"
_NONCE = re.compile(r"^[A-Za-z0-9_-]{24,96}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_B64 = re.compile(r"^[A-Za-z0-9_-]{80,120}={0,2}$")
_FIELDS = frozenset({
    "owner_hmac", "recovery_revision", "recovery_row_hmac",
    "new_totp_digest", "issued_epoch", "expires_epoch", "nonce",
})


class PrivateOwnerReenrollmentBlocked(ValueError):
    """Independent operator authorization or owner MFA recovery was denied."""


def _public_key(db: Session) -> Ed25519PublicKey:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1Q_PRIVATE_OFFLINE_REENROLL_ONLY") != "1"
        or os.getenv("P1Q_G2_OFFLINE_PROOF_REVIEWED") != "1"
        or db.bind is None):
        raise PrivateOwnerReenrollmentBlocked("Owner offline re-enrollment disabled")
    encoded = os.getenv("P1Q_OPERATOR_PUBLIC_KEY", "")
    try:
        raw = base64.b64decode(encoded, altchars=b"-_", validate=True)
        if len(raw) != 32:
            raise ValueError()
        return Ed25519PublicKey.from_public_bytes(raw)
    except (ValueError, TypeError):
        raise PrivateOwnerReenrollmentBlocked(
            "Independent operator verification key unavailable") from None


def _signed_body(value: dict) -> bytes:
    return _ATTESTATION_DOMAIN + json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _verify_attestation(
    key: Ed25519PublicKey, *, attestation: str, owner: str, state: OwnerPrivateRecoveryState,
    new_totp_secret: str, now: int,
) -> None:
    try:
        if type(attestation) is not str or not 100 <= len(attestation) <= 1800:
            raise ValueError()
        document = json.loads(attestation)
        if type(document) is not dict or set(document) != _FIELDS | {"signature"}:
            raise ValueError()
        body = {field: document[field] for field in _FIELDS}
        if (type(document["owner_hmac"]) is not str
            or document["owner_hmac"] != owner
            or type(document["recovery_revision"]) is not int
            or document["recovery_revision"] != state.revision
            or type(document["recovery_row_hmac"]) is not str
            or not hmac.compare_digest(document["recovery_row_hmac"], state.row_hmac)
            or type(document["new_totp_digest"]) is not str
            or _HEX.fullmatch(document["new_totp_digest"]) is None
            or not hmac.compare_digest(
                document["new_totp_digest"],
                sha256(b"personal-cfo:p1q:new-totp\0" + new_totp_secret.encode("ascii")).hexdigest())
            or type(document["issued_epoch"]) is not int
            or type(document["expires_epoch"]) is not int
            or not document["issued_epoch"] - 30 <= now <= document["expires_epoch"]
            or not 1 <= document["expires_epoch"] - document["issued_epoch"] <= 600
            or type(document["nonce"]) is not str
            or _NONCE.fullmatch(document["nonce"]) is None
            or type(document["signature"]) is not str
            or _B64.fullmatch(document["signature"]) is None):
            raise ValueError()
        signature = base64.b64decode(
            document["signature"], altchars=b"-_", validate=True)
        if len(signature) != 64:
            raise ValueError()
        key.verify(signature, _signed_body(body))
    except Exception:
        raise PrivateOwnerReenrollmentBlocked(
            "Independent owner re-enrollment attestation rejected") from None


def reenroll_private_owner_totp_offline(
    db: Session, *, owner_ref: str, password: str,
    new_totp_secret_base32: str, new_totp_code: str,
    signed_operator_attestation: str, now_epoch: int | None = None,
) -> dict:
    """Authorize a fresh MFA device without issuing a session or Google grant.

    Requires an already consumed one-time recovery code (account on hold),
    owner password, new device TOTP, and an offline-signed independent operator
    decision bound to the *current* audit state. The private signing key must
    never be installed in the application. Replays cannot lift a second hold.
    Any active local Google grant blocks the transition until separately
    revoked by a qualified operator and at the provider.
    """
    key = _public_key(db)
    try:
        owner_enc, owner_mac, _, recovery_enc, recovery_mac = recovery_config(db)
        owner = _owner(owner_mac, owner_ref)
        now = _now(now_epoch)
        if (type(password) is not str or not 16 <= len(password) <= 256
            or type(new_totp_secret_base32) is not str
            or type(new_totp_code) is not str or _PIN.fullmatch(new_totp_code) is None):
            raise PrivateOwnerReenrollmentBlocked("Owner re-enrollment inputs rejected")
        sealed = seal_totp(owner_enc, owner, new_totp_secret_base32)
        step = totp_step(new_totp_secret_base32, new_totp_code, now=now)
        if step is None:
            raise PrivateOwnerReenrollmentBlocked("New authenticator proof rejected")
        _lock(db)
        identity = _row(db)
        if identity is None or identity.owner_hmac != owner:
            raise PrivateOwnerReenrollmentBlocked("Owner identity unavailable")
        _verify_identity(owner_mac, identity)
        if (not check_password(password, identity.password_scrypt)
            or identity.locked_until_epoch > now):
            raise PrivateOwnerReenrollmentBlocked("Owner reauthentication rejected")
        if hmac.compare_digest(unseal_totp(owner_enc, identity),
                               new_totp_secret_base32):
            raise PrivateOwnerReenrollmentBlocked("A new authenticator is required")
        state = db.scalar(select(OwnerPrivateRecoveryState).where(
            OwnerPrivateRecoveryState.owner_hmac == owner).with_for_update())
        if state is None or not state.pending:
            raise PrivateOwnerReenrollmentBlocked("No pending owner recovery hold")
        bundle, previous = verify_recovery(db, state, recovery_mac, recovery_enc)
        _verify_attestation(
            key, attestation=signed_operator_attestation, owner=owner,
            state=state, new_totp_secret=new_totp_secret_base32, now=now,
        )
        active_grant = db.scalar(select(OwnerGoogleMetadataGrant.owner_hmac).where(
            OwnerGoogleMetadataGrant.revoked.is_(False)).limit(1))
        if active_grant is not None:
            raise PrivateOwnerReenrollmentBlocked(
                "Active Google grant must be revoked before device recovery")
        # Exhaust every earlier code; fresh codes require a later, successful
        # reauthenticated owner MFA+CSRF session and explicit issuance.
        bundle["used_hmacs"] = list(bundle["code_hmacs"])
        state.pending = False
        state.revision += 1
        state.ciphertext = seal_recovery(recovery_enc, owner, bundle)
        state.row_hmac = recovery_row_mac(recovery_mac, state)
        append_recovery(db, recovery_mac, state, "REENROLLED", previous, now)

        identity.totp_cipher = sealed
        identity.last_totp_step = step
        identity.failures = 0
        identity.locked_until_epoch = 0
        identity.window_started_epoch = now
        identity.revision += 1
        identity.row_hmac = _identity_mac(owner_mac, identity)
        revoked = db.execute(update(OwnerPrivateSession).where(
            OwnerPrivateSession.owner_hmac == owner,
            OwnerPrivateSession.revoked.is_(False),
        ).values(revoked=True)).rowcount
        db.commit()
        return {
            "independent_signed_operator_proof_checked": True,
            "replacement_authenticator_accepted": True,
            "recovery_hold_released": True,
            "prior_recovery_codes_invalidated": True,
            "sessions_revoked": revoked,
            "new_session_issued": False,
            "google_provider_grant_revoked_by_this_operation": False,
            "production_g2_accepted": False,
        }
    except (PrivateOwnerReenrollmentBlocked, PrivateOwnerRecoveryBlocked,
            PrivateOwnerIdentityBlocked):
        db.rollback()
        raise PrivateOwnerReenrollmentBlocked("Owner offline re-enrollment denied") from None
    except Exception:
        db.rollback()
        raise PrivateOwnerReenrollmentBlocked("Owner offline re-enrollment failed") from None
