"""Narrow FBR salary slab test vectors; no real return or tax due claims."""
import pytest


def fake(y, income, salary=None):
    return {'synthetic_fixture':True,'tax_year':y,
      'taxable_income_minor':income*100,
      'salary_chargeable_minor':(salary if salary is not None else income)*100,
      'confirms_no_separately_taxed_sources':True,
      'confirms_no_other_tax_adjustments':True}


@pytest.mark.parametrize('income,expected',[
 (0,0),(600000,0),(1200000,6000),(2200000,116000),
 (3200000,316000),(4100000,541000),(5600000,976000),
 (7000000,1424000),(10000000,2474000)
])
def test_2027_threshold_vectors(client,income,expected):
    r=client.post('/api/tax/salary-slab-preview',json=fake(2027,income))
    assert r.status_code==200,r.text
    out=r.json()
    assert out['salary_slab_component_minor']==expected*100
    assert out['tax_due_minor'] is None and not out['fbr_ready']


def test_2026_2027_salaried_difference(client):
    x=client.post('/api/tax/salary-slab-preview',json=fake(2026,3200000)).json()
    y=client.post('/api/tax/salary-slab-preview',json=fake(2027,3200000)).json()
    assert x['salary_slab_component_minor']==346000*100
    assert y['salary_slab_component_minor']==316000*100


def test_strict_salary_75pct_and_mixed_income_scope(client):
    assert client.post('/api/tax/salary-slab-preview',json=fake(2027,1000000,750000)).status_code==422
    assert client.post('/api/tax/salary-slab-preview',json=fake(2027,1000000,750001)).status_code==200
    assert client.post('/api/tax/salary-slab-preview',json=fake(2027,2000000,1000000)).status_code==422
    assert client.post('/api/tax/salary-slab-preview',json={**fake(2027,1000000),'confirms_no_separately_taxed_sources':False}).status_code==422
    assert client.post('/api/tax/salary-slab-preview',json={**fake(2027,1000000),'synthetic_fixture':False}).status_code==422
    assert client.post('/api/tax/salary-slab-preview',json=fake(2025,1200000)).status_code==422


def test_fbr_year_registry_is_explicit(client):
    for year in range(2023,2028):
        r=client.get(f'/api/tax/rules?tax_year={year}')
        assert r.status_code==200,r.text
        data=r.json()
        assert data['tax_year']==year and not data['filing_ready']
        assert data['salary_slab_preview_available']==(year>=2026)
        assert 'fbr.gov.pk' in data['source_index']
    assert client.get('/api/tax/rules?tax_year=2028').status_code==422


def test_evidence_only_opportunities_have_official_source(client,account):
    from test_imports import csv_bytes,upload
    raw=csv_bytes([['2025-03-01','Synthetic donation','100.00','','900.00','DON1'],
                   ['2025-03-02','Synthetic business cost','200.00','','700.00','BUS1']])
    assert upload(client,account,raw).status_code==201
    rows=client.get('/api/transactions?tax_year=2025').json()['rows']
    for row in rows:
        category='donation' if row['description']=='Synthetic donation' else 'business_expense'
        r=client.patch(f"/api/transactions/{row['id']}",json={'category':category,'note':'Synthetic evidence review pending'})
        assert r.status_code==200
    out=client.get('/api/tax/opportunities?tax_year=2025').json()
    assert out['opportunities']
    for hint in out['opportunities']:
        assert hint['potential_tax_savings'] is None
        assert hint['legal_eligibility_verified'] is False
        assert hint['qualification_status']=='EVIDENCE_REQUIRED'
        assert 'fbr.gov.pk' in hint['fbr_source_index']
        assert hint['law_provision']
    assert client.get('/api/summary?tax_year=2025').json()['tax_due'] is None