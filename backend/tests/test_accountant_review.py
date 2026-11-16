"""C2/C3 synthetic owner review, immutable event and filed separation."""
from dataclasses import FrozenInstanceError
import pytest
from app.accountant_review import (
    EvidenceCitation, ReviewWorkflowBlocked, start_case, progress_case,
    start_draft, progress_draft, redacted_case_summary,
)


def citation(kind="bank_statement", *, verified=True):
    return EvidenceCitation(source_ref="synthetic-evidence-0001",
                            source_kind=kind, locator="page-0001-row-002",
                            independently_verified=verified)


def _request(case):
    return progress_case(case, command_ref="synthetic-request-1", next_status="EVIDENCE_REQUESTED",
                         actor="owner", reason="Please provide original fictional bank source")


def test_full_review_flow_immutable_and_accountant_not_implicitly_authorized():
    original = start_case(case_ref="synthetic-case-0001", synthetic_fixture=True)
    requested = _request(original)
    response = progress_case(requested, command_ref="synthetic-reply-01",
                             next_status="OWNER_RESPONDED", actor="owner",
                             reason="Synthetic source reference attached for further review",
                             citations=(citation(),))
    reviewed = progress_case(response, command_ref="synthetic-reviewed-01",
                             next_status="REVIEWED", actor="owner",
                             reason="Fictional source detail checked by owner")
    with pytest.raises(ReviewWorkflowBlocked, match="authorized accountant"):
        progress_case(reviewed, command_ref="synthetic-accepted-01",
                      next_status="ACCOUNTANT_ACCEPTED", actor="owner",
                      reason="Owner may not impersonate an accountant")
    with pytest.raises(ReviewWorkflowBlocked, match="not authorized"):
        progress_case(reviewed, command_ref="synthetic-accepted-01",
                      next_status="ACCOUNTANT_ACCEPTED", actor="accountant",
                      reason="Accountant permission is absent")
    accepted = progress_case(reviewed, command_ref="synthetic-accepted-01",
                             next_status="ACCOUNTANT_ACCEPTED", actor="accountant",
                             accountant_authorized=True,
                             reason="Explicitly authorized fictional accountant accepted")
    assert len(original.events) == 0 and original.status == "OPEN"
    assert len(accepted.events) == 4
    assert accepted.status == "ACCOUNTANT_ACCEPTED"
    assert redacted_case_summary(accepted)["official_fbr_filed_verified"] is False
    with pytest.raises(FrozenInstanceError):
        original.status = "REVIEWED"


def test_exact_command_replay_and_conflicting_replay():
    original = start_case(case_ref="synthetic-case-0001", synthetic_fixture=True)
    requested = _request(original)
    assert _request(requested) is requested
    with pytest.raises(ReviewWorkflowBlocked, match="Conflicting"):
        progress_case(requested, command_ref="synthetic-request-1", next_status="REVIEWED",
                      actor="owner", reason="A different command with reused source reference")


def test_unsupported_transitions_missing_owner_evidence_and_correspondence_not_proof():
    case = start_case(case_ref="synthetic-case-0001", synthetic_fixture=True)
    with pytest.raises(ReviewWorkflowBlocked, match="out-of-order"):
        progress_case(case, command_ref="synthetic-reply-01", next_status="OWNER_RESPONDED",
                      actor="owner", reason="Cannot reply before request",
                      citations=(citation(),))
    with pytest.raises(ReviewWorkflowBlocked, match="evidence"):
        progress_case(_request(case), command_ref="synthetic-reply-02",
                      next_status="OWNER_RESPONDED", actor="owner",
                      reason="Missing supporting evidence")
    with pytest.raises(ReviewWorkflowBlocked, match="independent"):
        citation(kind="correspondence", verified=True)


def test_draft_owner_approval_never_means_filed_and_version_remains():
    draft = start_draft(version_ref="synthetic-book-v1", tax_year=2026, synthetic_fixture=True)
    under = progress_draft(draft, command_ref="synthetic-review-01",
                           next_status="UNDER_REVIEW", actor="owner",
                           reason="All artificial worksheet evidence requires review")
    approved = progress_draft(under, command_ref="synthetic-approve-01",
                              next_status="OWNER_APPROVED", actor="owner",
                              reason="Owner accepts this synthetic workbook for accountant discussion")
    assert draft.status == "DRAFT" and approved.status == "OWNER_APPROVED"
    assert len(approved.events) == 2
    assert redacted_case_summary(start_case(case_ref="synthetic-case-0001",
                           synthetic_fixture=True), approved)["official_fbr_filed_verified"] is False
    with pytest.raises(ReviewWorkflowBlocked, match="official FBR"):
        progress_draft(approved, command_ref="synthetic-file-01",
                       next_status="FILED", actor="owner",
                       reason="Workbook approval is not an IRIS submission")
    revision = start_draft(version_ref="synthetic-book-v2", tax_year=2026,
                           revision_of_ref=draft.version_ref, synthetic_fixture=True)
    assert revision.status == "DRAFT" and revision.revision_of_ref == draft.version_ref


def test_real_mode_rejected(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(ReviewWorkflowBlocked, match="Real"):
        start_case(case_ref="synthetic-case-0001", synthetic_fixture=True)
    with pytest.raises(ReviewWorkflowBlocked, match="synthetic"):
        start_draft(version_ref="synthetic-book-v1", tax_year=2026, synthetic_fixture=True)


def test_source_notes_do_not_appear_in_redacted_case_summary():
    original = start_case(case_ref="synthetic-case-0001", synthetic_fixture=True)
    requested = progress_case(original, command_ref="synthetic-request-01",
                              next_status="EVIDENCE_REQUESTED", actor="owner",
                              reason="Sensitive fake narrative for manual review")
    summary = redacted_case_summary(requested)
    assert "Sensitive fake narrative" not in str(summary)
    assert summary["immutable_event_count"] == 1
