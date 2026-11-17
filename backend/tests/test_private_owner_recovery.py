"""P1P: private MFA recovery one-time challenge and audit, fake accounts ONLY."""
import base64
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from hashlib import sha1
import hmac

import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa
from app.private_owner_identity import (
    enroll_private_owner,issue_private_owner_session,
    verify_private_owner_session,PrivateOwnerIdentityBlocked,
)
from app.private_owner_recovery import (
    issue_private_owner_recovery_codes,redeem_private_owner_recovery_code,
    private_recovery_hold_active,PrivateOwnerRecoveryBlocked,
)

OWNER="SYNTHETIC_OWNER_RECOVERY_0000001"
PASS="SYNTHETIC_private_owner_password_2026"
T=1_800_020_000
SEED=base64.b32encode(b"M"*20).decode("ascii")


def pin(now):
    step=now//30
    digest=hmac.new(b"M"*20,step.to_bytes(8,'big'),sha1).digest()
    off=digest[-1]&15
    return f"{(int.from_bytes(digest[off:off+4],'big')&0x7fffffff)%1000000:06d}"


@pytest.fixture
def env(monkeypatch,tmp_path):
    enc=lambda b:base64.urlsafe_b64encode(b*32).decode("ascii")
    for key,value in {
        "APP_DATA_MODE":"synthetic",
        "P1N_PRIVATE_OWNER_AUTH_ONLY":"1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED":"1",
        "P1N_SQLITE_FAKE_TEST_ONLY":"1",
        "P1N_OWNER_ENCRYPTION_KEY":enc(b"A"),
        "P1N_OWNER_IDENTITY_HMAC_KEY":enc(b"B"),
        "P1N_OWNER_SESSION_HMAC_KEY":enc(b"C"),
        "P1P_PRIVATE_RECOVERY_ONLY":"1",
        "P1P_G2_RECOVERY_REVIEWED":"1",
        "P1P_OWNER_RECOVERY_ENCRYPTION_KEY":enc(b"D"),
        "P1P_OWNER_RECOVERY_HMAC_KEY":enc(b"E"),
    }.items():
        monkeypatch.setenv(key,value)
    engine=create_engine("sqlite:///"+str(tmp_path/"fake-real-compatible-recovery.db"),
                         connect_args={"timeout":10})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        enroll_private_owner(s,owner_ref=OWNER,password=PASS,
            totp_secret_base32=SEED,now_epoch=T,verified_offline_bootstrap=True)
    with Session(engine) as s:
        proof=issue_private_owner_session(s,owner_ref=OWNER,
            password=PASS,totp_code=pin(T),now_epoch=T)
    yield engine,monkeypatch,proof
    engine.dispose()


def issue(engine,proof,now=T+1):
    with Session(engine) as s:
        return issue_private_owner_recovery_codes(
            s,owner_ref=OWNER,token=proof.cookie_token,
            csrf=proof.csrf_token,password=PASS,now_epoch=now)


def redeem(engine,code,**kwargs):
    with Session(engine) as s:
        return redeem_private_owner_recovery_code(
            s,owner_ref=OWNER,password=kwargs.get("password",PASS),
            recovery_code=code,now_epoch=kwargs.get("now",T+2),
            independently_verified_offline_owner=kwargs.get("verified",True))


def test_issuance_uses_mfa_csrf_and_never_stores_raw_codes(env):
    engine,_,proof=env
    receipt,codes=issue(engine,proof)
    assert receipt["recovery_codes_issued"]==8
    assert not receipt["raw_codes_persisted"]
    assert not receipt["owner_mfa_reset_approved"]
    assert len(codes)==8 and len(set(codes))==8
    assert all(len(x)==39 for x in codes) # eight 4-character groups + seven '-'
    with engine.connect() as c:
        row=c.execute(text("SELECT * FROM owner_private_recovery_states")).one()
        audits=c.execute(text("SELECT * FROM owner_private_recovery_audit")).all()
    serialized=str(row)+str(audits)
    assert serialized.find("P1P1:")>=0
    assert all(code not in serialized for code in codes)
    assert OWNER not in serialized and PASS not in serialized
    assert len(audits)==1


def test_wrong_csrf_session_and_password_deny_issuance(env):
    engine,_,proof=env
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerRecoveryBlocked):
            issue_private_owner_recovery_codes(s,owner_ref=OWNER,
                token=proof.cookie_token,csrf="fake",password=PASS,now_epoch=T+1)
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerRecoveryBlocked):
            issue_private_owner_recovery_codes(s,owner_ref=OWNER,
                token=proof.cookie_token,csrf=proof.csrf_token,
                password="wrong password 0000000000",now_epoch=T+1)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM owner_private_recovery_states")).scalar_one()==0


def test_approved_offline_redemption_revokes_sessions_and_holds_account(env):
    engine,_,proof=env
    _,codes=issue(engine,proof)
    with pytest.raises(PrivateOwnerRecoveryBlocked):
        redeem(engine,codes[0],verified=False)
    result=redeem(engine,codes[0])
    assert result["one_time_recovery_code_consumed"]
    assert result["account_recovery_hold_active"]
    assert result["owner_sessions_revoked"]>=1
    assert result["new_session_issued"] is False
    assert result["totp_reset_performed"] is False
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            verify_private_owner_session(s,owner_ref=OWNER,
                token=proof.cookie_token,now_epoch=T+3)
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            issue_private_owner_session(s,owner_ref=OWNER,
                password=PASS,totp_code=pin(T+30),now_epoch=T+30)
    with pytest.raises(PrivateOwnerRecoveryBlocked):
        redeem(engine,codes[0])
    with pytest.raises(PrivateOwnerRecoveryBlocked):
        redeem(engine,codes[1])
    with engine.connect() as c:
        state=c.execute(text("SELECT pending,revision FROM owner_private_recovery_states")).one()
        audits=c.execute(text("SELECT revision,action FROM owner_private_recovery_audit ORDER BY revision")).all()
    assert bool(state[0]) and state[1]==2
    assert [a[1] for a in audits]==["ISSUED","REDEEMED"]


def test_concurrent_code_redemption_only_one_consumes(env):
    engine,_,proof=env
    _,codes=issue(engine,proof)
    barrier=Barrier(2)
    def worker(i):
        barrier.wait(timeout=10)
        try:
            return redeem(engine,codes[i])
        except PrivateOwnerRecoveryBlocked:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=list(pool.map(worker,(0,1)))
    assert sum(x is not None for x in (a,b))==1
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM owner_private_recovery_audit")).scalar_one()==2


@pytest.mark.parametrize("table,column,value",[
    ("owner_private_recovery_states","ciphertext","P1P1:broken"),
    ("owner_private_recovery_states","pending",True),
    ("owner_private_recovery_states","row_hmac","0"*64),
    ("owner_private_recovery_states","revision",15),
    ("owner_private_recovery_audit","event_hmac","f"*64),
    ("owner_private_recovery_audit","previous_hmac","a"*64),
])
def test_tampered_recovery_state_audit_blocks_owner_sessions(env,table,column,value):
    engine,_,proof=env
    issue(engine,proof)
    with engine.begin() as c:
        c.execute(text(f"UPDATE {table} SET {column}=:v"),{"v":value})
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            verify_private_owner_session(s,owner_ref=OWNER,
                token=proof.cookie_token,now_epoch=T+3)
    with pytest.raises(PrivateOwnerRecoveryBlocked):
        redeem(engine,"AAAA-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA")


@pytest.mark.parametrize("key,value",[
    ("P1P_PRIVATE_RECOVERY_ONLY","0"),
    ("P1P_G2_RECOVERY_REVIEWED","0"),
    ("P1P_OWNER_RECOVERY_ENCRYPTION_KEY",""),
    ("P1P_OWNER_RECOVERY_HMAC_KEY",""),
])
def test_missing_recovery_keys_fail_closed_even_if_mfa_session_is_valid(env,key,value):
    engine,monkeypatch,proof=env
    issue(engine,proof)
    monkeypatch.setenv(key,value)
    with Session(engine) as s:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            verify_private_owner_session(s,owner_ref=OWNER,
                token=proof.cookie_token,now_epoch=T+2)


def test_real_mode_denies_all_recovery_operations(env):
    engine,monkeypatch,proof=env
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(PrivateOwnerRecoveryBlocked):
        issue(engine,proof)


def test_no_recovery_reset_or_public_controller_is_mounted(env):
    from app.preview_api import create_preview_app
    paths={r.path for r in create_preview_app().routes}
    assert "/api/owner/recover" not in paths
    assert "/internal/drive/auth/recovery" not in paths
