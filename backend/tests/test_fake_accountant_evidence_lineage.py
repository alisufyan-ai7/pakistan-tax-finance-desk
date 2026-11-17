"""G4: accountant draft-versus-filed provenance and missing evidence tests."""
import pytest
from app.fake_accountant_evidence_lineage import (
    FictionalEvidence,SyntheticEvidenceBlocked,evaluate_fake_accountant_evidence,
)

def row(kind,source,rev=1,status="DRAFT",previous=None,linked=None,year=2026):
    return FictionalEvidence(True,source*64,year,kind,rev,previous,status,
                             linked_filing_hmac=linked)


@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("G4_FAKE_ACCOUNTANT_EVIDENCE_ONLY","1")


def run(*rows,year=2026):
    return evaluate_fake_accountant_evidence(tax_year=year,artifacts=tuple(rows))


def test_accountant_draft_never_becomes_legal_filing():
    info=run(row("accountant_workbook","a"))
    assert info["tax_year"]==2026
    assert info["latest_workbook_status"]=="DRAFT"
    assert info["latest_workbook_revision"]==1
    assert "ACCOUNTANT_WORKBOOK_STILL_PROVISIONAL" in info["unresolved_evidence_flags"]
    assert "FBR_ACKNOWLEDGMENT_NOT_VERIFIED" in info["unresolved_evidence_flags"]
    assert info["accountant_workbook_is_filed"] is False
    assert info["official_fbr_filing_independently_verified"] is False
    assert info["actual_tax_due_minor"] is None and info["actual_wealth_minor"] is None


def test_provisional_revisions_cannot_overwrite_prior_workbook():
    info=run(row("accountant_workbook","a"),
             row("accountant_workbook","b",rev=2,previous=1,status="UNDER_REVIEW"))
    assert info["latest_workbook_revision"]==2
    assert info["latest_workbook_status"]=="UNDER_REVIEW"
    assert not info["accountant_workbook_is_filed"]
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a"),
            row("accountant_workbook","b",rev=3,previous=2))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a"),
            row("accountant_workbook","b",rev=2,previous=1),
            row("accountant_workbook","c",rev=2,previous=1))


def test_filing_claim_and_linked_fake_ack_never_prove_submission():
    filings=(
        row("accountant_workbook","a",status="APPROVED_INTERNAL"),
        row("bank_statement","b"),
        row("iris_income_return","c",status="FILING_CLAIMED"),
        row("iris_wealth_statement","d",status="FILING_CLAIMED"),
    )
    result=run(*filings)
    assert result["claimed_filing_present"]
    assert "CLAIMED_FILING_NEEDS_INDEPENDENT_ACKNOWLEDGMENT" in result["unresolved_evidence_flags"]
    fake_ack=row("fbr_acknowledgment","e",status="FILING_CLAIMED",linked="c"*64)
    result=run(*filings,fake_ack)
    assert result["linked_fixture_acknowledgment_count"]==1
    assert "FIXTURE_ACKNOWLEDGMENTS_REQUIRE_INDEPENDENT_IRIS_VERIFICATION" in result["unresolved_evidence_flags"]
    assert not result["official_fbr_filing_independently_verified"]
    assert result["real_bank_coverage_complete"] is False


def test_wrong_year_or_orphan_receipt_never_cross_links():
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a",year=2025))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("fbr_acknowledgment","a",status="FILING_CLAIMED",linked="f"*64))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("iris_income_return","a"),
            row("fbr_acknowledgment","b",status="FILING_CLAIMED",linked="f"*64))


def test_spoofed_status_or_receipt_field_cannot_self_certify():
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a",status="FILING_CLAIMED"))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("bank_statement","a",status="FILING_CLAIMED"))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("fbr_acknowledgment","a",status="APPROVED_INTERNAL",linked="b"*64))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("iris_wealth_statement","a",linked="b"*64))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a",status="FILED_VERIFIED"))


def test_duplicate_hashes_and_revision_mismatch_denied():
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a"),row("bank_statement","a"))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a",rev=1,previous=1))
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a",rev=2,previous=None))


def test_unverified_coverage_is_unknown_not_zero():
    response=run()
    assert response["latest_workbook_status"]=="UNKNOWN"
    assert response["actual_tax_due_minor"] is None
    assert response["actual_wealth_minor"] is None
    assert not response["real_data_authorized"]
    assert "BANK_ACCOUNT_PERIOD_COVERAGE_UNKNOWN" in response["unresolved_evidence_flags"]


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("G4_FAKE_ACCOUNTANT_EVIDENCE_ONLY","0"),
])
def test_real_fbr_bank_data_and_auto_filing_denied(monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    with pytest.raises(SyntheticEvidenceBlocked):
        run(row("accountant_workbook","a"))


def test_no_public_api_for_fbr_or_wealth_release():
    from app.preview_api import create_preview_app
    routes={r.path for r in create_preview_app().routes}
    assert "/api/fbr/file" not in routes
    assert "/api/wealth/real" not in routes
