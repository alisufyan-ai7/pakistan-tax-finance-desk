"""P1T: fictional-only private MFA -> OAuth HTTP handshake and URL privacy."""
import base64
import hmac
from hashlib import sha1
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models, private_owner_identity as identity  # noqa: F401
from app import private_owner_google_oauth_state as oauth_state
from app.db import Base
from app.drive_google_oauth import PERSONAL_CFO_RAILWAY_CALLBACK
from app.drive_inbox_planner import _index
from app.private_owner_oauth_http_gateway import create_synthetic_private_owner_oauth_gateway
from app.preview_api import create_preview_app

T = 1_800_240_000
OWNER = "SYNTHETIC_OWNER_HTTP_OAUTH_2026"
PASSWORD = "SYNTHETIC_owner_MFA_not_live_2026"
SEED = base64.b32encode(b"J" * 20).decode("ascii")
CLIENT = "000000000000-syntheticdev.apps.googleusercontent.com"
FOLDER = "SYNTHETIC_TEST_FOLDER_ONE_ONLY_2026"
HOST = "personal-cfo-api-preview.railway.internal"
PUBLIC = "https://personal-cfo-frontend-preview-development.up.railway.app"
GATEWAY = "synthetic_private_gateway_key_never_live_2026_00000123456789"
CODE = "SYNTHETIC_NOT_A_GOOGLE_CODE_2026"
COOKIE = "__Host-personal-cfo-owner"


def otp(now=T):
    digest = hmac.new(b"J"*20, (now//30).to_bytes(8,"big"),sha1).digest()
    at = digest[-1] & 15
    return f"{(int.from_bytes(digest[at:at+4], 'big')&0x7fffffff)%1000000:06d}"


def h(*, origin=PUBLIC, **kwargs):
    result = {
        "x-forwarded-proto": "https",
        "x-personal-cfo-private-gateway": GATEWAY,
    }
    if origin is not None:
        result["origin"] = origin
    result.update(kwargs)
    return result


@pytest.fixture
def client(monkeypatch,tmp_path):
    key = lambda b: base64.urlsafe_b64encode(b*32).decode("ascii")
    values = {
        "APP_DATA_MODE":"synthetic",
        "P1N_PRIVATE_OWNER_AUTH_ONLY":"1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED":"1",
        "P1N_SQLITE_FAKE_TEST_ONLY":"1",
        "P1N_OWNER_ENCRYPTION_KEY":key(b"A"),
        "P1N_OWNER_IDENTITY_HMAC_KEY":key(b"B"),
        "P1N_OWNER_SESSION_HMAC_KEY":key(b"C"),
        "P1Q_PRIVATE_HTTP_GATEWAY_ONLY":"1",
        "P1Q_G2_PRIVATE_INGRESS_REVIEWED":"1",
        "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN":GATEWAY,
        "P1Q_PRIVATE_OWNER_REF":OWNER,
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY":"1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY":"1",
        "P1B_GOOGLE_CLIENT_ID":CLIENT,
        "P1B_GOOGLE_REDIRECT_URI":PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_FOLDER_ID":FOLDER,
        "DRIVE_INDEX_HMAC_KEY":key(b"F"),
        "P1R_PRIVATE_OAUTH_STATE_ONLY":"1",
        "P1R_G2_SESSION_OAUTH_REVIEWED":"1",
        "P1R_SQLITE_FAKE_TEST_ONLY":"1",
        "P1R_OAUTH_STATE_ENCRYPTION_KEY":key(b"D"),
        "P1R_OAUTH_STATE_HMAC_KEY":key(b"E"),
        "P1T_SYNTHETIC_HTTP_OAUTH_ONLY":"1",
        "P1T_G2_HTTP_REHEARSAL_REVIEWED":"1",
        "P1C_GOOGLE_NETWORK_ENABLED":"0",
    }
    for name,value in values.items():
        monkeypatch.setenv(name,value)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    monkeypatch.setattr(identity,"_now",lambda epoch=None: T if epoch is None else epoch)
    monkeypatch.setattr(oauth_state,"_now",lambda epoch=None: T if epoch is None else epoch)
    engine = create_engine("sqlite:///"+str(tmp_path/"synthetic-only-private-oauth.db"),
        connect_args={"timeout":10})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        identity.enroll_private_owner(s,owner_ref=OWNER,password=PASSWORD,
            totp_secret_base32=SEED,now_epoch=T,verified_offline_bootstrap=True)
    app = create_synthetic_private_owner_oauth_gateway(lambda:Session(engine))
    with TestClient(app,base_url="https://"+HOST) as c:
        yield c,engine,monkeypatch
    engine.dispose()


def login(c):
    response=c.post("/internal/drive/auth/login",
        headers=h(),json={"password":PASSWORD,"totp_code":otp()})
    assert response.status_code==200,response.text
    return response.json()["csrf_token"]


def start(c,csrf):
    return c.post("/internal/drive/oauth/start",
                  headers=h(**{"x-csrf-token":csrf}))


def state_from_url(url):
    data=parse_qs(urlsplit(url).query)
    return data["state"][0],data


def callback(c,state,*,path=None,headers=None):
    return c.get(path or
        ("/internal/drive/oauth/callback?state="+state+"&code="+CODE),
        headers=h(origin=None) if headers is None else headers,
        follow_redirects=False)


def assert_scrubbed(response,state):
    assert response.status_code==303
    assert response.headers["location"]=="/"
    assert response.headers["cache-control"]=="no-store"
    assert response.headers["referrer-policy"]=="no-referrer"
    assert CODE not in str(response.headers)+response.text
    assert state not in str(response.headers)+response.text


def test_http_mfa_csrf_to_pkce_to_one_time_callback_never_connects_google(client):
    c,engine,_=client
    assert c.get("/internal/drive/oauth/status",headers=h(origin=None)).status_code==401
    csrf=login(c)
    assert c.get("/internal/drive/oauth/status",headers=h(origin=None)).json()["google_drive_app_connected"] is False
    initiated=start(c,csrf)
    assert initiated.status_code==200,initiated.text
    report=initiated.json()
    assert report["synthetic_only"]
    assert report["google_token_exchange_performed"] is False
    assert report["google_connection_active"] is False
    state,params=state_from_url(report["authorization_url"])
    assert params["scope"]==["https://www.googleapis.com/auth/drive.metadata.readonly"]
    assert params["redirect_uri"]==[PERSONAL_CFO_RAILWAY_CALLBACK]
    assert params["code_challenge_method"]==["S256"]
    assert params["client_id"]==[CLIENT]
    with engine.connect() as db:
        raw=str(db.execute(text("SELECT * FROM owner_private_oauth_attempts")).one())
        for private in (state,csrf,CODE,PASSWORD,FOLDER,CLIENT):
            assert private not in raw
        assert "P1R1:" in raw
    reply=callback(c,state)
    assert_scrubbed(reply,state)
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT status FROM owner_private_oauth_attempts")).scalar_one()=="claimed"
    retry=callback(c,state)
    assert_scrubbed(retry,state)
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT COUNT(*) FROM owner_private_oauth_attempts")).scalar_one()==1
    assert not c.get("/internal/drive/oauth/status",
        headers=h(origin=None)).json()["google_drive_app_connected"]


def test_bad_csrf_body_and_wrong_origin_deny_oauth_start(client):
    c,engine,_=client
    csrf=login(c)
    assert start(c,"wrong-csrf").status_code==401
    assert c.post("/internal/drive/oauth/start",
        headers=h(origin="https://attacker.invalid",**{"x-csrf-token":csrf})).status_code==403
    assert c.post("/internal/drive/oauth/start",
        headers=h(**{"x-csrf-token":csrf}),json={}).status_code==400
    assert c.post("/internal/drive/oauth/start?override=1",
        headers=h(**{"x-csrf-token":csrf})).status_code==403
    assert c.post("/internal/drive/oauth/start",
        headers=h(**{"x-csrf-token":csrf,"x-forwarded-host":"bad.example"})).status_code==403
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT count(*) FROM owner_private_oauth_attempts")).scalar_one()==0


def test_duplicate_callback_query_missing_session_and_bad_code_do_not_claim(client):
    c,engine,_=client
    csrf=login(c)
    state,_=state_from_url(start(c,csrf).json()["authorization_url"])
    malformed=[
        "/internal/drive/oauth/callback?state="+state+"&state="+state+"&code="+CODE,
        "/internal/drive/oauth/callback?state="+state+"&code="+CODE+"&code="+CODE,
        "/internal/drive/oauth/callback?error=access_denied&state="+state,
        "/internal/drive/oauth/callback?state="+state+"&code=short",
        "/internal/drive/oauth/callback?state="+state,
    ]
    for path in malformed:
        assert_scrubbed(callback(c,state,path=path),state)
    c.cookies.clear()
    assert_scrubbed(callback(c,state),state)
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT status FROM owner_private_oauth_attempts")).scalar_one()=="pending"


@pytest.mark.parametrize("name,value",[
    ("P1T_G2_HTTP_REHEARSAL_REVIEWED","0"),
    ("P1B_GOOGLE_CLIENT_ID","717001562537-b5ot38lac68nu4atlt3grvatg92p3ql4.apps.googleusercontent.com"),
    ("P1B_GOOGLE_FOLDER_ID","OWNER_REAL_FOLDER_MUST_NOT_BE_ACCEPTED"),
    ("P1C_GOOGLE_NETWORK_ENABLED","1"),
    ("APP_DATA_MODE","real"),
])
def test_fake_only_contract_cannot_be_upgraded_to_live_google_by_flags(client,name,value):
    c,engine,monkeypatch=client
    csrf=login(c)
    monkeypatch.setenv(name,value)
    assert start(c,csrf).status_code==503
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT COUNT(*) FROM owner_private_oauth_attempts")).scalar_one()==0


def test_only_separately_instantiated_candidate_has_oauth_http_routes(client):
    c,_,_=client
    candidate={r.path for r in c.app.routes}
    assert {"/internal/drive/oauth/start",
            "/internal/drive/oauth/callback",
            "/internal/drive/oauth/status"} <= candidate
    assert "/internal/drive/oauth/disconnect" not in candidate
    assert "/internal/finance/ledger" not in candidate
    live={r.path for r in create_preview_app().routes}
    assert not any(x.startswith("/internal/drive/oauth/") for x in live)
    assert "/api/drive/oauth/callback" not in live
