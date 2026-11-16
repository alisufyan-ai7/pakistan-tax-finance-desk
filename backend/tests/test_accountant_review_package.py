"""C4 privacy-redacted accountant manifest from existing B2/C2 domains."""
from datetime import date
import pytest
from app.accountant_review import (
    start_case,progress_case,start_draft,
)
from app.statement_coverage import AccountScope, account_month_coverage, SourcePeriod
from app.accountant_review_package import review_package_manifest,ReviewPackageBlocked


def missing():
    acc=AccountScope(account_ref="synthetic-account-xyz",legal_owner="individual",currency="PKR")
    return account_month_coverage([acc],[],start_month=date(2024,7,1),end_month=date(2024,8,1))


def case():
    original=start_case(case_ref="fictional-case-00001",synthetic_fixture=True)
    return progress_case(original,command_ref="fictional-command-01",
        next_status="EVIDENCE_REQUESTED",actor="owner",
        reason="Obtain the missing artificial source statement")


def test_redacted_manifest_does_not_show_names_notes_or_financial_values():
    c=case()
    draft=start_draft(version_ref="fictional-draft-v1",tax_year=2025,synthetic_fixture=True)
    p=review_package_manifest([c],[draft],missing())
    assert p["unresolved_account_month_count"]==2
    assert p["pending_review_case_count"]==1
    assert p["case_count"]==1 and p["draft_version_count"]==1
    assert not p["accountant_export_ready"] and not p["official_fbr_filing_verified"]
    assert not p["source_rows_verified"] and p["tax_due_minor"] is None
    assert "fictional-case-00001" not in str(p)
    assert "artificial source statement" not in str(p)
    assert "synthetic-account-xyz" not in str(p)
    assert len(p["opaque_case_hmacs"][0])==64


def test_duplicate_cases_and_false_ledger_claims_fail_closed():
    c=case()
    with pytest.raises(ReviewPackageBlocked,match="Duplicate"):
        review_package_manifest([c,c],[],missing())
    cov=missing()
    cov["coverage_rows"][0]["financial_balance_minor"]=0
    with pytest.raises(ReviewPackageBlocked,match="unverified"):
        review_package_manifest([],[],cov)


def test_closed_case_must_have_matching_chain():
    c=case()
    from dataclasses import replace
    changed=replace(c,status="ACCOUNTANT_ACCEPTED")
    with pytest.raises(ReviewPackageBlocked,match="history"):
        review_package_manifest([changed],[],missing())


def test_real_mode_refused(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(ReviewPackageBlocked,match="Real"):
        review_package_manifest([],[],missing())


def test_unverified_coverage_not_silently_accepted():
    with pytest.raises(ReviewPackageBlocked,match="receipt"):
        review_package_manifest([],[],{})
