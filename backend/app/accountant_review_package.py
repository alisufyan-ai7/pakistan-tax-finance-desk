"""C4: privacy-redacted, read-only synthetic accountant review-package manifest.

No workbook export/printing, no genuine documents, no filing status promotion.
Only counts and keyed opaque review-case identifiers; no owner/source names,
financial totals, notes, or sheet contents. This is not an accountant login.
"""
from __future__ import annotations

from collections import Counter
import os

from .accountant_review import ReviewCase, DraftWorkbook, ReviewWorkflowBlocked
from .g1c_preflight import _tag


class ReviewPackageBlocked(ValueError):
    """Evidence queue is unverified, inconsistent or not synthetic-only."""


_COVERAGE = frozenset({"OBSERVED","PARTIAL","MISSING","CONFLICTING","UNSUPPORTED"})
_OUTSTANDING = frozenset({"OPEN","EVIDENCE_REQUESTED","OWNER_RESPONDED","REVIEWED"})


def review_package_manifest(
    cases: list[ReviewCase], drafts: list[DraftWorkbook], coverage_receipt: dict,
) -> dict:
    """Prepare non-identifying review counts without executing or exporting files.

    A complete account×month coverage receipt can help triage *questions*,
    not prove source rows, returns, exemptions or tax liability. Case refs are
    HMAC-blinded, not carried into a review package as plaintext identifiers.
    """
    if os.getenv("APP_DATA_MODE","synthetic")!="synthetic":
        raise ReviewPackageBlocked("Real accountant package creation is prohibited")
    if (not isinstance(cases,list) or not isinstance(drafts,list) or
        len(cases)>500 or len(drafts)>50 or not isinstance(coverage_receipt,dict)):
        raise ReviewPackageBlocked("Invalid bounded review package request")
    if (coverage_receipt.get("synthetic_only") is not True or
        coverage_receipt.get("read_only") is not True or
        not isinstance(coverage_receipt.get("coverage_rows"),list) or
        len(coverage_receipt["coverage_rows"])>7200):
        raise ReviewPackageBlocked("Explicit synthetic coverage receipt required")
    rows=coverage_receipt["coverage_rows"]
    totals=Counter()
    for row in rows:
        if not isinstance(row,dict) or row.get("status") not in _COVERAGE:
            raise ReviewPackageBlocked("Unknown account coverage classification")
        if row.get("financial_balance_minor") is not None or row.get("transaction_count") is not None:
            raise ReviewPackageBlocked("Package cannot accept unverified economic totals")
        totals[row["status"]]+=1
    unique=set()
    statuses=Counter()
    opaque_refs=[]
    evidence_citations=0
    for case in cases:
        if not isinstance(case,ReviewCase) or case.case_ref in unique:
            raise ReviewPackageBlocked("Duplicate or invalid review case")
        unique.add(case.case_ref)
        # Check a consistent sequence, including the initial state and actor
        # restrictions, without attempting to authorize a remote accountant.
        previous="OPEN"
        commands=set()
        for ev in case.events:
            if (ev.command_ref in commands or ev.previous != previous or
                not ev.reason.strip() or ev.next not in
                {"OPEN","EVIDENCE_REQUESTED","OWNER_RESPONDED","REVIEWED",
                 "ACCOUNTANT_ACCEPTED","REJECTED"}):
                raise ReviewPackageBlocked("Inconsistent immutable case event sequence")
            commands.add(ev.command_ref)
            previous=ev.next
            evidence_citations+=len(ev.citations)
        if previous != case.status:
            raise ReviewPackageBlocked("Review case status disagrees with event history")
        statuses[case.status]+=1
        opaque_refs.append(_tag(b"accountant-review-case",case.case_ref))
    draft_ids=set()
    for draft in drafts:
        if not isinstance(draft,DraftWorkbook) or draft.version_ref in draft_ids:
            raise ReviewPackageBlocked("Duplicate or invalid draft version")
        draft_ids.add(draft.version_ref)
        if draft.status not in ("DRAFT","UNDER_REVIEW","OWNER_APPROVED"):
            raise ReviewPackageBlocked("Only DRAFT lineage may enter a review package")
    incomplete=sum(totals[s] for s in ("PARTIAL","MISSING","CONFLICTING","UNSUPPORTED"))
    pending=sum(statuses[s] for s in _OUTSTANDING)
    return {
        "synthetic_only":True,"read_only":True,
        "case_count":len(cases),"draft_version_count":len(drafts),
        "case_status_counts":dict(sorted(statuses.items())),
        "opaque_case_hmacs":sorted(opaque_refs),
        "cited_evidence_reference_count":evidence_citations,
        "coverage_status_counts":{x:totals[x] for x in sorted(_COVERAGE)},
        "unresolved_account_month_count":incomplete,
        "pending_review_case_count":pending,
        "review_needed":bool(incomplete or pending),
        "source_rows_verified":False,
        "workbook_formulas_recalculated":False,
        "official_fbr_filing_verified":False,
        "accountant_export_ready":False,
        "tax_due_minor":None,
        "full_wealth_reconciled":False,
    }
