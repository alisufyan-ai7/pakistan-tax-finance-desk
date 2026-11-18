"""P1F: hostile synthetic-only owner-MFA/OAuth callback gateway contract tests."""
from __future__ import annotations

import base64
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import time

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.auth_mfa import (
    password_hash, csrf_for_session, session_token, token_digest,
)
from app.drive_google_oauth import PERSONAL_CFO_RAILWAY_CALLBACK
from app.drive_inbox_planner import _index
from app.cloud_drive_oauth_vault import (
    CloudOAuthCustodyBlocked, remember_fake_cloud_attempt,
    claim_fake_cloud_attempt,
)
from app.drive_google_oauth import begin_google_metadata_consent, private_google_configuration
from app.drive_cloud_owner_gateway import (
    COOKIE, ORIGIN, HOST, PRIVATE_ROUTES, OwnerCloudGatewayBlocked,
    apply_candidate_session_cookie, create_fake_private_oauth_gateway,
    provision_fake_mfa_session,
)
from app.preview_api import create_preview_app

FOLDER = "SYNTHETIC_P1F_OWNER_GATEWAY_FOLDER_2026"
PASSWORD = "synthetic-p1f-password-strong-12345"
SECRET = base64.b32encode(b"SYNTHETIC_P1F_TOTP_SECRET_FOR_TEST").decode()
CODE = "SYNTHETIC_GOOGLE_CODE_FICTIONAL_ONLY_123456789"


def otp(when: int) -> str:
    key = base64.b32decode(SECRET)
    mac = hmac.new(key, (when // 30).to_bytes(8, "big"), hashlib.sha1).digest()
    off = mac[-1] & 15
    return f"{((int.from_bytes(mac[off:off+4], 'big') & 0x7fffffff) % 1_000_000):06d}"


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    for key, value in {
        "APP_DATA_MODE": "synthetic",
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY": "1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY": "1",
        "P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY": "1",
        "P1E_SQLITE_TEST_ONLY": "1",
        "P1F_SYNTHETIC_OWNER_GATEWAY_ONLY": "1",
        "P1B_GOOGLE_REDIRECT_URI": PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_CLIENT_ID": "000000000000-syntheticdev.apps.googleusercontent.com",
        "P1B_GOOGLE_FOLDER_ID": FOLDER,
        "DRIVE_INDEX_HMAC_KEY": base64.urlsafe_b64encode(b"D" * 32).decode(),
        "P1E_FAKE_CLOUD_VAULT_KEY": base64.urlsafe_b64encode(b"E" * 32).decode(),
        "P1E_FAKE_CLOUD_INDEX_KEY": base64.urlsafe_b64encode(b"J" * 32).decode(),
        "P1F_FAKE_OWNER_PASSWORD_SCRYPT": password_hash(PASSWORD, bytes(range(16))),
        "P1F_FAKE_OWNER_TOTP_SECRET": SECRET,
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    db = create_engine(
        "sqlite:///" + str(tmp_path / "synthetic-gateway.db"),
        connect_args={"timeout": 10},
    )
    Base.metadata.create_all(db)
    factory = lambda: Session(db)
    stamp = int(time.time())
    with factory() as session:
        raw = provision_fake_mfa_session(
            session, username="synthetic-owner", password=PASSWORD,
            totp_code=otp(stamp - 30), now_epoch=stamp - 30,
        )
    with TestClient(create_fake_private_oauth_gateway(factory), base_url=ORIGIN) as client:
        client.cookies.set(COOKIE, raw)
        yield client, db, factory, raw, stamp
    db.dispose()


def headers(raw: str) -> dict:
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf_for_session(raw)}


def test_mfa_issued_session_is_hashed_and_has_secure_lax_cookie(isolated):
    client, engine, _, raw, _ = isolated
    assert len(raw) > 40
    with engine.connect() as db:
        token_sha, csrf_sha = db.execute(text(
            "SELECT token_sha256,csrf_sha256 FROM owner_sessions"
        )).one()
    assert raw != token_sha and len(token_sha) == 64
    assert csrf_sha == token_digest(csrf_for_session(raw))
    response = JSONResponse({"synthetic_only": True})
    apply_candidate_session_cookie(response, raw)
    cookie = response.headers["set-cookie"]
    assert "__Host-cfo-drive-owner=" in cookie
    assert "secure" in cookie.lower() and "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "path=/" in cookie.lower() and "domain=" not in cookie.lower()
    status = client.get("/internal/drive/oauth/status")
    assert status.status_code == 200
    assert status.json()["csrf_token"] == csrf_for_session(raw)
    assert status.json()["google_drive_app_connected"] is False
    assert status.headers["cache-control"] == "no-store"
    assert status.headers["referrer-policy"] == "no-referrer"


def test_exact_railway_https_origin_and_internal_routes_only(isolated):
    client, _, _, raw, _ = isolated
    assert len(PRIVATE_ROUTES) == 5
    assert all(path.startswith("/internal/drive/") for _, path in PRIVATE_ROUTES)
    assert client.post("/internal/drive/oauth/start", headers=headers(raw)).status_code == 200
    assert client.get("/api/accounts").status_code == 404
    assert client.get("/api/drive/oauth/callback").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.post("/internal/drive/oauth/callback").status_code == 405
    assert client.get("/internal/drive/oauth/start").status_code == 405
    assert client.post("/internal/drive/oauth/start?redirect=https://evil.example",
                       headers=headers(raw)).status_code == 400
    assert client.get("/internal/drive/oauth/status?token=not-allowed").status_code == 400


def test_csrf_and_origin_required_for_mutations(isolated):
    client, _, _, raw, _ = isolated
    route = "/internal/drive/oauth/start"
    assert client.post(route).status_code == 403
    assert client.post(route, headers={"X-CSRF-Token": csrf_for_session(raw)}).status_code == 403
    assert client.post(route, headers={"Origin": ORIGIN}).status_code == 403
    assert client.post(route, headers={
        "Origin": "https://evil.example",
        "X-CSRF-Token": csrf_for_session(raw),
    }).status_code == 403
    assert client.post(route, headers={
        "Origin": ORIGIN, "X-CSRF-Token": "0"*64,
    }).status_code == 403
    assert client.post(route, headers=headers(raw)).status_code == 200
    assert client.post("/internal/drive/oauth/disconnect").status_code == 403
    assert client.post("/internal/drive/auth/logout").status_code == 403


def test_insecure_host_and_forwarded_header_bypass_denied(isolated):
    client, engine, factory, raw, _ = isolated
    route = "/internal/drive/oauth/status"
    for invalid in [
        {"Host": "evil.example"},
        {"Host": HOST + ":8443"},
        {"X-Forwarded-Host": HOST},
        {"X-Forwarded-Proto": "https"},
    ]:
        assert client.get(route, headers=invalid).status_code == 403
    with TestClient(create_fake_private_oauth_gateway(factory),
                    base_url="http://" + HOST) as insecure:
        insecure.cookies.set(COOKIE, raw)
        assert insecure.get(route).status_code == 403
    with TestClient(create_fake_private_oauth_gateway(factory),
                    base_url="https://evil.example") as spoof:
        spoof.cookies.set(COOKIE, raw)
        assert spoof.get(route).status_code == 403


def test_fake_oauth_state_bound_to_mfa_cookie_and_once_claimable(isolated):
    client, engine, factory, raw, stamp = isolated
    start = client.post("/internal/drive/oauth/start", headers=headers(raw))
    assert start.status_code == 200, start.text
    data = start.json()
    state = data["fake_state"]
    assert data["google_authorization_url"] is None
    assert data["google_connection_active"] is False
    assert data["synthetic_only"] is True
    with engine.connect() as db:
        row = db.execute(text("SELECT state_hmac,payload_cipher FROM drive_cloud_oauth_attempts")).one()
        assert state not in str(row)
        assert raw not in str(row)
        assert row[1].startswith("CFOC1:")
    callback = "/internal/drive/oauth/callback"
    params = {"state": state, "code": CODE}
    assert client.get(callback, params={"state": state, "code":"4/0ACTUAL_GOOGLE_CODE"}).status_code == 400
    assert client.get(callback, params={"state": state, "code":CODE, "next":"//evil"}).status_code == 400
    assert client.get(callback, params=[("state",state),("state",state),("code",CODE)]).status_code == 400
    second = session_token()
    # Another authenticated browser cannot steal the first owner's callback.
    with factory() as db:
        now = datetime.now(timezone.utc)
        db.add(models.OwnerSession(
            token_sha256=token_digest(second),
            csrf_sha256=token_digest(csrf_for_session(second)),
            created_at=now, expires_at=now+timedelta(minutes=15), revoked=False,
        ))
        db.commit()
    client.cookies.set(COOKIE, second)
    assert client.get(callback, params=params).status_code == 400
    client.cookies.set(COOKIE, raw)
    success = client.get(callback, params=params)
    assert success.status_code == 200
    assert success.json()["state_claimed_once"] is True
    assert success.json()["google_connection_active"] is False
    assert success.headers["cache-control"] == "no-store"
    assert client.get(callback, params=params).status_code == 400


def test_unbound_oauth_state_cannot_be_claimed_as_bound_or_vice_versa(isolated):
    _, _, factory, raw, _ = isolated
    cfg = private_google_configuration()
    a = begin_google_metadata_consent(cfg)
    b = begin_google_metadata_consent(cfg)
    with factory() as db:
        remember_fake_cloud_attempt(db, pending=a)
        remember_fake_cloud_attempt(db, pending=b, owner_session_digest=token_digest(raw))
    with factory() as db:
        with pytest.raises(CloudOAuthCustodyBlocked):
            claim_fake_cloud_attempt(db, state=a.state,
                                     owner_session_digest=token_digest(raw))
    with factory() as db:
        with pytest.raises(CloudOAuthCustodyBlocked):
            claim_fake_cloud_attempt(db, state=b.state)
    with factory() as db:
        assert claim_fake_cloud_attempt(db, state=a.state).folder_hmac == cfg.folder_hmac
    with factory() as db:
        assert claim_fake_cloud_attempt(db, state=b.state,
                                        owner_session_digest=token_digest(raw)).folder_hmac == cfg.folder_hmac


def test_revocation_logout_session_expiry_and_bad_cookie(isolated):
    client, engine, _, raw, _ = isolated
    assert client.post("/internal/drive/oauth/disconnect",
                       headers=headers(raw)).status_code == 200
    response = client.post("/internal/drive/auth/logout",headers=headers(raw))
    assert response.status_code == 200
    assert response.json()["session_revoked"] is True
    client.cookies.set(COOKIE,raw)
    assert client.get("/internal/drive/oauth/status").status_code == 401
    with engine.begin() as db:
        db.execute(text("UPDATE owner_sessions SET revoked=0, expires_at='2000-01-01T00:00:00+00:00'"))
    assert client.get("/internal/drive/oauth/status").status_code == 401
    client.cookies.set(COOKIE,"short")
    assert client.get("/internal/drive/oauth/status").status_code == 401


def test_mfa_wrong_password_and_totp_replay_not_issuable(isolated):
    _, engine, factory, _, stamp = isolated
    with factory() as db:
        with pytest.raises(OwnerCloudGatewayBlocked):
            provision_fake_mfa_session(db, username="synthetic-owner",
                password="wrong", totp_code=otp(stamp), now_epoch=stamp)
        with pytest.raises(OwnerCloudGatewayBlocked):
            provision_fake_mfa_session(db, username="attacker",
                password=PASSWORD, totp_code=otp(stamp), now_epoch=stamp)
        with pytest.raises(OwnerCloudGatewayBlocked):
            provision_fake_mfa_session(db, username="synthetic-owner",
                password=PASSWORD, totp_code="000000", now_epoch=stamp)
    with factory() as db:
        valid = provision_fake_mfa_session(db, username="synthetic-owner",
                password=PASSWORD, totp_code=otp(stamp), now_epoch=stamp)
        assert len(valid) > 40
    with factory() as db:
        with pytest.raises(OwnerCloudGatewayBlocked):
            provision_fake_mfa_session(db, username="synthetic-owner",
                password=PASSWORD, totp_code=otp(stamp), now_epoch=stamp)


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("P1F_SYNTHETIC_OWNER_GATEWAY_ONLY","0"),
    ("P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY","0"),
    ("P1B_GOOGLE_FOLDER_ID","REAL_OWNER_FOLDER"),
    ("P1B_GOOGLE_CLIENT_ID","real-123456789.apps.googleusercontent.com"),
])
def test_invalid_real_or_disabled_configuration_fails_closed(isolated, monkeypatch, variable, value):
    client, _, _, _, _ = isolated
    monkeypatch.setenv(variable,value)
    result = client.get("/internal/drive/oauth/status")
    assert result.status_code == 503
    assert "REAL_OWNER" not in result.text
    assert "real-123" not in result.text


def test_public_railway_preview_still_has_no_google_auth_routes(isolated):
    routes = {r.path for r in create_preview_app().routes}
    assert not any("/drive/oauth/" in p or "/drive/auth/" in p for p in routes)
    assert "/api/drive/oauth/callback" not in routes
    from pathlib import Path
    nginx = (Path(__file__).parents[2] / "frontend" / "nginx.railway.conf").read_text()
    assert "location = /api/preview/status" in nginx
    assert "location = /api/drive/oauth/callback" in nginx
    assert 'if ($p1ao_google_ingress != "1") { return 404; }' in nginx
    assert "location /api/" not in nginx
    assert "location = /api/drive/oauth/start" in nginx
