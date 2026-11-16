"""Owner-facing structural API contract is authenticated but not financial data ready."""
from datetime import date
import pytest

from app.statement_coverage import AccountScope, account_month_coverage
from app.accountant_review import start_case, start_draft, progress_case
from app.owner_workspace_status import build_owner_workspace_status, OwnerWorkspaceBlocked


def synthetic_coverage():
    return account_month_coverage(
        [AccountScope(account_ref="fictional-owner-account",legal_owner="individual",currency="PKR")],
        [], start_month=date(2024,7,1),end_month=date(2024,8,1),
    )


def test_missing_all_owner_sources_is_unknown_not_a_zero_balance():
    result=build_owner_workspace_status(2027)
    assert result["contract"]=="owner_workspace_status_v1"
    assert result["coverage"]["state"]=="UNAVAILABLE"
    assert result["coverage"]["account_month_count"] is None
    assert all(v is None for v in result["coverage"]["status_counts"].values())
    assert result["accountant"]["pending_count"] is None
    assert result["tax_rule_coverage"]["domain_count"]==16
    assert result["tax_rule_coverage"]["narrow_preview_domain_count"]==1
    assert not result["tax_rule_coverage"]["statutory_liability_ready"]
    assert all(v is None for v in result["financial_facts"].values())
    assert not any(result["required_gates"].values())


def test_review_and_months_are_structural_but_do_not_expose_case_or_account():
    cover=synthetic_coverage()
    case=start_case(case_ref="fictional-case-private",synthetic_fixture=True)
    case=progress_case(case,command_ref="fictional-command-one",
        next_status="EVIDENCE_REQUESTED",actor="owner",
        reason="Missing fictional source statement requires follow-up")
    draft=start_draft(version_ref="fictional-draft-private",tax_year=2025,
        synthetic_fixture=True)
    result=build_owner_workspace_status(2025,coverage_receipt=cover,
        review_cases=[case],draft_workbooks=[draft])
    assert result["coverage"]["status_counts"]["MISSING"]==2
    assert result["coverage"]["account_month_count"]==2
    assert result["coverage"]["missing_is_zero"] is False
    assert result["accountant"]["pending_count"]==1
    assert result["accountant"]["draft_version_count"]==1
    assert result["financial_facts"]["net_worth_minor"] is None
    assert "fictional-case-private" not in str(result)
    assert "fictional-owner-account" not in str(result)
    assert "requires follow-up" not in str(result)
    assert not result["accountant"]["official_filing_verified"]


def test_cross_owner_and_unknown_economic_amounts_are_rejected():
    cover=synthetic_coverage()
    cover["coverage_rows"][0]["legal_owner"]="company"
    with pytest.raises(OwnerWorkspaceBlocked,match="mixed-owner"):
        build_owner_workspace_status(2025,coverage_receipt=cover)
    cover=synthetic_coverage()
    cover["coverage_rows"][0]["financial_balance_minor"]=0
    with pytest.raises(OwnerWorkspaceBlocked,match="mixed-owner"):
        build_owner_workspace_status(2025,coverage_receipt=cover)


def test_review_manifest_requires_all_provisional_source_inputs():
    with pytest.raises(OwnerWorkspaceBlocked,match="complete"):
        build_owner_workspace_status(2026,review_cases=[])
    with pytest.raises(OwnerWorkspaceBlocked,match="complete"):
        build_owner_workspace_status(2026,draft_workbooks=[],coverage_receipt=synthetic_coverage())


@pytest.mark.parametrize("year",[2022,2028,True,"2026"])
def test_unreviewed_tax_years_never_infer_fbr_liability(year):
    with pytest.raises(OwnerWorkspaceBlocked,match="Unsupported"):
        build_owner_workspace_status(year)


def test_real_mode_rejected_before_any_owner_source_query(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(OwnerWorkspaceBlocked,match="Real-data"):
        build_owner_workspace_status(2027)


def test_authenticated_status_endpoint_does_not_return_sample_money(client):
    result=client.get("/api/owner/workspace/status?tax_year=2027")
    assert result.status_code==200, result.text
    out=result.json()
    assert out["contract"]=="owner_workspace_status_v1"
    assert out["financial_facts"]["bank_balance_minor"] is None
    assert out["coverage"]["state"]=="UNAVAILABLE"
    assert out["data_source"]=="NO_CONNECTED_OWNER_FINANCIAL_EVIDENCE"
    assert result.headers["cache-control"]=="no-store"
    assert "fictional" not in result.text.lower()
    assert client.get("/api/owner/workspace/status?tax_year=2028").status_code==422


def test_status_api_requires_owner_basic_auth(client):
    old=client.auth
    client.auth=None
    try:
        res=client.get("/api/owner/workspace/status?tax_year=2026")
        assert res.status_code==401
    finally:
        client.auth=old
