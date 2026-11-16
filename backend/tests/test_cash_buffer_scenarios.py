"""Synthetic cash buffer scenario and no false observed-fact claims."""
from datetime import date
import pytest
from app.cash_buffer_scenarios import (
    ScenarioFlow,BufferScenario,BufferScenarioBlocked,simulate_cash_buffer,
)


def scenario(*,opening=100000,verified=True):
    return BufferScenario(synthetic_fixture=True,opening_month=date(2024,6,1),
        opening_balance_minor=opening,opening_source_verified_in_fixture=verified,
        essential_monthly_spend_minor=20000,reserve_target_months=3,
        horizon_months=2,flows=(
            ScenarioFlow(synthetic_fixture=True,month_offset=1,kind="assumed_expense",
                         amount_minor=25000,assumption_ref="fictional-expected-rent"),
            ScenarioFlow(synthetic_fixture=True,month_offset=2,kind="assumed_income",
                         amount_minor=40000,assumption_ref="fictional-expected-income"),
        ))


def test_scenario_labeled_hypothetical_not_observed_savings():
    r=simulate_cash_buffer(scenario(),month_coverage={"2024-07":"OBSERVED","2024-08":"MISSING"})
    assert [x["scenario_balance_minor"] for x in r["months"]]==[75000,115000]
    assert r["reserve_target_minor"]==60000
    assert r["missing_or_conflicting_coverage_months"]==1
    assert r["months"][1]["observed_bank_balance_minor"] is None
    assert all(not x["source_backed_forecast"] for x in r["months"])
    assert r["tax_due_minor"] is None and r["realized_savings_minor"] is None
    assert not r["automatic_payment_or_investment_action"]


def test_unknown_opening_stays_null_not_zero():
    r=simulate_cash_buffer(scenario(opening=None,verified=False),month_coverage={})
    assert all(x["scenario_balance_minor"] is None for x in r["months"])
    assert all(x["scenario_reserve_shortfall_minor"] is None for x in r["months"])


def test_buffer_shortfall_is_scenario_only():
    r=simulate_cash_buffer(scenario(opening=65000),month_coverage={})
    assert r["months"][0]["scenario_reserve_shortfall_minor"]==20000
    assert r["months"][0]["observed_bank_balance_minor"] is None


def test_strict_no_float_no_duplicate_or_horizon_extra():
    with pytest.raises(ValueError):
        scenario(opening=12.5)
    bad=ScenarioFlow(synthetic_fixture=True,month_offset=3,kind="assumed_expense",
                     amount_minor=100,assumption_ref="fictional-late-outflow")
    with pytest.raises(ValueError):
        scenario().model_copy(update={"flows":(bad,)}) if False else BufferScenario(
            **{**scenario().model_dump(),"flows":(bad,)})
    with pytest.raises(ValueError):
        BufferScenario(**{**scenario().model_dump(),"opening_month":date(2024,6,3)})


def test_real_data_mode_refused(monkeypatch):
    s=scenario()
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(BufferScenarioBlocked,match="Real"):
        simulate_cash_buffer(s,month_coverage={})
