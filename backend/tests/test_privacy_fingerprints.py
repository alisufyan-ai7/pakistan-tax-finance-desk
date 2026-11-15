"""Dedicated keyed synthetic banking identifiers; no genuine statements."""
import base64
import hashlib
import hmac
import os
import sqlite3
import pytest
from app.privacy_fingerprints import FingerprintKeyError, document_digest, transaction_digest, require_dedup_key
from test_imports import csv_bytes, upload


def test_dedup_key_required_and_not_interchangeable(monkeypatch):
    monkeypatch.delenv('LEDGER_DEDUP_HMAC_KEY', raising=False)
    with pytest.raises(FingerprintKeyError):
        require_dedup_key()
    monkeypatch.setenv('LEDGER_DEDUP_HMAC_KEY','not-a-valid-base64-key')
    with pytest.raises(FingerprintKeyError):
        document_digest(b'privacy test')


def test_document_ids_are_deterministic_and_not_raw_sha256():
    raw = b'synthetic account,date,amount,description'
    a = document_digest(raw)
    assert a == document_digest(raw)
    assert a != hashlib.sha256(raw).hexdigest()
    assert a != document_digest(raw + b'!')
    assert len(a) == 64


def test_transaction_hash_is_keyed_and_domain_separated(monkeypatch):
    old = hashlib.sha256(b'2024-01-01|100|synthetic internal label').hexdigest()
    first = transaction_digest(old)
    assert first != old and first != document_digest(old.encode())
    monkeypatch.setenv('LEDGER_DEDUP_HMAC_KEY', base64.urlsafe_b64encode(b'X'*32).decode())
    assert transaction_digest(old) != first
    with pytest.raises(ValueError):
        transaction_digest('garbage')


def test_bank_import_hmac_still_deduplicates_and_never_stores_plain_hash(client, account, tmp_path):
    raw = csv_bytes([
        ['2024-05-10', 'Synthetic shop purchase', '20.00', '', '80.00', 'T1'],
        ['2024-05-11', 'Synthetic salary', '', '100.00', '180.00', 'T2'],
    ])
    first = upload(client, account, raw)
    assert first.status_code == 201, first.text
    assert first.json()['accepted'] == 2
    second = upload(client, account, raw)
    assert second.status_code == 200 and second.json()['file_duplicate'] is True
    with sqlite3.connect(tmp_path / 'test.db') as db:
        doc_key = db.execute('SELECT sha256 FROM documents').fetchone()[0]
        tx_keys = [x[0] for x in db.execute('SELECT fingerprint FROM transactions ORDER BY id')]
    assert doc_key == document_digest(raw)
    assert doc_key != hashlib.sha256(raw).hexdigest()
    assert len(tx_keys) == 2 and all(len(v) == 64 for v in tx_keys)
    assert all('synthetic' not in v.lower() for v in tx_keys)


def test_hmac_misconfiguration_rejects_new_app_database(tmp_path, monkeypatch):
    from app.main import create_app
    monkeypatch.delenv('LEDGER_DEDUP_HMAC_KEY', raising=False)
    with pytest.raises(RuntimeError, match='deduplication HMAC'):
        create_app(f'sqlite:///{tmp_path / "missing-key.db"}')


def test_legacy_unkeyed_documents_fail_closed(client, account, tmp_path):
    from app.main import create_app
    raw = csv_bytes([['2024-06-01','Synthetic old ledger','1.00','','99.00','LEGACY']])
    assert upload(client, account, raw).status_code == 201
    with sqlite3.connect(tmp_path / 'test.db') as db:
        db.execute("UPDATE documents SET digest_scheme='legacy_sha256'")
        db.commit()
    with pytest.raises(RuntimeError, match='Legacy unkeyed'):
        create_app(f'sqlite:///{tmp_path / "test.db"}')