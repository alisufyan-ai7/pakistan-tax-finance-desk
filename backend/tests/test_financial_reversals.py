"""Append-only synthetic corrections; never delete the bank source or audit trail."""
from __future__ import annotations

import sqlite3
from test_financial_links import account_at, bank_tx, loan, allocate


def reverse_loan(client, loan_id, allocation_id, reason='Synthetic correction supported by independent review'):
    return client.post(f'/api/finance/loans/{loan_id}/allocations/{allocation_id}/reverse',
                       json={'reason': reason})


def reverse_transfer(client, transfer_id, reason='Synthetic transfer confirmation reversed with evidence'):
    return client.post(f'/api/finance/transfers/{transfer_id}/reverse',
                       json={'reason': reason})


def test_cannot_reverse_advance_while_repayment_would_exceed_balance(client):
    a = account_at(client, 'Synthetic Loan Cycle')
    incoming = bank_tx(client, a, '2024-01-01', 'loan advance', '100.00', 'credit', 'LREV1', 'loan_received')
    outgoing = bank_tx(client, a, '2024-02-01', 'loan repayment', '40.00', 'debit', 'LREV2', 'debt_principal_paid')
    identifier = loan(client)
    advance = allocate(client, identifier, incoming, 10000).json()['id']
    repayment = allocate(client, identifier, outgoing, 4000).json()['id']
    cannot = reverse_loan(client, identifier, advance)
    assert cannot.status_code == 409
    assert client.get(f'/api/finance/loans/{identifier}?as_of=2024-03-01').json()['outstanding_principal_minor'] == 6000
    assert reverse_loan(client, identifier, repayment).status_code == 201
    assert reverse_loan(client, identifier, advance).status_code == 201
    end = client.get(f'/api/finance/loans/{identifier}?as_of=2024-03-01').json()
    assert end['outstanding_principal_minor'] == 0
    assert sorted(x['status'] for x in end['allocations']) == ['REVERSED', 'REVERSED']
    assert len(client.get('/api/finance/links/audit').json()['loan_reversals']) == 2
    assert client.get('/api/transactions?tax_year=2024').json()['rows']  # source preserved


def test_reversal_is_idempotent_and_transaction_can_be_reallocated(client):
    a = account_at(client, 'Synthetic Loan Correction')
    tid = bank_tx(client, a, '2024-05-01', 'loan to reverse', '99.00', 'credit', 'REVX', 'loan_received')
    source = loan(client)
    target = loan(client)
    original = allocate(client, source, tid, 9900).json()['id']
    first = reverse_loan(client, source, original)
    assert first.status_code == 201
    same = reverse_loan(client, source, original)
    assert same.status_code == 200 and same.json()['already_reversed']
    reassigned = allocate(client, target, tid, 9900)
    assert reassigned.status_code == 201, reassigned.text
    assert client.get(f'/api/finance/loans/{source}').json()['outstanding_principal_minor'] == 0
    assert client.get(f'/api/finance/loans/{target}').json()['outstanding_principal_minor'] == 9900
    assert client.patch(f'/api/transactions/{tid}', json={'category': 'salary'}).status_code == 409


def test_reversal_requires_meaningful_reason_and_matching_source(client):
    a = account_at(client, 'Synthetic Reversal Validation')
    tid = bank_tx(client, a, '2024-01-07', 'reversal record', '50.00', 'credit', 'VR-1', 'loan_received')
    first = loan(client)
    second = loan(client)
    allocation = allocate(client, first, tid, 5000).json()['id']
    assert reverse_loan(client, first, allocation, 'short').status_code == 422
    assert reverse_loan(client, second, allocation).status_code == 404
    assert reverse_loan(client, first, '00000000-0000-0000-0000-000000000000').status_code == 404
    assert client.get(f'/api/finance/loans/{first}').json()['outstanding_principal_minor'] == 5000


def test_confirmed_transfer_revoked_and_reconfirmed_without_deleting_history(client):
    source = account_at(client, 'Synthetic Transfer Source')
    target = account_at(client, 'Synthetic Transfer Destination')
    debit = bank_tx(client, source, '2025-07-01', 'own cash transfer debit', '10.00', 'debit', 'T-DA', 'own_transfer')
    credit_a = bank_tx(client, target, '2025-07-02', 'own transfer original credit', '10.00', 'credit', 'T-CA', 'own_transfer')
    credit_b = bank_tx(client, target, '2025-07-03', 'own transfer corrected credit', '10.00', 'credit', 'T-CB', 'own_transfer')
    transfer = client.post('/api/finance/transfers/confirm',json={
        'debit_transaction_id': debit, 'credit_transaction_id': credit_a,
        'evidence_note': 'Independent synthetic source and destination statements'
    })
    assert transfer.status_code == 201
    id1 = transfer.json()['id']
    assert reverse_transfer(client, id1).status_code == 201
    replay = reverse_transfer(client, id1)
    assert replay.status_code == 200 and replay.json()['already_reversed']
    changed = client.post('/api/finance/transfers/confirm',json={
        'debit_transaction_id': debit, 'credit_transaction_id': credit_b,
        'evidence_note': 'Corrected source matching on synthetic statements'
    })
    assert changed.status_code == 201, changed.text
    active = client.get('/api/finance/transfers/confirmed?tax_year=2026').json()['transfers']
    assert len(active) == 1 and active[0]['credit_transaction_id'] == credit_b
    audit = client.get('/api/finance/links/audit').json()
    assert len(audit['transfer_revocations']) == 1
    assert client.patch(f'/api/transactions/{credit_a}',json={'category':'other_income'}).status_code == 200
    assert client.patch(f'/api/transactions/{debit}',json={'category':'personal_expense'}).status_code == 409


def test_reversal_notes_are_encrypted_at_rest(client, tmp_path):
    account = account_at(client, 'Synthetic Revocation Crypto')
    tid = bank_tx(client, account, '2024-03-01', 'synthetic reversal', '18.00', 'credit', 'ENC-REV', 'loan_received')
    loan_id = loan(client)
    allocation_id = allocate(client, loan_id, tid, 1800).json()['id']
    reason = 'Synthetic reason for reversing the allocation'
    assert reverse_loan(client, loan_id, allocation_id, reason).status_code == 201
    with sqlite3.connect(tmp_path / 'test.db') as db:
        raw = db.execute('SELECT reason FROM loan_allocation_reversals').fetchone()[0]
    assert raw.startswith('TFLE1:') and reason not in raw
    history = client.get('/api/finance/links/audit').json()
    assert history['loan_reversals'][0]['reason'] == reason


def test_reversal_linkage_preserves_null_tax_calculation(client):
    a = account_at(client, 'Synthetic Tax Unknown')
    tid = bank_tx(client, a, '2026-08-01', 'borrowed not income', '500.00', 'credit', 'TX', 'loan_received')
    lid = loan(client)
    aid = allocate(client, lid, tid, 50000).json()['id']
    assert reverse_loan(client, lid, aid).status_code == 201
    annual = client.get('/api/summary?tax_year=2027').json()
    assert annual['tax_due'] is None and annual['fbr_ready'] is False
