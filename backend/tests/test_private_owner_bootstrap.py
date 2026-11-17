"""P1W: fake-only atomic initial owner MFA+recovery enrollment tests."""
import base64
from hashlib import sha1
import hmac
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.private_owner_bootstrap import (
    PrivateOwnerBootstrapBlocked, enroll_single_owner_with_recovery,
)
from app.private_owner_identity import (
    PrivateOwnerIdentityBlocked, issue_private_owner_session,
)
from app.private_owner_recovery import (
    redeem_private_owner_recovery_code,
)

OWNER = "SYNTHETIC_SINGLE_OWNER_P1W_2026"
PW = "SYNTHETIC_distinct_password_never_live_2026"
SEED = base64.b32encode(b"M"*20).decode("ascii")
T = 1_800_245_000


def otp(epoch=T):
    raw = base64.b32decode(SEED)
    digest = hmac.new(raw, (epoch//30).to_bytes(8, "big"), sha1).digest()
    offset = digest[-1] & 15
    return f"{(int.from_bytes(digest[offset:offset+4], 'big')&0x7fffffff)%1000000:06d}"


@pytest.fixture
def db(monkeypatch,tmp_path):
    key = lambda b: base64.urlsafe_b64encode(b*32).decode()
    signer=Ed25519PrivateKey.generate()
    pub=base64.urlsafe_b64encode(
        signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    env={
        "APP_DATA_MODE":"synthetic",
        "P1N_PRIVATE_OWNER_AUTH_ONLY":"1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED":"1",
        "P1N_SQLITE_FAKE_TEST_ONLY":"1",
        "P1N_OWNER_ENCRYPTION_KEY":key(b"A"),
        "P1N_OWNER_IDENTITY_HMAC_KEY":key(b"B"),
        "P1N_OWNER_SESSION_HMAC_KEY":key(b"C"),
        "P1P_PRIVATE_RECOVERY_ONLY":"1",
        "P1P_G2_RECOVERY_REVIEWED":"1",
        "P1P_OWNER_RECOVERY_ENCRYPTION_KEY":key(b"D"),
        "P1P_OWNER_RECOVERY_HMAC_KEY":key(b"E"),
        "P1Q_PRIVATE_OFFLINE_REENROLL_ONLY":"1",
        "P1Q_G2_OFFLINE_PROOF_REVIEWED":"1",
        "P1Q_OPERATOR_PUBLIC_KEY":pub,
        "P1W_ATOMIC_OWNER_BOOTSTRAP_ONLY":"1",
        "P1W_G2_TERMINAL_CUSTODY_REVIEWED":"1",
    }
    for name,value in env.items():
        monkeypatch.setenv(name,value)
    engine=create_engine("sqlite:///"+str(tmp_path/"p1w-owner-synthetic.db"))
    Base.metadata.create_all(engine)
    yield engine, monkeypatch
    engine.dispose()


def attempt(engine, *, password=PW, code=None, approved=True):
    with Session(engine) as s:
        return enroll_single_owner_with_recovery(
            s, owner_ref=OWNER, password=password,
            totp_secret_base32=SEED, confirmed_totp_code=code or otp(),
            now_epoch=T, independently_verified_admin_session=approved)


def test_one_owner_password_totp_and_recovery_kit_created_atomically(db):
    engine,_ = db
    report,codes=attempt(engine)
    assert report["single_owner_enrolled"]
    assert report["owner_role"]=="owner"
    assert report["human_user_count"]==1
    assert report["recovery_codes_issued"]==8
    assert not report["session_issued"]
    assert not report["google_consent_established"]
    assert len(codes)==len(set(codes))==8
    assert all(len(code)==39 for code in codes)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM owner_private_identities")).scalar_one()==1
        assert c.execute(text("SELECT count(*) FROM owner_private_recovery_states")).scalar_one()==1
        assert c.execute(text("SELECT action FROM owner_private_recovery_audit")).scalar_one()=="ISSUED"
        assert c.execute(text("SELECT pending FROM owner_private_recovery_states")).scalar_one() in (0,False)
        identity=str(c.execute(text("SELECT * FROM owner_private_identities")).one())
        recovery=str(c.execute(text("SELECT * FROM owner_private_recovery_states")).one())
        for forbidden in (PW,SEED,codes[0],OWNER):
            assert forbidden not in identity+recovery
    with pytest.raises(PrivateOwnerBootstrapBlocked):
        attempt(engine)
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            issue_private_owner_session(s, owner_ref=OWNER, password=PW,
                                        totp_code=otp(T), now_epoch=T)
    with Session(engine) as s:
        proof=issue_private_owner_session(s,owner_ref=OWNER,
            password=PW,totp_code=otp(T+31),now_epoch=T+31)
        assert proof.cookie_token
    with Session(engine) as s:
        result=redeem_private_owner_recovery_code(s,owner_ref=OWNER,
            password=PW,recovery_code=codes[0],now_epoch=T+32,
            independently_verified_offline_owner=True)
        assert result["account_recovery_hold_active"]


@pytest.mark.parametrize("kind",["wrong_code","unapproved_operator","short_password","missing_key",
                                  "wrong_public_key","disabled","real_mode"])
def test_invalid_or_unapproved_bootstrap_leaves_zero_owner_state(db,kind):
    engine,monkeypatch=db
    args={}
    if kind=="wrong_code":args["code"]="000000"
    elif kind=="unapproved_operator":args["approved"]=False
    elif kind=="short_password":args["password"]="too-short"
    elif kind=="missing_key":monkeypatch.setenv("P1P_OWNER_RECOVERY_HMAC_KEY","")
    elif kind=="wrong_public_key":monkeypatch.setenv("P1Q_OPERATOR_PUBLIC_KEY","not-valid")
    elif kind=="disabled":monkeypatch.setenv("P1W_ATOMIC_OWNER_BOOTSTRAP_ONLY","0")
    elif kind=="real_mode":monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(PrivateOwnerBootstrapBlocked):
        attempt(engine,**args)
    with engine.connect() as c:
        for table in ("owner_private_identities","owner_private_recovery_states",
                      "owner_private_recovery_audit","owner_private_sessions"):
            assert c.execute(text("SELECT count(*) FROM "+table)).scalar_one()==0


def test_public_api_never_mounts_operator_first_run_or_recovery_routes(db):
    from app.preview_api import create_preview_app
    paths={r.path for r in create_preview_app().routes}
    assert not any(path.startswith("/internal/drive/auth/") for path in paths)
    assert "/api/owner/enroll" not in paths
    assert "/api/owner/recovery" not in paths
