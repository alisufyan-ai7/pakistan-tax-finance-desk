"""P1Q: signed offline replacement authenticator, fictional-only recovery tests."""
import base64
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1, sha256
import hmac
import json
from threading import Barrier

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.models import OwnerPrivateIdentity, OwnerPrivateRecoveryState
from app.private_owner_identity import (
    PrivateOwnerIdentityBlocked, enroll_private_owner, issue_private_owner_session,
    verify_private_owner_session,
)
from app.private_owner_recovery import (
    PrivateOwnerRecoveryBlocked, issue_private_owner_recovery_codes,
    redeem_private_owner_recovery_code,
)
from app.private_owner_reenrollment import (
    PrivateOwnerReenrollmentBlocked, reenroll_private_owner_totp_offline,
)

OWNER = "SYNTHETIC_OWNER_REENROLL_2026_01"
PASSWORD = "SYNTHETIC_password_never_live_2026"
T = 1_800_120_000
OLD = base64.b32encode(b"M" * 20).decode("ascii")
NEW = base64.b32encode(b"N" * 20).decode("ascii")
OTHER = base64.b32encode(b"P" * 20).decode("ascii")
PREFIX = b"personal-cfo:p1q:offline-reenrollment:v1\0"


def otp(secret, epoch):
    raw = base64.b32decode(secret)
    digest = hmac.new(raw, (epoch // 30).to_bytes(8, "big"), sha1).digest()
    offset = digest[-1] & 15
    return f"{(int.from_bytes(digest[offset:offset+4], 'big') & 0x7fffffff) % 1000000:06d}"


@pytest.fixture
def state(monkeypatch, tmp_path):
    enc = lambda b: base64.urlsafe_b64encode(b * 32).decode("ascii")
    for name, value in {
        "APP_DATA_MODE": "synthetic",
        "P1N_PRIVATE_OWNER_AUTH_ONLY": "1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED": "1",
        "P1N_SQLITE_FAKE_TEST_ONLY": "1",
        "P1N_OWNER_ENCRYPTION_KEY": enc(b"A"),
        "P1N_OWNER_IDENTITY_HMAC_KEY": enc(b"B"),
        "P1N_OWNER_SESSION_HMAC_KEY": enc(b"C"),
        "P1P_PRIVATE_RECOVERY_ONLY": "1",
        "P1P_G2_RECOVERY_REVIEWED": "1",
        "P1P_OWNER_RECOVERY_ENCRYPTION_KEY": enc(b"D"),
        "P1P_OWNER_RECOVERY_HMAC_KEY": enc(b"E"),
        "P1Q_PRIVATE_OFFLINE_REENROLL_ONLY": "1",
        "P1Q_G2_OFFLINE_PROOF_REVIEWED": "1",
    }.items():
        monkeypatch.setenv(name, value)
    signer = Ed25519PrivateKey.generate()  # invented, TEST only; never persisted
    public = signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    monkeypatch.setenv("P1Q_OPERATOR_PUBLIC_KEY",
                       base64.urlsafe_b64encode(public).decode("ascii"))
    engine = create_engine("sqlite:///" + str(tmp_path / "p1q-fake-only.sqlite"),
                           connect_args={"timeout": 15})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        enroll_private_owner(s, owner_ref=OWNER, password=PASSWORD,
                             totp_secret_base32=OLD, now_epoch=T,
                             verified_offline_bootstrap=True)
    with Session(engine) as s:
        proof = issue_private_owner_session(s, owner_ref=OWNER, password=PASSWORD,
                                            totp_code=otp(OLD, T), now_epoch=T)
    with Session(engine) as s:
        _, codes = issue_private_owner_recovery_codes(
            s, owner_ref=OWNER, token=proof.cookie_token, csrf=proof.csrf_token,
            password=PASSWORD, now_epoch=T+1)
    with Session(engine) as s:
        redeem_private_owner_recovery_code(
            s, owner_ref=OWNER, password=PASSWORD, recovery_code=codes[0],
            now_epoch=T+2, independently_verified_offline_owner=True)
    yield engine, monkeypatch, signer, proof, codes
    engine.dispose()


def certificate(engine, signer, *, secret=NEW, issued=T+3, expires=T+93):
    with Session(engine) as s:
        identity = s.scalar(select(OwnerPrivateIdentity))
        hold = s.scalar(select(OwnerPrivateRecoveryState))
        body = {
            "owner_hmac": identity.owner_hmac,
            "recovery_revision": hold.revision,
            "recovery_row_hmac": hold.row_hmac,
            "new_totp_digest": sha256(
                b"personal-cfo:p1q:new-totp\0" + secret.encode("ascii")).hexdigest(),
            "issued_epoch": issued,
            "expires_epoch": expires,
            "nonce": "SYNTHETIC_NONCE_NEVER_USED_LIVE_2026",
        }
    signed = PREFIX + json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    body["signature"] = base64.urlsafe_b64encode(signer.sign(signed)).decode("ascii")
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def apply(engine, signed, *, new_secret=NEW, code=None, now=T+3, password=PASSWORD):
    with Session(engine) as s:
        return reenroll_private_owner_totp_offline(
            s, owner_ref=OWNER, password=password,
            new_totp_secret_base32=new_secret,
            new_totp_code=code or otp(new_secret, now),
            signed_operator_attestation=signed, now_epoch=now)


def test_signed_offline_replacement_is_one_time_and_old_sessions_codes_die(state):
    engine, _, signer, proof, codes = state
    signed = certificate(engine, signer)
    result = apply(engine, signed)
    assert result["independent_signed_operator_proof_checked"]
    assert result["recovery_hold_released"]
    assert result["prior_recovery_codes_invalidated"]
    assert not result["new_session_issued"]
    assert not result["production_g2_accepted"]
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            verify_private_owner_session(s, owner_ref=OWNER,
                                         token=proof.cookie_token, now_epoch=T+4)
    with pytest.raises(PrivateOwnerReenrollmentBlocked):
        apply(engine, signed)
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerRecoveryBlocked):
            redeem_private_owner_recovery_code(
                s, owner_ref=OWNER, password=PASSWORD, recovery_code=codes[1],
                now_epoch=T+5, independently_verified_offline_owner=True)
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            issue_private_owner_session(s, owner_ref=OWNER, password=PASSWORD,
                                        totp_code=otp(OLD, T+65), now_epoch=T+65)
    with Session(engine) as s:
        new_session = issue_private_owner_session(s, owner_ref=OWNER,
            password=PASSWORD, totp_code=otp(NEW, T+65), now_epoch=T+65)
        assert new_session.expires_epoch == T+965
    with engine.connect() as connection:
        events = connection.execute(text(
            "SELECT action FROM owner_private_recovery_audit ORDER BY revision")).scalars().all()
        assert events == ["ISSUED", "REDEEMED", "REENROLLED"]
        hold = connection.execute(text(
            "SELECT pending,revision FROM owner_private_recovery_states")).one()
        assert not hold[0] and hold[1] == 3
        raw = str(connection.execute(text("SELECT * FROM owner_private_identities")).one())
        assert OLD not in raw and NEW not in raw and PASSWORD not in raw
    with Session(engine) as s:
        assert verify_private_owner_session(s, owner_ref=OWNER,
            token=new_session.cookie_token, now_epoch=T+66)["private_owner_mfa_session_valid"]


@pytest.mark.parametrize("defect", [
    "unsigned", "wrong_signer", "different_secret", "expired",
    "wrong_password", "wrong_totp", "old_authenticator",
])
def test_invalid_or_expired_operator_authorization_cannot_release_hold(state, defect):
    engine, _, signer, _, _ = state
    signed = certificate(engine, signer, expires=T+10)
    kwargs = {}
    if defect == "unsigned":
        signed = json.dumps({**json.loads(signed), "signature": "A"*88})
    elif defect == "wrong_signer":
        signed = certificate(engine, Ed25519PrivateKey.generate(), expires=T+10)
    elif defect == "different_secret":
        kwargs["new_secret"] = OTHER
    elif defect == "expired":
        kwargs["now"] = T+11
    elif defect == "wrong_password":
        kwargs["password"] = "SYNTHETIC_wrong_password_2026"
    elif defect == "wrong_totp":
        kwargs["code"] = "000000"
    elif defect == "old_authenticator":
        kwargs["new_secret"] = OLD
        signed = certificate(engine, signer, secret=OLD)
    with pytest.raises(PrivateOwnerReenrollmentBlocked):
        apply(engine, signed, **kwargs)
    with engine.connect() as connection:
        hold = connection.execute(text(
            "SELECT pending,revision FROM owner_private_recovery_states")).one()
        assert hold[0] and hold[1] == 2
        count = connection.execute(text(
            "SELECT count(*) FROM owner_private_recovery_audit")).scalar_one()
        assert count == 2


def test_attestation_is_bound_to_exact_recovery_audit_revision(state):
    engine, _, signer, _, _ = state
    signed = certificate(engine, signer)
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE owner_private_recovery_states SET row_hmac=:h"),
            {"h": "f" * 64})
    with pytest.raises(PrivateOwnerReenrollmentBlocked):
        apply(engine, signed)


def test_unreviewed_config_and_real_finance_mode_still_fail_closed(state):
    engine, monkeypatch, signer, _, _ = state
    signed = certificate(engine, signer)
    monkeypatch.setenv("P1Q_PRIVATE_OFFLINE_REENROLL_ONLY", "0")
    with pytest.raises(PrivateOwnerReenrollmentBlocked):
        apply(engine, signed)
    monkeypatch.setenv("P1Q_PRIVATE_OFFLINE_REENROLL_ONLY", "1")
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(PrivateOwnerReenrollmentBlocked):
        apply(engine, signed)


def test_public_preview_does_not_mount_offline_owner_reenrollment(state):
    from app.preview_api import create_preview_app
    routes = {route.path for route in create_preview_app().routes}
    assert "/api/owner/reenroll" not in routes
    assert "/api/owner/recover" not in routes
