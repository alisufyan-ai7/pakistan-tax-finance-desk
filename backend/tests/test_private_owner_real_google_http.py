"""P1AL: fake-provider integration of real-compatible Google metadata routes."""
import base64
import hmac
import json
from hashlib import sha1
from urllib.parse import parse_qs, urlsplit

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
