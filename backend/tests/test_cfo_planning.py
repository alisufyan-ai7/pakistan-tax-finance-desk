"""Hypothetical CFO scenarios and synthetic encrypted-journal briefing tests."""
from copy import deepcopy
from app.cfo_planning import CFOScenarioInput, scenario_forecast

SCENARIO={
  "synthetic_fixture":True, "currency":"PKR", "opening_liquid_minor":120000,
  "essential_monthly_outflow_minor":40000,"reserve_target_months":3,
  "forecast_months":4,
  "flows":[
    {"rule_id":"income_one","category":"salary","direction":"in", "amount_minor":50000,
     "start_month":1,"end_month":4,"every_months":1,"assumption_note":"Synthetic salary assumption"},
    {"rule_id":"expense_one","category":"living_expense","direction":"out","amount_minor":30000,
     "start_month":1,"end_month":4,"every_months":1,"assumption_note":"Synthetic living expense assumption"},
  ],
  "goals":[{"goal_id":"emergency","amount_minor":80000,"due_month":4,"evidence_note":"Synthetic goal for scenario"}],
}


def test_pure_forecast_periodic_flows_and_goals():
    r=scenario_forecast(CFOScenarioInput(**SCENARIO))
    assert [m["projected_liquid_minor"] for m in r["months"]]==[140000,160000,180000,200000]
    assert r["reserve_target_minor"]==120000
    assert r["goals"][0]["on_track_in_scenario"] is True
    assert r["tax_due_minor"] is None and not r["investment_advice_verified"]
    assert r["category_movement_minor"]["salary"]==200000


def test_one_off_investment_shortfall_flag_not_trade_advice(client):
    scenario=deepcopy(SCENARIO)
    scenario["flows"].append({"rule_id":"investment_one","category":"investment_contribution","direction":"out",
                              "amount_minor":220000,"start_month":2,"end_month":2,"every_months":1,
                              "assumption_note":"Synthetic one-time investment proposal"})
    result=client.post('/api/finance/advisor/scenarios',json=scenario)
    assert result.status_code==200,result.text
    body=result.json()
    assert body["first_negative_month"]==2
    ids={i["code"] for i in body["insights"]}
    assert 'PROJECTED_SHORTFALL' in ids and 'INVESTMENT_VS_LIQUIDITY' in ids
    assert body["investment_advice_verified"] is False
    assert all(i["potential_tax_savings_minor"] is None for i in body["insights"])
    assert not body["fbr_filing_ready"]


def test_bounded_rule_recurrence_and_no_fabricated_months(client):
    scenario=deepcopy(SCENARIO)
    scenario["flows"]=[{"rule_id":"quarterly","category":"business_receipt","direction":"in",
      "amount_minor":10000,"start_month":1,"end_month":4,"every_months":3,
      "assumption_note":"Synthetic quarterly cash inflows"}]
    result=client.post('/api/finance/advisor/scenarios',json=scenario)
    assert result.status_code==200,result.text
    rows=result.json()["months"]
    assert [r['receipts_minor'] for r in rows]==[10000,0,0,10000]


def test_scenarios_fail_closed_on_bad_inputs(client):
    cases=[
        {"synthetic_fixture":False}, {"currency":"USD"}, {"opening_liquid_minor":True},
        {"opening_liquid_minor":-1}, {"forecast_months":61},
        {"flows":[SCENARIO['flows'][0], SCENARIO['flows'][0]]},
        {"flows":[{**SCENARIO['flows'][0],"direction":"out"}]},
        {"flows":[{**SCENARIO['flows'][0],"end_month":5}]},
        {"goals":[{**SCENARIO['goals'][0],"due_month":5}]},
    ]
    for variant in cases:
        item={**SCENARIO,**variant}
        response=client.post('/api/finance/advisor/scenarios',json=item)
        assert response.status_code==422,(variant,response.text)


def test_briefing_does_not_count_non_operating_flows_as_income(client):
    base={"synthetic_fixture":True,"source_type":"owner_declared","posted_on":"2024-06-30",
          "amount_minor":15000,"account_ref":"synthetic-account","evidence_note":"Explicit fictional synthetic advisor record"}
    events=[
      {"source_ref":"CFO-INCOME-001","event_kind":"income","direction":"credit"},
      {"source_ref":"CFO-SPEND-001","event_kind":"expense","direction":"debit","amount_minor":9000},
      {"source_ref":"CFO-LOAN-0001","event_kind":"loan_advance","direction":"credit","amount_minor":50000},
      {"source_ref":"CFO-TRANSFER-01","event_kind":"bank_transfer","direction":"credit","amount_minor":50000},
    ]
    for e in events:
        posted=client.post('/api/finance/private-events',json={**base,**e})
        assert posted.status_code==201,posted.text
    brief=client.get('/api/finance/advisor/briefing?tax_year=2024')
    assert brief.status_code==200,brief.text
    data=brief.json()
    assert data['event_count']==4
    assert data['observed_labeled_income_credits_minor']==15000
    assert data['observed_labeled_expense_debits_minor']==9000
    assert data['observed_labeled_difference_minor']==6000
    assert data['other_or_nonoperating_event_count']==2
    assert data['months_without_observations'] and not data['coverage_verified']
    assert data['tax_due_minor'] is None and data['net_worth_minor'] is None
    assert 'PRIVATE_EVENT_JOURNAL_ONLY' == data['source_scope']
    assert client.get('/api/summary?tax_year=2024').json()['record_count']==0


def test_briefing_missing_data_not_zero_past_completeness(client):
    response=client.get('/api/finance/advisor/briefing?tax_year=2023')
    assert response.status_code==200
    data=response.json()
    assert data['event_count']==0 and not data['coverage_verified']
    assert len(data['months_without_observations'])==12
    assert data['tax_due_minor'] is None


def test_advisor_auth_and_year_limit(client):
    assert client.get('/api/finance/advisor/briefing?tax_year=2022').status_code==422
    assert client.get('/api/finance/advisor/briefing?tax_year=2024',auth=None).status_code==401
    assert client.post('/api/finance/advisor/scenarios',json=SCENARIO,auth=None).status_code==401