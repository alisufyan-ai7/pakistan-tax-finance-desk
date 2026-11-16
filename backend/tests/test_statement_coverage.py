"""B2 account×month synthetic coverage, idempotence and unknown checks."""
from datetime import date
import pytest
from app.statement_coverage import (
    AccountScope, SourcePeriod, CoverageBlocked, account_month_coverage,
)


A = AccountScope(account_ref="synthetic-personal-account", legal_owner="individual", currency="PKR")
B = AccountScope(account_ref="synthetic-company-account", legal_owner="company", currency="USD")


def src(name, account=A.account_ref, start="2024-07-01", end="2024-07-31", *,
        state="accepted", complete=True, balanced=True):
    return SourcePeriod(
        synthetic_fixture=True, source_ref=name, account_ref=account,
        period_start=date.fromisoformat(start), period_end=date.fromisoformat(end),
        source_state=state,
        complete_declared=complete if state == "accepted" else False,
        balances_verified=balanced if state == "accepted" else False,
    )


def view(sources, *, accounts=None, first=date(2024, 7, 1), last=date(2024, 9, 1)):
    return account_month_coverage(accounts or [A], sources, start_month=first, end_month=last)


def test_exact_complete_period_and_missing_are_not_zero():
    result = view([src("synthetic-source-001")])
    assert [r["status"] for r in result["coverage_rows"]] == ["OBSERVED", "MISSING", "MISSING"]
    assert result["counts"]["MISSING"] == 2
    assert result["complete_account_month_coverage"] is False
    assert all(row["financial_balance_minor"] is None for row in result["coverage_rows"])
    assert all(row["transaction_count"] is None for row in result["coverage_rows"])
    assert result["tax_due_minor"] is None
    assert result["coverage_rows"][0]["tax_year"] == 2025


def test_partial_month_and_unverified_running_balances_remain_partial():
    result = view([src("synthetic-half-month", start="2024-07-01", end="2024-07-15")])
    assert result["coverage_rows"][0]["status"] == "PARTIAL"
    notverified = view([src("synthetic-full-unverified", balanced=False)])
    assert notverified["coverage_rows"][0]["status"] == "PARTIAL"
    unreported = view([src("synthetic-unconfirmed", complete=False)])
    assert unreported["coverage_rows"][0]["status"] == "PARTIAL"


def test_disjoint_verified_periods_can_cover_a_full_month():
    good = [src("synthetic-first-half", end="2024-07-15"),
            src("synthetic-second-half", start="2024-07-16")]
    assert view(good)["coverage_rows"][0]["status"] == "OBSERVED"


def test_conflicting_distinct_sources_and_quarantined_intersection():
    sources = [src("synthetic-source-001"),
               src("synthetic-source-002", start="2024-07-30", end="2024-08-02")]
    result = view(sources)
    assert result["coverage_rows"][0]["status"] == "CONFLICTING"
    assert result["coverage_rows"][1]["status"] == "PARTIAL"
    bad = src("synthetic-quarantined", state="quarantined")
    assert view([bad])["coverage_rows"][0]["status"] == "UNSUPPORTED"
    assert view([bad, sources[0]])["coverage_rows"][0]["status"] == "CONFLICTING"


def test_same_source_exact_replay_does_not_double_count():
    s = src("synthetic-identical")
    result = view([s, s, s], first=date(2024, 7, 1), last=date(2024, 7, 1))
    assert result["counts"]["OBSERVED"] == 1
    assert result["coverage_rows"][0]["accepted_source_count"] == 1
    other = src("synthetic-identical", end="2024-07-15")
    with pytest.raises(CoverageBlocked, match="Conflicting replay"):
        view([s, other])


def test_person_and_company_account_scopes_are_separate():
    result = view([src("synthetic-company-source", account=B.account_ref)],
                  accounts=[A, B], first=date(2024, 7, 1), last=date(2024, 7, 1))
    assert [r["status"] for r in result["coverage_rows"]] == ["MISSING", "OBSERVED"]
    assert [r["legal_owner"] for r in result["coverage_rows"]] == ["individual", "company"]
    assert [r["currency"] for r in result["coverage_rows"]] == ["PKR", "USD"]


def test_june_to_july_tax_year_boundary():
    result = view([], first=date(2024, 6, 1), last=date(2024, 7, 1))
    assert [r["tax_year"] for r in result["coverage_rows"]] == [2024, 2025]


def test_undeclared_account_duplicate_account_and_large_horizon_block():
    with pytest.raises(CoverageBlocked, match="undeclared"):
        view([src("synthetic-foreign", account="not-declared")])
    with pytest.raises(CoverageBlocked, match="Duplicate account"):
        view([], accounts=[A, A])
    with pytest.raises(CoverageBlocked, match="horizon"):
        view([], first=date(2023, 1, 1), last=date(2029, 1, 1))


def test_real_mode_fails_before_records_are_examined(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(CoverageBlocked, match="Real"):
        view([src("synthetic-source-001")])


def test_source_periods_invalid_or_rejected_claims_block():
    with pytest.raises(ValueError):
        src("synthetic-inverted", start="2024-08-01", end="2024-07-01")
    with pytest.raises(ValueError):
        SourcePeriod(synthetic_fixture=True, source_ref="synthetic-unverifiable",
                     account_ref=A.account_ref,
                     period_start=date(2024, 7, 1), period_end=date(2024, 7, 31),
                     source_state="unsupported", balances_verified=True)
