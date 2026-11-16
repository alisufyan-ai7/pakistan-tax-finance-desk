"""C2/C3: immutable synthetic accountant review and DRAFT lifecycle contracts.

Pure state transitions (no API, database or real accountant access). The owner
remains the only authenticated actor in the actual application; prospective
accountant transitions require separate later G2 authorization and are NOT
enabled by this module. Correspondence is never authoritative bank/FBR proof.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import os
from typing import Literal


class ReviewWorkflowBlocked(ValueError):
    """Unknown actor, transition, replay or evidence cannot be certified."""


CaseStatus = Literal[
    "OPEN", "EVIDENCE_REQUESTED", "OWNER_RESPONDED", "REVIEWED",
    "ACCOUNTANT_ACCEPTED", "REJECTED",
]
DraftStatus = Literal["DRAFT", "UNDER_REVIEW", "OWNER_APPROVED"]
SourceKind = Literal[
    "bank_statement", "fbr_acknowledgment", "workbook", "correspondence",
    "asset_document", "loan_document",
]
VALID_CASE_FLOW = {
    "OPEN": frozenset({"EVIDENCE_REQUESTED", "REVIEWED"}),
    "EVIDENCE_REQUESTED": frozenset({"OWNER_RESPONDED", "REJECTED"}),
    "OWNER_RESPONDED": frozenset({"EVIDENCE_REQUESTED", "REVIEWED"}),
    "REVIEWED": frozenset({"EVIDENCE_REQUESTED", "ACCOUNTANT_ACCEPTED", "REJECTED"}),
    "ACCOUNTANT_ACCEPTED": frozenset(),
    "REJECTED": frozenset(),
}
VALID_DRAFT_FLOW = {
    "DRAFT": frozenset({"UNDER_REVIEW"}),
    "UNDER_REVIEW": frozenset({"OWNER_APPROVED", "DRAFT"}),
    "OWNER_APPROVED": frozenset(),
}


def _guard() -> None:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise ReviewWorkflowBlocked("Real accountant evidence workflow prohibited")


def _label(v: str, label: str) -> str:
    if not isinstance(v, str) or not 4 <= len(v) <= 96 or v != v.strip():
        raise ReviewWorkflowBlocked(f"Invalid {label}")
    return v


@dataclass(frozen=True)
class EvidenceCitation:
    source_ref: str
    source_kind: SourceKind
    locator: str
    independently_verified: bool = False

    def __post_init__(self):
        _label(self.source_ref, "source reference")
        _label(self.locator, "source locator")
        if self.source_kind not in (
            "bank_statement", "fbr_acknowledgment", "workbook",
            "correspondence", "asset_document", "loan_document"
        ):
            raise ReviewWorkflowBlocked("Unknown evidence type")
        if self.source_kind in ("workbook", "correspondence") and self.independently_verified:
            raise ReviewWorkflowBlocked("Drafts or messages cannot prove independent bank/FBR facts")


@dataclass(frozen=True)
class ReviewEvent:
    command_ref: str
    previous: CaseStatus
    next: CaseStatus
    actor: Literal["owner", "accountant"]
    reason: str
    citations: tuple[EvidenceCitation, ...]

    def __post_init__(self):
        _label(self.command_ref, "review command reference")
        if not isinstance(self.reason, str) or not 12 <= len(self.reason.strip()) <= 500:
            raise ReviewWorkflowBlocked("A substantive review reason is required")
        if not isinstance(self.citations, tuple) or len(self.citations) > 20:
            raise ReviewWorkflowBlocked("Invalid review evidence list")


@dataclass(frozen=True)
class ReviewCase:
    case_ref: str
    status: CaseStatus = "OPEN"
    events: tuple[ReviewEvent, ...] = ()

    def __post_init__(self):
        _label(self.case_ref, "case reference")


def start_case(*, case_ref: str, synthetic_fixture: bool) -> ReviewCase:
    _guard()
    if synthetic_fixture is not True:
        raise ReviewWorkflowBlocked("Only synthetic review cases are supported")
    return ReviewCase(case_ref=case_ref)


def progress_case(
    case: ReviewCase, *, command_ref: str, next_status: str,
    actor: str, reason: str, citations: tuple[EvidenceCitation, ...] = (),
    accountant_authorized: bool = False,
) -> ReviewCase:
    _guard()
    if not isinstance(case, ReviewCase) or not isinstance(citations, tuple):
        raise ReviewWorkflowBlocked("Invalid case command")
    if actor not in ("owner", "accountant") or next_status not in VALID_CASE_FLOW:
        raise ReviewWorkflowBlocked("Unknown review actor/status")
    prior = next((x for x in case.events if x.command_ref == command_ref), None)
    if prior is not None:
        # Only exact command replay can be idempotent. Contextual authorization
        # must still be checked: a previous accountant transition cannot be
        # replayed after permission was revoked.
        if prior.actor == "accountant" and not accountant_authorized:
            raise ReviewWorkflowBlocked("Accountant access not authorized")
        if (prior.next, prior.actor, prior.reason, prior.citations) == (
            next_status, actor, reason, citations
        ):
            return case
        raise ReviewWorkflowBlocked("Conflicting command replay")
    if actor == "accountant" and not accountant_authorized:
        raise ReviewWorkflowBlocked("Accountant access not authorized")
    if actor == "accountant" and next_status != "ACCOUNTANT_ACCEPTED":
        raise ReviewWorkflowBlocked("Accountant role cannot perform owner transitions")
    if next_status == "ACCOUNTANT_ACCEPTED" and actor != "accountant":
        raise ReviewWorkflowBlocked("Only a separately authorized accountant can accept")
    if next_status == "OWNER_RESPONDED" and (actor != "owner" or not citations):
        raise ReviewWorkflowBlocked("Owner response requires explicit evidence citations")
    if next_status == "REVIEWED" and actor != "owner":
        raise ReviewWorkflowBlocked("Only owner may mark case reviewed")
    if next_status not in VALID_CASE_FLOW[case.status]:
        raise ReviewWorkflowBlocked("Unsupported or out-of-order case transition")
    event = ReviewEvent(command_ref=command_ref, previous=case.status,
                        next=next_status, actor=actor,
                        reason=reason, citations=citations)
    return replace(case, status=next_status, events=case.events + (event,))


@dataclass(frozen=True)
class DraftEvent:
    command_ref: str
    previous: DraftStatus
    next: DraftStatus
    reason: str


@dataclass(frozen=True)
class DraftWorkbook:
    version_ref: str
    tax_year: int
    revision_of_ref: str | None = None
    status: DraftStatus = "DRAFT"
    events: tuple[DraftEvent, ...] = ()

    def __post_init__(self):
        _label(self.version_ref, "workbook version reference")
        if not 2023 <= self.tax_year <= 2100:
            raise ReviewWorkflowBlocked("Unsupported synthetic tax year")
        if self.revision_of_ref is not None and self.revision_of_ref == self.version_ref:
            raise ReviewWorkflowBlocked("A workbook revision cannot reference itself")


def start_draft(*, version_ref: str, tax_year: int,
                synthetic_fixture: bool, revision_of_ref: str | None = None) -> DraftWorkbook:
    _guard()
    if synthetic_fixture is not True:
        raise ReviewWorkflowBlocked("Only synthetic accountant drafts are supported")
    return DraftWorkbook(version_ref=version_ref, tax_year=tax_year, revision_of_ref=revision_of_ref)


def progress_draft(draft: DraftWorkbook, *, command_ref: str,
                   next_status: str, actor: str, reason: str) -> DraftWorkbook:
    _guard()
    if not isinstance(draft, DraftWorkbook) or actor != "owner":
        raise ReviewWorkflowBlocked("Only owner can review a synthetic draft")
    if next_status not in VALID_DRAFT_FLOW:
        raise ReviewWorkflowBlocked("Draft approval cannot claim official FBR filing")
    prior = next((x for x in draft.events if x.command_ref == command_ref), None)
    if prior is not None:
        if (prior.next, prior.reason) == (next_status, reason):
            return draft
        raise ReviewWorkflowBlocked("Conflicting workbook command replay")
    if next_status not in VALID_DRAFT_FLOW[draft.status]:
        raise ReviewWorkflowBlocked("Invalid workbook review progression")
    _label(command_ref, "workbook command reference")
    if not isinstance(reason, str) or len(reason.strip()) < 12:
        raise ReviewWorkflowBlocked("Workbook review action requires reason")
    event = DraftEvent(command_ref=command_ref, previous=draft.status,
                       next=next_status, reason=reason)
    return replace(draft, status=next_status, events=draft.events + (event,))


def redacted_case_summary(case: ReviewCase, draft: DraftWorkbook | None = None) -> dict:
    _guard()
    return {
        "synthetic_only": True,
        "case_ref": case.case_ref, "case_status": case.status,
        "immutable_event_count": len(case.events),
        "evidence_reference_count": sum(len(x.citations) for x in case.events),
        "evidence_is_not_official_filing_proof": True,
        "draft_status": draft.status if draft else None,
        "official_fbr_filed_verified": False,
        "owner_approval_does_not_file_return": True,
        "tax_due_minor": None, "fbr_ready": False,
    }
