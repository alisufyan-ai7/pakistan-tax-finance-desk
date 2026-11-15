"""G1-b encrypted PostgreSQL snapshot/restore guard tests. No real documents."""
import base64
import json
from pathlib import Path
import secrets

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.pg_recovery import (
    MAGIC, SCHEMA_REVISION, PgRecoveryBlocked, _decode, _guard,
    _connection_config, create_pg_snapshot, restore_pg_snapshot,
)
from app.db import Base
from app import models


@pytest.fixture
def fake_pg_key(monkeypatch):
    key = b"R" * 32
    monkeypatch.setenv("PG_SNAPSHOT_KEY", base64.urlsafe_b64encode(key).decode())
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    return key


def _synthetic_manifest():
    return {"format":"TFPG1","schema_revision":SCHEMA_REVISION,
            "source_database":"synthetic_sandbox",
            "tables":[{"table":name,"count":0,"sha256":
                __import__("hashlib").sha256(b"").hexdigest(),"csv_b64":""}
                 for name in sorted(Base.metadata.tables)]}


def _blob(key: bytes, manifest=None):
    payload = json.dumps(manifest or _synthetic_manifest(), sort_keys=True).encode()
    nonce = b"1" * 12
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, payload, MAGIC)


def test_synthetic_manifest_rejects_wrong_key_tamper_and_incomplete_inventory(fake_pg_key):
    blob = _blob(fake_pg_key)
    assert _decode(blob, fake_pg_key)["format"] == "TFPG1"
    with pytest.raises(PgRecoveryBlocked, match="authentication"):
        _decode(blob, b"X" * 32)
    damaged = bytearray(blob)
    damaged[-1] ^= 1
    with pytest.raises(PgRecoveryBlocked, match="authentication"):
        _decode(bytes(damaged), fake_pg_key)
    missing = _synthetic_manifest()
    missing["tables"] = missing["tables"][:-1]
    with pytest.raises(PgRecoveryBlocked, match="Incomplete"):
        _decode(_blob(fake_pg_key, missing), fake_pg_key)


def test_snapshot_key_required_separate_and_real_mode_forbidden(fake_pg_key, monkeypatch):
    assert _guard() == fake_pg_key
    monkeypatch.setenv("PG_SNAPSHOT_KEY", base64.urlsafe_b64encode(b"S" * 32).decode())
    with pytest.raises(PgRecoveryBlocked, match="differ"):
        _guard()
    monkeypatch.delenv("PG_SNAPSHOT_KEY")
    with pytest.raises(PgRecoveryBlocked, match="32 bytes"):
        _guard()
    monkeypatch.setenv("PG_SNAPSHOT_KEY", base64.urlsafe_b64encode(fake_pg_key).decode())
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(PgRecoveryBlocked, match="synthetic"):
        _guard()


def test_only_explicit_synthetic_db_identifiers_allowed(fake_pg_key, monkeypatch):
    monkeypatch.setenv("PG_SNAPSHOT_SOURCE_DSN","postgresql://user:fake@localhost:5432/production")
    with pytest.raises(PgRecoveryBlocked, match="synthetic"):
        _connection_config("PG_SNAPSHOT_SOURCE_DSN", restore=False)
    monkeypatch.setenv("PG_SNAPSHOT_RESTORE_DSN","postgresql://user:fake@localhost:5432/synthetic_sandbox")
    with pytest.raises(PgRecoveryBlocked, match="synthetic"):
        _connection_config("PG_SNAPSHOT_RESTORE_DSN", restore=True)
    monkeypatch.setenv("PG_SNAPSHOT_SOURCE_DSN","postgresql://user:fake@localhost:5432/synthetic_sandbox")
    assert _connection_config("PG_SNAPSHOT_SOURCE_DSN", restore=False)[1] == "synthetic_sandbox"


def test_no_network_or_file_if_synthetic_connection_not_configured(fake_pg_key, tmp_path, monkeypatch):
    monkeypatch.delenv("PG_SNAPSHOT_SOURCE_DSN", raising=False)
    backup = tmp_path / "snapshot.tfpg"
    with pytest.raises(PgRecoveryBlocked, match="provided"):
        create_pg_snapshot(backup)
    assert not backup.exists()
    monkeypatch.delenv("PG_SNAPSHOT_RESTORE_DSN", raising=False)
    with pytest.raises(PgRecoveryBlocked, match="provided"):
        restore_pg_snapshot(backup)
