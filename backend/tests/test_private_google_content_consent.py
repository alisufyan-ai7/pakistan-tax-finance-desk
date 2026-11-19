"""P4 exact-scope Google content grant contract: ALL provider calls fake."""
import base64
from urllib.parse import parse_qs, urlsplit

import pytest

from app.drive_google_oauth import PERSONAL_CFO_RAILWAY_CALLBACK
from app.drive_inbox_planner import _index
from app import private_google_content_consent as content

FOLDER="SYNTHETIC_P4_OWNER_ONLY_SOURCE_FOLDER_2026"
CLIENT="000000000000-syntheticdev.apps.googleusercontent.com"
CODE="SYNTHETIC_CONTENT_AUTH_CODE_2026_NO_GOOGLE"
ACCESS="synthetic_content_access_token_"+"A"*45
REFRESH="synthetic_content_refresh_token_"+"B"*45


@pytest.fixture
def configured(monkeypatch):
    env={
        "APP_DATA_MODE":"synthetic",
        "P4_CONTENT_OAUTH_CONTRACT_ONLY":"1",
        "P4_G2_OWNER_SESSION_CONTENT_REVIEWED":"1",
        "P4_G3_RESTRICTED_SCOPE_ACCEPTED":"1",
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY":"1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY":"1",
        "P1B_GOOGLE_CLIENT_ID":CLIENT,
        "P1B_GOOGLE_REDIRECT_URI":PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_FOLDER_ID":FOLDER,
        "DRIVE_INDEX_HMAC_KEY":base64.urlsafe_b64encode(b"F"*32).decode("ascii"),
        "P1C_GOOGLE_CLIENT_SECRET":"synthetic_client_secret_not_ever_real_2026",
    }
    for name,value in env.items():
        monkeypatch.setenv(name,value)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    from app.drive_google_oauth import private_google_configuration
    return private_google_configuration(),monkeypatch


def test_content_prompt_always_one_exact_scope_and_existing_verified_client(configured):
    cfg,_=configured
    pending=content.begin_google_content_read_consent(config=cfg)
    query=parse_qs(urlsplit(pending.authorization_url).query)
    assert query["scope"]==[content.GOOGLE_CONTENT_READ_SCOPE]
    assert query["redirect_uri"]==[PERSONAL_CFO_RAILWAY_CALLBACK]
    assert query["client_id"]==[CLIENT]
    assert query["response_type"]==["code"]
    assert query["access_type"]==["offline"]
    assert query["prompt"]==["consent"]
    assert query["include_granted_scopes"]==["false"]
    assert query["code_challenge_method"]==["S256"]
    assert "code_verifier" not in query
    assert pending.folder_hmac==_index("folder",FOLDER)
    assert pending.state==query["state"][0]
    assert len(pending.pkce_verifier)>=43
    assert pending.authorization_url not in repr(pending)
    assert pending.pkce_verifier not in repr(pending)
    assert pending.state not in repr(pending)
    assert "drive.metadata.readonly" not in pending.authorization_url


@pytest.mark.parametrize("name",[
    "P4_CONTENT_OAUTH_CONTRACT_ONLY",
    "P4_G2_OWNER_SESSION_CONTENT_REVIEWED",
    "P4_G3_RESTRICTED_SCOPE_ACCEPTED",
])
def test_independent_release_gates_default_off(configured,name):
    cfg,monkeypatch=configured
    monkeypatch.setenv(name,"0")
    with pytest.raises(content.PrivateContentConsentBlocked):
        content.begin_google_content_read_consent(config=cfg)


def test_real_data_mode_rejected_no_implicit_consent(configured):
    cfg,monkeypatch=configured
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(content.PrivateContentConsentBlocked):
        content.begin_google_content_read_consent(config=cfg)


def _provider(scope=content.GOOGLE_CONTENT_READ_SCOPE,refresh=True):
    calls=[]
    def transport(method,url,form,bearer):
        calls.append((method,url,form,bearer))
        assert method=="POST"
        assert url=="https://oauth2.googleapis.com/token"
        assert bearer is None
        return {
            "access_token":ACCESS,"refresh_token":REFRESH if refresh else None,
            "scope":scope,"token_type":"Bearer","expires_in":3600,
        }
    return calls,transport


def test_exchange_accepts_only_exact_readonly_with_offline_refresh(configured):
    cfg,_=configured
    pending=content.begin_google_content_read_consent(config=cfg)
    calls,provider=_provider()
    access,refresh=content.exchange_google_content_code(
        code=CODE,verifier=pending.pkce_verifier,config=cfg,transport=provider)
    assert access==ACCESS and refresh==REFRESH
    assert len(calls)==1
    assert calls[0][2]["grant_type"]=="authorization_code"
    assert calls[0][2]["code_verifier"]==pending.pkce_verifier
    assert calls[0][2]["redirect_uri"]==PERSONAL_CFO_RAILWAY_CALLBACK


@pytest.mark.parametrize("scope",[
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
    content.GOOGLE_CONTENT_READ_SCOPE+" https://www.googleapis.com/auth/drive.metadata.readonly",
    "",
])
def test_metadata_only_or_broader_token_does_not_authorize_file_bytes(configured,scope):
    cfg,_=configured
    _,provider=_provider(scope=scope)
    with pytest.raises(content.PrivateContentConsentBlocked):
        content.exchange_google_content_code(
            code=CODE,verifier="A"*64,config=cfg,transport=provider)


def test_no_offline_refresh_token_means_no_durable_content_authority(configured):
    cfg,_=configured
    _,provider=_provider(refresh=False)
    with pytest.raises(content.PrivateContentConsentBlocked):
        content.exchange_google_content_code(
            code=CODE,verifier="A"*64,config=cfg,transport=provider)


def test_refresh_is_content_scope_bound_and_may_rotate(configured):
    cfg,_=configured
    calls,provider=_provider()
    access,rotated=content.refresh_google_content_token(
        refresh_token=REFRESH,config=cfg,transport=provider)
    assert access==ACCESS and rotated==REFRESH
    assert calls[0][2]["grant_type"]=="refresh_token"
    assert calls[0][2]["refresh_token"]==REFRESH
    assert "code" not in calls[0][2]


def test_bad_private_state_does_not_call_provider(configured):
    cfg,_=configured
    calls,provider=_provider()
    for code,verifier in [
        ("bad","A"*64),
        (CODE,"SHORT"),
        (CODE,"X"*64+"\n"),
    ]:
        with pytest.raises(content.PrivateContentConsentBlocked):
            content.exchange_google_content_code(
                code=code,verifier=verifier,config=cfg,transport=provider)
    assert calls==[]


def test_failed_provider_never_exposes_client_or_refresh(configured):
    cfg,_=configured
    def dangerous(*args):
        raise ValueError("PRIVATE_SECRET_OR_SOURCE_NAME_DO_NOT_LOG")
    with pytest.raises(content.PrivateContentConsentBlocked) as err:
        content.exchange_google_content_code(
            code=CODE,verifier="A"*64,config=cfg,transport=dangerous)
    assert "PRIVATE_SECRET" not in str(err.value)


def test_public_preview_has_no_content_oauth_route(configured):
    from app.preview_api import create_preview_app
    paths={r.path for r in create_preview_app().routes}
    assert "/internal/drive/content/oauth/start" not in paths
    assert "/api/drive/content/oauth/start" not in paths
