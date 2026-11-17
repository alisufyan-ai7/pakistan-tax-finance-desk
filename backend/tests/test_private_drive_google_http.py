"""P1C Google metadata flow: authentic replay-safe state and owner-only folder."""
import base64
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from app.drive_google_oauth import (
    GOOGLE_METADATA_SCOPE, begin_google_metadata_consent,
    private_google_configuration,
)
from app.drive_inbox_planner import _index
from app.private_drive_oauth_vault import PrivateGoogleOAuthVault
from app.private_drive_google_http import (
    PrivateGoogleNetworkBlocked, complete_private_google_oauth,
    list_private_owner_folder_page, refresh_google_access_token,
    verify_owner_private_folder,
)

FOLDER="SYNTHETIC_OWNER_APPROVED_ONLY_FOLDER_2026"
TOKEN="synthetic_access_token_fixed_by_local_fake_123"
REFRESH="synthetic_REFRESH_TOKEN_not_google_live_123456789"

@pytest.fixture
def private_config(monkeypatch,tmp_path):
    private_dir=tmp_path/"private"
    private_dir.mkdir(mode=0o700)
    private_dir.chmod(0o700)
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY","1")
    monkeypatch.setenv("P1C_LOCAL_OAUTH_VAULT_ENABLED","1")
    monkeypatch.setenv("P1C_GOOGLE_NETWORK_ENABLED","1")
    monkeypatch.setenv("P1C_PRIVATE_OWNER_MFA_ACCEPTED","1")
    monkeypatch.setenv("P1C_OAUTH_VAULT_PATH",str(private_dir/"oauth.sqlite3"))
    monkeypatch.setenv("P1C_OAUTH_VAULT_KEY",base64.urlsafe_b64encode(b"K"*32).decode())
    monkeypatch.setenv("P1C_GOOGLE_CLIENT_SECRET","fake-registered-secret-never-used-123456789")
    monkeypatch.setenv("P1B_GOOGLE_CLIENT_ID","000000000000-syntheticdev.apps.googleusercontent.com")
    monkeypatch.setenv("P1B_GOOGLE_REDIRECT_URI","https://localhost:8443/api/drive/oauth/callback")
    monkeypatch.setenv("P1B_GOOGLE_FOLDER_ID",FOLDER)
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",base64.urlsafe_b64encode(b"D"*32).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    return private_google_configuration()


def _transport_recording(calls, *, folder=None, broader_scope=False, extra_files=None):
    def transport(method,url,form,bearer):
        calls.append((method,url,form,bearer))
        if method=="POST":
            if form["grant_type"]=="authorization_code":
                assert form["code_verifier"]
                assert form["redirect_uri"]=="https://localhost:8443/api/drive/oauth/callback"
                assert form["client_secret"]=="fake-registered-secret-never-used-123456789"
                return {"access_token":TOKEN,"refresh_token":REFRESH,
                        "scope":"https://www.googleapis.com/auth/drive" if broader_scope else GOOGLE_METADATA_SCOPE,
                        "token_type":"Bearer","expires_in":3600}
            if form["grant_type"]=="refresh_token":
                return {"access_token":TOKEN,"scope":GOOGLE_METADATA_SCOPE,
                        "token_type":"Bearer","expires_in":3600}
        if method=="GET":
            if "/drive/v3/files/" in url:
                return {"id":folder or FOLDER,"mimeType":"application/vnd.google-apps.folder",
                        "trashed":False,"shared":False,"owners":[{"me":True}]}
            return {"files":extra_files if extra_files is not None else [],
                    "incompleteSearch":False}
        raise AssertionError("Unexpected fake Google transport")
    return transport


def test_real_shape_local_consent_exchange_is_never_broader_than_metadata(private_config):
    vault=PrivateGoogleOAuthVault()
    pending=begin_google_metadata_consent(private_config)
    vault.remember_attempt(pending,current=private_config)
    seen=[]
    result=complete_private_google_oauth(
        vault,state=pending.state,code="4/synthetic_authorization_code_123456",
        transport=_transport_recording(seen))
    assert result["owner_metadata_consent"]=="SEALED_LOCAL"
    assert result["approved_private_folder_verified"]
    assert result["background_app_sync_enabled"] is False
    assert result["financial_reconciliation_enabled"] is False
    assert vault.redacted_status()["private_local_grant_sealed"] is True
    with pytest.raises(PrivateGoogleNetworkBlocked):
        complete_private_google_oauth(
            vault,state=pending.state,code="4/synthetic_authorization_code_123456",
            transport=_transport_recording([]))
    assert sum(method=="POST" for method,_,_,_ in seen)==1
    assert sum(method=="GET" for method,_,_,_ in seen)==1
    assert all("alt=media" not in url for _,url,_,_ in seen)
    grant=vault.load_grant()
    assert grant["scope"]==GOOGLE_METADATA_SCOPE
    refreshed,new_refresh=refresh_google_access_token(
        refresh_token=grant["refresh_token"],config=private_config,
        transport=_transport_recording([]))
    assert refreshed==TOKEN and new_refresh is None


def test_invalid_or_broader_grant_does_not_store_secret(private_config):
    vault=PrivateGoogleOAuthVault()
    pending=begin_google_metadata_consent(private_config)
    vault.remember_attempt(pending,current=private_config)
    with pytest.raises(PrivateGoogleNetworkBlocked):
        complete_private_google_oauth(
            vault,state=pending.state,code="4/synthetic_authorization_code_123456",
            transport=_transport_recording([],broader_scope=True))
    assert vault.redacted_status()["private_local_grant_sealed"] is False


@pytest.mark.parametrize("change",[
    {"folder":"OTHER_PRIVATE_FOLDER_2026"},
])
def test_folder_mismatch_does_not_store_grant(private_config,change):
    vault=PrivateGoogleOAuthVault()
    pending=begin_google_metadata_consent(private_config)
    vault.remember_attempt(pending,current=private_config)
    with pytest.raises(PrivateGoogleNetworkBlocked):
        complete_private_google_oauth(
            vault,state=pending.state,code="4/synthetic_authorization_code_123456",
            transport=_transport_recording([],**change))
    assert vault.redacted_status()["private_local_grant_sealed"] is False


def test_google_metadata_list_is_fixed_to_owner_folder_and_no_content(private_config):
    calls=[]
    fake_file={
        "id":"SYNTHETIC_SOURCE_FILE_0001","name":"fake_loan.pdf","mimeType":"application/pdf",
        "parents":[FOLDER],"size":"1500","modifiedTime":"2026-11-17T12:00:00+05:00",
    }
    page=list_private_owner_folder_page(
        access_token=TOKEN,config=private_config,
        transport=_transport_recording(calls,extra_files=[fake_file]))
    assert len(page["files"])==1
    assert len(calls)==1
    url=urlsplit(calls[0][1])
    q=parse_qs(url.query)
    assert q["q"]==[f"'{FOLDER}' in parents and trashed = false"]
    assert q["corpora"]==["user"]
    assert q["fields"]==["nextPageToken,incompleteSearch,files(id,name,mimeType,parents,size,modifiedTime,md5Checksum,trashed)"]
    assert "alt" not in q
    assert calls[0][0]=="GET"
    with pytest.raises(PrivateGoogleNetworkBlocked):
        list_private_owner_folder_page(
            access_token=TOKEN,config=private_config,
            transport=_transport_recording([],extra_files=[
                {**fake_file,"parents":["SYNTHETIC_UNRELATED_FOLDER_001"]},
            ]))


def test_owner_mfa_and_live_network_default_off(private_config,monkeypatch):
    monkeypatch.delenv("P1C_PRIVATE_OWNER_MFA_ACCEPTED")
    with pytest.raises(PrivateGoogleNetworkBlocked):
        list_private_owner_folder_page(
            access_token=TOKEN,config=private_config,
            transport=_transport_recording([]))
    monkeypatch.setenv("P1C_PRIVATE_OWNER_MFA_ACCEPTED","1")
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(PrivateGoogleNetworkBlocked):
        refresh_google_access_token(
            refresh_token=REFRESH,config=private_config,transport=_transport_recording([]))


def test_public_railway_preview_never_exposes_local_oauth_code():
    from app.preview_api import create_preview_app
    route_names={route.path for route in create_preview_app().routes}
    for path in (
        "/api/drive/oauth/start","/api/drive/oauth/callback",
        "/api/drive/oauth/status","/api/drive/oauth/disconnect",
    ):
        assert path not in route_names
