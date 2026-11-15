"""Synthetic-only movement pairing: no claimed tax and no loan balances."""
from datetime import date
from types import SimpleNamespace
from app.movement_analysis import analyze_movements
from test_imports import csv_bytes, upload


def item(i, account, day, *, debit=0, credit=0, category="own_transfer", reviewed=True, excluded=False, overlap=False, resolved=False):
    return SimpleNamespace(id=i,account_id=account,posted_on=date.fromisoformat(day),
        debit_minor=debit,credit_minor=credit,category=category,reviewed=reviewed,
        excluded=excluded,overlap_possible=overlap,overlap_resolved=resolved)


def window(items, owners=None):
    return analyze_movements(items, owners or {"A":"individual","B":"individual","C":"individual"}, date(2025,7,1),date(2026,6,30))


def test_unique_cross_account_pair_only_candidate_not_confirmed():
    rows=[item("d","A","2025-09-01",debit=120000),item("c","B","2025-09-02",credit=120000)]
    result=window(rows)
    assert len(result['transfer_candidates'])==1
    assert result['transfer_candidates'][0]['status']=='UNVERIFIED_TRANSFER_CANDIDATE'
    assert result['transfer_candidates'][0]['amount_pkr']=='1200.00'
    assert result['loan_balance_verified'] is False
    assert result['tax_eligibility_verified'] is False


def test_two_sided_ambiguity_never_autopairs():
    rows=[item("d","A","2025-09-01",debit=10000),
          item("c1","B","2025-09-01",credit=10000),
          item("c2","C","2025-09-01",credit=10000)]
    result=window(rows)
    assert result['transfer_candidates']==[]
    assert result['ambiguous_transfer_transaction_ids']==['c1','c2','d']


def test_same_account_other_entity_and_unreviewed_do_not_pair():
    rows=[item('d','A','2025-09-01',debit=8000),item('c','A','2025-09-01',credit=8000)]
    assert window(rows)['transfer_candidates']==[]
    rows=[item('d','A','2025-09-01',debit=8000),item('c','B','2025-09-01',credit=8000)]
    assert window(rows,{'A':'individual','B':'company'})['transfer_candidates']==[]
    rows[1].reviewed=False
    assert window(rows)['transfer_candidates']==[]
    assert window(rows)['unreviewed_record_count']==1


def test_year_boundary_and_principal_totals_without_tax_claims():
    rows=[item('d','A','2025-06-30',debit=5000),item('c','B','2025-07-01',credit=5000),
          item('loan','B','2025-08-02',credit=200000,category='loan_received'),
          item('zakat','B','2025-08-05',debit=2500,category='zakat')]
    result=window(rows)
    assert len(result['transfer_candidates'])==1
    assert result['reviewed_non_earnings_movement_pkr']=={
        'loan_received':'2000.00','own_transfer':'50.00','zakat':'25.00'}
    assert result['tax_eligibility_verified'] is False


def test_actual_synthetic_api_remains_read_only_and_conservative(client, account):
    second=client.post('/api/accounts',json={'name':'Second synthetic account','institution':'Other example'}).json()['id']
    first=csv_bytes([["2025-10-01","synthetic own transfer out","75.00","","925.00","OUTREF"]])
    inbound=csv_bytes([["2025-10-02","synthetic own transfer in","","75.00","1075.00","INREF"]])
    assert upload(client,account,first,opening_balance='1000.00').status_code==201
    assert upload(client,second,inbound,opening_balance='1000.00').status_code==201
    rows=client.get('/api/transactions?tax_year=2026').json()['rows']
    for tx in rows:
        assert client.patch(f"/api/transactions/{tx['id']}",json={'category':'own_transfer','note':'Synthetic own movement'}).status_code==200
    result=client.get('/api/finance/movement-review?tax_year=2026')
    assert result.status_code==200, result.text
    payload=result.json()
    assert len(payload['transfer_candidates'])==1
    assert payload['transfer_candidates'][0]['amount_pkr']=='75.00'
    assert payload['tax_eligibility_verified'] is False
    assert payload['loan_balance_verified'] is False
    assert client.get('/api/summary?tax_year=2026').json()['classified_totals']=={'own_transfer':'150.00'}