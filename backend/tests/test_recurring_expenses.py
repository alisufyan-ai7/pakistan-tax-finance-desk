"""E1 synthetic recurrence detection: no savings guesses, no hidden months."""
from datetime import date
import pytest
from app.recurring_expenses import SyntheticOutflow, RecurringBlocked, estimate_recurring_outflows


def item(source, month, amount=9900, **opts):
    params=dict(
        synthetic_fixture=True, source_ref=source, account_ref="synthetic-account",
        merchant_key="fictional-hmac-merchant-01", posted_on=date(2024,month,3),
        amount_minor=amount, category="subscription",
        reviewed=True, independently_source_verified=True,
    )
    params.update(opts)
    return SyntheticOutflow(**params)


def check(rows, months=None):
    return estimate_recurring_outflows(rows,
        observed_months_by_account={"synthetic-account": set(months or ("2024-07","2024-08","2024-09"))})


def test_monthly_candidate_annualized_as_estimate_not_savings():
    rows=[item("syn-observation-jul",7),item("syn-observation-aug",8),
          item("syn-observation-sep",9)]
    r=check(rows)
    assert r["candidates"][0]["status"] == "RECURRING_CANDIDATE"
    assert r["candidates"][0]["cadence_months"] == 1
    assert r["candidates"][0]["typical_charge_minor"] == 9900
    assert r["candidates"][0]["estimated_annual_minor"] == 9900*12
    assert r["candidates"][0]["annual_estimate_is_observed_spending"] is False
    assert r["realized_savings_minor"] is None and r["tax_due_minor"] is None


def test_gap_unknown_prevents_guessing_missing_month_as_zero():
    rows=[item("syn-observation-jul",7),item("syn-observation-aug",8),item("syn-observation-sep",9)]
    r=check(rows,months={"2024-07","2024-09"})
    out=r["candidates"][0]
    assert out["status"]=="REVIEW_REQUIRED"
    assert out["estimated_annual_minor"] is None
    assert out["observed_coverage_gap_count"]==1


def test_missing_source_review_and_transfers_excluded():
    rows=[item("syn-1-jul",7, reviewed=False),
          item("syn-2-aug",8, independently_source_verified=False),
          item("syn-3-sep",9, category="own_transfer")]
    r=check(rows)
    assert r["excluded_or_unverified_source_count"]==3
    assert r["candidates"]==[]


def test_double_charge_and_variable_amount_forces_review():
    rows=[item("syn-1-jul",7),item("syn-2-aug",8),item("syn-3-sep",9),
          item("syn-4-sep",9)]
    out=check(rows)["candidates"][0]
    assert out["status"]=="REVIEW_REQUIRED" and out["estimated_annual_minor"] is None
    rows=[item("syn-1-jul",7),item("syn-2-aug",8, amount=20000),item("syn-3-sep",9)]
    assert check(rows)["candidates"][0]["estimated_annual_minor"] is None


def test_idempotent_source_replays_and_conflicts():
    rows=[item("syn-1-jul",7),item("syn-2-aug",8),item("syn-3-sep",9)]
    result=check(rows+rows)
    assert result["candidates"][0]["observed_charge_count"]==3
    with pytest.raises(RecurringBlocked,match="Conflicting"):
        check(rows+[item("syn-1-jul",7,amount=10000)])


def test_quarterly_needs_contiguous_observed_account_coverage():
    rows=[
        SyntheticOutflow(synthetic_fixture=True,source_ref=f"syn-q-{m}",
          account_ref="synthetic-account",merchant_key="fictional-merchant-q",
          posted_on=date(2024,m,3),amount_minor=12000,category="insurance",
          reviewed=True,independently_source_verified=True)
        for m in (1,4,7)
    ]
    allmonths={f"2024-{m:02d}" for m in range(1,8)}
    out=check(rows,months=allmonths)["candidates"][0]
    assert out["cadence_months"]==3 and out["estimated_annual_minor"]==48000
    out=check(rows,months={"2024-01","2024-04","2024-07"})["candidates"][0]
    assert out["estimated_annual_minor"] is None and out["status"]=="REVIEW_REQUIRED"


def test_strict_pk_no_float_and_invalid_coverage():
    with pytest.raises(ValueError):
        item("syn-float",7, amount=12.5)
    with pytest.raises(RecurringBlocked,match="Coverage"):
        estimate_recurring_outflows([item("syn-1-jul",7)],
            observed_months_by_account={"synthetic-account":{"2024-99"}})


def test_real_mode_fails_closed(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(RecurringBlocked,match="Real"):
        check([item("syn-1-jul",7)])
