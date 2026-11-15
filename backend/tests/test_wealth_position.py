"""Read-only synthetic financial position: never invent real wealth or taxes."""
from __future__ import annotations

from test_imports import csv_bytes, upload
from test_financial_links import account_at, loan
from test_cash_wealth import opening, movement


def statement(client, account, day, desc, amount, direction, balance, ref):
    debit = amount if direction == 'debit' else ''
    credit = amount if direction == 'credit' else ''
    raw = csv_bytes([[day, desc, debit, credit, balance, ref]])
    result = upload(client, account, raw)
    assert result.status_code == 201, result.text
    return result.json()


def test_no_accounts_never_creates_net_worth_or_tax(client):
    r = client.get('/api/finance/wealth/observed?as_of=2025-06-30')
    assert r.status_code == 200
    obj = r.json()
    assert obj['recorded_components_position_minor'] is None
    assert obj['net_worth_minor'] is None and obj['tax_due'] is None
    assert 'NO_REGISTERED_BANK_ACCOUNTS' in obj['missing_evidence']
    assert 'NO_DECLARED_CASH_HOLDINGS' in obj['missing_evidence']
    assert obj['fbr_wealth_reconciled'] is False


def test_bank_cash_loans_ytd_are_only_recorded_components(client):
    acc=account_at(client,'Synthetic Observable PKR Bank')
    statement(client,acc,'2024-06-30','synthetic income','1000.00','credit','1000.00','OBS1')
    statement(client,acc,'2025-06-30','synthetic income later','300.00','credit','1300.00','OBS2')
    cid=opening(client,amount=5000)
    borrowed=loan(client,'borrowed',opening=10000)
    lent=loan(client,'lent',opening=2000)
    first=client.get('/api/finance/wealth/observed?as_of=2024-06-30').json()
    second=client.get('/api/finance/wealth/observed?as_of=2025-06-30').json()
    assert first['bank_observed_minor']==100000
    assert first['cash_declared_minor']==5000
    assert first['loan_liabilities_declared_minor']==10000
    assert first['loan_receivables_declared_minor']==2000
    assert first['recorded_components_position_minor']==97000
    assert second['recorded_components_position_minor']==127000
    assert first['recorded_components_present']
    assert first['net_worth_minor'] is None and not first['fbr_wealth_reconciled']
    fiscal=client.get('/api/finance/wealth/annual?tax_year=2025').json()
    assert fiscal['status']=='RECORDED_COMPONENTS_ONLY_NOT_FBR'
    assert fiscal['recorded_component_change_minor']==30000
    assert fiscal['tax_due'] is None
    assert cid and borrowed and lent


def test_stale_bank_is_excluded_even_if_last_balance_is_known(client):
    acc=account_at(client,'Synthetic Stale Account')
    statement(client,acc,'2024-01-01','older synthetic salary','100.00','credit','100.00','STALE')
    opening(client,amount=0)
    snapshot=client.get('/api/finance/wealth/observed?as_of=2024-06-30').json()
    bank=snapshot['bank_accounts'][0]
    assert bank['status']=='STALE_BANK_OBSERVATION'
    assert bank['observed_balance_minor']==10000
    assert bank['included_balance_minor'] is None
    assert snapshot['recorded_components_position_minor'] is None
    assert any('STALE_BANK_OBSERVATION' in gap for gap in snapshot['missing_evidence'])


def test_latest_row_without_bank_balance_must_not_fallback(client):
    acc=account_at(client,'Synthetic Partial Balance')
    statement(client,acc,'2024-06-28','salary synthetic','100.00','credit','100.00','P1')
    statement(client,acc,'2024-06-30','unverified second row','10.00','debit','','P2')
    opening(client)
    snapshot=client.get('/api/finance/wealth/observed?as_of=2024-06-30').json()
    assert snapshot['bank_accounts'][0]['status']=='MISSING_LATEST_BANK_BALANCE'
    assert snapshot['recorded_components_position_minor'] is None


def test_conflicting_same_day_export_evidence_never_guesses(client):
    acc=account_at(client,'Synthetic Same Day Conflict')
    statement(client,acc,'2024-06-30','sample one','100.00','credit','100.00','C1')
    statement(client,acc,'2024-06-30','sample two','50.00','credit','50.00','C2')
    opening(client)
    snapshot=client.get('/api/finance/wealth/observed?as_of=2024-06-30').json()
    assert snapshot['bank_accounts'][0]['status']=='CONFLICTING_SAME_DAY_BALANCES'
    assert snapshot['recorded_components_position_minor'] is None


def test_last_row_same_document_wins_and_no_bank_source_is_certified(client):
    acc=account_at(client,'Same Document Cash Bank')
    raw=csv_bytes([
        ['2024-06-30','one','', '100.00','100.00','R1'],
        ['2024-06-30','two','25.00','','75.00','R2'],
    ])
    assert upload(client,acc,raw,opening_balance='0.00').status_code==201
    opening(client,amount=0)
    snapshot=client.get('/api/finance/wealth/observed?as_of=2024-06-30').json()
    assert snapshot['bank_observed_minor']==7500
    assert snapshot['recorded_components_position_minor']==7500
    assert snapshot['bank_accounts'][0]['status']=='OBSERVED_BANK_BALANCE_NOT_CERTIFIED'
    assert snapshot['fbr_wealth_reconciled'] is False


def test_declared_cash_manual_receipts_remain_unverified(client):
    acc=account_at(client,'Synthetic Manual Cash Bank')
    statement(client,acc,'2024-06-30','bank last','50.00','credit','50.00','MAN1')
    cid=opening(client,amount=1000)
    assert movement(client,cid,'manual_receipt',500,'2024-06-01').status_code==201
    snapshot=client.get('/api/finance/wealth/observed?as_of=2024-06-30').json()
    assert snapshot['unverified_manual_cash_receipts_minor']==500
    assert snapshot['recorded_components_position_minor']==6500
    assert snapshot['net_worth_minor'] is None and snapshot['tax_due'] is None
    assert 'REGISTERED_ACCOUNTS' in snapshot['source_scope']


def test_annual_gap_is_unknown_not_negative_wealth(client):
    acc=account_at(client,'Synthetic Only Closing Year')
    statement(client,acc,'2025-06-30','first bank import','100.00','credit','100.00','FY1')
    opening(client,amount=0)
    report=client.get('/api/finance/wealth/annual?tax_year=2025').json()
    assert report['recorded_component_change_minor'] is None
    assert report['status']=='INSUFFICIENT_SOURCE_COVERAGE'
    assert report['opening_observed']['recorded_components_position_minor'] is None
    assert report['closing_observed']['recorded_components_position_minor']==10000
    assert client.get('/api/finance/wealth/annual?tax_year=2022').status_code==422