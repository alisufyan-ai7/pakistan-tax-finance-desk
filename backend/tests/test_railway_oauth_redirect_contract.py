"""P1D: exact owner-confirmed Railway callback is a contract, never a public API."""

import base64
from urllib.parse import parse_qs, urlsplit

import pytest

from app.drive_google_oauth import (
    GOOGLE_METADATA_SCOPE,
    PERSONAL_CFO_RAILWAY_CALLBACK,
    PrivateDriveOAuthBlocked,
    begin_google_metadata_consent,
    private_google_configuration,
)
from app.drive_inbox_planner import _index
from app.preview_api import create_preview_app


@pytest.fixture(autouse=True)
def fake_private_config(monkeypatch):
    folder = "SYNTHETIC_APPROVED_FOLDER_NOT_OWNER_DATA_2026"
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY", "1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY", base64.urlsafe_b64encode(b"D" * 32).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", folder))
    monkeypatch.setenv("P1B_GOOGLE_FOLDER_ID", folder)
    monkeypatch.setenv("P1B_GOOGLE_CLIENT_ID", "000000000000-syntheticdev.apps.googleusercontent.com")
    monkeypatch.setenv("P1B_GOOGLE_REDIRECT_URI", PERSONAL_CFO_RAILWAY_CALLBACK)
    monkeypatch.delenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY", raising=False)


def test_cloud_redirect_stays_disabled_without_explicit_contract_flag():
    with pytest.raises(PrivateDriveOAuthBlocked):
        private_google_configuration()


def test_google_consent_url_uses_exact_registered_cloud_redirect_without_secrets(monkeypatch):
    monkeypatch.setenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY", "1")
    config = private_google_configuration()
    assert config.redirect_uri == PERSONAL_CFO_RAILWAY_CALLBACK
    prepared = begin_google_metadata_consent(config)
    parts = urlsplit(prepared.authorization_url)
    params = parse_qs(parts.query)
    assert parts.scheme == "https" and parts.hostname == "accounts.google.com"
    assert params["redirect_uri"] == [PERSONAL_CFO_RAILWAY_CALLBACK]
    assert params["scope"] == [GOOGLE_METADATA_SCOPE]
    assert params["state"] == [prepared.state]
    assert params["code_challenge_method"] == ["S256"]
    assert params["access_type"] == ["offline"]
    assert config.folder_id not in prepared.authorization_url
    assert "client_secret" not in prepared.authorization_url


@pytest.mark.parametrize("bad_uri", [
    "https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback/",
    "http://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback",
    "https://personal-cfo-api-preview-development.up.railway.app/api/drive/oauth/callback",
    "https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/start",
    "https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback?to=other",
    "https://personal-cfo-frontend-preview-development.up.railway.app.evil.test/api/drive/oauth/callback",
    "https://personal-cfo-frontend-preview-development.up.railway.app:8443/api/drive/oauth/callback",
    "https://other-personal-cfo-project.up.railway.app/api/drive/oauth/callback",
    "https://localhost:8443/api/drive/oauth/callback?next=evil",
])
def test_cloud_flag_does_not_authorize_any_other_host_route_or_query(monkeypatch, bad_uri):
    monkeypatch.setenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY", "1")
    monkeypatch.setenv("P1B_GOOGLE_REDIRECT_URI", bad_uri)
    with pytest.raises(PrivateDriveOAuthBlocked):
        private_google_configuration()


def test_real_mode_cannot_use_cloud_consent_contract(monkeypatch):
    monkeypatch.setenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY", "1")
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(PrivateDriveOAuthBlocked):
        private_google_configuration()


def test_public_preview_has_no_oauth_routes():
    route_paths = {route.path for route in create_preview_app().routes}
    assert "/api/drive/oauth/start" not in route_paths
    assert "/api/drive/oauth/callback" not in route_paths
    assert "/api/drive/oauth/status" not in route_paths
    assert "/api/drive/oauth/disconnect" not in route_paths

def test_cloud_mode_rejects_owner_retired_localhost_redirect(monkeypatch):
    monkeypatch.setenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY", "1")
    monkeypatch.setenv(
        "P1B_GOOGLE_REDIRECT_URI",
        "https://localhost:8443/api/drive/oauth/callback",
    )
    with pytest.raises(PrivateDriveOAuthBlocked):
        private_google_configuration()


def test_local_dev_contract_retained_only_when_cloud_flag_is_absent(monkeypatch):
    monkeypatch.delenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY", raising=False)
    monkeypatch.setenv(
        "P1B_GOOGLE_REDIRECT_URI",
        "https://localhost:8443/api/drive/oauth/callback",
    )
    assert private_google_configuration().redirect_uri.startswith("https://localhost:")

