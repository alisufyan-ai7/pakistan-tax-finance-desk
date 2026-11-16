"""D4: versioned synthetic filed-vs-DRAFT wealth continuity review.

This is NOT an IRIS authentication implementation, FBR filed-status verifier,
wealth reconciliation certification or tax calculator. Its acknowledgement flag
is trusted ONLY as a synthetic fixture assertion; actual authentication requires
private G1/G2/G3 source-verification infrastructure.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import os
from typing import Literal


class WealthContinuityBlocked(ValueError):
    """Unsupported identity, status or filing revision source graph."""


@dataclass(frozen=True)
class WealthSource:
    source_ref: str
    tax_year: int
    legal_owner: Literal["individual", "company", "aop"]
    currency: Literal["PKR"]
    state: Literal["draft", "filed_original", "filed_revision"]
    revision_number: int
    revision_of_ref: str | None = None
    acknowledged_source_ref: str | None = None
    acknowledgement_verified_in_fixture: bool = False
    opening_wealth_minor: int | None = None
    closing_wealth_minor: int | None = None
    synthetic_fixture: Literal[True] = True

    def __post_init__(self):
        if (self.synthetic_fixture is not True or
            not isinstance(self.source_ref,str) or not 6 <= len(self.source_ref) <= 100 or
            type(self.tax_year) is not int or not 2023 <= self.tax_year <= 2100 or
            type(self.revision_number) is not int or self.revision_number < 1):
            raise WealthContinuityBlocked("Unsupported synthetic wealth source identity")
        if self.legal_owner not in ("individual","company","aop") or self.currency != "PKR":
            raise WealthContinuityBlocked("Unsupported wealth source legal person or currency")
        if self.state not in ("draft","filed_original","filed_revision"):
            raise WealthContinuityBlocked("Unsupported document state")
        if self.state == "filed_original" and (self.revision_of_ref is not None or self.revision_number != 1):
            raise WealthContinuityBlocked("Filed original must have one first revision")
        if self.state == "filed_revision" and self.revision_of_ref is None:
            raise WealthContinuityBlocked("Filed revisions require an original ancestor")
        if self.state == "draft" and (self.acknowledged_source_ref is not None or
                                       self.acknowledgement_verified_in_fixture):
            raise WealthContinuityBlocked("Unfiled draft cannot carry official filing acknowledgement")
        if self.acknowledgement_verified_in_fixture and not (
            self.acknowledged_source_ref and
            len(self.acknowledged_source_ref) >= 6 and
            self.state != "draft"
        ):
            raise WealthContinuityBlocked("Acknowledgement assertion requires independent source reference")
        for number in (self.opening_wealth_minor,self.closing_wealth_minor):
            if number is not None and (type(number) is not int or abs(number) > 10**16):
                raise WealthContinuityBlocked("Wealth values must be exact bounded integer minor units")


def _guard() -> None:
    if os.getenv("APP_DATA_MODE","synthetic") != "synthetic":
        raise WealthContinuityBlocked("Real-source wealth continuity is not authorized")


def _verified_filed(src: WealthSource) -> bool:
    return src.state.startswith("filed_") and src.acknowledgement_verified_in_fixture


def _validate_graph(sources: list[WealthSource]) -> None:
    if len(sources) > 500:
        raise WealthContinuityBlocked("Source inventory too large")
    by_id = {}
    source_versions = set()
    originals = Counter()
    for s in sources:
        if s.source_ref in by_id:
            raise WealthContinuityBlocked("Duplicate wealth source reference")
        by_id[s.source_ref] = s
        if s.state == "filed_original":
            originals[(s.tax_year,s.legal_owner)] += 1
        if s.state.startswith("filed_"):
            key=(s.tax_year,s.legal_owner,s.revision_number)
            if key in source_versions:
                raise WealthContinuityBlocked("Conflicting filed revision numbers")
            source_versions.add(key)
    if any(v!=1 for v in originals.values()):
        raise WealthContinuityBlocked("Ambiguous multiple filed originals")
    for s in sources:
        if s.revision_of_ref is None:
            continue
        parent=by_id.get(s.revision_of_ref)
        if (parent is None or parent.source_ref==s.source_ref or
            parent.tax_year != s.tax_year or parent.legal_owner != s.legal_owner or
            parent.currency != s.currency or parent.revision_number >= s.revision_number):
            raise WealthContinuityBlocked("Missing, incompatible or reversed source revision ancestry")
        if s.state == "filed_revision" and parent.state not in ("filed_original","filed_revision"):
            raise WealthContinuityBlocked("Filed revision cannot descend from draft")


def _latest_verified_filed(sources: list[WealthSource]) -> WealthSource | None:
    matches=[s for s in sources if _verified_filed(s)]
    return max(matches,key=lambda x:x.revision_number) if matches else None


def review_wealth_year_boundary(sources: list[WealthSource], *,
                                current_tax_year: int, legal_owner: str) -> dict:
    """Compare prior VERIFIED-FILED closing with current filed or DRAFT opening.

    No source values are imputed; a discrepancy is a *review question*, never
    evidence that prior filed return is wrong or another filing was submitted.
    """
    _guard()
    if (type(current_tax_year) is not int or not 2024 <= current_tax_year <= 2100 or
        legal_owner not in ("individual","company","aop") or not isinstance(sources,list)):
        raise WealthContinuityBlocked("Invalid wealth continuity request")
    _validate_graph(sources)
    before=[s for s in sources if s.tax_year==current_tax_year-1 and s.legal_owner==legal_owner]
    present=[s for s in sources if s.tax_year==current_tax_year and s.legal_owner==legal_owner]
    prior=_latest_verified_filed(before)
    current=_latest_verified_filed(present)
    if current is None:
        drafts=[s for s in present if s.state=="draft"]
        current=max(drafts,key=lambda x:x.revision_number) if drafts else None
    if prior is None:
        status="PRIOR_FILED_EVIDENCE_REQUIRED"
    elif current is None:
        status="CURRENT_OPENING_EVIDENCE_REQUIRED"
    elif prior.closing_wealth_minor is None or current.opening_wealth_minor is None:
        status="MISSING_EVIDENCE"
    elif current.opening_wealth_minor == prior.closing_wealth_minor:
        status="MATCH_SOURCE_VALUES"
    else:
        status="REVIEW_REQUIRED"
    difference=(
        current.opening_wealth_minor-prior.closing_wealth_minor
        if prior is not None and current is not None and
        prior.closing_wealth_minor is not None and current.opening_wealth_minor is not None
        else None
    )
    return {
        "synthetic_only":True, "read_only":True,
        "current_tax_year":current_tax_year, "legal_owner":legal_owner,
        "status":status,
        "previous_verified_filing_available":prior is not None,
        "current_source_state":current.state if current is not None else None,
        "current_source_is_draft":current is not None and current.state=="draft",
        "filing_acknowledgement_verified_by_application":False,
        "synthetic_acknowledgement_fixture_only":True,
        "previous_closing_wealth_minor":prior.closing_wealth_minor if prior else None,
        "current_opening_wealth_minor":current.opening_wealth_minor if current else None,
        "difference_minor":difference,
        "prior_filed_return_declared_wrong":False,
        "wealth_reconciled_to_bank_cash_assets":False,
        "requires_manual_review":status!="MATCH_SOURCE_VALUES" or (
            current is not None and current.state=="draft"
        ),
        "fbr_ready":False,"tax_due_minor":None,
    }
