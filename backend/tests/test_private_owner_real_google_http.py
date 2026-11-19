"""P1AL: fake-provider integration of real-compatible Google metadata routes."""
import base64
import hmac
import json
from hashlib import sha1
from urllib.parse import parse_qs, urlsplit, urlencode

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models, private_owner_identity as identity  # noqa: F401
from app import private_owner_google_oauth_state as oauth_state
from app.db import Base
from app.drive_google_oauth import (
    GOOGLE_METADATA_SCOPE, PERSONAL_CFO_RAILWAY_CALLBACK,
)
from app.drive_inbox_planner import _index
from app.private_owner_real_google_http import (
    create_review_only_private_google_http_gateway,
)
from app.preview_api import create_preview_app

T = 1_800_270_000
OWNER = "SYNTHETIC_REAL_CLOUD_OWNER_2026"
PASSWORD = "SYNTHETIC_cloud_owner_passphrase_not_real"
SEED = base64.b32encode(b"J" * 20).decode("ascii")
CLIENT = "000000000000-syntheticdev.apps.googleusercontent.com"
FOLDER = "SYNTHETIC_APPROVED_OWNER_CLOUD_FOLDER_2026"
GATEWAY = "SYNTHETIC_PRIVATE_GATEWAY_CLOUD_2026_" + "F" * 48
HOST = "personal-cfo-api-preview.railway.internal"
PUBLIC = "https://personal-cfo-frontend-preview-development.up.railway.app"
ACCESS = "synthetic_access_token_never_google_" + "A" * 25
REFRESH = "synthetic_refresh_token_never_google_" + "B" * 30
CODE = "SYNTHETIC_OAUTH_CODE_NOT_GOOGLE_2026"


def key(byte):
    return base64.urlsafe_b64encode(bytes([byte]) * 32).decode("ascii")


def otp():
    digest = hmac.new(b"J" * 20, (T // 30).to_bytes(8, "big"), sha1).digest()
    pos = digest[-1] & 15
    return f"{(int.from_bytes(digest[pos:pos+4], 'big') & 0x7fffffff)%1000000:06d}"


def headers(*, origin=PUBLIC, csrf=None):
    value = {
        "x-forwarded-proto": "https",
        "x-personal-cfo-private-gateway": GATEWAY,
    }
    if origin is not None:
        value["origin"] = origin
    if csrf is not None:
        value["x-csrf-token"] = csrf
    return value


@pytest.fixture
def owner_client(monkeypatch, tmp_path):
    env = {
        "APP_DATA_MODE": "synthetic",
        "P1N_PRIVATE_OWNER_AUTH_ONLY": "1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED": "1",
        "P1N_SQLITE_FAKE_TEST_ONLY": "1",
        "P1N_OWNER_ENCRYPTION_KEY": key(1),
        "P1N_OWNER_IDENTITY_HMAC_KEY": key(2),
        "P1N_OWNER_SESSION_HMAC_KEY": key(3),
        "P1W_OWNER_REF": OWNER,
        "P1Q_PRIVATE_HTTP_GATEWAY_ONLY": "1",
        "P1Q_G2_PRIVATE_INGRESS_REVIEWED": "1",
        "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN": GATEWAY,
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY": "1",
        "P1B_GOOGLE_CLIENT_ID": CLIENT,
        "P1B_GOOGLE_REDIRECT_URI": PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_FOLDER_ID": FOLDER,
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY": "1",
        "DRIVE_INDEX_HMAC_KEY": key(4),
        "P1R_PRIVATE_OAUTH_STATE_ONLY": "1",
        "P1R_G2_SESSION_OAUTH_REVIEWED": "1",
        "P1R_SQLITE_FAKE_TEST_ONLY": "1",
        "P1R_OAUTH_STATE_ENCRYPTION_KEY": key(5),
        "P1R_OAUTH_STATE_HMAC_KEY": key(6),
        "P1M_PRIVATE_METADATA_CUSTODY_ONLY": "1",
        "P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED": "1",
        "P1M_SQLITE_FAKE_TEST_ONLY": "1",
        "P1M_METADATA_ENCRYPTION_KEYS_JSON": json.dumps({
            "cfo-google-key-v1": key(7),
            "cfo-google-key-v2": key(8),
        }),
        "P1M_METADATA_ACTIVE_KEY_ID": "cfo-google-key-v2",
        "P1M_METADATA_ROW_HMAC_KEY": key(9),
        "P1AL_CLOUD_METADATA_NETWORK_ONLY": "1",
        "P1AL_G2_EXACT_OAUTH_REVIEWED": "1",
        "P1C_GOOGLE_NETWORK_ENABLED": "1",
        "P1C_PRIVATE_OWNER_MFA_ACCEPTED": "1",
        "P1C_GOOGLE_CLIENT_SECRET": "synthetic_web_client_secret_not_real_2026",
        "P1AJ_OWNER_LOGIN_RUNTIME": "1",
        "P1AJ_G2_EXACT_INGRESS_REVIEWED": "1",
        "P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED": "1",
    }
    for k, value in env.items():
        monkeypatch.setenv(k, value)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    monkeypatch.setattr(identity, "_now",
                        lambda now_epoch=None: T if now_epoch is None else now_epoch)
    monkeypatch.setattr(oauth_state, "_now",
                        lambda now_epoch=None: T if now_epoch is None else now_epoch)

    engine = create_engine("sqlite:///" + str(tmp_path / "fictional-owner.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        identity.enroll_private_owner(
            db, owner_ref=OWNER, password=PASSWORD,
            totp_secret_base32=SEED, now_epoch=T,
            verified_offline_bootstrap=True,
        )
    seen = []

    def transport(method, url, form, bearer):
        seen.append((method, url, form is not None, bearer is not None))
        if method == "POST" and url == "https://oauth2.googleapis.com/token":
            assert form["grant_type"] == "authorization_code"
            assert form["code"] == CODE
            assert form["redirect_uri"] == PERSONAL_CFO_RAILWAY_CALLBACK
            assert bearer is None
            return {
                "access_token": ACCESS,
                "refresh_token": REFRESH,
                "scope": GOOGLE_METADATA_SCOPE,
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        if method == "GET" and url.startswith(
            "https://www.googleapis.com/drive/v3/files/" + FOLDER
        ):
            assert form is None and bearer == ACCESS
            return {
                "id": FOLDER,
                "mimeType": "application/vnd.google-apps.folder",
                "trashed": False,
                "shared": False,
                "owners": [{"me": True}],
            }
        raise AssertionError("Forbidden external request in fake transport")

    app = create_review_only_private_google_http_gateway(
        lambda: Session(engine), transport=transport,
    )
    with TestClient(app, base_url="https://" + HOST) as c:
        yield c, engine, seen, monkeypatch
    engine.dispose()


def login(c):
    r = c.post("/internal/drive/auth/login", headers=headers(),
               json={"password": PASSWORD, "totp_code": otp()})
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


def state_from(c, csrf):
    r = c.post("/internal/drive/oauth/start", headers=headers(csrf=csrf))
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["scope"] == "DRIVE_METADATA_ONLY"
    url = payload["authorization_url"]
    parsed = parse_qs(urlsplit(url).query)
    assert parsed["scope"] == [GOOGLE_METADATA_SCOPE]
    assert parsed["redirect_uri"] == [PERSONAL_CFO_RAILWAY_CALLBACK]
    assert parsed["code_challenge_method"] == ["S256"]
    assert parsed["client_id"] == [CLIENT]
    return parsed["state"][0]


def callback(c, state, *, path=None):
    return c.get(
        path or "/internal/drive/oauth/callback?state=" + state + "&code=" + CODE,
        headers=headers(origin=None), follow_redirects=False,
    )


def assert_scrubbed(r, state):
    assert r.status_code == 303
    assert r.headers["location"] == "/owner-login"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert state not in str(r.headers) + r.text
    assert CODE not in str(r.headers) + r.text
    assert REFRESH not in str(r.headers) + r.text


def test_encrypted_real_compatible_google_consent_with_fake_provider(owner_client):
    c, engine, seen, _ = owner_client
    assert c.get("/internal/drive/oauth/status",
                 headers=headers(origin=None)).status_code == 401
    csrf = login(c)
    state = state_from(c, csrf)
    assert c.get("/internal/drive/oauth/status",
                 headers=headers(origin=None)).json()["google_drive_app_connected"] is False
    r = callback(c, state)
    assert_scrubbed(r, state)
    assert [x[0] for x in seen] == ["POST", "GET"]
    status = c.get("/internal/drive/oauth/status",
                   headers=headers(origin=None))
    assert status.status_code == 200
    assert status.json()["google_drive_app_connected"] is True
    assert status.json()["original_content_import_enabled"] is False
    with engine.connect() as db:
        grant = str(db.execute(text(
            "SELECT * FROM owner_google_metadata_grants"
        )).one())
        attempt = str(db.execute(text(
            "SELECT * FROM owner_private_oauth_attempts"
        )).one())
        assert "P1M1:" in grant
        assert "claimed" in attempt
        for secret in (REFRESH, CODE, state, ACCESS, PASSWORD, FOLDER):
            assert secret not in grant + attempt

    retry = callback(c, state)
    assert_scrubbed(retry, state)
    assert len(seen) == 2  # no repeat provider exchange


@pytest.mark.parametrize("change", [
    "duplicate_state", "duplicate_code", "no_code",
    "wrong_state", "missing_cookie", "wrong_gateway",
])
def test_untrusted_callback_scrubbed_without_google_request(owner_client,change):
    c, engine, seen, _ = owner_client
    state = state_from(c, login(c))
    path = "/internal/drive/oauth/callback?state=" + state + "&code=" + CODE
    if change == "duplicate_state":
        path += "&state=" + state
    elif change == "duplicate_code":
        path += "&code=" + CODE
    elif change == "no_code":
        path = "/internal/drive/oauth/callback?state=" + state
    elif change == "wrong_state":
        path = "/internal/drive/oauth/callback?state=" + "F"*48 + "&code=" + CODE
    elif change == "missing_cookie":
        c.cookies.clear()
    elif change == "wrong_gateway":
        r = c.get(path, headers={
            **headers(origin=None),
            "x-personal-cfo-private-gateway": "SYNTHETIC_" + "Q"*60,
        }, follow_redirects=False)
        assert_scrubbed(r, state)
        assert seen == []
        return
    assert_scrubbed(callback(c,state,path=path),state)
    assert seen == []
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT status FROM owner_private_oauth_attempts"
        )).scalar_one() == "pending"


def test_default_off_and_wrong_origin_block_start(owner_client):
    c, _, seen, monkeypatch = owner_client
    csrf = login(c)
    assert c.post("/internal/drive/oauth/start",
                  headers=headers(origin="https://evil.invalid",csrf=csrf)).status_code == 403
    assert c.post("/internal/drive/oauth/start",
                  headers=headers(csrf="invalid")).status_code == 401
    assert c.post("/internal/drive/oauth/start",
                  headers=headers(csrf=csrf),json={}).status_code == 400
    monkeypatch.setenv("P1AL_CLOUD_METADATA_NETWORK_ONLY","0")
    assert c.post("/internal/drive/oauth/start",
                  headers=headers(csrf=csrf)).status_code == 503
    assert seen == []
    assert "/internal/drive/oauth/callback" not in {
        r.path for r in create_preview_app().routes
    }



def test_owner_session_can_resume_after_google_callback_without_new_totp(
    owner_client,
):
    """Navigation destroys in-memory CSRF, never the HttpOnly session cookie."""
    c, _, seen, _ = owner_client
    initial_csrf = login(c)
    state = state_from(c, initial_csrf)
    assert_scrubbed(callback(c, state), state)
    rejoined = c.get(
        "/internal/drive/auth/session", headers=headers(origin=None),
    )
    assert rejoined.status_code == 200
    refreshed = rejoined.json()
    assert refreshed["authenticated"] is True
    assert refreshed["real_financial_data_enabled"] is False
    assert refreshed["csrf_token"] != initial_csrf
    assert len(refreshed["csrf_token"]) >= 40
    assert c.post(
        "/internal/drive/oauth/start",
        headers=headers(csrf=initial_csrf),
    ).status_code == 401
    assert c.post(
        "/internal/drive/oauth/start",
        headers=headers(csrf=refreshed["csrf_token"]),
    ).status_code == 200
    assert len(seen) == 2  # No new Google network request on OAuth start.



def test_private_owner_documents_reuses_bounded_p1ap_snapshot_after_csrf(
    owner_client,
):
    from app import private_owner_real_google_http as app_http
    c, _, seen, monkeypatch = owner_client
    csrf = login(c)
    snapshot = {
        "contract": "personal_cfo_owner_metadata_review_preview_v1",
        "connection": "APPROVED_METADATA_GRANT_USED",
        "folder": "ONE_OWNER_APPROVED_FOLDER",
        "snapshot_complete": True,
        "total": 1,
        "items": [{
            "display_name": "SYNTHETIC.pdf",
            "virtual_collection": "bank_statements",
            "review_status": "needs_review",
            "size_bytes": 123,
            "modified_time": "2026-11-18T00:00:00+00:00",
            "original_content_imported": False,
            "financial_claims_verified": False,
        }],
        "snapshot_persisted": False,
        "background_sync_active": False,
        "source_bytes_downloaded": False,
        "real_financial_data_enabled": False,
    }
    calls = []
    def fake_snapshot(**kwargs):
        assert kwargs["owner_ref"] == OWNER
        assert callable(kwargs["session_factory"])
        calls.append(True)
        return snapshot
    monkeypatch.setattr(app_http, "scan_one_owner_folder_metadata", fake_snapshot)
    for bad in (
        c.post("/internal/drive/metadata/refresh",
               headers=headers(csrf="bad")),
        c.post("/internal/drive/metadata/refresh",
               headers=headers(csrf=csrf, origin="https://evil.invalid")),
        c.post("/internal/drive/metadata/refresh",
               headers=headers(csrf=csrf), json={}),
        c.post("/internal/drive/metadata/refresh?override=1",
               headers=headers(csrf=csrf)),
    ):
        assert bad.status_code in (400, 401, 403)
    assert calls == []
    response = c.post(
        "/internal/drive/metadata/refresh", headers=headers(csrf=csrf)
    )
    assert response.status_code == 200
    assert response.json() == snapshot
    assert response.headers["cache-control"] == "no-store"
    assert calls == [True]
    assert seen == []  # No Google network in this authenticated shell test.


@pytest.mark.parametrize("ancillary", [
    {"scope": GOOGLE_METADATA_SCOPE, "authuser": "0", "prompt": "consent"},
    {"scope": GOOGLE_METADATA_SCOPE, "authuser": "0", "prompt": "consent",
     "hd": "example.com", "iss": "https://accounts.google.com"},
    {"scope": GOOGLE_METADATA_SCOPE, "hd": "example.com",
     "unknown_google_response_field": "unrecognized_but_ignored"},
    {"authuser": "not_used_for_identity", "prompt": "account_selection_changed"},
])
def test_real_google_callback_ignores_ancillary_fields_per_rfc6749(
    owner_client, ancillary,
):
    """Only code+bound PKCE state authorize; Google may add hd/iss/etc."""
    c, engine, seen, _ = owner_client
    state = state_from(c, login(c))
    query = urlencode({"state": state, "code": CODE, **ancillary})
    response = callback(c, state, path="/internal/drive/oauth/callback?" + query)
    assert_scrubbed(response, state)
    assert [method for method, *_ in seen] == ["POST", "GET"]
    status = c.get("/internal/drive/oauth/status", headers=headers(origin=None))
    assert status.status_code == 200
    assert status.json()["google_drive_app_connected"] is True
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants"
        )).scalar_one() == 1
        assert db.execute(text(
            "SELECT status FROM owner_private_oauth_attempts"
        )).scalar_one() == "claimed"


@pytest.mark.parametrize("addition", [
    "&scope=" + GOOGLE_METADATA_SCOPE + "&scope=" + GOOGLE_METADATA_SCOPE,
    "&authuser=0&authuser=1",
    "&prompt=consent&prompt=consent",
    "&code=ANOTHER_FAKE_CODE_DO_NOT_ACCEPT",
    "&iss=https%3A%2F%2Fevil.invalid",
    "&iss=https%3A%2F%2Faccounts.google.com&iss=https%3A%2F%2Faccounts.google.com",
    "&error=access_denied",
    "&error_description=test",
    "&%0A=bad_name",
    "&unknown=" + "F"*2100,
])
def test_invalid_or_ambiguous_oauth_response_still_fails_closed(
    owner_client, addition,
):
    c, engine, seen, _ = owner_client
    state = state_from(c, login(c))
    base = "/internal/drive/oauth/callback?state=" + state + "&code=" + CODE
    assert_scrubbed(callback(c, state, path=base + addition), state)
    assert seen == []
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT status FROM owner_private_oauth_attempts"
        )).scalar_one() == "pending"
        assert db.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants"
        )).scalar_one() == 0


def test_actual_token_scope_must_remain_exact_metadata_readonly(
    owner_client, monkeypatch,
):
    from app import private_owner_real_google_http as google_http
    c, engine, seen, _ = owner_client
    state = state_from(c, login(c))
    def scope_denied(**kwargs):
        from app.private_drive_google_http import PrivateGoogleNetworkBlocked
        raise PrivateGoogleNetworkBlocked(
            "Provider token missing exact metadata scope"
        )
    monkeypatch.setattr(google_http, "exchange_google_code", scope_denied)
    assert_scrubbed(callback(
        c, state, path="/internal/drive/oauth/callback?" + urlencode({
            "state": state, "code": CODE, "hd": "example.com",
            "iss": "https://accounts.google.com",
        }),
    ), state)
    status = c.get("/internal/drive/oauth/status", headers=headers(origin=None))
    assert status.json()["google_drive_app_connected"] is False
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants"
        )).scalar_one() == 0


def test_provider_failure_emits_only_safe_stage_without_code_or_state(
    owner_client, monkeypatch, caplog,
):
    from app import private_owner_real_google_http as http
    c, engine, seen, _ = owner_client
    state = state_from(c, login(c))
    fake_error = "FAKE_300_CHAR_PROVIDER_SECRET_NEVER_LOGGED"
    def fail_exchange(**kwargs):
        raise RuntimeError(fake_error)
    monkeypatch.setattr(http, "exchange_google_code", fail_exchange)
    with caplog.at_level("WARNING", logger="personal_cfo.oauth_callback"):
        response = callback(
            c, state,
            path="/internal/drive/oauth/callback?" + urlencode({
                "state": state, "code": CODE, "scope": GOOGLE_METADATA_SCOPE,
                "authuser": "0", "prompt": "consent",
            }),
        )
    assert_scrubbed(response, state)
    logs = " ".join(record.getMessage() for record in caplog.records)
    assert "stage=google_code_exchange" in logs
    for sensitive in (state, CODE, REFRESH, ACCESS, FOLDER, CLIENT, fake_error):
        assert sensitive not in logs
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants"
        )).scalar_one() == 0
    assert seen == []


def _content_oauth_client(owner_client):
    """Share only the fabricated DB, never the real production gateway."""
    from app.private_owner_real_google_http import (
        create_review_only_private_google_http_gateway,
    )
    from app.private_google_content_consent import GOOGLE_CONTENT_READ_SCOPE
    from app.private_content_grant_custody import read_private_content_grant
    c, engine, _, monkeypatch = owner_client
    for name in (
        "P4_CONTENT_OAUTH_CONTRACT_ONLY",
        "P4_G2_OWNER_SESSION_CONTENT_REVIEWED",
        "P4_G3_RESTRICTED_SCOPE_ACCEPTED",
        "P4B_PRIVATE_CONTENT_GRANT_CUSTODY",
        "P4B_G2_OWNER_CONTENT_GRANT_REVIEWED",
        "P4B_G3_EXACT_CONTENT_SCOPE_ATTESTED",
        "P4C_CONTENT_OAUTH_RUNTIME",
        "P4C_G2_CONTENT_OAUTH_CALLBACK_REVIEWED",
        "P4C_G3_READONLY_SOURCE_POLICY_REVIEWED",
    ):
        monkeypatch.setenv(name,"1")
    calls=[]
    selected={"scope":GOOGLE_CONTENT_READ_SCOPE}
    def content_provider(method,url,form,bearer):
        calls.append((method,url,form is not None))
        if method=="POST":
            assert url=="https://oauth2.googleapis.com/token"
            assert form["code"]==CODE
            assert form["grant_type"]=="authorization_code"
            assert form["code_verifier"]
            assert bearer is None
            return {
                "access_token":ACCESS,"refresh_token":REFRESH,
                "scope":selected["scope"],"token_type":"Bearer","expires_in":3600,
            }
        if method=="GET":
            assert url.startswith("https://www.googleapis.com/drive/v3/files/"+FOLDER)
            assert bearer==ACCESS
            return {
                "id":FOLDER,"mimeType":"application/vnd.google-apps.folder",
                "trashed":False,"shared":False,"owners":[{"me":True}],
            }
        raise AssertionError("Unexpected fake provider method")
    app=create_review_only_private_google_http_gateway(
        lambda:Session(engine),transport=content_provider,
        enable_content_oauth=True,
    )
    return TestClient(app,base_url="https://"+HOST),engine,calls,selected


def test_separate_content_oauth_end_to_end_fake_google_encrypted_grant(owner_client):
    from app.private_content_grant_custody import read_private_content_grant
    c,engine,calls,selected=_content_oauth_client(owner_client)
    with c:
        csrf=login(c)
        status=c.get("/internal/drive/content/oauth/status",
                     headers=headers(origin=None))
        assert status.status_code==200
        assert status.json()=={
            "content_scope":"DRIVE_READONLY_CONTENT",
            "google_content_grant_stored":False,
            "source_bytes_downloaded":False,
            "financial_data_enabled":False,
        }
        response=c.post("/internal/drive/content/oauth/start",
                        headers=headers(csrf=csrf))
        assert response.status_code==200
        body=response.json()
        assert body["scope"]=="DRIVE_READONLY_CONTENT"
        assert body["google_content_grant_stored"] is False
        assert body["source_bytes_downloaded"] is False
        params=parse_qs(urlsplit(body["authorization_url"]).query)
        assert params["scope"]==["https://www.googleapis.com/auth/drive.readonly"]
        assert params["include_granted_scopes"]==["false"]
        state=params["state"][0]
        result=callback(c,state)
        assert_scrubbed(result,state)
        status=c.get("/internal/drive/content/oauth/status",
                     headers=headers(origin=None))
        assert status.status_code==200
        assert status.json()["google_content_grant_stored"] is True
        assert status.json()["source_bytes_downloaded"] is False
        assert [x[0] for x in calls]==["POST","GET"]
        with Session(engine) as db:
            assert read_private_content_grant(
                db,owner_ref=OWNER,folder_id=FOLDER,client_id=CLIENT)==REFRESH
        with engine.connect() as db:
            stored=str(db.execute(text(
                "SELECT * FROM owner_google_metadata_grants")).one())
            assert "P4C1:" in stored
            for secret in (REFRESH,ACCESS,CODE,state,FOLDER):
                assert secret not in stored
        assert_scrubbed(callback(c,state),state)
        assert len(calls)==2  # no second exchange after state consumed


def test_bad_content_scope_never_persists_a_refresh_token(owner_client):
    c,engine,calls,selected=_content_oauth_client(owner_client)
    selected["scope"]="https://www.googleapis.com/auth/drive.metadata.readonly"
    with c:
        csrf=login(c)
        payload=c.post("/internal/drive/content/oauth/start",
                       headers=headers(csrf=csrf)).json()
        state=parse_qs(urlsplit(payload["authorization_url"]).query)["state"][0]
        assert_scrubbed(callback(c,state),state)
        assert c.get("/internal/drive/content/oauth/status",
                     headers=headers(origin=None)).json()["google_content_grant_stored"] is False
        with engine.connect() as db:
            assert db.execute(text(
                "SELECT count(*) FROM owner_google_metadata_grants")).scalar_one()==0
        assert [x[0] for x in calls]==["POST"]


def test_content_route_rejects_no_mfa_csrf_foreign_origin_or_body(owner_client):
    c,_,calls,_=_content_oauth_client(owner_client)
    with c:
        assert c.post("/internal/drive/content/oauth/start",
                      headers=headers()).status_code==401
        csrf=login(c)
        assert c.post("/internal/drive/content/oauth/start",
                      headers=headers(csrf="wrong")).status_code==401
        assert c.post("/internal/drive/content/oauth/start",
                      headers=headers(origin="https://evil.invalid",csrf=csrf)).status_code==403
        assert c.post("/internal/drive/content/oauth/start",
                      headers=headers(csrf=csrf),json={}).status_code==400
        assert calls==[]


def test_existing_metadata_cookie_and_grant_still_work_when_content_gate_on(owner_client):
    c,engine,calls,selected=_content_oauth_client(owner_client)
    selected["scope"]=GOOGLE_METADATA_SCOPE
    with c:
        csrf=login(c)
        state=state_from(c,csrf)
        assert_scrubbed(callback(c,state),state)
        response=c.get("/internal/drive/oauth/status",
                       headers=headers(origin=None))
        assert response.status_code==200
        assert response.json()["google_drive_app_connected"] is True
        response=c.get("/internal/drive/content/oauth/status",
                       headers=headers(origin=None))
        assert response.json()["google_content_grant_stored"] is False
        assert len(calls)==2


def test_content_routes_do_not_exist_in_default_metadata_only_factory(owner_client):
    c,_,_,_=owner_client
    paths={route.path for route in c.app.routes}
    assert "/internal/drive/content/oauth/start" not in paths
    assert "/internal/drive/content/oauth/status" not in paths


def test_p5d_owner_review_comments_scoped_to_actual_fake_folder_and_mfa(owner_client):
    """True end-to-end private comment route uses existing P1N MFA and AEAD SQL."""
    from app.drive_inbox_planner import DriveFile, _index as blind
    from app import private_original_source_preflight as preflight
    from app import private_content_grant_custody as custody
    from app import private_google_content_consent as content
    from datetime import datetime, timezone

    _original_client,engine,_seen,monkeypatch=owner_client
    for flag in (
        "P4_CONTENT_OAUTH_CONTRACT_ONLY",
        "P4_G2_OWNER_SESSION_CONTENT_REVIEWED",
        "P4_G3_RESTRICTED_SCOPE_ACCEPTED",
        "P4B_PRIVATE_CONTENT_GRANT_CUSTODY",
        "P4B_G2_OWNER_CONTENT_GRANT_REVIEWED",
        "P4B_G3_EXACT_CONTENT_SCOPE_ATTESTED",
        "P4C_CONTENT_OAUTH_RUNTIME",
        "P4C_G2_CONTENT_OAUTH_CALLBACK_REVIEWED",
        "P4C_G3_READONLY_SOURCE_POLICY_REVIEWED",
        "P5D_OWNER_REVIEW_HTTP_RUNTIME",
        "P5B_OWNER_REVIEW_COMMENTS_ENABLED",
        "P5B_G2_PRIVATE_REVIEW_ENCRYPTION_ACCEPTED",
        "P5B_G3_FINANCIAL_REVIEW_SCHEMA_ACCEPTED",
    ):
        monkeypatch.setenv(flag,"1")
    fake=DriveFile(
        id="SYNTHETIC_OWNER_REVIEW_APPROVED_FILE_2026",
        name="fake-financial-original.pdf",mime_type="application/pdf",
        parent_ids=(FOLDER,),size_bytes=250,
        modified_time=datetime(2026,11,19,tzinfo=timezone.utc),
        md5_checksum="a"*32,trashed=False,
    )
    monkeypatch.setattr(preflight,"_inventory",lambda *a,**kw:(fake,))
    monkeypatch.setattr(custody,"read_private_content_grant",lambda *a,**kw:"Z"*55)
    monkeypatch.setattr(content,"refresh_google_content_token",lambda **kw:(ACCESS,None))
    app=create_review_only_private_google_http_gateway(
        lambda:Session(engine),
        enable_content_oauth=True,enable_review_comments=True,
    )
    subject=blind("file",fake.id)
    with TestClient(app,base_url="https://"+HOST) as client:
        unauth=client.get("/internal/finance/review/status",
                          headers=headers(origin=None))
        assert unauth.status_code==401
        csrf=login(client)
        status=client.get("/internal/finance/review/status",
                          headers=headers(origin=None))
        assert status.status_code==200
        assert status.json()["review_enabled"] is True
        assert status.json()["auto_resolve"] is False
        good=client.post("/internal/finance/review/comment",
                         headers=headers(csrf=csrf),
                         json={"subject_hmac":subject,"subject_kind":"document",
                               "comment":"Synthetic clarification: possible own transfer."})
        assert good.status_code==200,good.text
        assert good.json()["review_state"]=="PENDING_EVIDENCE_RECONCILIATION"
        assert good.json()["automatically_resolved"] is False
        history=client.post("/internal/finance/review/history",
                            headers=headers(csrf=csrf),
                            json={"subject_hmac":subject,"subject_kind":"document"})
        assert history.status_code==200,history.text
        assert history.json()["comment_count"]==1
        assert history.json()["comments"][0]["comment"].startswith("Synthetic clarification")
        assert history.json()["automatic_resolution_performed"] is False
        with engine.connect() as conn:
            raw=str(conn.execute(text(
                "SELECT * FROM owner_financial_review_comments")).all())
            assert "Synthetic clarification" not in raw
            assert "possible own transfer" not in raw
            assert subject in raw
        bad=client.post("/internal/finance/review/comment",
                        headers=headers(csrf=csrf),
                        json={"subject_hmac":"f"*64,"subject_kind":"document",
                              "comment":"Not a pinned folder document."})
        assert bad.status_code==403
        bad=client.post("/internal/finance/review/comment",
                        headers=headers(csrf=csrf),
                        json={"subject_hmac":subject,"subject_kind":"transaction",
                              "comment":"Unreconciled row should not auto-clear."})
        assert bad.status_code==400
        bad=client.post("/internal/finance/review/comment",
                        headers=headers(csrf="wrong"),
                        json={"subject_hmac":subject,"subject_kind":"document",
                              "comment":"No CSRF."})
        assert bad.status_code==401
        monkeypatch.setenv("P5D_OWNER_REVIEW_HTTP_RUNTIME","0")
        assert client.get("/internal/finance/review/status",
                          headers=headers(origin=None)).status_code==503


def test_p5d_routes_not_mounted_when_unreviewed(owner_client):
    c,_,_,_=owner_client
    paths={r.path for r in c.app.routes}
    assert "/internal/finance/review/status" not in paths
    assert "/internal/finance/review/comment" not in paths
    assert "/internal/finance/review/history" not in paths
