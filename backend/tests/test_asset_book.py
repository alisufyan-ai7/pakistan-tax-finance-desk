"""Synthetic encrypted investment/asset records. No third-party market quotes."""
import sqlite3

BASE={'synthetic_fixture':True,'kind':'mutual_fund','label':'Synthetic units holding',
      'as_of':'2024-06-30','acquired_on':'2024-01-01','quantity':'12.5',
      'cost_basis_minor':100000,'declared_value_minor':125000,
      'evidence_basis':'Explicit synthetic position evidence only'}


def test_immutable_encrypted_asset_snapshot(client,tmp_path):
    r=client.post('/api/finance/assets/snapshots',json=BASE)
    assert r.status_code==201,r.text
    body=r.json();assert body['valuation_verified'] is False
    with sqlite3.connect(tmp_path/'test.db') as db:
        stored=db.execute('SELECT payload_json FROM asset_snapshots').fetchone()[0]
    assert stored.startswith('TFLE1:') and 'Synthetic units holding' not in stored
    assert '125000' not in stored and '2024-06-30' not in stored
    p=client.get('/api/finance/assets/position?as_of=2024-06-30').json()
    assert p['declared_asset_components_minor']==125000 and p['net_worth_minor'] is None


def test_replay_conflicts_and_time_travel(client):
    first=client.post('/api/finance/assets/snapshots',json=BASE)
    assert first.status_code==201
    identical=client.post('/api/finance/assets/snapshots',json={**BASE,'position_id':first.json()['position_id']})
    assert identical.status_code==200 and identical.json()['already_recorded']
    changed=client.post('/api/finance/assets/snapshots',json={**BASE,'position_id':first.json()['position_id'],'declared_value_minor':222000})
    assert changed.status_code==409
    later={**BASE,'position_id':first.json()['position_id'],'as_of':'2025-06-30','declared_value_minor':180000}
    assert client.post('/api/finance/assets/snapshots',json=later).status_code==201
    assert client.get('/api/finance/assets/position?as_of=2024-06-29').json()['registered_snapshot_count']==0
    assert client.get('/api/finance/assets/position?as_of=2024-06-30').json()['declared_asset_components_minor']==125000
    assert client.get('/api/finance/assets/position?as_of=2025-06-30').json()['declared_asset_components_minor']==180000


def test_unknown_values_propagate_null(client):
    a={**BASE,'declared_value_minor':None}
    assert client.post('/api/finance/assets/snapshots',json=a).status_code==201
    x=client.get('/api/finance/assets/position?as_of=2024-06-30').json()
    assert x['declared_asset_components_minor'] is None
    assert x['unvalued_position_count']==1
    assert x['net_worth_minor'] is None


def test_lent_liabilities_are_not_income(client):
    payload={**BASE,'kind':'other_liability','label':'Synthetic personal liability',
        'declared_value_minor':80000,'quantity':None}
    assert client.post('/api/finance/assets/snapshots',json=payload).status_code==201
    x=client.get('/api/finance/assets/position?as_of=2024-06-30').json()
    assert x['declared_asset_components_minor']==0 and x['declared_liability_components_minor']==80000
    assert x['net_worth_minor'] is None and x['tax_due_minor'] is None


def test_asset_invalid_evidence_and_owner(client):
    assert client.post('/api/finance/assets/snapshots',json={**BASE,'synthetic_fixture':False}).status_code==422
    assert client.post('/api/finance/assets/snapshots',json={**BASE,'legal_owner':'company'}).status_code==422
    assert client.post('/api/finance/assets/snapshots',json={**BASE,'kind':'unverified_product'}).status_code==422
    assert client.post('/api/finance/assets/snapshots',json={**BASE,'quantity':'NaN'}).status_code==422
    assert client.post('/api/finance/assets/snapshots',json={**BASE,'declared_value_minor':None,'cost_basis_minor':None}).status_code==422


def test_assets_do_not_affect_fbr_tax_results(client):
    assert client.post('/api/finance/assets/snapshots',json=BASE).status_code==201
    summary=client.get('/api/summary?tax_year=2024').json()
    assert summary['tax_due'] is None and not summary['fbr_ready']