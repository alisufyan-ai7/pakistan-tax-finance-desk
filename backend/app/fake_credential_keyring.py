"""P1K: owner credential key lifecycle rehearsal with fictional grants ONLY.

No owner token, Google authorization, live key store, Railway setting, public
route, or production recovery is reachable from this module. Key material is
passed in by isolated CI; nothing is written to storage or logged.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import json
import os
import re
import secrets
import hmac
from hashlib import sha256
from types import MappingProxyType
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_ID = re.compile(r"^fixture-key-v[1-9][0-9]{0,3}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_SYNTHETIC = re.compile(r"^SYNTHETIC_FAKE_REFRESH_[A-Za-z0-9_-]{16,120}$")
_PREFIX = "CFO_FAKE_KR1:"


class FakeKeyCustodyBlocked(ValueError):
    """A genuine credential or insufficiently attested key custody is blocked."""


@dataclass(frozen=True)
class FakeCredentialKeyring:
    active_id: str
    keys: object


def _guard() -> None:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1K_FAKE_KEY_CUSTODY_ONLY") != "1"):
        raise FakeKeyCustodyBlocked("Real credential key management unavailable")


def make_fake_keyring(*, active_id: str, encoded_keys: dict) -> FakeCredentialKeyring:
    """Fixture-only two-version keyring; distinct 256-bit secrets required."""
    _guard()
    if (type(active_id) is not str or _ID.fullmatch(active_id) is None
        or type(encoded_keys) is not dict
        or not 2 <= len(encoded_keys) <= 5
        or active_id not in encoded_keys):
        raise FakeKeyCustodyBlocked("Invalid independent keyring")
    keys = {}
    for name, encoded in encoded_keys.items():
        if (type(name) is not str or _ID.fullmatch(name) is None
            or type(encoded) is not str):
            raise FakeKeyCustodyBlocked("Invalid independent keyring")
        try:
            secret=base64.b64decode(encoded,altchars=b"-_",validate=True)
        except (UnicodeError, ValueError):
            raise FakeKeyCustodyBlocked("Invalid independent keyring") from None
        if len(secret)!=32:
            raise FakeKeyCustodyBlocked("Invalid independent keyring")
        keys[name]=secret
    if len(set(keys.values()))!=len(keys):
        raise FakeKeyCustodyBlocked("Key domains must be independent")
    return FakeCredentialKeyring(active_id, MappingProxyType(keys))


def _check_context(owner_hmac: str, folder_hmac: str) -> bytes:
    if (type(owner_hmac) is not str or _HEX.fullmatch(owner_hmac) is None
        or type(folder_hmac) is not str or _HEX.fullmatch(folder_hmac) is None
        or hmac.compare_digest(owner_hmac,folder_hmac)):
        raise FakeKeyCustodyBlocked("Authentic owner/folder binding required")
    return ("p1k:fictional-custody:v1:"+owner_hmac+":"+folder_hmac).encode("ascii")


def seal_fake_grant(*, ring: FakeCredentialKeyring,
                    owner_hmac: str, folder_hmac: str, fictional_token: str) -> str:
    _guard()
    aad=_check_context(owner_hmac,folder_hmac)
    if (type(fictional_token) is not str
        or _SYNTHETIC.fullmatch(fictional_token) is None
        or type(ring) is not FakeCredentialKeyring
        or ring.active_id not in ring.keys):
        raise FakeKeyCustodyBlocked("Only clearly fictional grants allowed")
    nonce=secrets.token_bytes(12)
    sealed=AESGCM(ring.keys[ring.active_id]).encrypt(
        nonce,fictional_token.encode("ascii"),aad+b":"+ring.active_id.encode("ascii"))
    body=base64.urlsafe_b64encode(nonce+sealed).decode("ascii")
    return _PREFIX+ring.active_id+":"+body


def open_fake_grant(*, ring: FakeCredentialKeyring,
                    owner_hmac: str, folder_hmac: str, sealed: str) -> str:
    _guard()
    aad=_check_context(owner_hmac,folder_hmac)
    if type(ring) is not FakeCredentialKeyring or type(sealed) is not str:
        raise FakeKeyCustodyBlocked("Unrecognized fictional grant envelope")
    try:
        if not sealed.startswith(_PREFIX) or len(sealed)>1200:
            raise ValueError()
        name,encoded=sealed[len(_PREFIX):].split(":",1)
        if _ID.fullmatch(name) is None or name not in ring.keys:
            raise ValueError()
        blob=base64.b64decode(encoded,altchars=b"-_",validate=True)
        if len(blob)<12+16 or len(blob)>320:
            raise ValueError()
        decoded=AESGCM(ring.keys[name]).decrypt(
            blob[:12],blob[12:],aad+b":"+name.encode("ascii")).decode("ascii")
        if _SYNTHETIC.fullmatch(decoded) is None:
            raise ValueError()
        return decoded
    except Exception:
        raise FakeKeyCustodyBlocked("Fictional credential cannot be authenticated") from None


def rotate_fake_grant(*, old_ring: FakeCredentialKeyring,
                      new_ring: FakeCredentialKeyring,
                      owner_hmac: str, folder_hmac: str, sealed: str) -> dict:
    """Rewrap with a new active key; old generation never leaves public output."""
    _guard()
    if (type(old_ring) is not FakeCredentialKeyring
        or type(new_ring) is not FakeCredentialKeyring
        or hmac.compare_digest(old_ring.active_id,new_ring.active_id)
        or old_ring.active_id in new_ring.keys):
        raise FakeKeyCustodyBlocked("Rotation must retire the old active key")
    fictional=open_fake_grant(ring=old_ring,owner_hmac=owner_hmac,
                             folder_hmac=folder_hmac,sealed=sealed)
    new_seal=seal_fake_grant(ring=new_ring,owner_hmac=owner_hmac,
                            folder_hmac=folder_hmac,fictional_token=fictional)
    if new_seal==sealed:
        raise FakeKeyCustodyBlocked("Rotation did not re-encrypt")
    return {"synthetic_only":True,"wrapped_grant":new_seal,
            "previous_key_retired":True,"new_key_id":new_ring.active_id,
            "old_grant_revoked_in_store":False,
            "independent_restore_test_required":True,
            "owner_mfa_recovery_verified":False,"real_google_access_enabled":False}


def inspect_fake_recovery_controls(*, audit: dict, password_reverified: bool,
                                   enrolled_mfa_present: bool) -> dict:
    """Audit reports alone never prove possession, production recovery or login.

    The caller must separately perform a persisted one-time code redemption.
    Even full self-asserted booleans cannot authorize a real MFA reset.
    """
    _guard()
    if (type(audit) is not dict
        or set(audit)!={"synthetic_only","audit_revision","active_code_count",
                       "audit_chain_verified","encrypted_state",
                       "prod_owner_recovery_certified"}
        or audit["synthetic_only"] is not True
        or type(audit["audit_revision"]) is not int or audit["audit_revision"]<1
        or type(audit["active_code_count"]) is not int
        or not 0<=audit["active_code_count"]<=12
        or audit["audit_chain_verified"] is not True
        or audit["encrypted_state"] is not True
        or audit["prod_owner_recovery_certified"] is not False
        or type(password_reverified) is not bool
        or type(enrolled_mfa_present) is not bool):
        raise FakeKeyCustodyBlocked("Recovery attestation unavailable")
    return {
        "synthetic_only":True,
        "recovery_codes_available":audit["active_code_count"]>0,
        "password_reverified_in_candidate":password_reverified,
        "enrolled_mfa_present_in_candidate":enrolled_mfa_present,
        "persisted_code_redemption_separately_required":True,
        "any_live_session_created":False,"real_mfa_reset_allowed":False,
        "owner_recovery_independently_approved":False,
        "real_data_authorized":False,
    }
