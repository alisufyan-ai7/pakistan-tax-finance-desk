"""P1R: fake-only MFA-bound persisted Google PKCE callback state tests."""
import base64
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1
import hmac
from threading import Barrier
from urllib.parse import urlsplit, parse_qs

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.drive_google_oauth import PERSONAL_CFO_RAILWAY_CALLBACK
from app.drive_inbox_planner import _index
from app.private_owner_identity import (
    enroll_private_owner, issue_private_owner_session, revoke_private_owner_session,
)
from app.private_owner_google_oauth_state import (
    PrivateOAuthStateBlocked, begin_private_session_google_oauth,
    consume_private_session_google_oauth,
)

T = 1_800_130_000
OWNER = "SYNTHETIC_P1R_OWNER_0000000001"
PASSWORD = "synthetic_mfa_password_2026_never_live"
SEED = base64.b32encode(b"J" * 20).decode("ascii")
FOLDER = "SYNTHETIC_ONE_OWNER_FOLDER_2026"
CLIENT = "000000000000-syntheticdev.apps.googleusercontent.com"
CODE = "SYNTHETIC_AUTH_CODE_NOT_GOOGLE_2026"


def otp(now):
    digest = hmac.new(b"J" * 20, (now//30).to_bytes(8, "big"), sha1).digest()
    offset = digest[-1] & 15
    return f"{(int.from_bytes(digest[offset:offset+4], 'big') & 0x7fffffff) % 1000000:06d}"


@pytest.fixture
def env(monkeypatch, tmp_path):
    enc = lambda x: base64.urlsafe_b64encode(x * 32).decode()
    config = {
        "APP_DATA_MODE": "synthetic",
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY": "1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY": "1",
        "P1B_GOOGLE_CLIENT_ID": CLIENT,
        "P1B_GOOGLE_REDIRECT_URI": PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_FOLDER_ID": FOLDER,
        "DRIVE_INDEX_HMAC_KEY": enc(b"F"),
        "P1N_PRIVATE_OWNER_AUTH_ONLY": "1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED": "1",
        "P1N_SQLITE_FAKE_TEST_ONLY": "1",
        "P1N_OWNER_ENCRYPTION_KEY": enc(b"A"),
        "P1N_OWNER_IDENTITY_HMAC_KEY": enc(b"B"),
        "P1N_OWNER_SESSION_HMAC_KEY": enc(b"C"),
        "P1R_PRIVATE_OAUTH_STATE_ONLY": "1",
        "P1R_G2_SESSION_OAUTH_REVIEWED": "1",
        "P1R_SQLITE_FAKE_TEST_ONLY": "1",
        "P1R_OAUTH_STATE_ENCRYPTION_KEY": enc(b"D"),
        "P1R_OAUTH_STATE_HMAC_KEY": enc(b"E"),
    }
    for name, value in config.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    engine = create_engine("sqlite:///" + str(tmp_path / "fake-mfa-oauth.db"),
                           connect_args={"timeout": 10})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        enroll_private_owner(s, owner_ref=OWNER, password=PASSWORD,
                             totp_secret_base32=SEED,
                             now_epoch=T, verified_offline_bootstrap=True)
    with Session(engine) as s:
        proof = issue_private_owner_session(s, owner_ref=OWNER,
            password=PASSWORD, totp_code=otp(T), now_epoch=T)
    yield engine, monkeypatch, proof
    engine.dispose()


def start(engine, proof, **kwargs):
    with Session(engine) as s:
        return begin_private_session_google_oauth(
            s, owner_ref=OWNER, session_token=proof.cookie_token,
            csrf_token=kwargs.get("csrf", proof.csrf_token),
            now_epoch=kwargs.get("now", T+1))


def claimed(engine, proof, state, **kwargs):
    with Session(engine) as s:
        return consume_private_session_google_oauth(
            s, owner_ref=OWNER, session_token=proof.cookie_token,
            state=state, code=kwargs.get("code", CODE),
            now_epoch=kwargs.get("now", T+2))


def rawstate(url):
    params = parse_qs(urlsplit(url).query)
    return params["state"][0], params


def test_real_compatible_attempt_has_encrypted_session_binding_and_one_use(env):
    engine, _, proof = env
    url = start(engine, proof)
    state, params = rawstate(url)
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert params["scope"] == ["https://www.googleapis.com/auth/drive.metadata.readonly"]
    assert params["redirect_uri"] == [PERSONAL_CFO_RAILWAY_CALLBACK]
    assert params["code_challenge_method"] == ["S256"]
    assert "code_verifier" not in params
    with engine.connect() as c:
        row = c.execute(text("SELECT * FROM owner_private_oauth_attempts")).one()
        raw = str(row)
        for secret in (state, proof.cookie_token, proof.csrf_token, FOLDER, CLIENT):
            assert secret not in raw
        assert "P1R1:" in raw
    attempt = claimed(engine, proof, state)
    assert len(attempt.verifier) >= 43
    assert attempt.metadata_only
    assert attempt.state_consumed_before_external_exchange
    with pytest.raises(PrivateOAuthStateBlocked):
        claimed(engine, proof, state)
    with engine.connect() as c:
        assert c.execute(text(
            "SELECT status FROM owner_private_oauth_attempts")).scalar_one() == "claimed"


def test_invalid_csrf_and_second_browser_session_cannot_use_first_state(env):
    engine, _, proof = env
    with pytest.raises(PrivateOAuthStateBlocked):
        start(engine, proof, csrf="wrong")
    state, _ = rawstate(start(engine, proof))
    with Session(engine) as s:
        other = issue_private_owner_session(
            s, owner_ref=OWNER, password=PASSWORD,
            totp_code=otp(T+31), now_epoch=T+31)
    with pytest.raises(PrivateOAuthStateBlocked):
        claimed(engine, other, state, now=T+32)
    assert claimed(engine, proof, state, now=T+32).metadata_only


def test_logout_and_expiration_cannot_claim_oauth_attempt(env):
    engine, _, proof = env
    state, _ = rawstate(start(engine, proof))
    with pytest.raises(PrivateOAuthStateBlocked):
        claimed(engine, proof, state, now=T+602)
    with Session(engine) as s:
        revoke_private_owner_session(s, owner_ref=OWNER, token=proof.cookie_token,
                                     csrf=proof.csrf_token, now_epoch=T+3)
    with pytest.raises(PrivateOAuthStateBlocked):
        claimed(engine, proof, state, now=T+4)


def test_invalid_callback_and_tampered_sql_fail_closed(env):
    engine, _, proof = env
    state, _ = rawstate(start(engine, proof))
    with pytest.raises(PrivateOAuthStateBlocked):
        claimed(engine, proof, state, code="bad")
    with pytest.raises(PrivateOAuthStateBlocked):
        claimed(engine, proof, state + "-tampered")
    with engine.begin() as c:
        c.execute(text(
            "UPDATE owner_private_oauth_attempts SET row_hmac=:m"), {"m": "f" * 64})
    with pytest.raises(PrivateOAuthStateBlocked):
        claimed(engine, proof, state)


@pytest.mark.parametrize("key,value", [
    ("P1R_G2_SESSION_OAUTH_REVIEWED", "0"),
    ("P1R_OAUTH_STATE_ENCRYPTION_KEY", ""),
    ("P1R_OAUTH_STATE_HMAC_KEY", ""),
    ("APP_DATA_MODE", "real"),
])
def test_default_off_or_missing_keys_never_begin(env, key, value):
    engine, monkeypatch, proof = env
    monkeypatch.setenv(key, value)
    with pytest.raises(PrivateOAuthStateBlocked):
        start(engine, proof)


def test_two_workers_cannot_claim_one_state_twice(env):
    engine, _, proof = env
    state, _ = rawstate(start(engine, proof))
    barrier = Barrier(2)
    def attempt(_):
        barrier.wait(timeout=10)
        try:
            return bool(claimed(engine, proof, state).metadata_only)
        except PrivateOAuthStateBlocked:
            return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, range(2)))
    assert sorted(results) == [False, True]


def test_private_oauth_vault_remains_unmounted_and_does_not_connect_google(env):
    from app.preview_api import create_preview_app
    paths = {route.path for route in create_preview_app().routes}
    assert "/internal/drive/oauth/callback" not in paths
    assert "/api/drive/oauth/callback" not in paths
