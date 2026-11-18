"""P1G #110: isolated MFA HTTP contract, fail-closed hostile requests."""
from __future__ import annotations
import base64
import hashlib
import hmac
from datetime import datetime,timezone
from time import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.db import Base
from app.auth_mfa import password_hash,csrf_for_session,token_digest
from app.drive_inbox_planner import _index
from app.drive_google_oauth import PERSONAL_CFO_RAILWAY_CALLBACK
from app.drive_cloud_owner_gateway import COOKIE,ORIGIN,HOST
from app.owner_login_http_candidate import create_fake_owner_login_http
from app.preview_api import create_preview_app

PASSWORD="synthetic-fake-login-password-256-bit"
SECRET=base64.b32encode(b"fictional-login-http-totp-key-1122").decode()
FOLDER="SYNTHETIC_P1G_HTTP_PRIVATE_FOLDER_2026"


def current_code():
    epoch=int(time())
    key=base64.b32decode(SECRET)
    mac=hmac.new(key,(epoch//30).to_bytes(8,"big"),hashlib.sha1).digest()
    offset=mac[-1]&15
    return f"{((int.from_bytes(mac[offset:offset+4],'big') & 0x7fffffff)%1000000):06d}"


@pytest.fixture
def fixture(tmp_path,monkeypatch):
    data={
        "APP_DATA_MODE":"synthetic",
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY":"1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY":"1",
        "P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY":"1",
        "P1E_SQLITE_TEST_ONLY":"1",
        "P1F_SYNTHETIC_OWNER_GATEWAY_ONLY":"1",
        "P1G_FAKE_LOGIN_THROTTLE_ONLY":"1",
        "P1G_FAKE_LOGIN_HTTP_CONTRACT_ONLY":"1",
        "P1G_SQLITE_TEST_ONLY":"1",
        "P1B_GOOGLE_REDIRECT_URI":PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_CLIENT_ID":"000000000000-syntheticdev.apps.googleusercontent.com",
        "P1B_GOOGLE_FOLDER_ID":FOLDER,
        "DRIVE_INDEX_HMAC_KEY":base64.urlsafe_b64encode(b"D"*32).decode(),
        "P1E_FAKE_CLOUD_VAULT_KEY":base64.urlsafe_b64encode(b"E"*32).decode(),
        "P1E_FAKE_CLOUD_INDEX_KEY":base64.urlsafe_b64encode(b"J"*32).decode(),
        "P1G_FAKE_THROTTLE_KEY":base64.urlsafe_b64encode(b"T"*32).decode(),
        "P1F_FAKE_OWNER_PASSWORD_SCRYPT":password_hash(PASSWORD,bytes(range(16))),
        "P1F_FAKE_OWNER_TOTP_SECRET":SECRET,
    }
    for k,v in data.items():
        monkeypatch.setenv(k,v)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    engine=create_engine("sqlite:///"+str(tmp_path/"http-owner-fake.db"),connect_args={"timeout":10})
    Base.metadata.create_all(engine)
    factory=lambda:Session(engine)
    with TestClient(create_fake_owner_login_http(factory),base_url=ORIGIN) as client:
        yield client,engine,monkeypatch,factory
    engine.dispose()


def valid():
    return {"username":"synthetic-owner","password":PASSWORD,"totp_code":current_code()}


def login(client,body=None,headers=None):
    return client.post("/internal/drive/auth/login",json=valid() if body is None else body,
                       headers={"Origin":ORIGIN,**(headers or {})})


def test_fake_login_cookie_status_rotate_logout_and_database_hash(fixture):
    client,engine,_,_=fixture
    response=login(client)
    assert response.status_code==200,response.text
    assert response.json()=={"synthetic_only":True,"mfa_session_issued":True,
                              "google_drive_connected":False,"real_data_authorized":False}
    cookie=response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    old_cookie=client.cookies.get(COOKIE)
    assert old_cookie is not None and len(old_cookie)>40
    with engine.connect() as conn:
        token=conn.execute(text("SELECT token_sha256 FROM owner_sessions")).scalar_one()
        assert len(token)==64 and token==token_digest(old_cookie)
        assert old_cookie not in str(conn.execute(text(
            "SELECT owner_hmac,failures FROM owner_login_throttles")).one())
    status=client.get("/internal/drive/auth/session")
    assert status.status_code==200
    assert status.headers["cache-control"]=="no-store"
    csrf=status.json()["csrf_token"]
    assert csrf==csrf_for_session(old_cookie)
    assert client.post("/internal/drive/auth/rotate",headers={"Origin":ORIGIN}).status_code==403
    rotated=client.post("/internal/drive/auth/rotate",headers={
        "Origin":ORIGIN,"X-CSRF-Token":csrf})
    assert rotated.status_code==200
    second=client.cookies.get(COOKIE)
    assert second!=old_cookie
    client.cookies.set(COOKIE,old_cookie)
    assert client.get("/internal/drive/auth/session").status_code==401
    client.cookies.set(COOKIE,second)
    csrf2=client.get("/internal/drive/auth/session").json()["csrf_token"]
    assert csrf2!=csrf
    response=client.post("/internal/drive/auth/logout",headers={
        "Origin":ORIGIN,"X-CSRF-Token":csrf2})
    assert response.status_code==200
    client.cookies.set(COOKIE,second)
    assert client.get("/internal/drive/auth/session").status_code==401


def test_locked_after_five_attempts_no_cookie_or_secrets(fixture):
    client,engine,_,_=fixture
    payload=valid()
    payload["password"]="wrong"
    for n in range(5):
        response=login(client,payload)
        assert response.status_code==401
        assert "set-cookie" not in response.headers
        assert PASSWORD not in response.text and SECRET not in response.text
    denied=login(client)
    assert denied.status_code==401 and "set-cookie" not in denied.headers
    with engine.connect() as conn:
        assert conn.execute(text("SELECT failures FROM owner_login_throttles")).scalar_one()==5
        assert conn.execute(text("SELECT count(*) FROM owner_sessions")).scalar_one()==0


def test_origin_tls_host_methods_and_json_bounds(fixture):
    client,engine,_,factory=fixture
    assert client.post("/internal/drive/auth/login",json=valid()).status_code==403
    assert login(client,headers={"Origin":"https://evil.example"}).status_code==403
    assert login(client,headers={"X-Forwarded-Proto":"https"}).status_code==403
    assert login(client,headers={"X-Forwarded-Host":HOST}).status_code==403
    assert login(client,headers={"Host":"evil.example"}).status_code==403
    assert login(client,headers={"Host":HOST+":8443"}).status_code==403
    assert client.get("/internal/drive/auth/login").status_code==405
    assert login(client,headers={"Content-Type":"text/plain"}).status_code==415
    assert login(client,{"username":"synthetic-owner","password":PASSWORD,"totp_code":"123456","leak":"x"}).status_code==400
    assert login(client,{"username":"synthetic-owner","password":"x"*700,"totp_code":"123456"}).status_code==400
    assert login(client,headers={"Origin":ORIGIN},body={"username":"synthetic-owner",
        "password":PASSWORD,"totp_code":"000000"}).status_code==401
    assert client.get("/docs").status_code==404
    assert client.get("/openapi.json").status_code==404
    with TestClient(create_fake_owner_login_http(factory),base_url="http://"+HOST) as bad:
        assert bad.post("/internal/drive/auth/login",json=valid(),
                        headers={"Origin":ORIGIN}).status_code==403


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("P1G_FAKE_LOGIN_HTTP_CONTRACT_ONLY","0"),
    ("P1G_FAKE_LOGIN_THROTTLE_ONLY","0"),
])
def test_missing_contract_and_real_mode_fail_closed(fixture,variable,value):
    client,engine,monkeypatch,_=fixture
    monkeypatch.setenv(variable,value)
    response=login(client)
    assert response.status_code in (401,503)
    assert "set-cookie" not in response.headers
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM owner_sessions")).scalar_one()==0


def test_no_public_auth_proxy_or_live_financial_access(fixture):
    routes={r.path for r in create_preview_app().routes}
    assert "/internal/drive/auth/login" not in routes
    assert "/internal/drive/auth/rotate" not in routes
    assert "/api/drive/oauth/callback" not in routes
    assert "/api/owner/login" not in routes
    from pathlib import Path
    nginx=(Path(__file__).parents[2]/"frontend/nginx.railway.conf").read_text()
    assert "location /api/" not in nginx
    assert "location = /api/drive/oauth/callback" not in nginx
    assert "location = /api/owner/login" in nginx
    assert 'if ($p1ak_owner_ingress != "1") { return 404; }' in nginx
    assert "location = /api/drive/oauth/start" not in nginx
