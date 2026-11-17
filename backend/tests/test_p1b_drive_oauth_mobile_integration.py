"""Priority 1B Google Drive app connection/review cross-surface release boundaries.

This integration proves the browser's sample document UI cannot become a
public actual source endpoint merely because the backend contains a
Google OAuth contract and internal synthetic metadata sync helper.
"""
from pathlib import Path

import pytest

from app.drive_google_oauth import (
    PrivateDriveOAuthBlocked, private_google_configuration,
    redact_private_connection_status,
)
from app.drive_private_sync import scan_private_synthetic_folder
from app.drive_inbox_planner import DriveInboxBlocked
from app.preview_api import create_preview_app


def test_oauth_requires_explicit_private_contract_and_no_default_connection(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.delenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY", raising=False)
    with pytest.raises(PrivateDriveOAuthBlocked):
        private_google_configuration()
    info = redact_private_connection_status(oauth_configured=False, token_vault_approved=False)
    assert info["connection"] == "AWAITING_PRIVATE_SETUP"
    assert info["google_drive_app_connected"] is False
    assert info["last_successful_app_sync"] is None


def test_no_genuine_data_mode_can_sync_even_with_fake_transport(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    monkeypatch.setenv("DRIVE_FAKE_TRANSPORT_ONLY", "1")
    monkeypatch.setenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY", "1")
    with pytest.raises(PrivateDriveOAuthBlocked):
        private_google_configuration()
    with pytest.raises(DriveInboxBlocked):
        scan_private_synthetic_folder(
            None, folder_id="SYNTHETIC_OWNER_ONLY_FOLDER_2026",
            get_page=lambda params: {"files": []},
            synthetic_authorization_approved=True,
        )


def test_private_preview_has_no_google_account_or_financial_ingest_routes():
    paths = {r.path for r in create_preview_app().routes}
    for forbidden in (
        "/api/drive/connect", "/api/drive/oauth/start",
        "/api/drive/oauth/callback", "/api/drive/sync",
        "/api/drive/inbox/status", "/api/documents/real",
    ):
        assert forbidden not in paths


def test_mobile_ui_marks_documents_as_fictional_and_no_account_connection():
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    doc_source = (frontend / "document-inbox.mjs").read_text(encoding="utf-8")
    index_source = (frontend / "index.html").read_text(encoding="utf-8")
    assert "GOOGLE DRIVE · APP CONNECTION PENDING" in doc_source
    assert "FICTIONAL PREVIEW" in doc_source
    assert "Actual synced files" in doc_source
    assert 'data-view="documents"' in index_source
    assert "fetch(" not in doc_source
    assert "private_google_configuration" not in doc_source
