"""G1 A7: encrypted typed synthetic economic movement proposals.

Write-side BANK amounts come ONLY from authenticated source statements. This
internal service adds *NON-BANK* owner-declared double-entry proposals for
cash, loans, investment cost, withholding candidates and asset opening cost,
all offset by an explicit unclassified clearing or opening-equity leg.

FBR income/wealth declarations and asset valuations are NON-POSTING claims;
no official filed acknowledgement, gains, asset value or net-worth authority.
No real data, legacy table rewrite, tax due or public API.
"""
from __future__ import annotations

from datetime import date
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy.orm import Session

from .canonical_journal import (
    _blind, JournalEvent, JournalLeg, record_synthetic_journal,
    CanonicalJournalBlocked,
)
from .canonical_bank_classification import _lookup as verified_neutral_bank
from .private_events import tax_year_of


class EconomicMovementBlocked(ValueError):
    """Unverified owner declaration or economic double-entry source."""


class OwnerEconomicMovement(BaseModel):
    """Synthetic owner claim, not accepted historical evidence or a real balance."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    synthetic_fixture: Literal[True]
    legal_owner: Literal["individual"] = "individual"
    currency: Literal["PKR"] = "PKR"
    source_ref: str = Field(min_length=8, max_length=80)
    account_ref: str = Field(min_length=8, max_length=80)
    posted_on: date
    movement_kind: Literal[
        "cash_movement", "loan_given_principal", "loan_taken_principal",
        "investment_cost", "withholding_candidate", "asset_cost_opening",
    ]
    amount_minor: StrictInt = Field(gt=0, le=10**15)
    direction: Literal["increase", "decrease"]
    explicit_owner_annotation: Literal[True]
    independent_source_verified: Literal[False] = False
    original_document_certified: Literal[False] = False

    @model_validator(mode="after")
    def validate_owner_proposal(self):
        if (not date(2022, 7, 1) <= self.posted_on <= date(2100, 6, 30)
            or self.account_ref != self.account_ref.strip()
            or self.source_ref != self.source_ref.strip()):
            raise ValueError("Unverified owner economic source/date/account")
        if self.movement_kind == "asset_cost_opening" and self.direction == "decrease":
            raise ValueError("Asset cost disposal requires a reviewed source/reversal workflow")
        return self


_DOMAIN_LEDGER = {
    "cash_movement": ("cash_transfer", "cash"),
    "loan_given_principal": ("loan_principal", "loan_receivable"),
    "loan_taken_principal": ("loan_principal", "loan_payable"),
    "investment_cost": ("investment_contribution", "investment_cost"),
    "withholding_candidate": ("withholding_candidate", "withholding_candidate"),
    "asset_cost_opening": ("owner_opening_assertion", "asset_cost"),
}
_CLEARED = "SYNTHETIC-DOMAIN-UNCLASSIFIED-CLEARING"
_OPENING = "SYNTHETIC-UNVERIFIED-OPENING-EQUITY"


def build_owner_economic_proposal(movement: OwnerEconomicMovement) -> JournalEvent:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic" or not isinstance(movement,OwnerEconomicMovement):
        raise EconomicMovementBlocked("Real or unvalidated economic source is prohibited")
    kind, account_kind = _DOMAIN_LEDGER[movement.movement_kind]
    signed = movement.amount_minor * (1 if movement.direction == "increase" else -1)
    other = "opening_equity" if movement.movement_kind == "asset_cost_opening" else "transfer_clearing"
    other_ref = _OPENING if other == "opening_equity" else _CLEARED
    source_key = "ECON-" + _blind("source",
        f"typed:{movement.legal_owner}:{movement.source_ref}")[:48]
    return JournalEvent(
        synthetic_fixture=True, legal_owner=movement.legal_owner,
        currency=movement.currency, source_ref=source_key,
        primary_account_ref=movement.account_ref,
        posted_on=movement.posted_on, event_kind=kind,
        legs=(
            JournalLeg(account_ref=movement.account_ref,
                       account_kind=account_kind,signed_minor=signed),
            JournalLeg(account_ref=other_ref,account_kind=other,signed_minor=-signed),
        ),
    )


def record_owner_economic_proposal(db: Session, *, movement: OwnerEconomicMovement) -> dict:
    """Preserve owner hypothesis inside AES-GCM posting, not M1 authoritative totals."""
    event = build_owner_economic_proposal(movement)
    try:
        receipt, replay = record_synthetic_journal(db,event)
    except CanonicalJournalBlocked:
        raise EconomicMovementBlocked("Conflicting or unverified economic proposal") from None
    return {
        "synthetic_only": True, "source_event_count": 1,
        "double_entry_balanced": receipt["balanced_to_zero"],
        "idempotent_replay": replay,
        "owner_proposal_only": True,
        "independent_source_verified": False,
        "fbr_official_acknowledgement_verified": False,
        "verified_asset_value_minor": None,
        "verified_investment_return_minor": None,
        "verified_account_balance_minor": None,
        "tax_due_minor": None,
        "active_legacy_authority_replaced": False,
        "real_data_authorized": False,
    }


def inspect_synthetic_bank_transfer_pair(
    db: Session, *, debit_source_ref: str, debit_row_number: int,
    credit_source_ref: str, credit_row_number: int,
    explicit_owner_annotation: bool,
) -> dict:
    """Evidence-only transfer pairing. Does NOT duplicate a single bank leg.

    Matching two amounts does NOT prove they belong to one owner or have the
    same counterparty; bank/owner/private reconciliation still required.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or explicit_owner_annotation is not True
        or not isinstance(debit_source_ref,str) or not isinstance(credit_source_ref,str)
        or not isinstance(debit_row_number,int) or not isinstance(credit_row_number,int)
        or type(debit_row_number) is not int or type(credit_row_number) is not int
        or debit_row_number < 1 or credit_row_number < 1
        or (debit_source_ref,debit_row_number)==(credit_source_ref,credit_row_number)):
        raise EconomicMovementBlocked("Two distinct reviewed synthetic bank rows required")
    try:
        debit = verified_neutral_bank(db, debit_source_ref, debit_row_number)
        credit = verified_neutral_bank(db, credit_source_ref, credit_row_number)
        from_amount = next(leg.signed_minor for leg in debit.legs if leg.account_kind=="bank")
        to_amount = next(leg.signed_minor for leg in credit.legs if leg.account_kind=="bank")
        if (from_amount >= 0 or to_amount <= 0 or from_amount + to_amount != 0
            or debit.primary_account_ref == credit.primary_account_ref):
            raise EconomicMovementBlocked("Matched transfer direction/account/amount unverified")
        pair_key = _blind("source",
            f"candidate-own-transfer:{debit.source_ref}:{credit.source_ref}")
    except EconomicMovementBlocked:
        raise
    except Exception:
        raise EconomicMovementBlocked("Sealed source-backed transfer pairing unavailable") from None
    return {
        "synthetic_only": True,
        "matched_neutral_bank_rows": 2,
        "candidate_transfer_hmac": pair_key,
        "additional_bank_postings_created": 0,
        "actual_same_owner_transfer_verified": False,
        "account_balances_certified": False,
        "tax_due_minor": None,
        "real_data_authorized": False,
    }
