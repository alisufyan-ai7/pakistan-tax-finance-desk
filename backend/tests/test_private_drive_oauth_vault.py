"""P1C: separate sealed local Google OAuth state and token vault with race denial."""
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import sqlite3
import stat
from threading import Barrier
import pytest

from app.drive_google_oauth import (
    GOOGLE_METADATA_SCOPE, begin_google_metadata_consent,
    private_google_configuration,
)
from app.drive_inbox_planner import _index
from app.private_drive_oauth_vault import (
    PrivateDriveVaultBlocked, PrivateGoogleOAuthVault,
)

FOLDER="SYNTHETIC_OWNER_APPROVED_ONLY_FOLDER_2026"


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    private_dir=tmp_path/"owner-only"
    private_dir.mkdir(mode=0o700)
    private_dir.chmod(0o700)
    vault_file=private_dir/"google-oauth.sqlite3"
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY","1")
    monkeypatch.setenv("P1C_LOCAL_OAUTH_VAULT_ENABLED","1")
    monkeypatch.setenv("P1C_OAUTH_VAULT_PATH",str(vault_file))
    monkeypatch.setenv("P1C_OAUTH_VAULT_KEY",base64.urlsafe_b64encode(b"K"*32).decode())
    monkeypatch.setenv("P1B_GOOGLE_CLIENT_ID","000000000000-syntheticdev.apps.googleusercontent.com")
    monkeypatch.setenv("P1B_GOOGLE_REDIRECT_URI","https://localhost:8443/api/drive/oauth/callback")
    monkeypatch.setenv("P1B_GOOGLE_FOLDER_ID",FOLDER)
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",base64.urlsafe_b64encode(b"D"*32).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    yield vault_file


def _pending():
    config=private_google_configuration()
    return begin_google_metadata_consent(config),config


def test_private_vault_mode_600_and_encrypted_pkce_and_grant(isolated):
    vault=PrivateGoogleOAuthVault()
    assert stat.S_IMODE(os.stat(isolated).st_mode)==0o600
    pending,cfg=_pending()
    vault.remember_attempt(pending,current=cfg)
    state=vault.consume_attempt(pending.state)
    assert state.pkce_verifier==pending.pkce_verifier
    assert state.folder_hmac==cfg.folder_hmac
    vault.store_grant(folder_hmac=cfg.folder_hmac,client_id=cfg.client_id,
                      refresh_token="synthetic_refresh_never_exchanged_123456789",
                      scope=GOOGLE_METADATA_SCOPE)
    assert vault.redacted_status()["private_local_grant_sealed"]
    restored=PrivateGoogleOAuthVault().load_grant()
    assert restored["refresh_token"]=="synthetic_refresh_never_exchanged_123456789"
    with sqlite3.connect(isolated) as db:
        rows=db.execute("SELECT state_hmac,payload_cipher FROM oauth_attempts").fetchall()
        credentials=db.execute("SELECT folder_hmac,payload_cipher FROM oauth_grants").fetchone()
    assert rows and rows[0][1].startswith("DCF1:")
    assert credentials[1].startswith("DCF1:")
    dump=str(rows)+str(credentials)
    for item in (pending.state,pending.pkce_verifier,"synthetic_refresh_never_exchanged",FOLDER,cfg.client_id):
        assert item not in dump
    vault.local_disconnect()
    assert not vault.redacted_status()["private_local_grant_sealed"]
    with pytest.raises(PrivateDriveVaultBlocked):
        vault.load_grant()


def test_two_independent_workers_claim_one_state_once(isolated):
    first=PrivateGoogleOAuthVault()
    pending,cfg=_pending()
    first.remember_attempt(pending,current=cfg)
    gate=Barrier(2)
    def worker(_):
        gate.wait(timeout=5)
        try:
            claimed=PrivateGoogleOAuthVault().consume_attempt(pending.state)
            return "claimed" if claimed.pkce_verifier==pending.pkce_verifier else "wrong"
        except PrivateDriveVaultBlocked:
            return "replay_denied"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(worker,range(2)))
    assert sorted(results)==["claimed","replay_denied"]
    with pytest.raises(PrivateDriveVaultBlocked):
        first.consume_attempt(pending.state)


def test_expired_state_not_consumed(isolated):
    vault=PrivateGoogleOAuthVault()
    pending,cfg=_pending()
    vault.remember_attempt(pending,current=cfg,now_unix=1800000000)
    with pytest.raises(PrivateDriveVaultBlocked):
        vault.consume_attempt(pending.state,now_unix=1800000600)


def test_ciphertext_tampering_and_key_loss_fail_closed(isolated,monkeypatch):
    vault=PrivateGoogleOAuthVault()
    pending,cfg=_pending()
    vault.remember_attempt(pending,current=cfg)
    with sqlite3.connect(isolated) as conn:
        conn.execute("UPDATE oauth_attempts SET payload_cipher='PLAIN_PKCE' ")
    with pytest.raises(PrivateDriveVaultBlocked):
        vault.consume_attempt(pending.state)
    vault.store_grant(folder_hmac=cfg.folder_hmac,client_id=cfg.client_id,
                      refresh_token="synthetic_refresh_never_exchanged_123456789",
                      scope=GOOGLE_METADATA_SCOPE)
    monkeypatch.setenv("P1C_OAUTH_VAULT_KEY",base64.urlsafe_b64encode(b"Z"*32).decode())
    with pytest.raises(PrivateDriveVaultBlocked):
        PrivateGoogleOAuthVault().load_grant()


def test_private_vault_wrong_folder_or_permissions_refused(isolated,monkeypatch):
    PrivateGoogleOAuthVault()
    isolated.chmod(0o644)
    with pytest.raises(PrivateDriveVaultBlocked):
        PrivateGoogleOAuthVault()
    isolated.chmod(0o600)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC","f"*64)
    with pytest.raises(Exception):
        private_google_configuration()


def test_real_mode_disabled_and_missing_vault_key_refused(isolated,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(PrivateDriveVaultBlocked):
        PrivateGoogleOAuthVault()
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.delenv("P1C_OAUTH_VAULT_KEY")
    with pytest.raises(PrivateDriveVaultBlocked):
        PrivateGoogleOAuthVault()
