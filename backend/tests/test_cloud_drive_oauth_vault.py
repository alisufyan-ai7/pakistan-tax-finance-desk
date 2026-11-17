"""P1E synthetic cloud custody hardening, never an actual Google connection."""
import base64
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa: F401
from app.drive_google_oauth import (
    begin_google_metadata_consent, private_google_configuration,
    PERSONAL_CFO_RAILWAY_CALLBACK,
)
from app.drive_inbox_planner import _index
from app.cloud_drive_oauth_vault import (
    CloudOAuthCustodyBlocked, remember_fake_cloud_attempt,
    claim_fake_cloud_attempt, seal_fake_cloud_grant, read_fake_cloud_grant,
    disconnect_fake_cloud_grant, cloud_connection_status,
)
from app.preview_api import create_preview_app

FOLDER = "SYNTHETIC_P1E_ONLY_APPROVED_FOLDER_2026"
FAKE_GRANT = "SYNTHETIC_FAKE_REFRESH_NOT_ACTUAL_GOOGLE_CREDENTIAL_12345"


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY", "1")
    monkeypatch.setenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY", "1")
    monkeypatch.setenv("P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY", "1")
    monkeypatch.setenv("P1E_SQLITE_TEST_ONLY", "1")
    monkeypatch.setenv("P1B_GOOGLE_REDIRECT_URI", PERSONAL_CFO_RAILWAY_CALLBACK)
    monkeypatch.setenv("P1B_GOOGLE_CLIENT_ID",
                       "000000000000-syntheticdev.apps.googleusercontent.com")
    monkeypatch.setenv("P1B_GOOGLE_FOLDER_ID", FOLDER)
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
                       base64.urlsafe_b64encode(b"D" * 32).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    monkeypatch.setenv("P1E_FAKE_CLOUD_VAULT_KEY",
                       base64.urlsafe_b64encode(b"E" * 32).decode())
    monkeypatch.setenv("P1E_FAKE_CLOUD_INDEX_KEY",
                       base64.urlsafe_b64encode(b"J" * 32).decode())
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "fake-cloud.db"),
        connect_args={"timeout": 10},
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def pending():
    return begin_google_metadata_consent(private_google_configuration())


def test_sealed_state_is_single_use_and_sql_does_not_expose_verifier(isolated):
    attempt = pending()
    with Session(isolated) as db:
        report = remember_fake_cloud_attempt(db, pending=attempt)
        assert report == {"fake_attempt_sealed": True,
                          "expires_in_seconds": 600,
                          "live_google_connection": False}
    with isolated.connect() as conn:
        row = conn.execute(text(
            "SELECT state_hmac,folder_hmac,payload_cipher,status "
            "FROM drive_cloud_oauth_attempts"
        )).one()
        assert len(row[0]) == len(row[1]) == 64
        assert row[2].startswith("CFOC1:") and row[3] == "pending"
        assert attempt.state not in str(row)
        assert attempt.pkce_verifier not in str(row)
        assert FOLDER not in str(row)
    with Session(isolated) as db:
        claimed = claim_fake_cloud_attempt(db, state=attempt.state)
        assert claimed.pkce_verifier == attempt.pkce_verifier
        assert claimed.folder_hmac == _index("folder", FOLDER)
        with pytest.raises(CloudOAuthCustodyBlocked, match="replayed"):
            claim_fake_cloud_attempt(db, state=attempt.state)
    with isolated.connect() as conn:
        assert conn.execute(text(
            "SELECT status FROM drive_cloud_oauth_attempts"
        )).scalar_one() == "claimed"


def test_two_workers_only_one_can_claim_the_same_state(isolated):
    attempt = pending()
    with Session(isolated) as db:
        remember_fake_cloud_attempt(db, pending=attempt)
    gate = Barrier(2)
    def worker(_):
        gate.wait(timeout=10)
        with Session(isolated) as db:
            try:
                return claim_fake_cloud_attempt(
                    db, state=attempt.state
                ).pkce_verifier == attempt.pkce_verifier
            except CloudOAuthCustodyBlocked:
                return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(worker, range(2)))
    assert sorted(result) == [False, True]


def test_expiry_wrong_state_and_tampering_are_denied(isolated):
    attempt = pending()
    with Session(isolated) as db:
        remember_fake_cloud_attempt(db, pending=attempt, now_epoch=1_800_000_000)
        with pytest.raises(CloudOAuthCustodyBlocked):
            claim_fake_cloud_attempt(db, state=attempt.state, now_epoch=1_800_000_600)
        with pytest.raises(CloudOAuthCustodyBlocked):
            claim_fake_cloud_attempt(db, state="invalid")
    with isolated.begin() as conn:
        conn.execute(text("UPDATE drive_cloud_oauth_attempts SET payload_cipher='tampered'"))
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked, match="authentication"):
            claim_fake_cloud_attempt(db, state=attempt.state, now_epoch=1_800_000_001)


def test_fake_grant_encrypted_recoverable_and_revocable(isolated):
    with Session(isolated) as db:
        seal_fake_cloud_grant(db, refresh_token=FAKE_GRANT)
    with isolated.connect() as conn:
        row = conn.execute(text(
            "SELECT folder_hmac,payload_cipher FROM drive_cloud_oauth_grants"
        )).one()
        assert row[1].startswith("CFOC1:")
        assert FAKE_GRANT not in str(row)
        assert FOLDER not in str(row)
    with Session(isolated) as db:
        assert read_fake_cloud_grant(db) == FAKE_GRANT
    # SQLite's BEGIN IMMEDIATE must begin a fresh write transaction.
    with Session(isolated) as db:
        disconnect_fake_cloud_grant(db)
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked):
            read_fake_cloud_grant(db)


def test_real_google_token_and_wrong_key_are_refused(isolated, monkeypatch):
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked):
            seal_fake_cloud_grant(
                db, refresh_token="1//this_would_be_a_real_google_refresh_token"
            )
        seal_fake_cloud_grant(db, refresh_token=FAKE_GRANT)
    monkeypatch.setenv("P1E_FAKE_CLOUD_VAULT_KEY",
                       base64.urlsafe_b64encode(b"Q" * 32).decode())
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked, match="authentication"):
            read_fake_cloud_grant(db)


def test_fail_closed_on_missing_keys_disabled_flag_and_real_mode(isolated, monkeypatch):
    monkeypatch.delenv("P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY")
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked):
            remember_fake_cloud_attempt(db, pending=pending())
    monkeypatch.setenv("P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY", "1")
    monkeypatch.delenv("P1E_FAKE_CLOUD_INDEX_KEY")
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked):
            seal_fake_cloud_grant(db, refresh_token=FAKE_GRANT)
    monkeypatch.setenv("P1E_FAKE_CLOUD_INDEX_KEY",
                       base64.urlsafe_b64encode(b"J" * 32).decode())
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked):
            read_fake_cloud_grant(db)


def test_real_client_or_folder_can_never_enter_test_vault(isolated, monkeypatch):
    monkeypatch.setenv("P1B_GOOGLE_CLIENT_ID",
                       "987654321-realownerclient.apps.googleusercontent.com")
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked, match="fictional"):
            seal_fake_cloud_grant(db, refresh_token=FAKE_GRANT)
    monkeypatch.setenv("P1B_GOOGLE_CLIENT_ID",
                       "000000000000-syntheticdev.apps.googleusercontent.com")
    monkeypatch.setenv("P1B_GOOGLE_FOLDER_ID", "REAL_OWNER_FOLDER_ID")
    with Session(isolated) as db:
        with pytest.raises(CloudOAuthCustodyBlocked):
            seal_fake_cloud_grant(db, refresh_token=FAKE_GRANT)


def test_no_preview_route_or_misleading_connection_status(isolated):
    assert cloud_connection_status() == {
        "google_drive_app_connected": False,
        "cloud_oauth_handler_live": False,
        "scheduled_real_drive_sync_enabled": False,
        "real_document_import_enabled": False,
        "financial_reconciliation_enabled": False,
    }
    routes = {route.path for route in create_preview_app().routes}
    assert "/api/drive/oauth/callback" not in routes
    assert "/api/drive/oauth/start" not in routes
    assert "/api/drive/oauth/status" not in routes
