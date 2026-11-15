"""M2o: genuinely restored synthetic candidate, never in-place migration."""
import base64
import json
import sqlite3
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag
from app.synthetic_migration import MigrationBlocked, migrate_restored_synthetic_candidate
from app.synthetic_backup import restore_backup
from test_imports import csv_bytes, upload


def config(monkeypatch):
    monkeypatch.setenv('BACKUP_KEY', base64.urlsafe_b64encode(b'B' * 32).decode())


def work(client, account, rows=None):
    raw = csv_bytes(rows or [
        ['2024-06-30', 'synthetic income A', '', '200.00', '200.00', 'M2O-A'],
        ['2024-07-01', 'synthetic expense B', '30.00', '', '170.00', 'M2O-B'],
    ])
    r = upload(client, account, raw)
    assert r.status_code == 201, r.text
    result = []
    for year in (2024, 2025):
        for t in client.get(f'/api/transactions?tax_year={year}').json()['rows']:
            category = 'salary' if t['credit'] == '200.00' else 'personal_expense'
            x = client.patch(f"/api/transactions/{t['id']}", json={
                'category': category, 'note': 'Reviewed original purely synthetic bank record',
            })
            assert x.status_code == 200, x.text
            result.append(t)
    return result


def locations(tmp_path):
    return dict(
        database=tmp_path / 'test.db',
        evidence_dir=tmp_path / 'evidence',
        backup_file=tmp_path / 'm2o-recovery.tfbk',
        candidate_directory=tmp_path / 'candidate',
        receipt_file=tmp_path / 'm2o-receipt.json',
    )


def run(tmp_path):
    return migrate_restored_synthetic_candidate(**locations(tmp_path))


def counts(path: Path):
    with sqlite3.connect(path) as db:
        old = db.execute('SELECT count(*) FROM transactions').fetchone()[0]
        new = db.execute('SELECT count(*) FROM private_financial_events').fetchone()[0]
    return old, new


def test_verified_candidate_has_two_years_no_source_edits_or_double_count(client, account, tmp_path, monkeypatch):
    config(monkeypatch)
    work(client, account)
    prior = client.get('/api/summary?tax_year=2024').json()
    assert prior['record_count'] == 1
    with sqlite3.connect(tmp_path/'test.db') as con:
        before = con.execute('SELECT id, debit_minor, credit_minor, posted_on FROM transactions ORDER BY id').fetchall()
    receipt = run(tmp_path)
    assert receipt['source_count'] == receipt['mirrors_verified'] == receipt['new_private_event_mirrors'] == 2
    assert receipt['verified_restored_backup'] and not receipt['migration_promoted']
    assert receipt['candidate_contains_plaintext_legacy_tables'] is True
    assert receipt['tax_due_minor'] is None
    assert counts(tmp_path/'test.db') == (2, 0)
    assert counts(tmp_path/'candidate'/'finance.db') == (2, 2)
    with sqlite3.connect(tmp_path/'test.db') as con:
        assert before == con.execute('SELECT id, debit_minor, credit_minor, posted_on FROM transactions ORDER BY id').fetchall()
    with sqlite3.connect(tmp_path/'candidate'/'finance.db') as con:
        values = con.execute('SELECT payload_json,source_hmac,year_hmac FROM private_financial_events').fetchall()
        assert len(values) == 2
        for payload,source,year in values:
            assert payload.startswith('TFLE1:') and len(source) == len(year) == 64
            assert '2024-06-30' not in payload and '20000' not in payload
    assert client.get('/api/summary?tax_year=2024').json() == prior
    audit = (tmp_path/'m2o-receipt.json').read_text()
    assert '20000' not in audit and account not in audit and 'synthetic income A' not in audit
    assert (tmp_path/'m2o-receipt.json').stat().st_mode & 0o777 == 0o600
    assert b'20000' not in (tmp_path/'m2o-recovery.tfbk').read_bytes()
    with pytest.raises(MigrationBlocked, match='new'):
        run(tmp_path)


def test_unreviewed_source_blocks_before_creating_backup(client, account, tmp_path, monkeypatch):
    config(monkeypatch)
    assert upload(client, account, csv_bytes([
        ['2023-12-01', 'synthetic unreviewed record', '20.00', '', '', 'UNR-M2O'],
    ])).status_code == 201
    with pytest.raises(MigrationBlocked, match='review'):
        run(tmp_path)
    assert not (tmp_path/'m2o-recovery.tfbk').exists()
    assert not (tmp_path/'candidate').exists()
    assert counts(tmp_path/'test.db') == (1, 0)


def test_conflicting_prior_encrypted_mirror_rejected_without_legacy_mutation(client, account, tmp_path, monkeypatch):
    config(monkeypatch)
    first = work(client, account)[0]
    fake = {
        'synthetic_fixture': True, 'source_ref': f"legacy-m1:{first['id']}",
        'source_type': 'synthetic_bank', 'event_kind': 'income',
        'posted_on': '2024-06-30', 'amount_minor': 9999,
        'account_ref': account, 'direction': 'credit',
        'evidence_note': 'Deliberately conflicting synthetic private mirror',
    }
    assert client.post('/api/finance/private-events', json=fake).status_code == 201
    with pytest.raises(MigrationBlocked, match='contradicts'):
        run(tmp_path)
    assert (tmp_path/'m2o-recovery.tfbk').exists()
    assert not (tmp_path/'candidate').exists()
    assert counts(tmp_path/'test.db') == (2, 1)


def test_injected_partial_failure_restores_original_only(client, account, tmp_path, monkeypatch):
    config(monkeypatch)
    work(client, account)
    with pytest.raises(MigrationBlocked, match='Injected'):
        migrate_restored_synthetic_candidate(
            **locations(tmp_path), inject_failure_after=1,
        )
    assert counts(tmp_path/'test.db') == (2, 0)
    assert not (tmp_path/'candidate').exists()
    assert not (tmp_path/'m2o-receipt.json').exists()
    recovered = restore_backup(tmp_path/'m2o-recovery.tfbk', tmp_path/'second-recovery')
    assert recovered['sqlite_integrity_check'] == 'ok'
    assert counts(tmp_path/'second-recovery'/'finance.db') == (2, 0)


def test_replay_matching_reviewed_mirror_is_idempotent_in_candidate(client, account, tmp_path, monkeypatch):
    config(monkeypatch)
    first = work(client, account)[0]
    exact = {
        'synthetic_fixture': True, 'source_ref': f"legacy-m1:{first['id']}",
        'source_type': 'synthetic_bank', 'event_kind': 'income',
        'posted_on': '2024-06-30', 'amount_minor': 20000,
        'account_ref': account, 'direction': 'credit',
        'evidence_note': 'Explicit synthetic M1 reviewed ledger source for migration preview',
    }
    assert client.post('/api/finance/private-events', json=exact).status_code == 201
    receipt = run(tmp_path)
    assert receipt['new_private_event_mirrors'] == 1
    assert counts(tmp_path/'candidate'/'finance.db') == (2, 2)
    assert counts(tmp_path/'test.db') == (2, 1)


def test_wrong_or_reused_keys_fail_before_backup(client, account, tmp_path, monkeypatch):
    config(monkeypatch)
    work(client, account)
    monkeypatch.delenv('BACKUP_KEY')
    with pytest.raises(Exception):
        run(tmp_path)
    assert not (tmp_path/'m2o-recovery.tfbk').exists()
    config(monkeypatch)
    monkeypatch.setenv('BACKUP_KEY', base64.urlsafe_b64encode(b'P' * 32).decode())
    with pytest.raises(MigrationBlocked, match='distinct'):
        run(tmp_path)
    assert counts(tmp_path/'test.db') == (2, 0)


def test_real_data_mode_and_overlapping_output_rejected(client, account, tmp_path, monkeypatch):
    config(monkeypatch)
    work(client, account)
    monkeypatch.setenv('APP_DATA_MODE', 'real')
    with pytest.raises(MigrationBlocked, match='Real financial'):
        run(tmp_path)
    monkeypatch.delenv('APP_DATA_MODE')
    with pytest.raises(MigrationBlocked, match='new|overlap'):
        migrate_restored_synthetic_candidate(
            tmp_path/'test.db', tmp_path/'evidence',
            tmp_path/'test.db', tmp_path/'candidate',
        )


def test_failure_to_restore_retains_encrypted_recovery(client, account, tmp_path, monkeypatch):
    import app.synthetic_migration as m
    config(monkeypatch)
    work(client, account)
    def fail_restore(*args, **kwargs):
        raise InvalidTag('simulated wrong recovery key')
    monkeypatch.setattr(m, 'restore_backup', fail_restore)
    with pytest.raises(InvalidTag):
        run(tmp_path)
    assert (tmp_path/'m2o-recovery.tfbk').exists()
    assert not (tmp_path/'candidate').exists()
    assert counts(tmp_path/'test.db') == (2, 0)