"""Batch-2 integration: all five synthetic contracts coexist, real mode denied."""
from datetime import date

import pytest

from app.g1c_preflight import SOURCE_COLUMNS, analyze_source_rows
from app.canonical_fact_parity import _facts, CanonicalFactsBlocked
from app.source_batch_evidence import (
    SourceLine, SyntheticStatementBatch, validate_synthetic_batch_registry,
    BatchEvidenceBlocked,
)
from app.statement_coverage import AccountScope, account_month_coverage
from app.accountant_review import start_case, start_draft
from app.accountant_review_package import review_package_manifest, ReviewPackageBlocked
from app.cash_buffer_scenarios import (
    BufferScenario, ScenarioFlow, simulate_cash_buffer, BufferScenarioBlocked,
)
from app.tax_rule_coverage import tax_rule_gap_matrix, TaxCoverageBlocked


def batch():
    return SyntheticStatementBatch(
        synthetic_fixture=True,account_ref="fictional-owner-account",
        legal_owner="individual",currency="PKR",source_ref="fictional-statement-001",
        digest_hmac="a"*64,parser_version="synthetic-v1",
        period_start=date(2024,7,1),period_end=date(2024,7,31),
        opening_balance_minor=10000,closing_balance_minor=10500,
        rows=(SourceLine(row_number=1,posted_on=date(2024,7,15),
            debit_minor=0,credit_minor=500,balance_minor=10500,
            source_row_ref="fictional-row-0001"),),
    )


def scenario():
    return BufferScenario(synthetic_fixture=True,
        opening_month=date(2024,6,1),opening_balance_minor=None,
        opening_source_verified_in_fixture=False,
        essential_monthly_spend_minor=20000,reserve_target_months=3,
        horizon_months=2,flows=(
            ScenarioFlow(synthetic_fixture=True,month_offset=1,
                kind="assumed_expense",amount_minor=3000,
                assumption_ref="fictional-next-rent"),
        ))


def test_batch2_source_candidate_never_certifies_import_filing_or_wealth():
    batch_report=validate_synthetic_batch_registry([batch()])
    assert batch_report["verified_running_balance_batch_count"]==1
    assert batch_report["accounting_accepted"] is False
    # A source-candidate passing its arithmetic does NOT attest that its
    # opening, file signature or full account-month coverage are certified.
    account=AccountScope(account_ref="fictional-owner-account",
                         legal_owner="individual",currency="PKR")
    coverage=account_month_coverage([account],[],
        start_month=date(2024,7,1),end_month=date(2024,8,1))
    assert coverage["counts"]["MISSING"]==2
    assert all(x["financial_balance_minor"] is None for x in coverage["coverage_rows"])
    case=start_case(case_ref="fictional-case-001",synthetic_fixture=True)
    draft=start_draft(version_ref="fictional-work-v1",tax_year=2025,
                      synthetic_fixture=True)
    review=review_package_manifest([case],[draft],coverage)
    assert review["unresolved_account_month_count"]==2
    assert not review["accountant_export_ready"] and not review["official_fbr_filing_verified"]
    future=simulate_cash_buffer(scenario(),month_coverage={})
    assert all(x["scenario_balance_minor"] is None for x in future["months"])
    assert not future["private_data_ready"]
    tax=tax_rule_gap_matrix((2025,2026))
    assert tax["total_tax_engine_verified"] is False and tax["tax_due_minor"] is None
    empty_graph={table:[] for table in SOURCE_COLUMNS}
    canonical=_facts(empty_graph,analyze_source_rows(empty_graph))
    assert canonical["typed_economic_source_fact_count"]==0
    assert not canonical["ledger_authority_switched"]
    assert not canonical["plaintext_legacy_tables_retired"]
    assert canonical["actual_tax_due_minor"] is None


def test_batch2_five_new_modules_all_block_real_financial_mode(monkeypatch):
    candidate=batch()
    plan=scenario()
    account=AccountScope(account_ref="fictional-owner-account",
                         legal_owner="individual",currency="PKR")
    coverage=account_month_coverage([account],[],
        start_month=date(2024,7,1),end_month=date(2024,7,1))
    graph={table:[] for table in SOURCE_COLUMNS}
    census=analyze_source_rows(graph)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(CanonicalFactsBlocked):
        _facts(graph,census)
    with pytest.raises(BatchEvidenceBlocked):
        validate_synthetic_batch_registry([candidate])
    with pytest.raises(ReviewPackageBlocked):
        review_package_manifest([],[],coverage)
    with pytest.raises(BufferScenarioBlocked):
        simulate_cash_buffer(plan,month_coverage={})
    with pytest.raises(TaxCoverageBlocked):
        tax_rule_gap_matrix((2026,))
