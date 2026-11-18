"""P1Q: fake-only private HTTP login/session/logout with exact-ingress controls."""
import base64
from hashlib import sha1
import hmac
import json

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models, private_owner_identity as identity  # noqa: F401
from app.db import Base
from app.private_owner_http_gateway import create_private_owner_http_gateway
from app.preview_api import create_preview_app

T = 1_800_200_000
OWNER = "SYNTHETIC_OWNER_HTTP_0000000001"
PASSWORD = "SYNTHETIC_owner_HTTP_passphrase_2026"
SEED = base64.b32encode(b"J"*20).decode("ascii")
HOST = "personal-cfo-api-preview.railway.internal"
ORIGIN = "https://personal-cfo-frontend-preview-development.up.railway.app"
SECRET = "synthetic_private_gateway_never_live_value_2026_0123456789ABCDEFG"
COOKIE = "__Host-personal-cfo-owner"


def otp(now=T):
    raw = base64.b32decode(SEED)
    digest = hmac.new(raw, (now//30).to_bytes(8,"big"), sha1).digest()
    p = digest[-1] & 15
    return f"{(int.from_bytes(digest[p:p+4], 'big')&0x7fffffff)%1000000:06d}"


@pytest.fixture
def client(monkeypatch,tmp_path):
    key = lambda b: base64.urlsafe_b64encode(b*32).decode("ascii")
    env = {
        "APP_DATA_MODE": "synthetic",
        "P1N_PRIVATE_OWNER_AUTH_ONLY": "1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED": "1",
        "P1N_SQLITE_FAKE_TEST_ONLY": "1",
        "P1N_OWNER_ENCRYPTION_KEY": key(b"A"),
        "P1N_OWNER_IDENTITY_HMAC_KEY": key(b"B"),
        "P1N_OWNER_SESSION_HMAC_KEY": key(b"C"),
        "P1Q_PRIVATE_HTTP_GATEWAY_ONLY": "1",
        "P1Q_G2_PRIVATE_INGRESS_REVIEWED": "1",
        "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN": SECRET,
        "P1W_OWNER_REF": OWNER,
    }
    for name, value in env.items():
        monkeypatch.setenv(name,value)
    monkeypatch.setattr(identity,"_now",lambda now_epoch=None: T if now_epoch is None else now_epoch)
    engine = create_engine("sqlite:///"+str(tmp_path/"fake-http-gateway.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        identity.enroll_private_owner(
            db, owner_ref=OWNER, password=PASSWORD,
            totp_secret_base32=SEED, now_epoch=T,
            verified_offline_bootstrap=True)
    app = create_private_owner_http_gateway(lambda: Session(engine))
    with TestClient(app,base_url="https://"+HOST) as c:
        yield c, monkeypatch, engine
    engine.dispose()


def headers(*, origin=ORIGIN, token=SECRET, proto="https", **extra):
    result = {"x-forwarded-proto":proto,
              "x-personal-cfo-private-gateway":token}
    if origin is not None:
        result["origin"] = origin
    result.update(extra)
    return result


def login(c, **kwargs):
    return c.post("/internal/drive/auth/login", headers=kwargs.pop("headers",headers()),
        json={"password":kwargs.get("password",PASSWORD),
              "totp_code":kwargs.get("code",otp())})


def test_private_login_cookie_status_and_logout_csrf(client):
    c, _, engine = client
    assert c.get("/internal/drive/auth/session", headers=headers()).status_code == 401
    response = login(c)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["google_connected"] is False
    assert payload["real_financial_data_enabled"] is False
    csrf = payload["csrf_token"]
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(COOKIE+"=")
    assert "httponly" in cookie.lower() and "secure" in cookie.lower()
    assert "samesite=lax" in cookie.lower() and "path=/" in cookie.lower()
    assert "domain=" not in cookie.lower()
    for key in ("Cache-Control","Referrer-Policy","X-Frame-Options"):
        assert key in response.headers
    status = c.get("/internal/drive/auth/session",headers=headers(origin=None))
    assert status.status_code == 200 and status.json()["authenticated"]
    denied = c.post("/internal/drive/auth/logout",
         headers={**headers(), "x-csrf-token":"fake-invalid-token"})
    assert denied.status_code == 401
    out = c.post("/internal/drive/auth/logout",
        headers={**headers(),"x-csrf-token":csrf})
    assert out.status_code == 200 and out.json()["local_session_revoked"]
    assert out.json()["google_grant_revoked"] is False
    assert c.get("/internal/drive/auth/session",headers=headers(origin=None)).status_code == 401
    with engine.connect() as db:
        raw = str(db.execute(text("SELECT * FROM owner_private_sessions")).all())
        assert PASSWORD not in raw and SEED not in raw and SECRET not in raw
        assert csrf not in raw


@pytest.mark.parametrize("bad", [
    {"origin":"https://evil.invalid"},
    {"origin":None},
    {"token":"WRONG_"+"A"*60},
    {"proto":"http"},
    {"extra":{"x-forwarded-host":"untrusted.example"}},
    {"extra":{"x-forwarded-for":"198.51.100.55"}},
    {"extra":{"forwarded":"host=example.com"}},
])
def test_login_rejects_untrusted_edge_origin_and_spoofed_proxy_headers(client,bad):
    c,_,_ = client
    args = dict(bad)
    extra = args.pop("extra",{})
    h = headers(**args,**extra)
    assert login(c,headers=h).status_code == 403


def test_wrong_password_bad_totp_and_body_shape_fail_without_secrets(client):
    c,_,_=client
    wrong=login(c,password="SYNTHETIC_fake_wrong_passphrase")
    assert wrong.status_code == 401
    assert PASSWORD not in wrong.text and SEED not in wrong.text
    assert login(c,code="abc123").status_code == 400
    assert c.post("/internal/drive/auth/login",headers=headers(),
                  data='{"password":"fake","password":"double"}').status_code in (400,415)
    assert c.post("/internal/drive/auth/login",headers=headers(),
        content=b"x"*3000).status_code in (400,415)


def test_gateway_never_exposes_wildcard_google_finance_recovery_or_cors(client):
    c,_,_=client
    for path in (
        "/internal/drive/oauth/callback", "/internal/drive/oauth/start",
        "/internal/finance/ledger", "/internal/drive/auth/recovery",
        "/api/owner/login","/api/drive/oauth/callback"
    ):
        assert c.get(path,headers=headers(origin=None)).status_code == 404
    for path in ("/internal/drive/auth/login","/internal/drive/auth/logout"):
        assert c.get(path,headers=headers(origin=None)).status_code == 405
    live_paths={r.path for r in create_preview_app().routes}
    assert not any("/internal/drive/auth/" in s for s in live_paths)


def test_default_off_real_finance_missing_owner_and_wrong_gateway_secret_block(client):
    c,monkeypatch,_=client
    monkeypatch.setenv("P1Q_PRIVATE_HTTP_GATEWAY_ONLY","0")
    assert login(c).status_code == 503
    monkeypatch.setenv("P1Q_PRIVATE_HTTP_GATEWAY_ONLY","1")
    monkeypatch.setenv("APP_DATA_MODE","real")
    assert login(c).status_code == 503
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1W_OWNER_REF","")
    assert login(c).status_code == 503
    monkeypatch.setenv("P1W_OWNER_REF",OWNER)
    monkeypatch.setenv("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN","bad")
    assert login(c).status_code == 403



def test_duplicate_valid_login_members_and_transfer_encoding_denied(client):
    c, _, engine = client
    # All individual values are otherwise valid. A parser that silently
    # accepts the last repeated member can create credential ambiguity.
    for duplicated in (
        ('{"password":"' + PASSWORD + '","password":"' + PASSWORD
         + '","totp_code":"' + otp() + '"}'),
        ('{"password":"' + PASSWORD + '","totp_code":"' + otp()
         + '","totp_code":"' + otp() + '"}'),
    ):
        response = c.post(
            "/internal/drive/auth/login",
            headers={**headers(), "content-type": "application/json"},
            content=duplicated.encode("ascii"),
        )
        assert response.status_code == 400
        assert PASSWORD not in response.text
        assert SEED not in response.text

    # No owner session or replay counter should result from malformed JSON.
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT COUNT(*) FROM owner_private_sessions"
        )).scalar_one() == 0
    assert login(c).status_code == 200



def test_legacy_duplicate_owner_reference_cannot_replace_escrowed_one(client):
    c, monkeypatch, _ = client
    monkeypatch.delenv("P1W_OWNER_REF")
    monkeypatch.setenv("P1Q_PRIVATE_OWNER_REF", OWNER)
    assert login(c).status_code == 503
    monkeypatch.setenv("P1W_OWNER_REF", OWNER)
    assert login(c).status_code == 200
