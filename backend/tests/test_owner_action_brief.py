"""E3 fabricated owner signals: source completeness, maturity, bills and safeguards."""
from datetime import date
import pytest
from pydantic import ValidationError

from app.owner_action_brief import (
    CoveredSpending, ScheduledBill, InvestmentTerm, FollowUp,
    OwnerSignalsBlocked, build_owner_action_brief,
)

ASOF=date(2026,11,16)

def spending(month_start,through,amount,**extras):
    options=dict(synthetic_fixture=True,legal_owner="individual",
                 month_start=month_start,through_date=through,
                 total_expenses_minor=amount,coverage_complete=True,
                 classification_confirmed_in_fixture=True,
                 own_transfers_excluded=True,source_attested_in_fixture=True)
    options.update(extras)
    return CoveredSpending(**options)

def bill(ref="fictional-bill-001",due=date(2026,11,19),**extras):
    options=dict(synthetic_fixture=True,bill_ref=ref,name="Fictional home internet",
                 due_on=due,amount_minor=500000,recurrence="monthly",
                 schedule_state="OWNER_CONFIRMED_FIXTURE",payment_state="UNMATCHED")
    options.update(extras)
    return ScheduledBill(**options)

def invest(ref="fictional-investment-001",**extras):
    options=dict(synthetic_fixture=True,investment_ref=ref,name="Fictional term deposit",
                 type="fixed_deposit",principal_minor=25000000,
                 principal_source_attested_in_fixture=True,
                 return_terms="FIXED_CONTRACT",quoted_return_minor=750000,
                 return_quote_attested_in_fixture=True,
                 next_expected_return_on=date(2027,1,15),maturity_on=date(2027,12,31))
    options.update(extras)
    return InvestmentTerm(**options)

def briefing(**kwargs):
    return build_owner_action_brief(as_of=ASOF,synthetic_fixture=True,**kwargs)

def test_unknown_expenses_remain_null_not_zero():
    out=briefing()
    month=out["month_to_date"]
    assert month["expense_minor"] is None
    assert month["prior_same_window_expense_minor"] is None
    assert month["expense_growth_pct"] is None
    assert month["growth_state"]=="UNKNOWN_INCOMPLETE_COVERAGE"
    assert out["financial_source_ready"] is False
    assert out["actual_wealth_or_tax_ready"] is False

def test_comparable_same_day_months_can_show_rising_spend_but_never_tax():
    out=briefing(
        current_spend=spending(date(2026,11,1),ASOF,18000000),
        prior_spend=spending(date(2026,10,1),date(2026,10,16),15000000),
    )
    assert out["month_to_date"]["expense_growth_pct"]==20
    assert out["month_to_date"]["growth_state"]=="RISING"
    assert out["month_to_date"]["expense_minor"]==18000000
    assert out["month_to_date"]["estimated_year_end_spend_minor"] is None
    assert out["month_to_date"]["own_transfers_excluded_if_available"] is True

@pytest.mark.parametrize("field",["coverage_complete","classification_confirmed_in_fixture",
                                   "source_attested_in_fixture","own_transfers_excluded"])
def test_incomplete_inaccurate_or_unreviewed_spend_never_becomes_current_total(field):
    current=spending(date(2026,11,1),ASOF,10000000,**{field:False})
    prior=spending(date(2026,10,1),date(2026,10,16),9000000)
    out=briefing(current_spend=current,prior_spend=prior)
    assert out["month_to_date"]["expense_minor"] is None
    assert out["month_to_date"]["expense_growth_pct"] is None

def test_prior_zero_does_not_generate_infinite_growth():
    out=briefing(current_spend=spending(date(2026,11,1),ASOF,10000),
                 prior_spend=spending(date(2026,10,1),date(2026,10,16),0))
    assert out["month_to_date"]["expense_growth_pct"] is None
    assert out["month_to_date"]["growth_state"]=="UNKNOWN_INCOMPLETE_COVERAGE"

def test_cross_legal_owner_and_nonmatching_calendar_windows_rejected():
    other=spending(date(2026,11,1),ASOF,100000,legal_owner="company")
    with pytest.raises(OwnerSignalsBlocked,match="Mixed"):
        briefing(current_spend=other)
    with pytest.raises(OwnerSignalsBlocked,match="Noncomparable"):
        briefing(current_spend=spending(date(2026,11,1),date(2026,11,15),100000))

def test_calendar_boundary_clamps_prior_february_same_day():
    now=date(2027,3,31)
    out=build_owner_action_brief(
        as_of=now,synthetic_fixture=True,
        current_spend=spending(date(2027,3,1),now,12000),
        prior_spend=spending(date(2027,2,1),date(2027,2,28),10000),
    )
    assert out["month_to_date"]["comparison_prior_through"]=="2027-02-28"
    assert out["month_to_date"]["expense_growth_pct"]==20

def test_bill_attention_does_not_assume_owner_marked_means_bank_paid():
    out=briefing(bills=(
        bill("fictional-bill-001",due=date(2026,11,12)),
        bill("fictional-bill-002",due=date(2026,11,19),payment_state="OWNER_MARKED"),
        bill("fictional-bill-003",due=date(2026,11,21),schedule_state="CANDIDATE"),
        bill("fictional-bill-004",due=date(2026,12,21),
             payment_state="MATCHED_SOURCE_FIXTURE",payment_posted_on=date(2026,11,14)),
    ))
    assert [x["status"] for x in out["bills"]["items"]]==[
        "OVERDUE_NOT_VERIFIED_PAID","PAYMENT_REVIEW","SCHEDULE_REVIEW",
        "PAID_SOURCE_MATCHED_SAMPLE"]
    assert out["bills"]["needs_attention_count"]==2
    assert out["bills"]["payment_actions_enabled"] is False
    assert out["bills"]["items"][2]["amount_minor"] is None

def test_investment_cashflow_dates_are_not_guaranteed_returns():
    out=briefing(investments=(
        invest(),
        invest("fictional-investment-002",name="Fictional equity fund",type="fund",
               return_terms="VARIABLE",quoted_return_minor=None,
               return_quote_attested_in_fixture=False,
               principal_source_attested_in_fixture=False,
               next_expected_return_on=None),
    ))
    first,second=out["investments"]["items"]
    assert first["next_expected_return_on"]=="2027-01-15"
    assert first["quoted_return_minor"]==750000
    assert first["return_state"]=="CONTRACT_QUOTE_NOT_GUARANTEED"
    assert first["actual_return_received_minor"] is None
    assert first["tax_due_or_withholding_minor"] is None
    assert second["principal_minor"] is None
    assert second["quoted_return_minor"] is None
    assert out["investments"]["returns_guaranteed"] is False

def test_variable_fund_with_fixed_quote_forbidden():
    with pytest.raises(ValidationError):
        invest(return_terms="VARIABLE")

def test_open_followup_sorted_without_implying_notifications():
    a=FollowUp(synthetic_fixture=True,followup_ref="fictional-followup-1",
               title="Request missing statement",kind="source",
               due_on=date(2026,11,12),status="OPEN",source_state="CANDIDATE")
    b=FollowUp(synthetic_fixture=True,followup_ref="fictional-followup-2",
               title="Review accountant workbook",kind="accountant",
               due_on=date(2026,11,18),status="OPEN",source_state="CANDIDATE")
    c=FollowUp(synthetic_fixture=True,followup_ref="fictional-followup-3",
               title="Fictional completed review",kind="other",
               due_on=date(2026,11,13),status="DONE",source_state="CONFIRMED_FIXTURE")
    out=briefing(followups=(b,c,a))
    assert out["followups"]["open_count"]==2
    assert out["followups"]["items"][0]["status"]=="OVERDUE"
    assert out["followups"]["items"][1]["status"]=="DUE_SOON"
    assert out["followups"]["notifications_sent"] is False

def test_duplicate_refs_and_invalid_scope_rejected():
    with pytest.raises(OwnerSignalsBlocked,match="Duplicate"):
        briefing(bills=(bill(),bill()))
    with pytest.raises(OwnerSignalsBlocked):
        build_owner_action_brief(as_of=ASOF,synthetic_fixture=False)
    with pytest.raises(OwnerSignalsBlocked):
        briefing(bills=(bill(legal_owner="company"),))

def test_real_mode_refused_before_any_projection(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(OwnerSignalsBlocked,match="Real-data"):
        briefing()

def test_no_payment_trade_or_income_filing_is_executed():
    out=briefing(bills=(bill(),),investments=(invest(),))
    assert out["bills"]["items"][0]["automatic_payment_authorized"] is False
    assert out["investments"]["items"][0]["automatic_trade_authorized"] is False
    assert out["financial_source_ready"] is False
    assert "tax_due_minor" not in out
