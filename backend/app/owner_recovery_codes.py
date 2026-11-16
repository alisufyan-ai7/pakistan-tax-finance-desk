"""G2 F2: pure, one-time owner MFA recovery-code primitive (synthetic only).

NOT a deployed recovery endpoint or an authenticated session. Caller MUST
independently verify owner password and MFA before issuing codes, and verify
owner password before redeeming; persisted row locking and audit are pending.
Plain codes must be presented once and never logged or stored in GitHub.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from hashlib import sha256
import hmac
import os
import re
from secrets import token_bytes
from typing import Literal


class RecoveryBlocked(ValueError):
    """Unverified, replayed or unsupported recovery operation."""


@dataclass(frozen=True)
class RecoveryBundle:
    owner_hmac: str
    issued_epoch: int
    code_hmacs: tuple[str, ...]
    consumed_hmacs: frozenset[str] = frozenset()
    synthetic_only: Literal[True] = True


def _key() -> bytes:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise RecoveryBlocked("Real account recovery is not yet available")
    encoded = os.getenv("OWNER_RECOVERY_HMAC_KEY", "")
    try:
        key = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeError):
        raise RecoveryBlocked("Recovery crypto key unavailable") from None
    if len(key) != 32:
        raise RecoveryBlocked("Recovery crypto key unavailable")
    return key


def _tag(domain: bytes, item: str) -> str:
    return hmac.new(_key(), b"personal-cfo:owner-recovery:v1:" + domain + b"\0" +
                    item.encode("ascii"), sha256).hexdigest()


def _normalize_code(code: str) -> str:
    if not isinstance(code, str) or not re.fullmatch(r"[A-Z2-7]{4}(?:-[A-Z2-7]{4}){7}", code):
        raise RecoveryBlocked("Recovery code invalid or already used")
    return code.replace("-", "")


def issue_recovery_bundle(*, owner_ref: str, mfa_confirmed: bool,
                          issued_epoch: int, count: int = 8) -> tuple[RecoveryBundle, tuple[str, ...]]:
    """Owner MFA re-verification is required at call boundary; codes display ONCE."""
    if mfa_confirmed is not True or not isinstance(owner_ref, str) or not re.fullmatch(r"[a-z0-9_-]{4,40}", owner_ref):
        raise RecoveryBlocked("Existing owner MFA verification required to issue recovery codes")
    if type(issued_epoch) is not int or issued_epoch <= 0 or type(count) is not int or not 4 <= count <= 12:
        raise RecoveryBlocked("Recovery code issuance policy invalid")
    _key()
    raw = [base64.b32encode(token_bytes(20)).decode("ascii").rstrip("=") for _ in range(count)]
    # 160-bit codes, 8 groups x 4 symbols. Hashes are owner-bound, never plain.
    codes = tuple("-".join(code[i:i+4] for i in range(0,32,4)) for code in raw)
    hashes = tuple(_tag(b"code", owner_ref + ":" + item) for item in raw)
    if len(set(hashes)) != count:
        raise RecoveryBlocked("Recovery entropy collision")
    return RecoveryBundle(owner_hmac=_tag(b"owner", owner_ref),
                          issued_epoch=issued_epoch, code_hmacs=hashes), codes


def redeem_recovery_code(*, bundle: RecoveryBundle, owner_ref: str,
                         presented_code: str, password_confirmed: bool,
                         now_epoch: int) -> RecoveryBundle:
    """Pure state transition: caller must atomically persist BEFORE granting MFA recovery.

    A used code never becomes usable again. This function DOES NOT log in,
    reset MFA, rotate secrets, grant a session, or persist the new state.
    """
    if password_confirmed is not True or not isinstance(bundle, RecoveryBundle):
        raise RecoveryBlocked("Owner password and recovery state required")
    if type(now_epoch) is not int or now_epoch < bundle.issued_epoch or now_epoch - bundle.issued_epoch > 365*86400:
        raise RecoveryBlocked("Recovery bundle expired or unavailable")
    if not isinstance(owner_ref, str) or not hmac.compare_digest(bundle.owner_hmac, _tag(b"owner", owner_ref)):
        raise RecoveryBlocked("Recovery code invalid or already used")
    candidate = _tag(b"code", owner_ref + ":" + _normalize_code(presented_code))
    found = False
    for value in bundle.code_hmacs:
        found = hmac.compare_digest(candidate, value) or found
    if not found or candidate in bundle.consumed_hmacs:
        raise RecoveryBlocked("Recovery code invalid or already used")
    return replace(bundle, consumed_hmacs=bundle.consumed_hmacs | {candidate})
