"""G1 A7 synthetic bank annotation: balanced, reversible, never an income fact.

Owner-labelled classification CANDIDATES consume a single previously sealed
and neutral-posted bank row. No inferred income, verified taxes, balance or
real-data write. This internal non-HTTP service is not owner authentication.
Only one first candidate and one exact inverse are supported: corrections
beyond reversal require a separately reviewed typed source contract.
"""
from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .canonical_bank_posting import _events
from .canonical_journal import (
    CanonicalJournalBlocked, JournalEvent, JournalLeg, _blind,
    _verify_record, record_synthetic_journal,
)
from .confidential_bank import (
    ConfidentialBankBatch, _verified_payload,
    _blind as bank_blind, require_confidential_bank_store,
)
from .models import CanonicalJournalEntry


class ClassificationBlocked(ValueError):
    """Owner-synthetic candidate is not backed by an unchanged bank source."""


class BankCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    synthetic_fixture: Literal[True]
    source_ref: str = Field(min_length=8, max_length=80)
    row_number: StrictInt = Field(ge=1, le=100000)
    # These are OWNER-ANNOTATED possibilities; never tax or earnings proofs.
    candidate: Literal["income_candidate", "expense_candidate"]
    explicit_owner_annotation: Literal[True]


def _lookup(db: Session, source_ref: str, row_number: int) -> JournalEvent:
    try:
        require_confidential_bank_store(db)
        row = db.scalar(select(ConfidentialBankBatch).where(
            ConfidentialBankBatch.source_hmac ==
            bank_blind("source", "individual:" + source_ref)
        ))
        if row is None:
            raise ClassificationBlocked("Sealed synthetic bank source missing")
        source = _verified_payload(row)
        if source.legal_owner != "individual" or source.source_ref != source_ref:
            raise ClassificationBlocked("Sealed bank owner or source mismatch")
        found = [e for e, line in zip(_events(source), source.rows)
                 if line.row_number == row_number]
        if len(found) != 1:
            raise ClassificationBlocked("Unverified synthetic statement row")
        neutral = found[0]
        actual = db.scalar(select(CanonicalJournalEntry).where(
            CanonicalJournalEntry.source_hmac ==
            _blind("source", f"{neutral.legal_owner}:{neutral.source_ref}")
        ))
        if actual is None or _verify_record(actual) != neutral:
            raise ClassificationBlocked("Unchanged neutral bank posting is required")
        return neutral
    except ClassificationBlocked:
        raise
    except Exception:
        raise ClassificationBlocked("Bank/source classification provenance unavailable") from None


def _candidate_ref(neutral: JournalEvent) -> str:
    return "CLASS-" + _blind("source", "candidate:" + neutral.source_ref)[:48]


def _reversal_ref(neutral: JournalEvent) -> str:
    return "REVERSE-" + _blind("source", "reversal:" + neutral.source_ref)[:48]


def _candidate_event(neutral: JournalEvent, candidate: str) -> JournalEvent:
    bank_legs = [leg for leg in neutral.legs if leg.account_kind == "bank"]
    if len(bank_legs) != 1:
        raise ClassificationBlocked("Ambiguous source bank direction")
    direction = bank_legs[0].signed_minor
    if (candidate == "income_candidate" and direction <= 0 or
        candidate == "expense_candidate" and direction >= 0):
        raise ClassificationBlocked("Candidate contradicts observed bank direction")
    kind = "income" if candidate == "income_candidate" else "expense"
    return JournalEvent(
        synthetic_fixture=True, legal_owner=neutral.legal_owner,
        currency=neutral.currency, source_ref=_candidate_ref(neutral),
        posted_on=neutral.posted_on,
        primary_account_ref="SYNTHETIC-UNCLASSIFIED-COUNTERENTRY",
        event_kind="classification_candidate",
        legs=(
            JournalLeg(account_kind="transfer_clearing",
                       account_ref="SYNTHETIC-UNCLASSIFIED-COUNTERENTRY",
                       signed_minor=direction),
            JournalLeg(account_kind=kind,
                       account_ref="SYNTHETIC-OWNER-CANDIDATE-"+kind.upper(),
                       signed_minor=-direction),
        ),
    )


def annotate_synthetic_bank_candidate(
    db: Session, *, annotation: BankCandidate,
) -> dict:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic" or not isinstance(annotation,BankCandidate):
        raise ClassificationBlocked("Real or unvalidated bank annotation refused")
    neutral = _lookup(db, annotation.source_ref, annotation.row_number)
    expected = _candidate_event(neutral, annotation.candidate)
    try:
        undo = db.scalar(select(CanonicalJournalEntry).where(
            CanonicalJournalEntry.source_hmac ==
            _blind("source", f"individual:{_reversal_ref(neutral)}")
        ))
        if undo is not None:
            raise ClassificationBlocked("Reversed classification cannot be reactivated")
        receipt, replayed = record_synthetic_journal(db, expected)
        return {
            "synthetic_only": True,
            "bank_observation_unchanged": True,
            "balanced_candidate_entry": receipt["balanced_to_zero"],
            "candidate_replayed": replayed,
            "owner_assertion_only": True,
            "reviewed_income_or_expense": False,
            "official_tax_calculation": None,
            "legacy_accounting_switched": False,
            "real_data_authorized": False,
        }
    except ClassificationBlocked:
        raise
    except CanonicalJournalBlocked:
        raise ClassificationBlocked("Conflicting owner candidate annotation") from None


def reverse_synthetic_bank_candidate(
    db: Session, *, source_ref: str, row_number: int,
    explicit_correction: bool,
) -> dict:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic" or explicit_correction is not True:
        raise ClassificationBlocked("Synthetic correction authorization required")
    if type(source_ref) is not str or type(row_number) is not int or row_number <= 0:
        raise ClassificationBlocked("Invalid source correction")
    neutral = _lookup(db, source_ref, row_number)
    try:
        row = db.scalar(select(CanonicalJournalEntry).where(
            CanonicalJournalEntry.source_hmac ==
            _blind("source", f"individual:{_candidate_ref(neutral)}")
        ))
        if row is None:
            raise ClassificationBlocked("No original classification candidate")
        before = _verify_record(row)
        if (before.event_kind != "classification_candidate"
            or len(before.legs) != 2
            or before.legs[1].account_kind not in {"income", "expense"}):
            raise ClassificationBlocked("Classification is not linked to authenticated bank evidence")
        expected_kind = ("income_candidate" if before.legs[1].account_kind == "income"
                         else "expense_candidate")
        if before != _candidate_event(neutral, expected_kind):
            raise ClassificationBlocked("Classification is not linked to authenticated bank evidence")
        reverse = JournalEvent(
            synthetic_fixture=True, legal_owner=before.legal_owner,
            currency=before.currency, source_ref=_reversal_ref(neutral),
            posted_on=before.posted_on, primary_account_ref=before.primary_account_ref,
            event_kind="classification_reversal",
            legs=tuple(
                JournalLeg(account_kind=leg.account_kind,
                           account_ref=leg.account_ref,
                           signed_minor=-leg.signed_minor)
                for leg in before.legs
            ),
        )
        receipt, replayed = record_synthetic_journal(db, reverse)
        return {
            "synthetic_only": True,
            "exact_inverse_posted": receipt["balanced_to_zero"],
            "correction_replayed": replayed,
            "original_classification_deleted": False,
            "original_bank_evidence_unchanged": True,
            "classified_owner_income_tax_verified": False,
            "real_data_authorized": False,
        }
    except ClassificationBlocked:
        raise
    except Exception:
        raise ClassificationBlocked("Reversible candidate correction failed closed") from None
