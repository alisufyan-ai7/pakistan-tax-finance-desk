"""P1N: genuine-compatible MFA storage/session guards, all test inputs invented."""
from __future__ import annotations
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa: F401
from app.private_owner_identity import (
    PrivateOwnerIdentityBlocked, enroll_private_owner,
    issue_private_owner_session,verify_private_owner_session,
    revoke_private_owner_session,inspect_private_recovery_availability,
)

OWNER="SYNTHETIC_OWNER_0000000000000001"
WRONG="SYNTHETIC_OWNER_0000000000000002"
PASSWORD="fictional-owner-long-password-2026-A"
MFA=base64.b32encode(b"K"*20).decode("ascii")
T=1_800_000_000


def code(now):
    t=now//30
    d=hmac.new(b"K"*20,t.to_bytes(8,"big"),hashlib.sha1).digest()
    o=d[-1]&15
    return f"{(int.from_bytes(d[o:o+4],'big')&0x7fffffff)%1000000:06d}"


def fake_env(monkeypatch):
    enc=lambda b:base64.urlsafe_b64encode(b*32).decode()
    for name,val in {
        "APP_DATA_MODE":"synthetic",
        "P1N_PRIVATE_OWNER_AUTH_ONLY":"1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED":"1",
        "P1N_SQLITE_FAKE_TEST_ONLY":"1",
        "P1N_OWNER_ENCRYPTION_KEY":enc(b"A"),
        "P1N_OWNER_IDENTITY_HMAC_KEY":enc(b"B"),
        "P1N_OWNER_SESSION_HMAC_KEY":enc(b"C"),
    }.items():
        monkeypatch.setenv(name,val)


@pytest.fixture
def environment(monkeypatch,tmp_path):
    fake_env(monkeypatch)
    engine=create_engine("sqlite:///"+str(tmp_path/"fake-owner-auth.db"),
                         connect_args={"timeout":10})
    Base.metadata.create_all(engine)
    yield engine,monkeypatch
    engine.dispose()


def enroll(engine,**kwargs):
    with Session(engine) as s:
        return enroll_private_owner(
            s,owner_ref=kwargs.get("owner",OWNER),password=kwargs.get("password",PASSWORD),
            totp_secret_base32=kwargs.get("totp",MFA),now_epoch=T,
            verified_offline_bootstrap=kwargs.get("verified",True))


def login(engine,now=T,otp=None,owner=OWNER,password=PASSWORD):
    with Session(engine) as s:
        return issue_private_owner_session(
            s,owner_ref=owner,password=password,totp_code=otp or code(now),now_epoch=now)


def verify(engine,proof,now=T,csrf=None,mutation=False,owner=OWNER):
    with Session(engine) as s:
        return verify_private_owner_session(s,owner_ref=owner,
            token=proof.cookie_token,csrf=csrf,mutation=mutation,now_epoch=now)


def test_single_owner_enrollment_stores_no_raw_owner_password_or_mfa(environment):
    engine,_=environment
    receipt=enroll(engine)
    assert receipt["private_metadata_owner_enrolled"]
    assert not receipt["recovery_independently_accepted"]
    assert not receipt["real_google_connection_established"]
    with engine.connect() as c:
        record=c.execute(text("SELECT * FROM owner_private_identities")).one()
    assert "scrypt-v1$" in str(record)
    assert "P1N1:" in str(record)
    for secret in (OWNER,PASSWORD,MFA):
        assert secret not in str(record)
    assert len(record[-1])==64
    with pytest.raises(PrivateOwnerIdentityBlocked):
        enroll(engine,owner=WRONG)
    with pytest.raises(PrivateOwnerIdentityBlocked):
        enroll(engine)


def test_owner_mfa_one_step_once_and_csrf_mutations_separate(environment):
    engine,_=environment
    enroll(engine)
    proof=login(engine)
    assert len(proof.cookie_token)>=40
    assert len(proof.csrf_token)>=40
    assert proof.expires_epoch==T+900
    assert verify(engine,proof)["private_owner_mfa_session_valid"]
    with pytest.raises(PrivateOwnerIdentityBlocked):
        verify(engine,proof,mutation=True)
    with pytest.raises(PrivateOwnerIdentityBlocked):
        verify(engine,proof,csrf="bad",mutation=True)
    assert verify(engine,proof,csrf=proof.csrf_token,mutation=True)["private_owner_mfa_session_valid"]
    with pytest.raises(PrivateOwnerIdentityBlocked):
        login(engine)  # same TOTP step cannot be replayed across sessions
    with engine.connect() as c:
        row=c.execute(text("SELECT * FROM owner_private_sessions")).one()
    assert proof.cookie_token not in str(row)
    assert proof.csrf_token not in str(row)
    assert OWNER not in str(row)


def test_expiry_revocation_and_wrong_owner(environment):
    engine,_=environment
    enroll(engine)
    p=login(engine)
    with pytest.raises(PrivateOwnerIdentityBlocked):
        verify(engine,p,owner=WRONG)
    with pytest.raises(PrivateOwnerIdentityBlocked):
        verify(engine,p,now=T+901)
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            revoke_private_owner_session(s,owner_ref=OWNER,
                token=p.cookie_token,csrf="bad",now_epoch=T)
    with Session(engine) as s:
        receipt=revoke_private_owner_session(s,owner_ref=OWNER,
            token=p.cookie_token,csrf=p.csrf_token,now_epoch=T)
        assert receipt["owner_session_revoked"]
        assert receipt["google_provider_grant_revoked"] is False
    with pytest.raises(PrivateOwnerIdentityBlocked):
        verify(engine,p)


def test_cross_worker_same_totp_and_first_login_only_one_succeeds(environment):
    engine,_=environment
    enroll(engine)
    barrier=Barrier(2)
    def worker(_):
        barrier.wait(timeout=10)
        try:
            return login(engine)
        except PrivateOwnerIdentityBlocked:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(worker,(1,2)))
    assert sum(v is not None for v in outcomes)==1
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM owner_private_sessions")).scalar_one()==1


def test_five_persistent_failed_attempts_lockout_then_recover_next_step(environment):
    engine,_=environment
    enroll(engine)
    for i in range(5):
        with pytest.raises(PrivateOwnerIdentityBlocked):
            login(engine,now=T+i,password="incorrect password 0000000000")
    with engine.connect() as c:
        locked=c.execute(text(
            "SELECT failures,locked_until_epoch FROM owner_private_identities")).one()
    assert locked[0]==5
    assert locked[1]>=T+900
    with pytest.raises(PrivateOwnerIdentityBlocked):
        login(engine,now=T+10)
    # 5 failed passwords can never mint a cookie.
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM owner_private_sessions")).scalar_one()==0
    ok=login(engine,now=T+930)
    assert ok.expires_epoch==T+1830


@pytest.mark.parametrize("column,value",[
    ("password_scrypt","bad-rewritten-hash"),
    ("totp_cipher","P1N1:bad"),
    ("failures",3),
    ("last_totp_step",123),
    ("row_hmac","0"*64),
])
def test_sql_identity_tampering_detected_before_login(environment,column,value):
    engine,_=environment
    enroll(engine)
    with engine.begin() as c:
        c.execute(text(f"UPDATE owner_private_identities SET {column}=:v"),{"v":value})
    with pytest.raises(PrivateOwnerIdentityBlocked):
        login(engine)


def test_missing_bootstrap_review_and_second_owner_blocked(environment):
    engine,_=environment
    with pytest.raises(PrivateOwnerIdentityBlocked):
        enroll(engine,verified=False)
    assert enroll(engine)["private_metadata_owner_enrolled"]
    with pytest.raises(PrivateOwnerIdentityBlocked):
        enroll(engine,owner=WRONG)


@pytest.mark.parametrize("key,value",[
    ("APP_DATA_MODE","real"),
    ("P1N_PRIVATE_OWNER_AUTH_ONLY","0"),
    ("P1N_G2_OWNER_IDENTITY_REVIEWED","0"),
    ("P1N_OWNER_ENCRYPTION_KEY",""),
    ("P1N_OWNER_SESSION_HMAC_KEY",""),
])
def test_owner_mfa_remains_default_off_without_key_g2_review(environment,key,value):
    engine,monkeypatch=environment
    monkeypatch.setenv(key,value)
    with pytest.raises(PrivateOwnerIdentityBlocked):
        enroll(engine)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM owner_private_identities")).scalar_one()==0


def test_no_live_recovery_bypass_and_public_oauth_mount(environment):
    status=inspect_private_recovery_availability()
    assert not status["real_mfa_recovery_available"]
    assert not status["authenticator_reset_permitted"]
    assert not status["production_oauth_activation_approved"]
    from app.preview_api import create_preview_app
    routes={r.path for r in create_preview_app().routes}
    for r in ("/api/owner/login","/api/owner/recover",
              "/api/drive/oauth/callback","/api/drive/oauth/start"):
        assert r not in routes
