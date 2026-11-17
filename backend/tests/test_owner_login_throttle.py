"""P1G: synthetic-only multi-worker owner MFA throttling; never hosted login."""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import hmac
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.auth_mfa import password_hash, token_digest
from app.drive_google_oauth import PERSONAL_CFO_RAILWAY_CALLBACK
from app.drive_inbox_planner import _index
from app.owner_login_throttle import (
    issue_throttled_fake_owner_session, fake_throttle_health,
    OwnerThrottleBlocked, ATTEMPTS, LOCK_SECONDS,
)

FOLDER = "SYNTHETIC_P1G_THROTTLED_OWNER_ONLY_2026"
PASSWORD = "synthetic-only-password-strong-4567"
SECRET = base64.b32encode(b"synthetic-p1g-totp-key-12345678901").decode()
T = 1_800_000_000


def otp(epoch: int) -> str:
    key = base64.b32decode(SECRET)
    digest = hmac.new(key, (epoch//30).to_bytes(8,"big"), hashlib.sha1).digest()
    off = digest[-1] & 0x0f
    return f"{((int.from_bytes(digest[off:off+4],'big') & 0x7fffffff)%1000000):06d}"


@pytest.fixture
def env(tmp_path, monkeypatch):
    for k,v in {
        "APP_DATA_MODE":"synthetic",
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY":"1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY":"1",
        "P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY":"1",
        "P1F_SYNTHETIC_OWNER_GATEWAY_ONLY":"1",
        "P1G_FAKE_LOGIN_THROTTLE_ONLY":"1",
        "P1G_SQLITE_TEST_ONLY":"1",
        "P1E_SQLITE_TEST_ONLY":"1",
        "P1B_GOOGLE_REDIRECT_URI":PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_CLIENT_ID":"000000000000-syntheticdev.apps.googleusercontent.com",
        "P1B_GOOGLE_FOLDER_ID":FOLDER,
        "DRIVE_INDEX_HMAC_KEY":base64.urlsafe_b64encode(b"D"*32).decode(),
        "P1E_FAKE_CLOUD_VAULT_KEY":base64.urlsafe_b64encode(b"E"*32).decode(),
        "P1E_FAKE_CLOUD_INDEX_KEY":base64.urlsafe_b64encode(b"J"*32).decode(),
        "P1G_FAKE_THROTTLE_KEY":base64.urlsafe_b64encode(b"T"*32).decode(),
        "P1F_FAKE_OWNER_PASSWORD_SCRYPT":password_hash(PASSWORD, bytes(range(16))),
        "P1F_FAKE_OWNER_TOTP_SECRET":SECRET,
    }.items():
        monkeypatch.setenv(k,v)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder",FOLDER))
    engine = create_engine(
        "sqlite:///"+str(tmp_path/"owner-throttle.db"),
        connect_args={"timeout":10},
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def login(db, *, password=PASSWORD, username="synthetic-owner", code=None, at=T):
    return issue_throttled_fake_owner_session(
        db, username=username, password=password,
        totp_code=code if code is not None else otp(at),
        now_epoch=at,
    )


def test_success_issues_only_hashed_short_synthetic_session(env):
    with Session(env) as db:
        raw=login(db)
        report=fake_throttle_health(db)
        assert report["durable_multiworker_contract"] is True
        assert report["hosted_owner_login_enabled"] is False
        assert report["real_data_authorized"] is False
    with env.connect() as conn:
        identity, failures=conn.execute(text(
            "SELECT owner_hmac,failures FROM owner_login_throttles"
        )).one()
        token, expires=conn.execute(text(
            "SELECT token_sha256,expires_at FROM owner_sessions"
        )).one()
        assert len(identity)==64 and failures==0
        assert "synthetic-owner" not in identity
        assert raw not in token and token==token_digest(raw)
        assert isinstance(expires, str) or isinstance(expires, datetime)


def test_lockout_counts_password_username_and_otp_failures_before_mfa(env):
    for n in range(ATTEMPTS):
        with Session(env) as db:
            with pytest.raises(OwnerThrottleBlocked, match="rejected"):
                login(db,password="wrong",at=T+n)
    with Session(env) as db:
        with pytest.raises(OwnerThrottleBlocked):
            login(db,at=T+ATTEMPTS)
    with env.connect() as conn:
        row=conn.execute(text(
            "SELECT failures,locked_until_epoch FROM owner_login_throttles"
        )).one()
        assert row[0]==ATTEMPTS
        assert row[1]==T+ATTEMPTS-1+LOCK_SECONDS
        assert conn.execute(text("SELECT COUNT(*) FROM owner_sessions")).scalar_one()==0
    with Session(env) as db:
        assert len(login(db,at=T+ATTEMPTS+LOCK_SECONDS+60))>=40
    with env.connect() as conn:
        assert conn.execute(text(
            "SELECT failures FROM owner_login_throttles"
        )).scalar_one()==0


def test_wrong_username_or_totp_rejected_and_counted(env):
    with Session(env) as db:
        with pytest.raises(OwnerThrottleBlocked):
            login(db,username="attacker-owner")
    with Session(env) as db:
        with pytest.raises(OwnerThrottleBlocked):
            login(db,code="000000")
    with env.connect() as conn:
        assert conn.execute(text(
            "SELECT failures FROM owner_login_throttles"
        )).scalar_one()==2


def test_replayed_totp_is_failure_not_second_session(env):
    with Session(env) as db:
        raw=login(db)
    with Session(env) as db:
        with pytest.raises(OwnerThrottleBlocked):
            login(db)
    with env.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM owner_sessions")).scalar_one()==1
        assert conn.execute(text(
            "SELECT failures FROM owner_login_throttles"
        )).scalar_one()==1


def test_concurrent_workers_only_issue_one_session_per_otp(env):
    barrier=Barrier(2)
    def worker(_):
        barrier.wait(timeout=10)
        with Session(env) as db:
            try:
                return login(db)
            except OwnerThrottleBlocked:
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(worker,range(2)))
    assert sum(raw is not None for raw in results)==1
    with env.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM owner_sessions")).scalar_one()==1
        assert conn.execute(text(
            "SELECT failures FROM owner_login_throttles"
        )).scalar_one()==1


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("P1G_FAKE_LOGIN_THROTTLE_ONLY","0"),
    ("P1F_SYNTHETIC_OWNER_GATEWAY_ONLY","0"),
    ("P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY","0"),
    ("P1B_GOOGLE_FOLDER_ID","ACTUAL_OWNER_FOLDER_NOT_FAKE"),
])
def test_real_mode_or_bad_fake_config_cannot_authenticate(env,monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    with Session(env) as db:
        with pytest.raises(OwnerThrottleBlocked):
            login(db)
    with env.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM owner_sessions")).scalar_one()==0


def test_required_separate_throttle_key_and_input_bounds(env,monkeypatch):
    monkeypatch.setenv("P1G_FAKE_THROTTLE_KEY", "")
    with Session(env) as db:
        with pytest.raises(OwnerThrottleBlocked):
            login(db)
    monkeypatch.setenv("P1G_FAKE_THROTTLE_KEY",base64.urlsafe_b64encode(b"T"*32).decode())
    with Session(env) as db:
        with pytest.raises(OwnerThrottleBlocked):
            login(db,username="x"*129)
        with pytest.raises(OwnerThrottleBlocked):
            login(db,at=True)


def test_fixture_only_source_no_public_owner_login(env):
    from app.preview_api import create_preview_app
    from app.drive_cloud_owner_gateway import create_fake_private_oauth_gateway
    assert not any("/login" in route.path or "/oauth" in route.path
                   for route in create_preview_app().routes)
    assert not any("/login" in route.path
                   for route in create_fake_private_oauth_gateway(lambda:Session(env)).routes)
