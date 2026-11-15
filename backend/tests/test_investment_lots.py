"""Pure synthetic FIFO cost-lot arithmetic and API security regression."""
from copy import deepcopy
from app.investment_lots import calculate_lot_scenario, LotScenarioInput

BASE = {
    "synthetic_fixture": True,
    "currency": "PKR", "as_of": "2025-06-30",
    "opening_lots": [
        {"lot_ref":"OPEN-2023-01", "asset_ref":"SYNTH-SHARE-A", "asset_class":"equity",
         "acquired_on":"2023-05-15", "quantity":"10", "cost_basis_minor":100000,
         "evidence_note":"Fictional prior-year inventory declaration"}
    ],
    "trades": [
        {"source_ref":"BROKER-BUY-0001", "asset_ref":"SYNTH-SHARE-A", "asset_class":"equity",
         "kind":"buy", "executed_on":"2024-07-01", "sequence":1, "quantity":"5",
         "unit_price_minor":20000, "fees_minor":500,
         "evidence_note":"Fictional bought securities statement"},
        {"source_ref":"BROKER-SELL-0001", "asset_ref":"SYNTH-SHARE-A", "asset_class":"equity",
         "kind":"sell", "executed_on":"2024-07-10", "sequence":2, "quantity":"12",
         "unit_price_minor":30000, "fees_minor":1000,
         "evidence_note":"Fictional synthetic broker sale details"},
    ],
}


def test_fifo_opening_lots_partial_sales_and_fees():
    result=calculate_lot_scenario(LotScenarioInput(**BASE))
    item=result['holdings'][0]
    # first 10 from opening at cost 100000, next 2 from 5 @ 20000 + 500 fee = 40200
    assert item['remaining_quantity']=='3'
    assert item['remaining_fifo_cost_minor']==60300
    assert item['synthetic_realized_result_minor']==(360000-1000)-(100000+40200)
    assert result['synthetic_realized_result_by_tax_year_minor']['2025']==218800
    assert item['taxable_capital_gain_minor'] is None
    assert result['tax_due_minor'] is None


def test_rounding_conserves_remaining_fifo_cost_for_fractional_units():
    args={"synthetic_fixture":True, "as_of":"2024-06-30", "opening_lots":[], "trades":[
       {"source_ref":"CRYPTO-BUY-0001","asset_ref":"TEST-CRYPTO","asset_class":"crypto","kind":"buy",
        "executed_on":"2024-01-01","sequence":1,"quantity":"3","unit_price_minor":101,"fees_minor":1,
        "evidence_note":"Fictional crypto inventory cost basis"},
       {"source_ref":"CRYPTO-SELL-01","asset_ref":"TEST-CRYPTO","asset_class":"crypto","kind":"sell",
        "executed_on":"2024-01-02","sequence":1,"quantity":"1","unit_price_minor":101,"fees_minor":0,
        "evidence_note":"Fictional crypto matching sale units"},
       {"source_ref":"CRYPTO-SELL-02","asset_ref":"TEST-CRYPTO","asset_class":"crypto","kind":"sell",
        "executed_on":"2024-01-03","sequence":1,"quantity":"2","unit_price_minor":101,"fees_minor":0,
        "evidence_note":"Fictional second crypto matching sale"},
    ]}
    r=calculate_lot_scenario(LotScenarioInput(**args))
    holding=r['holdings'][0]
    assert holding['remaining_quantity']=='0'
    assert holding['remaining_fifo_cost_minor']==0
    assert holding['synthetic_realized_result_minor']==(303-304)


def test_separate_assets_and_july_tax_year_boundary(client):
    args=deepcopy(BASE)
    args['trades'].append({"source_ref":"GOLD-BUY-0000001","asset_ref":"SYNTH-GOLD-X","asset_class":"gold",
       "kind":"buy","executed_on":"2025-02-01","sequence":1,"quantity":"0.5",
       "unit_price_minor":40000,"fees_minor":100,
       "evidence_note":"Fictional half-unit gold acquisition"})
    res=client.post('/api/finance/investments/lot-scenario',json=args)
    assert res.status_code==200,res.text
    data=res.json()
    assert data['holding_count']==2
    assert data['taxable_capital_gains_minor'] is None
    assert next(x for x in data['holdings'] if x['asset_class']=='gold')['remaining_fifo_cost_minor']==20100
    assert data['historical_holdings_completeness_verified'] is False


def test_oversell_rejected_not_assumed_short(client):
    args=deepcopy(BASE)
    args['trades'][-1]['quantity']='20'
    res=client.post('/api/finance/investments/lot-scenario',json=args)
    assert res.status_code==422
    assert 'opening' in res.text.lower() or 'lots' in res.text.lower()


def test_duplicate_sources_ambiguous_order_and_asset_class_mismatch(client):
    a=deepcopy(BASE)
    a['trades'].append({**a['trades'][0], 'source_ref':a['trades'][1]['source_ref'], 'sequence':3})
    assert client.post('/api/finance/investments/lot-scenario',json=a).status_code==422
    b=deepcopy(BASE)
    b['trades'][1]['executed_on']=b['trades'][0]['executed_on']
    b['trades'][1]['sequence']=b['trades'][0]['sequence']
    assert client.post('/api/finance/investments/lot-scenario',json=b).status_code==422
    c=deepcopy(BASE)
    c['trades'][0]['asset_class']='gold'
    assert client.post('/api/finance/investments/lot-scenario',json=c).status_code==422
    d=deepcopy(BASE)
    d['opening_lots'][0]['acquired_on']='2025-01-01'
    assert client.post('/api/finance/investments/lot-scenario',json=d).status_code==422


def test_invalid_precision_dates_currency_and_types(client):
    cases=[{"synthetic_fixture":False},{"currency":"USD"},{"as_of":"2022-06-30"},
           {"trades":[{**BASE['trades'][0],"quantity":"1e30"}]},
           {"trades":[{**BASE['trades'][0],"quantity":"1.000000001"}]},
           {"trades":[{**BASE['trades'][0],"unit_price_minor":True}]},
           {"trades":[{**BASE['trades'][0],"fees_minor":-1}]},
           {"trades":[{**BASE['trades'][0],"executed_on":"2026-01-01"}]}]
    for change in cases:
        res=client.post('/api/finance/investments/lot-scenario',json={**BASE,**change})
        assert res.status_code==422,(change,res.text)


def test_july_june_tax_year_rollover(client):
    args={"synthetic_fixture":True,"as_of":"2024-07-02","opening_lots":[],"trades":[]}
    for i,day in enumerate(['2024-06-30','2024-07-01']):
        args['trades'] += [
          {"source_ref":f"TEST-BUY-{i:04d}","asset_ref":"SYMBOL","asset_class":"equity","kind":"buy",
           "executed_on":day,"sequence":1,"quantity":"1","unit_price_minor":1000,"fees_minor":0,
           "evidence_note":"Fictional independent tax-year purchase"},
          {"source_ref":f"TEST-SELL-{i:03d}","asset_ref":"SYMBOL","asset_class":"equity","kind":"sell",
           "executed_on":day,"sequence":2,"quantity":"1","unit_price_minor":2000,"fees_minor":0,
           "evidence_note":"Fictional independent tax-year sale"},
        ]
    res=client.post('/api/finance/investments/lot-scenario',json=args)
    assert res.status_code==200,res.text
    assert res.json()['synthetic_realized_result_by_tax_year_minor']=={'2024':1000,'2025':1000}


def test_auth_and_fbr_not_claimed(client):
    assert client.post('/api/finance/investments/lot-scenario',json=BASE,auth=None).status_code==401
    report=client.post('/api/finance/investments/lot-scenario',json=BASE).json()
    assert report['fbr_tax_method_approved'] is False
    assert report['market_prices_verified'] is False
    assert report['fbr_ready'] is False