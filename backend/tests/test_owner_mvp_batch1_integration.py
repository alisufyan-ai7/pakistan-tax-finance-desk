"""Owner MVP Batch 1 cross-lane synthetic acceptance: B2+C2+E1+A5a.

No actual records, host resources, accountant messages or tax calculations.
Only combines domain contracts after independent PR-head validations.
"""
from datetime import date

import pytest

from app.statement_coverage import AccountScope, SourcePeriod, CoverageBlocked, account_month_coverage
from app.recurring_expenses import SyntheticOutflow, RecurringBlocked, estimate_recurring_outflows
from app.accountant_review import (
    ReviewWorkflowBlocked, EvidenceCitation,
    start_case, progress_case, start_draft, progress_draft, redacted_case_summary,
)
from app.g1c_projection import SealedProjectionBlocked, inspect_restored_sealed_candidate


def _coverage():
    account = AccountScope(account_ref="synthetic-owner-account-001",
                           legal_owner="individual", currency="PKR")
    periods = [
        SourcePeriod(synthetic_fixture=True, source_ref=f"synthetic-statement-{month}",
                     account_ref=account.account_ref,
                     period_start=date(2024, month, 1),
                     period_end=date(2024, month, days),
                     source_state="accepted", complete_declared=True,
                     balances_verified=True)
        for month,days in ((7,31),(8,31),(9,30))
    ]
    return account_month_coverage([account], periods,
        start_month=date(2024,7,1), end_month=date(2024,9,1))


def test_batch1_coverage_to_recurring_to_owner_draft_review_never_filed():
    coverage=_coverage()
    assert coverage["complete_account_month_coverage"]
    eligible_months={row["month"] for row in coverage["coverage_rows"]
                     if row["status"]=="OBSERVED"}
    assert eligible_months=={"2024-07","2024-08","2024-09"}
    outflows=[
        SyntheticOutflow(
            synthetic_fixture=True, source_ref=f"synthetic-outflow-{month}",
            account_ref="synthetic-owner-account-001",
            merchant_key="synthetic-opaque-merchant-key",
            posted_on=date(2024,month,6),amount_minor=7000,
            category="subscription",reviewed=True,independently_source_verified=True)
        for month in (7,8,9)
    ]
    estimate=estimate_recurring_outflows(outflows,
        observed_months_by_account={"synthetic-owner-account-001":eligible_months})
    candidate=estimate["candidates"][0]
    assert candidate["status"]=="RECURRING_CANDIDATE"
    assert candidate["estimated_annual_minor"]==84_000
    assert candidate["realized_savings_minor"] is None
    assert coverage["tax_due_minor"] is estimate["tax_due_minor"] is None
    case=start_case(case_ref="synthetic-case-batch1", synthetic_fixture=True)
    case=progress_case(case,command_ref="synthetic-request-01",
        next_status="EVIDENCE_REQUESTED",actor="owner",
        reason="Ask owner for distinct original synthetic bank evidence")
    case=progress_case(case,command_ref="synthetic-reply-01",
        next_status="OWNER_RESPONDED",actor="owner",
        reason="Only fictional supporting correspondence is available",
        citations=(EvidenceCitation(source_ref="synthetic-message-01",
                                    source_kind="correspondence",locator="fictional-note-01"),))
    case=progress_case(case,command_ref="synthetic-review-01",
        next_status="REVIEWED",actor="owner",
        reason="Evidence is incomplete, so retain a review-only classification")
    draft=start_draft(version_ref="synthetic-draft-2025-v1",
                      tax_year=2025,synthetic_fixture=True)
    draft=progress_draft(draft,command_ref="synthetic-open-review-01",
        next_status="UNDER_REVIEW",actor="owner",
        reason="Synthetic workbook discussion requires accountant review")
    summary=redacted_case_summary(case,draft)
    assert summary["case_status"]=="REVIEWED"
    assert summary["draft_status"]=="UNDER_REVIEW"
    assert summary["official_fbr_filed_verified"] is False
    assert summary["tax_due_minor"] is None
    assert "supporting correspondence" not in str(summary)


def test_all_four_batch1_lanes_refuse_real_mode_before_financial_access(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(CoverageBlocked):
        _coverage()
    with pytest.raises(RecurringBlocked):
        estimate_recurring_outflows([],
            observed_months_by_account={"synthetic-owner-account-001":set()})
    with pytest.raises(ReviewWorkflowBlocked):
        start_case(case_ref="synthetic-case-batch1",synthetic_fixture=True)
    with pytest.raises(SealedProjectionBlocked):
        inspect_restored_sealed_candidate()
