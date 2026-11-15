"""M2e: synthetic-only, ledger-backed loan allocations and own-transfer confirmation."""
from __future__ import annotations

import sqlite3
from datetime import date

from test_imports import csv_bytes, upload


def account_at(client, name):
    result = client.post('/api/accounts', json={'name': name, 'institution': 'Synthetic Bank'})
    assert result.status_code == 201, result.text
    return result.json()['id']


def bank_tx(client, account, day, desc, amount, direction, reference, category):
    debit = amount if direction == 'debit' else ''
    credit = amount if direction == 'credit' else ''
    raw = csv_bytes([[day, desc, debit, credit, '', reference]])
    assert upload(client, account, raw).status_code == 201
    tax_year = date.fromisoformat(day).year + (date.fromisoformat(day).month >= 7)
    rows = client.get(f'/api/transactions?tax_year={tax_year}').json()['rows']
    match = next(x for x in rows if x['description'] == desc)
    response = client.patch(f"/api/transactions/{match['id']}", json={
        'category': category, 'note': 'Independently checked synthetic classification'
    })
    assert response.status_code == 200, response.text
    return match['id']


def loan(client, direction='borrowed', opening=0, opening_as_of='2023-01-01'):
    response = client.post('/api/finance/loans', json={
        'direction': direction,
        'counterparty_label': 'Synthetic friendly lender',
        'opening_as_of': opening_as_of,
        'opening_principal_minor': opening,
        'opening_basis': 'Explicit synthetic opening confirmation',
    })
    assert response.status_code == 201, response.text
    return response.json()['id']


def allocate(client, loan_id, tid, principal, markup=0):
    return client.post(f'/api/finance/loans/{loan_id}/allocations', json={
        'transaction_id': tid, 'principal_minor': principal, 'markup_minor': markup,
        'evidence_note': 'Synthetic repayment schedule reviewed independently',
    })


def test_borrowed_loan_principal_markup_separate_and_as_of(client):
    a = account_at(client, 'Synthetic Checking')
    credit = bank_tx(client, a, '2023-08-01', 'synthetic borrowed advance', '1000.00', 'credit', 'LN-A', 'loan_received')
    payment = bank_tx(client, a, '2024-07-01', 'synthetic split installment', '350.00', 'debit', 'LN-B', 'loan_installment_paid')
    identifier = loan(client, 'borrowed')
    assert allocate(client, identifier, credit, 100000).status_code == 201
    assert allocate(client, identifier, payment, 30000, 5000).status_code == 201
    early = client.get('/api/finance/loans?as_of=2024-06-30').json()['loans'][0]
    assert early['outstanding_principal_minor'] == 100000
    assert early['markup_observed_minor'] == 0
    current = client.get('/api/finance/loans?as_of=2024-07-02').json()['loans'][0]
    assert current['outstanding_principal_minor'] == 70000
    assert current['principal_advanced_minor'] == 100000
    assert current['principal_repaid_minor'] == 30000
    assert current['markup_observed_minor'] == 5000
    assert current['balance_kind'] == 'liability'
    assert not current['tax_treatment_verified'] and not current['opening_evidence_verified']
    assert client.get('/api/summary?tax_year=2025').json()['tax_due'] is None


def test_lent_loan_receivable_and_plain_principal_repayment(client):
    a = account_at(client, 'Synthetic Savings')
    given = bank_tx(client, a, '2024-09-01', 'synthetic loan given', '500.00', 'debit', 'LE-A', 'loan_given')
    repaid = bank_tx(client, a, '2025-01-01', 'synthetic loan repaid', '200.00', 'credit', 'LE-B', 'loan_repayment_received')
    identifier = loan(client, 'lent', 10000)
    assert allocate(client, identifier, given, 50000).status_code == 201
    assert allocate(client, identifier, repaid, 20000).status_code == 201
    result = client.get(f'/api/finance/loans/{identifier}?as_of=2025-02-01').json()
    assert result['outstanding_principal_minor'] == 40000
    assert result['balance_kind'] == 'receivable_asset'
    assert result['markup_observed_minor'] == 0


def test_exact_replay_is_idempotent_and_conflicting_relink_rejected(client):
    a = account_at(client, 'Account A')
    tid = bank_tx(client, a, '2026-07-01', 'loan debit synthetic', '100.00', 'credit', 'IDEMP', 'loan_received')
    first = loan(client)
    second = loan(client)
    assert allocate(client, first, tid, 10000).status_code == 201
    replay = allocate(client, first, tid, 10000)
    assert replay.status_code == 200 and replay.json()['already_linked']
    assert allocate(client, second, tid, 10000).status_code == 409
    assert allocate(client, first, tid, 9000).status_code == 409
    assert len(client.get(f'/api/finance/loans/{first}').json()['allocations']) == 1


def test_overpayment_and_out_of_order_backdated_posting_rejected(client):
    a = account_at(client, 'Synthetic Principal')
    repayment = bank_tx(client, a, '2024-02-03', 'loan repayment earlier', '40.00', 'debit', 'PR-A', 'debt_principal_paid')
    advance = bank_tx(client, a, '2024-02-04', 'loan advance later', '100.00', 'credit', 'PR-B', 'loan_received')
    identifier = loan(client)
    assert allocate(client, identifier, advance, 10000).status_code == 201
    assert allocate(client, identifier, repayment, 4000).status_code == 409
    assert client.get(f'/api/finance/loans/{identifier}').json()['outstanding_principal_minor'] == 10000


def test_invalid_categorization_and_split_and_missing_evidence(client):
    a = account_at(client, 'Synthetic No Evidence')
    given = bank_tx(client, a, '2026-08-01', 'loan should be lent', '100.00', 'debit', 'VAL-A', 'loan_given')
    identifier = loan(client, 'borrowed')
    assert allocate(client, identifier, given, 10000).status_code == 422
    tx = bank_tx(client, a, '2026-08-02', 'loan advance', '100.00', 'credit', 'VAL-B', 'loan_received')
    assert allocate(client, identifier, tx, 9000, 1000).status_code == 422
    assert allocate(client, identifier, tx, 9000).status_code == 422
    malformed = client.post('/api/finance/loans', json={
        'direction': 'borrowed', 'counterparty_label': ' ',
        'opening_as_of': '2024-01-01', 'opening_principal_minor': -1, 'opening_basis': 'bad basis'
    })
    assert malformed.status_code == 422


def test_loan_allocation_freezes_source_classification(client):
    a = account_at(client, 'Freeze Source')
    tx = bank_tx(client, a, '2025-01-01', 'borrowed synthetic', '50.00', 'credit', 'FREEZE', 'loan_received')
    loan_id = loan(client)
    assert allocate(client, loan_id, tx, 5000).status_code == 201
    rejected = client.patch(f'/api/transactions/{tx}', json={'category': 'salary', 'note': 'trying to change linked transaction'})
    assert rejected.status_code == 409
    assert client.get('/api/transactions?tax_year=2025').json()['rows'][0]['category'] == 'loan_received'


def test_transfer_confirmed_across_tax_year_and_replay(client):
    source = account_at(client, 'Source A')
    target = account_at(client, 'Target B')
    outgoing = bank_tx(client, source, '2026-06-30', 'synthetic transfer out', '250.00', 'debit', 'TR-O', 'own_transfer')
    incoming = bank_tx(client, target, '2026-07-01', 'synthetic transfer in', '250.00', 'credit', 'TR-I', 'own_transfer')
    request = {'debit_transaction_id': outgoing, 'credit_transaction_id': incoming,
               'evidence_note': 'Two account statements and owner evidence checked'}
    first = client.post('/api/finance/transfers/confirm', json=request)
    assert first.status_code == 201, first.text
    second = client.post('/api/finance/transfers/confirm', json=request)
    assert second.status_code == 200 and second.json()['already_confirmed']
    old = client.get('/api/finance/transfers/confirmed?tax_year=2026').json()['transfers']
    new = client.get('/api/finance/transfers/confirmed?tax_year=2027').json()['transfers']
    assert len(old) == len(new) == 1
    assert old[0]['status'] == 'OWNER_CONFIRMED_NOT_INDEPENDENTLY_VERIFIED'
    assert old[0]['no_tax_claim']
    assert client.patch(f'/api/transactions/{incoming}', json={'category': 'salary'}).status_code == 409


def test_transfer_requires_distinct_accounts_and_equal_amounts(client):
    a = account_at(client, 'Only Account')
    b = account_at(client, 'Different Account')
    outgoing = bank_tx(client, a, '2025-02-01', 'synthetic 100 out', '100.00', 'debit', 'OUT-100', 'own_transfer')
    same_bank = bank_tx(client, a, '2025-02-01', 'synthetic 100 in same account', '100.00', 'credit', 'IN-100', 'own_transfer')
    smaller = bank_tx(client, b, '2025-02-02', 'synthetic 90 in', '90.00', 'credit', 'IN-90', 'own_transfer')
    bad_note = {'debit_transaction_id': outgoing, 'credit_transaction_id': same_bank,
                'evidence_note': 'Independent source account record'}
    assert client.post('/api/finance/transfers/confirm', json=bad_note).status_code == 409
    bad_note['credit_transaction_id'] = smaller
    assert client.post('/api/finance/transfers/confirm', json=bad_note).status_code == 409
    assert client.get('/api/finance/transfers/confirmed?tax_year=2025').json()['transfers'] == []


def test_loan_and_transfer_labels_encrypted_in_synthetic_database(client, tmp_path):
    identifier = loan(client)
    a = account_at(client, 'Synthetic Finance')
    tx = bank_tx(client, a, '2024-01-12', 'advance to be linked', '55.00', 'credit', 'CRYPT-TX', 'loan_received')
    assert allocate(client, identifier, tx, 5500).status_code == 201
    with sqlite3.connect(tmp_path / 'test.db') as db:
        label, basis = db.execute('SELECT counterparty_label, opening_basis FROM loan_accounts').fetchone()
        note = db.execute('SELECT evidence_note FROM loan_allocations').fetchone()[0]
    assert all(value.startswith('TFLE1:') for value in [label, basis, note])
    assert 'Synthetic friendly lender' not in label and 'reviewed independently' not in note


def test_real_mode_disabled(client, monkeypatch, tmp_path):
    from app.main import create_app
    monkeypatch.setenv('APP_DATA_MODE', 'real')
    import pytest
    with pytest.raises(RuntimeError, match='Real-data mode'):
        create_app(f'sqlite:///{tmp_path / "still-disabled.db"}')


def test_new_financial_field_key_rotation(client, tmp_path, monkeypatch):
    """Key rotation includes encrypted loan labels and allocation evidence."""
    import base64
    import json
    import os
    from sqlalchemy import create_engine
    from app.rotate_ledger_keys import rotate_fields
    a = account_at(client, 'Rotation Synthetic Account')
    tx = bank_tx(client, a, '2024-05-01', 'rotation loan advance', '70.00', 'credit',
                 'ROTATE-LN', 'loan_received')
    loan_id = loan(client)
    assert allocate(client, loan_id, tx, 7000).status_code == 201
    old_keys = json.loads(os.environ['LEDGER_FIELD_KEYS_JSON'])
    old_keys['rotation_v2'] = base64.urlsafe_b64encode(b"R" * 32).decode()
    monkeypatch.setenv('LEDGER_FIELD_KEYS_JSON', json.dumps(old_keys))
    engine = create_engine(f'sqlite:///{tmp_path / "test.db"}')
    try:
        pending = rotate_fields(engine, new_key_id='rotation_v2', dry_run=True)
        assert pending['loan_accounts.counterparty_label'] == 1
        assert pending['loan_allocations.evidence_note'] == 1
        applied = rotate_fields(engine, new_key_id='rotation_v2', dry_run=False)
        assert applied['loan_accounts.opening_basis'] == 1
    finally:
        engine.dispose()
    with sqlite3.connect(tmp_path / 'test.db') as db:
        label = db.execute('SELECT counterparty_label FROM loan_accounts').fetchone()[0]
        note = db.execute('SELECT evidence_note FROM loan_allocations').fetchone()[0]
    assert label.startswith('TFLE1:rotation_v2:')
    assert note.startswith('TFLE1:rotation_v2:')
    assert client.get(f'/api/finance/loans/{loan_id}').status_code == 200
