"""M2g: cash in hand, bank-link evidence and historical wealth bridge.

All data and counterparties synthetic. No tax liability or FBR claim.
"""
from __future__ import annotations

import sqlite3
from test_financial_links import account_at, bank_tx


def opening(client, *, date='2023-01-01', amount=10000, label='Synthetic cash purse'):
    result = client.post('/api/finance/cash', json={
        'label': label, 'opening_as_of': date, 'opening_minor': amount,
        'evidence_basis': 'Owner-declared synthetic count at explicit opening date'
    })
    assert result.status_code == 201, result.text
    return result.json()['id']


def movement(client, cid, kind, amount, day, *, tid=None, note='Synthetic dated evidence for cash movement'):
    body = {'kind': kind, 'amount_minor': amount, 'posted_on': day,
            'evidence_note': note}
    if tid is not None:
        body['transaction_id'] = tid
    return client.post(f'/api/finance/cash/{cid}/movements', json=body)


def reverse(client, cid, mid, reason='Correction supported by synthetic source review'):
    return client.post(f'/api/finance/cash/{cid}/movements/{mid}/reverse', json={'reason': reason})


def test_withdrawal_spending_deposit_and_fy_boundary(client):
    acc = account_at(client, 'Synthetic Cash Bank')
    out = bank_tx(client, acc, '2025-06-30', 'cash ATM example', '80.00', 'debit', 'CASH-O', 'atm_cash')
    inc = bank_tx(client, acc, '2025-07-01', 'cash bank deposit example', '25.00', 'credit', 'CASH-I', 'cash_deposit')
    cid = opening(client, amount=2000)
    assert movement(client, cid, 'bank_withdrawal', 8000, '2025-06-30', tid=out).status_code == 201
    assert movement(client, cid, 'manual_spend', 1000, '2025-06-30').status_code == 201
    assert movement(client, cid, 'bank_deposit', 2500, '2025-07-01', tid=inc).status_code == 201
    prior = client.get(f'/api/finance/cash/{cid}?as_of=2025-06-30').json()
    later = client.get(f'/api/finance/cash/{cid}?as_of=2025-07-01').json()
    assert prior['cash_minor'] == 9000 and later['cash_minor'] == 6500
    fy2025 = client.get('/api/finance/cash/annual?tax_year=2025').json()
    fy2026 = client.get('/api/finance/cash/annual?tax_year=2026').json()
    assert fy2025['opening_cash_minor'] == 2000 and fy2025['closing_cash_minor'] == 9000
    assert fy2025['net_cash_change_minor'] == 7000
    assert fy2026['opening_cash_minor'] == 9000 and fy2026['closing_cash_minor'] == 6500
    assert fy2026['net_cash_change_minor'] == -2500
    assert fy2026['tax_due'] is None and not fy2026['fbr_wealth_verified']
    # Cash deposit must not enter earned-income categories or tax projections.
    assert client.get('/api/summary?tax_year=2026').json()['tax_due'] is None
    assert client.patch(f'/api/transactions/{out}', json={'category': 'personal_expense'}).status_code == 409
    assert client.patch(f'/api/transactions/{inc}', json={'category': 'salary'}).status_code == 409


def test_missing_opening_does_not_turn_into_zero_wealth(client):
    report = client.get('/api/finance/cash/annual?tax_year=2024').json()
    assert report['opening_cash_minor'] is None and not report['cash_coverage_complete']
    cid = opening(client, date='2023-10-01', amount=0)
    report = client.get('/api/finance/cash/annual?tax_year=2024').json()
    assert report['opening_cash_minor'] is None and report['closing_cash_minor'] == None
    assert report['cash_accounts'][0]['status'] == 'MISSING_OPENING_EVIDENCE'
    assert client.get(f'/api/finance/cash/{cid}?as_of=2023-09-30').json()['cash_minor'] is None
    fy2025 = client.get('/api/finance/cash/annual?tax_year=2025').json()
    assert fy2025['opening_cash_minor'] == 0 and fy2025['cash_coverage_complete']


def test_bank_source_validation_and_exact_replay(client):
    acc = account_at(client, 'Example Cash Checking')
    tid = bank_tx(client, acc, '2024-09-01', 'synthetic cash withdrawal', '50.00', 'debit', 'VALID-C', 'atm_cash')
    cid = opening(client)
    second = opening(client, label='Different synthetic holding')
    assert movement(client,cid,'bank_deposit',5000,'2024-09-01',tid=tid).status_code == 422
    assert movement(client,cid,'bank_withdrawal',4999,'2024-09-01',tid=tid).status_code == 422
    assert movement(client,cid,'bank_withdrawal',5000,'2024-09-02',tid=tid).status_code == 422
    first = movement(client,cid,'bank_withdrawal',5000,'2024-09-01',tid=tid)
    assert first.status_code == 201, first.text
    replay = movement(client,cid,'bank_withdrawal',5000,'2024-09-01',tid=tid)
    assert replay.status_code == 200 and replay.json()['already_linked']
    assert movement(client,second,'bank_withdrawal',5000,'2024-09-01',tid=tid).status_code == 409
    bad = client.post(f'/api/finance/cash/{cid}/movements',json={
        'kind':'manual_spend','amount_minor':500,'posted_on':'2024-09-02',
        'transaction_id':tid,'evidence_note':'An invalid manual entry with bank source'})
    assert bad.status_code == 422
    assert len(client.get(f'/api/finance/cash/{cid}').json()['movements']) == 1


def test_out_of_order_negative_balance_and_no_invalid_reverse(client):
    cid = opening(client, amount=0)
    incoming = movement(client,cid,'manual_receipt',10000,'2024-05-06')
    assert incoming.status_code == 201
    spent = movement(client,cid,'manual_spend',9000,'2024-05-07')
    assert spent.status_code == 201
    assert movement(client,cid,'manual_spend',2000,'2024-05-01').status_code == 409
    assert movement(client,cid,'manual_spend',2000,'2024-05-08').status_code == 409
    assert reverse(client,cid,incoming.json()['id']).status_code == 409
    assert reverse(client,cid,spent.json()['id']).status_code == 201
    assert reverse(client,cid,incoming.json()['id']).status_code == 201
    report = client.get(f'/api/finance/cash/{cid}?as_of=2024-05-10').json()
    assert report['cash_minor'] == 0
    assert sorted(x['status'] for x in report['movements']) == ['REVERSED','REVERSED']
    assert not report['fbr_wealth_verified']


def test_reversal_relinks_bank_source_and_preserves_history(client):
    acc = account_at(client, 'Synthetic Correction Bank')
    tid = bank_tx(client,acc,'2024-12-01','withdraw to cash','40.00','debit','RL-CASH','atm_cash')
    first = opening(client, amount=1000)
    second = opening(client, amount=0, label='Second counted cash holding')
    m = movement(client,first,'bank_withdrawal',4000,'2024-12-01',tid=tid)
    assert m.status_code == 201
    rid = reverse(client,first,m.json()['id'])
    assert rid.status_code == 201
    assert reverse(client,first,m.json()['id']).status_code == 200
    assert client.patch(f'/api/transactions/{tid}',json={'category':'atm_cash'}).status_code == 200
    changed = movement(client,second,'bank_withdrawal',4000,'2024-12-01',tid=tid)
    assert changed.status_code == 201,changed.text
    assert client.get(f'/api/finance/cash/{first}').json()['cash_minor'] == 1000
    assert client.get(f'/api/finance/cash/{second}').json()['cash_minor'] == 4000
    previous = client.get(f'/api/finance/cash/{first}').json()['movements'][0]
    assert previous['status'] == 'REVERSED' and previous['reversal_reason']


def test_cash_evidence_encrypted_and_no_tax_claim(client,tmp_path):
    cid = opening(client,label='Private synthetic hiding place',amount=500)
    m = movement(client,cid,'manual_spend',100,'2024-01-01',note='Explicit synthetic retail cash payment')
    assert m.status_code == 201
    assert reverse(client,cid,m.json()['id']).status_code == 201
    with sqlite3.connect(tmp_path/'test.db') as conn:
        label,basis = conn.execute('SELECT label,evidence_basis FROM cash_holdings').fetchone()
        note = conn.execute('SELECT evidence_note FROM cash_movements').fetchone()[0]
        reason = conn.execute('SELECT reason FROM cash_movement_reversals').fetchone()[0]
    for encrypted in (label,basis,note,reason):
        assert encrypted.startswith('TFLE1:') and 'synthetic' not in encrypted.lower()
    report=client.get(f'/api/finance/cash/{cid}?as_of=2024-02-01').json()
    assert report['cash_minor']==500 and not report['tax_treatment_verified']
    assert client.get('/api/summary?tax_year=2024').json()['tax_due'] is None


def test_reject_explicit_cash_without_proof_and_future_tax_year(client):
    cid=opening(client)
    assert movement(client,cid,'manual_receipt',100,'2024-01-01',note='short').status_code==422
    assert movement(client,cid,'manual_receipt',100,'2022-12-31').status_code==422
    assert client.get('/api/finance/cash/annual?tax_year=2022').status_code==422
    assert client.post('/api/finance/cash',json={'label':'x','opening_as_of':'2023-01-01',
        'opening_minor': -1,'evidence_basis':'short'}).status_code == 422