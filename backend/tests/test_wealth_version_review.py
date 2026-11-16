"""D4 fabricated wealth-source revisions and unknown-not-zero boundaries."""
import pytest
from app.wealth_version_review import WealthSource, WealthContinuityBlocked, review_wealth_year_boundary


def src(ref,year,state="filed_original",revision=1,opening=100000,closing=100000,
        parent=None,ack=True,owner="individual"):
    if state=="draft":
        ack=False
    return WealthSource(
        source_ref=ref,tax_year=year,legal_owner=owner,currency="PKR",state=state,
        revision_number=revision,revision_of_ref=parent,
        acknowledged_source_ref=("synthetic-ack-"+ref) if ack else None,
        acknowledgement_verified_in_fixture=ack,
        opening_wealth_minor=opening,closing_wealth_minor=closing,
        synthetic_fixture=True,
    )


def review(*rows,year=2026,owner="individual"):
    return review_wealth_year_boundary(list(rows),current_tax_year=year,legal_owner=owner)


def test_filed_prior_and_current_draft_matching_is_not_filed_or_bank_reconciled():
    p=src("synthetic-wealth-2025",2025,closing=300000)
    d=src("synthetic-draft-2026",2026,state="draft",opening=300000)
    result=review(p,d)
    assert result["status"]=="MATCH_SOURCE_VALUES"
    assert result["current_source_is_draft"]
    assert result["requires_manual_review"]
    assert result["filing_acknowledgement_verified_by_application"] is False
    assert result["wealth_reconciled_to_bank_cash_assets"] is False
    assert result["tax_due_minor"] is None


def test_discrepancy_is_question_not_invalid_filed_return_claim():
    r=review(src("synthetic-wealth-2025",2025,closing=300000),
             src("synthetic-draft-2026",2026,state="draft",opening=450000))
    assert r["difference_minor"]==150000
    assert r["status"]=="REVIEW_REQUIRED"
    assert r["prior_filed_return_declared_wrong"] is False


def test_latest_acknowledged_revision_selected_and_lineage_kept():
    original=src("synthetic-wealth-2025-v1",2025,closing=300000)
    revision=src("synthetic-wealth-2025-v2",2025,state="filed_revision",revision=2,
                 parent=original.source_ref,closing=400000)
    draft=src("synthetic-draft-2026",2026,state="draft",opening=400000)
    r=review(original,revision,draft)
    assert r["status"]=="MATCH_SOURCE_VALUES"
    assert r["previous_closing_wealth_minor"]==400000


def test_missing_prior_or_opening_does_not_become_zero():
    r=review(src("synthetic-draft-2026",2026,state="draft",opening=250000))
    assert r["status"]=="PRIOR_FILED_EVIDENCE_REQUIRED"
    assert r["difference_minor"] is None
    prior=src("synthetic-wealth-2025",2025,closing=None)
    current=src("synthetic-draft-2026",2026,state="draft",opening=0)
    r=review(prior,current)
    assert r["status"]=="MISSING_EVIDENCE"
    assert r["difference_minor"] is None


def test_unverified_filing_label_never_passes_prior_evidence():
    prior=src("synthetic-unverified-prior",2025,ack=False,closing=123)
    current=src("synthetic-draft-2026",2026,state="draft",opening=123)
    r=review(prior,current)
    assert r["status"]=="PRIOR_FILED_EVIDENCE_REQUIRED"


def test_person_and_company_wealth_sources_separated():
    personal=src("synthetic-personal-2025",2025,closing=100000)
    company=src("synthetic-company-2025",2025,owner="company",closing=500000)
    draft=src("synthetic-personal-2026",2026,state="draft",opening=100000)
    out=review(personal,company,draft)
    assert out["previous_closing_wealth_minor"]==100000


def test_wrong_revision_chain_and_duplicate_filed_starts_fail_closed():
    one=src("synthetic-a-2025",2025)
    two=src("synthetic-b-2025",2025)
    with pytest.raises(WealthContinuityBlocked,match="Conflicting filed revision numbers"):
        review(one,two)
    revision=src("synthetic-rev-2025",2025,state="filed_revision",
                 revision=2,parent="missing-original")
    with pytest.raises(WealthContinuityBlocked,match="ancestry"):
        review(revision)
    with pytest.raises(WealthContinuityBlocked,match="Duplicate"):
        review(one,one)


def test_draft_cannot_carry_ack_and_amounts_not_float():
    with pytest.raises(WealthContinuityBlocked,match="Unfiled draft"):
        WealthSource(source_ref="synthetic-bad-draft",tax_year=2026,
                     legal_owner="individual",currency="PKR",state="draft",
                     revision_number=1,acknowledged_source_ref="synthetic-ack")
    with pytest.raises(WealthContinuityBlocked,match="integer"):
        src("synthetic-float-2025",2025,closing=12.5)


def test_real_mode_denied(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(WealthContinuityBlocked,match="Real-source"):
        review()
