"""Offline M2r encrypted-only archival candidate; synthetic records exclusively."""
import base64
import json
import sqlite3
import uuid

import pytest
from cryptography.exceptions import InvalidTag

from app.secure_archive import ArchiveBlocked, export_synthetic_archive, verify_sealed_archive
from app.synthetic_backup import restore_backup
from app.ledger_crypto import seal
from test_imports import csv_bytes, upload


def _keys(monkeypatch):
    # These are public, deliberately unusable-for-real-money synthetic fixtures.
    for name, byte in [('BACKUP_KEY', b'B'), ('CONFIDENTIAL_ARCHIVE_KEY', b'A'),
                       ('CONFIDENTIAL_ARCHIVE_INDEX_KEY', b'I')]:
        monkeypatch.setenv(name, base64.urlsafe_b64encode(byte * 32).decode('ascii'))


def _loc(tmp_path):
    return dict(source=tmp_path/'test.db', evidence_dir=tmp_path/'evidence',
                encrypted_backup=tmp_path/'sealed-source-backup.tfbk',
                archive_file=tmp_path/'sealed-finance.db', receipt_file=tmp_path/'safe-audit.json')


def _seed(client, account, tmp_path):
    raw=csv_bytes([
       ['2024-06-30', 'M2R confidential income', '', '200.00', '200.00', 'R-2024'],
       ['2024-07-01', 'M2R confidential expense', '30.00', '', '170.00', 'R-2025'],
    ])
    res=upload(client,account,raw)
    assert res.status_code==201, res.text
    with sqlite3.connect(tmp_path/'test.db') as db:
        db.execute('INSERT INTO cash_holdings(id,label,legal_owner,currency,opening_as_of,opening_minor,evidence_basis,created_at) VALUES(?,?,?,?,?,?,?,?)',(
           str(uuid.uuid4()), seal('M2R PRIVATE CASH', 'cash_holdings.label'),'individual','PKR',
           '2023-01-02', 987654321,seal('Synthetic owner count','cash_holdings.evidence_basis'),
           '2026-11-16 00:00:00'))
        db.commit()


def test_sealed_projection_contains_no_plaintext_financial_columns(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    before=(tmp_path/'test.db').read_bytes()
    result=export_synthetic_archive(**_loc(tmp_path))
    assert result['verified'] and result['archive_verified_after_publish']
    assert result['original_source_retained'] and result['original_source_plaintext_still_present']
    assert not result['promoted_to_live'] and not result['real_data_approved']
    assert (tmp_path/'test.db').read_bytes()==before
    with sqlite3.connect(tmp_path/'sealed-finance.db') as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert tables=={'sealed_manifest','sealed_records'}
        assert db.execute("SELECT COUNT(*) FROM sealed_records WHERE kind='cash_holdings'").fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM sealed_records WHERE kind='transactions'").fetchone()[0]==2
    sealed=(tmp_path/'sealed-finance.db').read_bytes()
    for sensitive in (b'987654321',b'2023-01-02',b'2024-06-30',b'20000',b'M2R confidential',account.encode()):
        assert sensitive not in sealed
    assert (tmp_path/'sealed-finance.db').stat().st_mode & 0o777 == 0o600
    assert (tmp_path/'safe-audit.json').stat().st_mode & 0o777 == 0o600
    receipt=(tmp_path/'safe-audit.json').read_text()
    assert '987654321' not in receipt and account not in receipt
    assert verify_sealed_archive(tmp_path/'sealed-finance.db')['source_rows']==result['source_rows']


def test_encrypted_backup_independently_restorable_after_export(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    export_synthetic_archive(**_loc(tmp_path))
    restore=restore_backup(tmp_path/'sealed-source-backup.tfbk',tmp_path/'independent-restored')
    assert restore['sqlite_integrity_check']=='ok'
    with sqlite3.connect(tmp_path/'independent-restored'/'finance.db') as db:
        assert db.execute('SELECT opening_minor FROM cash_holdings').fetchone()[0]==987654321
    # The archive itself is sealed-only; no reconstructed plaintext DB on disk.
    assert not list(tmp_path.glob('.archive-verify-*'))


def test_tampered_or_missing_archive_data_detected(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    export_synthetic_archive(**_loc(tmp_path))
    with sqlite3.connect(tmp_path/'sealed-finance.db') as db:
        row=db.execute('SELECT blind_id,payload FROM sealed_records LIMIT 1').fetchone()
        damaged=row[1][:-1]+bytes([row[1][-1]^1])
        db.execute('UPDATE sealed_records SET payload=? WHERE blind_id=?',(damaged,row[0]))
        db.commit()
    with pytest.raises((InvalidTag,ArchiveBlocked)):
        verify_sealed_archive(tmp_path/'sealed-finance.db')


def test_archive_missing_record_fails_total_parity(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    export_synthetic_archive(**_loc(tmp_path))
    with sqlite3.connect(tmp_path/'sealed-finance.db') as db:
        db.execute('DELETE FROM sealed_records WHERE blind_id=(SELECT blind_id FROM sealed_records LIMIT 1)')
        db.commit()
    with pytest.raises(ArchiveBlocked, match='missing|excessive'):
        verify_sealed_archive(tmp_path/'sealed-finance.db')


def test_wrong_or_reused_keys_fail_closed(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    monkeypatch.setenv('CONFIDENTIAL_ARCHIVE_KEY', base64.urlsafe_b64encode(b'B'*32).decode('ascii'))
    with pytest.raises(ArchiveBlocked,match='differ'):
        export_synthetic_archive(**_loc(tmp_path))
    assert not (tmp_path/'sealed-source-backup.tfbk').exists()
    _keys(monkeypatch)
    export_synthetic_archive(**_loc(tmp_path))
    monkeypatch.setenv('CONFIDENTIAL_ARCHIVE_KEY',base64.urlsafe_b64encode(b'X'*32).decode('ascii'))
    with pytest.raises(InvalidTag):
        verify_sealed_archive(tmp_path/'sealed-finance.db')


def test_real_data_mode_forbidden_even_when_keys_valid(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    monkeypatch.setenv('APP_DATA_MODE','real')
    with pytest.raises(ArchiveBlocked,match='Real financial'):
        export_synthetic_archive(**_loc(tmp_path))
    assert not (tmp_path/'sealed-source-backup.tfbk').exists()


def test_unknown_table_prevents_incomplete_protection(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    with sqlite3.connect(tmp_path/'test.db') as db:
        db.execute('CREATE TABLE unexpected_synthetic_secrets (id INTEGER PRIMARY KEY, value TEXT)')
        db.execute('INSERT INTO unexpected_synthetic_secrets VALUES (1,?)',('secret owner note',))
        db.commit()
    with pytest.raises(ArchiveBlocked,match='Unrecognized or missing'):
        export_synthetic_archive(**_loc(tmp_path))
    assert not (tmp_path/'sealed-source-backup.tfbk').exists()


def test_failed_restore_stage_keeps_backup_and_source(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    original=(tmp_path/'test.db').read_bytes()
    with pytest.raises(ArchiveBlocked,match='Injected'):
        export_synthetic_archive(**_loc(tmp_path),inject_failure_after_backup=True)
    assert (tmp_path/'test.db').read_bytes()==original
    assert (tmp_path/'sealed-source-backup.tfbk').exists()
    assert not (tmp_path/'sealed-finance.db').exists()
    assert not (tmp_path/'safe-audit.json').exists()


def test_does_not_overwrite_existing_archive(client,account,tmp_path,monkeypatch):
    _keys(monkeypatch)
    _seed(client,account,tmp_path)
    export_synthetic_archive(**_loc(tmp_path))
    original=(tmp_path/'sealed-finance.db').read_bytes()
    with pytest.raises(ArchiveBlocked,match='overwrite'):
        export_synthetic_archive(**_loc(tmp_path))
    assert original==(tmp_path/'sealed-finance.db').read_bytes()