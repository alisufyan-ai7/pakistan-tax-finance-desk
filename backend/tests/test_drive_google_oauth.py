"""P1B: private Google consent has PKCE/state, never real token/Drive access."""
import base64
import os
from urllib.parse import urlsplit, parse_qs

import pytest

from app.drive_inbox_planner import _index
from app.drive_google_oauth import (
    GOOGLE_METADATA_SCOPE, PrivateDriveOAuthBlocked,
    private_google_configuration, begin_google_metadata_consent,
    validate_google_callback, redact_private_connection_status,
)

FOLDER = "SYNTHETIC_GOOGLE_INBOX_ONE_FOLDER_2026"


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY", "1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY", base64.urlsafe_b64encode(b"D" * 32).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    monkeypatch.setenv("P1B_GOOGLE_FOLDER_ID", FOLDER)
    monkeypatch.setenv("P1B_GOOGLE_CLIENT_ID", "000000000000-syntheticdev.apps.googleusercontent.com")
    monkeypatch.setenv("P1B_GOOGLE_REDIRECT_URI", "https://localhost:8443/api/drive/oauth/callback")


def test_strict_config_pkce_and_owner_visible_consent_not_credentials():
    cfg=private_google_configuration()
    ready=begin_google_metadata_consent(cfg)
    parsed=urlsplit(ready.authorization_url)
    q=parse_qs(parsed.query)
    assert parsed.netloc=="accounts.google.com" and parsed.scheme=="https"
    assert q["scope"]==[GOOGLE_METADATA_SCOPE]
    assert q["code_challenge_method"]==["S256"]
    assert q["access_type"]==["offline"]
    assert q["prompt"]==["consent"]
    assert len(q["code_challenge"][0])==43
    assert len(ready.state)>=40 and len(ready.pkce_verifier)>=48
    assert q["state"]==[ready.state]
    assert cfg.folder_id not in ready.authorization_url
    assert "client_secret" not in ready.authorization_url
    again=begin_google_metadata_consent(cfg)
    assert again.state!=ready.state and again.pkce_verifier!=ready.pkce_verifier


def test_callback_requires_exact_one_time_state_and_offline_metadata_scope():
    ready=begin_google_metadata_consent(private_google_configuration())
    result=validate_google_callback(
        state=ready.state, expected_state=ready.state,
        code="4/synthetic_google_authorization_code",
        granted_scope=GOOGLE_METADATA_SCOPE,
        refresh_token="synthetic_token_never_used_123456789",
    )
    assert result["scope"]=="DRIVE_METADATA_ONLY"
    assert not result["refresh_token_persisted_or_used"]
    assert not result["actual_google_connection_established"]
    assert "synthetic_token" not in str(result)
    for invalid in [
        {"state": "different_state_not_same_as_google_callback_abcdefghijkl"},
        {"granted_scope": "https://www.googleapis.com/auth/drive"},
        {"granted_scope": GOOGLE_METADATA_SCOPE + " https://www.googleapis.com/auth/drive"},
        {"refresh_token": ""},
        {"code": "bad"},
    ]:
        params=dict(
            state=ready.state, expected_state=ready.state,
            code="4/synthetic_google_authorization_code",
            granted_scope=GOOGLE_METADATA_SCOPE,
            refresh_token="synthetic_token_never_used_123456789",
        )
        params.update(invalid)
        with pytest.raises(PrivateDriveOAuthBlocked):
            validate_google_callback(**params)


@pytest.mark.parametrize("env, value", [
    ("APP_DATA_MODE", "real"),
    ("P1B_PRIVATE_OAUTH_CONTRACT_ONLY", "0"),
    ("P1B_GOOGLE_REDIRECT_URI", "https://personal-cfo-preview.up.railway.app/api/drive/oauth/callback"),
    ("P1B_GOOGLE_REDIRECT_URI", "https://localhost:8443/api/drive/oauth/callback?next=evil"),
    ("P1B_GOOGLE_REDIRECT_URI", "http://localhost:8443/api/drive/oauth/callback"),
    ("P1B_GOOGLE_FOLDER_ID", "UNRELATED_DRIVE_FOLDER_2026"),
    ("P1B_GOOGLE_CLIENT_ID", "garbage"),
])
def test_private_callback_cannot_use_public_host_or_other_folder(monkeypatch,env,value):
    monkeypatch.setenv(env,value)
    with pytest.raises(PrivateDriveOAuthBlocked):
        private_google_configuration()


def test_ui_connection_is_never_inferred_from_google_client_configuration():
    report=redact_private_connection_status(oauth_configured=True,token_vault_approved=False)
    assert report["google_drive_app_connected"] is False
    assert report["last_successful_app_sync"] is None
    assert report["real_document_import_enabled"] is False
