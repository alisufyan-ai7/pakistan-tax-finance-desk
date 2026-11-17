"""G4: synthetic accountant draft vs filed-source evidence lineage.

Public code cannot certify a real FBR filing, tax due, wealth continuity,
bank period coverage or personal numbers. Owner source bytes, filenames,
screenshots and authentications are never accepted by this contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from collections import Counter

_HEX64=re.compile(r"^[0-9a-f]{64}$")
_KINDS=frozenset({
    "accountant_workbook","bank_statement",
    "iris_income_return","iris_wealth_statement","fbr_acknowledgment",
})
_STATUSES=frozenset({"DRAFT","UNDER_REVIEW","APPROVED_INTERNAL","FILING_CLAIMED"})


class SyntheticEvidenceBlocked(ValueError):
    """Inconsistent or real-world source authority not accepted."""


@dataclass(frozen=True)
class FictionalEvidence:
    synthetic_fixture: bool
    source_hmac: str
    tax_year: int
    kind: str
    revision: int
    supersedes_revision: int | None
    workflow_status: str
    linked_filing_hmac: str | None = None


def evaluate_fake_accountant_evidence(
    *, tax_year: int, artifacts: tuple[FictionalEvidence,...],
) -> dict:
    """Distinguish draft/revisions/claimed submission/actual acknowledgment.

    A supplied 'FILING_CLAIMED' status or fixture acknowledgment never
    establishes an official FBR acceptance. No financial amount is modeled.
    """
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("G4_FAKE_ACCOUNTANT_EVIDENCE_ONLY") != "1"
        or type(tax_year) is not int or not 2023<=tax_year<=2100
        or type(artifacts) is not tuple or len(artifacts)>120):
        raise SyntheticEvidenceBlocked("Genuine accountant evidence is not authorized")
    seen=set()
    groups={}
    for row in artifacts:
        if (type(row) is not FictionalEvidence
            or row.synthetic_fixture is not True
            or type(row.source_hmac) is not str or _HEX64.fullmatch(row.source_hmac) is None
            or type(row.tax_year) is not int or row.tax_year!=tax_year
            or row.kind not in _KINDS
            or type(row.revision) is not int or not 1<=row.revision<=50
            or row.workflow_status not in _STATUSES
            or (row.supersedes_revision is not None
                and (type(row.supersedes_revision) is not int
                     or row.supersedes_revision<1))
            or (row.linked_filing_hmac is not None
                and (type(row.linked_filing_hmac) is not str
                     or _HEX64.fullmatch(row.linked_filing_hmac) is None))):
            raise SyntheticEvidenceBlocked("Untrusted fictional source provenance")
        if row.source_hmac in seen:
            raise SyntheticEvidenceBlocked("Duplicate source content or HMAC identity")
        seen.add(row.source_hmac)
        if (row.kind=="accountant_workbook" and row.workflow_status=="FILING_CLAIMED"
            or row.kind=="fbr_acknowledgment" and (
                row.linked_filing_hmac is None or row.workflow_status!="FILING_CLAIMED")
            or row.kind!="fbr_acknowledgment" and row.linked_filing_hmac is not None
            or row.kind=="bank_statement" and row.workflow_status=="FILING_CLAIMED"):
            raise SyntheticEvidenceBlocked("Source status does not prove a filed return")
        if row.revision==1 and row.supersedes_revision is not None:
            raise SyntheticEvidenceBlocked("First revision must not supersede")
        if row.revision>1 and row.supersedes_revision!=row.revision-1:
            raise SyntheticEvidenceBlocked("Unbroken immutable revision chain required")
        groups.setdefault(row.kind,[]).append(row)
    for kind,items in groups.items():
        if kind=="bank_statement":
            continue  # Multiple account×period banks are required; cannot infer coverage
        revs=[v.revision for v in items]
        if len(set(revs))!=len(revs) or sorted(revs)!=list(range(1,len(revs)+1)):
            raise SyntheticEvidenceBlocked("Revision history gap or conflict")
    filings={
        row.source_hmac: row for kind in ("iris_income_return","iris_wealth_statement")
        for row in groups.get(kind,[])
    }
    ack=groups.get("fbr_acknowledgment",[])
    if any(item.linked_filing_hmac not in filings for item in ack):
        raise SyntheticEvidenceBlocked("Orphan or cross-year filing acknowledgment")
    if len({a.linked_filing_hmac for a in ack})!=len(ack):
        raise SyntheticEvidenceBlocked("Repeated acknowledgment for same draft revision")
    workbook=groups.get("accountant_workbook",[])
    latest=max(workbook,key=lambda item:item.revision) if workbook else None
    declared_filing=any(x.workflow_status=="FILING_CLAIMED" for x in filings.values())
    gaps=[]
    for kind,reason in [
        ("accountant_workbook","ACCOUNTANT_WORKBOOK_DRAFT_MISSING"),
        ("bank_statement","BANK_ACCOUNT_PERIOD_COVERAGE_UNKNOWN"),
        ("iris_income_return","INCOME_RETURN_ORIGINAL_NOT_VERIFIED"),
        ("iris_wealth_statement","WEALTH_STATEMENT_ORIGINAL_NOT_VERIFIED"),
        ("fbr_acknowledgment","FBR_ACKNOWLEDGMENT_NOT_VERIFIED"),
    ]:
        if kind not in groups:
            gaps.append(reason)
    if declared_filing and not ack:
        gaps.append("CLAIMED_FILING_NEEDS_INDEPENDENT_ACKNOWLEDGMENT")
    if latest is not None and latest.workflow_status!="APPROVED_INTERNAL":
        gaps.append("ACCOUNTANT_WORKBOOK_STILL_PROVISIONAL")
    if ack:
        gaps.append("FIXTURE_ACKNOWLEDGMENTS_REQUIRE_INDEPENDENT_IRIS_VERIFICATION")
    # Even a supposedly complete synthetic sample cannot establish legal facts.
    return {
        "synthetic_only":True,
        "tax_year":tax_year,
        "artifact_type_counts":dict(sorted(Counter(x.kind for x in artifacts).items())),
        "latest_workbook_revision":latest.revision if latest else None,
        "latest_workbook_status":latest.workflow_status if latest else "UNKNOWN",
        "claimed_filing_present":declared_filing,
        "linked_fixture_acknowledgment_count":len(ack),
        "unresolved_evidence_flags":gaps,
        "next_owner_followup":"VERIFY_OFFICIAL_IRIS_AND_SOURCE_PERIODS_PRIVATELY",
        "accountant_workbook_is_filed":False,
        "official_fbr_filing_independently_verified":False,
        "real_bank_coverage_complete":False,
        "actual_tax_due_minor":None,
        "actual_wealth_minor":None,
        "source_financial_facts_authorized":False,
        "real_data_authorized":False,
    }
