"""G1 A7: authenticated synthetic economic source-claim graph, without double counting.

Ledger source postings are authoritative only *inside the separate synthetic
journal*. A bank credit is NOT income, a loan repayment is NOT earnings, a
declared asset valuation is NOT realized investment return, and FBR draft/filed
CLAIMS are not official FBR acknowledgements. All typed evidence claims remain
read-only and do not create additional money in the journal.

No real mode, tax liability, bank balance, authority cutover or document import.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import hmac
import json
import os
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .canonical_journal import (
    CanonicalJournalBlocked, JournalEvent, _canon, _guard,
    _verify_record, _key, MAX_SCAN,
)
from .canonical_bank_posting import _events
from .canonical_bank_classification import verify_synthetic_bank_classification_graph
from .confidential_bank import (
    ConfidentialBankBatch, _verified_payload, require_confidential_bank_store,
)
from .models import CanonicalJournalEntry
from .private_events import tax_year_of


class CanonicalGraphBlocked(ValueError):
    """Partial, inconsistent, unverified or ambiguous economic source graph."""


DOMAINS = (
    "cash_movement", "loan_principal", "investment_cost", "own_transfer",
    "withholding_candidate", "asset_valuation_claim", "fbr_income_claim",
    "fbr_wealth_claim",
)
MOVEMENT_LEGS = {
    "cash_movement": {"cash"},
    "loan_principal": {"loan_receivable", "loan_payable"},
    "investment_cost": {"investment_cost"},
    "own_transfer": {"bank"},
    "withholding_candidate": {"withholding_candidate"},
}


class EconomicSourceClaim(BaseModel):
    """Synthetic evidence metadata; not another posting and not a tax assertion."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    synthetic_fixture: Literal[True]
    legal_owner: Literal["individual"] = "individual"
    currency: Literal["PKR"] = "PKR"
    source_ref: str = Field(min_length=8, max_length=80)
    source_domain: Literal[
        "cash_movement", "loan_principal", "investment_cost", "own_transfer",
        "withholding_candidate", "asset_valuation_claim", "fbr_income_claim",
        "fbr_wealth_claim",
    ]
    posted_on: date
    account_ref: str = Field(min_length=8, max_length=80)
    movement_source_ref: str | None = Field(default=None, min_length=8, max_length=80)
    amount_minor: StrictInt | None = Field(default=None, ge=0, le=10**15)
    status: Literal["UNREVIEWED", "OWNER_DECLARED", "DRAFT_CLAIM", "FILED_CLAIM"] = "UNREVIEWED"

    @model_validator(mode="after")
    def check_semantics(self):
        if not date(2022, 7, 1) <= self.posted_on <= date(2100, 6, 30):
            raise ValueError("Unsupported economic source fiscal date")
        if self.source_ref != self.source_ref.strip() or self.account_ref != self.account_ref.strip():
            raise ValueError("Canonical source and account required")
        if self.source_domain in MOVEMENT_LEGS:
            if not self.movement_source_ref or not self.amount_minor:
                raise ValueError("Movements require a matched posting and positive claim amount")
            if self.status in {"DRAFT_CLAIM", "FILED_CLAIM"}:
                raise ValueError("Financial movement is not an FBR filing claim")
        elif self.movement_source_ref is not None:
            raise ValueError("Non-cash valuation or filing may not duplicate bank posting")
        if self.source_domain.startswith("fbr_"):
            if self.status not in {"DRAFT_CLAIM", "FILED_CLAIM"}:
                raise ValueError("Filed/draft FBR claim status must be explicit")
        elif self.status in {"DRAFT_CLAIM", "FILED_CLAIM"}:
            raise ValueError("Only FBR claims may assert an unverified filing status")
        return self


def _digest(value: object) -> str:
    """HMAC-only receipt: no raw source names, amounts, dates or references."""
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"),
                            default=str, ensure_ascii=True).encode("ascii")
    return hmac.new(_key(), b"personal-cfo:a7-claims:v1\0" + serialized, sha256).hexdigest()


def analyze_synthetic_economic_graph(
    db: Session, *, claims: tuple[EconomicSourceClaim, ...] = (),
) -> dict:
    """Read and authenticate *all* sealed posting rows and bank source batches.

    Assert a one-to-one match between encrypted bank rows and neutral bank
    postings. Other source-domain claims MUST map to existing non-bank journal
    legs, may NOT create money twice, and preserve unverified/FBR unknowns.
    No mutation, role switch, original file ingestion or financial totals.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise CanonicalGraphBlocked("Real economic authority is prohibited")
    if not isinstance(claims, tuple) or len(claims) > MAX_SCAN or not all(
        isinstance(c, EconomicSourceClaim) for c in claims
    ):
        raise CanonicalGraphBlocked("Unknown or unbounded typed economic claim")
    try:
        _guard(db, create=False)
        require_confidential_bank_store(db)
        journal_rows = db.scalars(select(CanonicalJournalEntry).limit(MAX_SCAN+1)).all()
        bank_rows = db.scalars(select(ConfidentialBankBatch).limit(MAX_SCAN+1)).all()
        if len(journal_rows) > MAX_SCAN or len(bank_rows) > MAX_SCAN:
            raise CanonicalGraphBlocked("Incomplete encrypted source scan")
        journal: dict[str, JournalEvent] = {}
        bank_events: dict[str, JournalEvent] = {}
        for row in journal_rows:
            event = _verify_record(row)
            if event.source_ref in journal:
                raise CanonicalGraphBlocked("Duplicate encrypted source reference")
            journal[event.source_ref] = event
        for row in bank_rows:
            batch = _verified_payload(row)
            for event in _events(batch):
                if event.source_ref in bank_events:
                    raise CanonicalGraphBlocked("Overlapping encrypted bank source row")
                bank_events[event.source_ref] = event
        actual_neutral = {
            ref: event for ref, event in journal.items()
            if event.event_kind == "bank_observation_unclassified"
        }
        if len(actual_neutral) != len(bank_events) or set(actual_neutral) != set(bank_events):
            raise CanonicalGraphBlocked("Missing or surplus neutral bank observation")
        for ref, expected in bank_events.items():
            if _canon(actual_neutral[ref]) != _canon(expected):
                raise CanonicalGraphBlocked("Conflicting bank source-to-journal posting")
        # Authenticate candidate/reversal graph as SOURCE-BOUND, not merely
        # balanced double entries; orphan or forged categories must fail closed.
        classification = verify_synthetic_bank_classification_graph(journal, bank_events)

        seen_source = set()
        seen_movement = set()
        normalized = []
        for claim in claims:
            unique_source = (claim.legal_owner, claim.source_ref)
            if unique_source in seen_source:
                raise CanonicalGraphBlocked("Duplicate economic evidence claim")
            seen_source.add(unique_source)
            if claim.source_ref in journal:
                raise CanonicalGraphBlocked("Evidence claim cannot replay a posting identity")
            if claim.source_domain in MOVEMENT_LEGS:
                if claim.movement_source_ref in seen_movement:
                    raise CanonicalGraphBlocked("Same money movement assigned to multiple claims")
                seen_movement.add(claim.movement_source_ref)
                event = journal.get(claim.movement_source_ref)
                if event is None or event.event_kind == "bank_observation_unclassified":
                    raise CanonicalGraphBlocked("Claimed movement not classified in canonical posting")
                if event.legal_owner != claim.legal_owner or event.currency != claim.currency:
                    raise CanonicalGraphBlocked("Mixed owner or currency in economic claim")
                if event.posted_on != claim.posted_on:
                    raise CanonicalGraphBlocked("Fiscal-date mismatch against authenticated posting")
                matching = [
                    leg for leg in event.legs
                    if leg.account_kind in MOVEMENT_LEGS[claim.source_domain]
                    and leg.account_ref == claim.account_ref
                ]
                if len(matching) != 1 or abs(matching[0].signed_minor) != claim.amount_minor:
                    raise CanonicalGraphBlocked("Claim amount/account not linked to protected posting")
                if claim.source_domain == "own_transfer" and sum(
                    leg.account_kind == "bank" for leg in event.legs
                ) < 2:
                    raise CanonicalGraphBlocked("Own transfer requires two bank account legs")
            normalized.append(claim.model_dump(mode="json"))
        counts = Counter(c.source_domain for c in claims)
        return {
            "synthetic_only": True,
            "read_only": True,
            "bank_source_rows_verified": len(bank_events),
            "neutral_postings_verified": len(actual_neutral),
            "source_bound_classification_candidates": classification["authenticated_candidate_entries"],
            "source_bound_inverse_reversals": classification["authenticated_exact_inverse_reversals"],
            "owner_classification_is_official_income": False,
            "other_canonical_postings": len(journal) - len(actual_neutral),
            "economic_claim_count": len(claims),
            "domain_claim_counts": {d: counts[d] for d in DOMAINS},
            "source_receipt_hmac": _digest({
                "bank": sorted((ref, _canon(e)) for ref, e in bank_events.items()),
                "journal": sorted((ref, _canon(e)) for ref, e in journal.items()),
                "claims": sorted(normalized, key=lambda c: (c["source_domain"], c["source_ref"])),
            }),
            "cross_domain_movements_double_counted": False,
            "unclassified_bank_observations": len(actual_neutral),
            "financial_scope_complete": False,
            "asset_valuation_is_realized_return": False,
            "fbr_acknowledgment_verified": False,
            "tax_due_minor": None,
            "net_worth_minor": None,
            "authority_cutover": False,
            "legacy_plaintext_retired": False,
            "real_data_authorized": False,
        }
    except CanonicalGraphBlocked:
        raise
    except Exception:
        raise CanonicalGraphBlocked("Protected economic source graph failed closed") from None
