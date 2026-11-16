"""G1 A6 foundation: actively writable, encrypted, double-entry SYNTHETIC journal.

Separate from the plaintext M1 ledger, the candidate archive and the public
Railway preview. No API route, real-record import, FBR certification, legacy
authority cutover, or account-balance certification is implied.
"""
from __future__ import annotations

import base64
from datetime import date
from hashlib import sha256
import hmac
import json
import os
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .ledger_crypto import keyring
from .models import CanonicalJournalEntry, CanonicalJournalKeyState
from .private_events import _index_key as event_index_key, tax_year_of
from .privacy_fingerprints import _key as dedup_key

MAX_MINOR = 10**15
MAX_SCAN = 500
SENTINEL = "personal-cfo:canonical-synthetic-journal:v1"


class CanonicalJournalBlocked(ValueError):
    """Invalid source, key, double-entry posting or journal continuity."""


def _key() -> bytes:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise CanonicalJournalBlocked("Real canonical financial mode prohibited")
    raw = os.getenv("CANONICAL_JOURNAL_HMAC_KEY", "")
    try:
        key = base64.b64decode(raw, altchars=b"-_", validate=True)
    except (ValueError, UnicodeError):
        raise CanonicalJournalBlocked("Canonical HMAC key unavailable") from None
    if len(key) != 32:
        raise CanonicalJournalBlocked("Canonical HMAC key must be 32 bytes")
    try:
        _, ring = keyring()
        independent = [*ring.values(), event_index_key(), dedup_key()]
        bank_key = os.getenv("CONFIDENTIAL_BANK_HMAC_KEY", "")
        if bank_key:
            independent.append(base64.b64decode(bank_key, altchars=b"-_", validate=True))
        if key in independent or len(set(independent)) != len(independent):
            raise CanonicalJournalBlocked("Independent finance crypto keys required")
    except CanonicalJournalBlocked:
        raise
    except Exception:
        raise CanonicalJournalBlocked("Finance crypto key configuration unavailable") from None
    return key


def _blind(domain: Literal["owner", "year", "account", "source"], value: str) -> str:
    if domain not in {"owner", "year", "account", "source"} or not isinstance(value, str) or not 1 <= len(value) <= 256:
        raise CanonicalJournalBlocked("Invalid finance index domain")
    return hmac.new(_key(), b"taxfin:canonical:v1:" + domain.encode("ascii") +
                    b"\x00" + value.encode("utf-8"), sha256).hexdigest()


class JournalLeg(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    account_ref: str = Field(min_length=8, max_length=80)
    account_kind: Literal[
        "bank", "cash", "income", "expense", "loan_receivable",
        "loan_payable", "investment_cost", "asset_cost",
        "transfer_clearing", "withholding_candidate", "opening_equity",
    ]
    # Accounting convention: a positive amount is DEBIT, negative CREDIT.
    signed_minor: StrictInt = Field(ge=-MAX_MINOR, le=MAX_MINOR)

    @model_validator(mode="after")
    def nonzero(self):
        if self.signed_minor == 0 or self.account_ref != self.account_ref.strip():
            raise ValueError("A nonzero, canonical account posting is required")
        return self


class JournalEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    synthetic_fixture: Literal[True]
    legal_owner: Literal["individual"] = "individual"
    currency: Literal["PKR"] = "PKR"
    source_ref: str = Field(min_length=8, max_length=80)
    primary_account_ref: str = Field(min_length=8, max_length=80)
    posted_on: date
    event_kind: Literal[
        "bank_receipt", "expense_paid", "own_transfer", "loan_principal",
        "investment_contribution", "cash_transfer", "withholding_candidate",
        "owner_opening_assertion",
    ]
    legs: tuple[JournalLeg, ...] = Field(min_length=2, max_length=12)
    source_statement_reconciled: Literal[False] = False
    accountant_reviewed: Literal[False] = False
    official_fbr_verified: Literal[False] = False

    @model_validator(mode="after")
    def validate_event(self):
        if not date(2022, 7, 1) <= self.posted_on <= date(2100, 6, 30):
            raise ValueError("Synthetic posting date outside supported years")
        if (self.source_ref != self.source_ref.strip()
            or self.primary_account_ref != self.primary_account_ref.strip()):
            raise ValueError("Canonical source/account references required")
        if sum(leg.signed_minor for leg in self.legs) != 0:
            raise ValueError("Double-entry journal does not balance to zero")
        if len({(leg.account_kind, leg.account_ref) for leg in self.legs}) != len(self.legs):
            raise ValueError("Duplicate journal account posting")
        if not any(leg.account_ref == self.primary_account_ref for leg in self.legs):
            raise ValueError("Primary account must have a posting leg")
        return self


def _canon(event: JournalEvent) -> str:
    return json.dumps(event.model_dump(mode="json"), separators=(",", ":"),
                      sort_keys=True, ensure_ascii=False)


def _guard(db: Session, *, create: bool) -> None:
    verifier = _blind("owner", SENTINEL)
    state = db.get(CanonicalJournalKeyState, "v1")
    if state is None:
        if db.scalar(select(CanonicalJournalEntry.id).limit(1)) is not None:
            raise CanonicalJournalBlocked("Journal key anchor missing for existing entries")
        if create:
            db.add(CanonicalJournalKeyState(id="v1", verifier_hmac=verifier, sentinel=SENTINEL))
        return
    if not hmac.compare_digest(state.verifier_hmac, verifier):
        raise CanonicalJournalBlocked("Canonical journal blind-index key mismatch")
    try:
        actual = state.sentinel
    except Exception:
        raise CanonicalJournalBlocked("Canonical journal encryption key unavailable") from None
    if actual != SENTINEL:
        raise CanonicalJournalBlocked("Journal encryption key continuity failed")


def _verify_record(row: CanonicalJournalEntry) -> JournalEvent:
    try:
        event = JournalEvent.model_validate_json(row.payload_json)
        owner = event.legal_owner
        year = tax_year_of(event.posted_on)
        if (not hmac.compare_digest(row.owner_hmac, _blind("owner", owner))
            or not hmac.compare_digest(row.year_hmac, _blind("year", f"{owner}:{year}"))
            or not hmac.compare_digest(row.account_hmac, _blind("account", f"{owner}:{event.primary_account_ref}"))
            or not hmac.compare_digest(row.source_hmac, _blind("source", f"{owner}:{event.source_ref}"))):
            raise CanonicalJournalBlocked("Canonical source index authentication failed")
        return event
    except CanonicalJournalBlocked:
        raise
    except Exception:
        raise CanonicalJournalBlocked("Authenticated canonical journal payload unreadable") from None


def record_synthetic_journal(db: Session, event: JournalEvent) -> tuple[dict, bool]:
    """Persist independently balanced source in active encrypted SQL transaction.

    The source is *not* merged into M1 tax, cash, bank or owner net-worth totals.
    """
    if not isinstance(event, JournalEvent):
        raise CanonicalJournalBlocked("Validated synthetic journal input required")
    _guard(db, create=True)
    source = _blind("source", f"{event.legal_owner}:{event.source_ref}")
    old = db.scalar(select(CanonicalJournalEntry).where(CanonicalJournalEntry.source_hmac == source))
    if old is not None:
        existing = _verify_record(old)
        if _canon(existing) != _canon(event):
            raise CanonicalJournalBlocked("Conflicting canonical source replay")
        db.rollback()
        return _receipt(old, existing), True
    row = CanonicalJournalEntry(
        id=str(uuid.uuid4()),
        owner_hmac=_blind("owner", event.legal_owner),
        year_hmac=_blind("year", f"{event.legal_owner}:{tax_year_of(event.posted_on)}"),
        account_hmac=_blind("account", f"{event.legal_owner}:{event.primary_account_ref}"),
        source_hmac=source, payload_json=_canon(event),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        old = db.scalar(select(CanonicalJournalEntry).where(CanonicalJournalEntry.source_hmac == source))
        if old is not None and _canon(_verify_record(old)) == _canon(event):
            return _receipt(old, event), True
        raise CanonicalJournalBlocked("Concurrent conflicting canonical financial posting") from None
    return _receipt(row, event), False


def _receipt(row: CanonicalJournalEntry, event: JournalEvent) -> dict:
    return {
        "id": row.id,
        "tax_year": tax_year_of(event.posted_on),
        "posting_count": len(event.legs),
        "balanced_to_zero": True,
        "synthetic_only": True,
        "owner_source_reconciled": False,
        "real_data_authorized": False,
        "active_within_separate_journal": True,
        "legacy_ledger_cutover": False,
        "verified_net_worth_minor": None,
        "fbr_tax_due_minor": None,
    }


def inspect_synthetic_journal(db: Session, *, primary_account_ref: str, tax_year: int) -> dict:
    """Authenticate source rows; show demonstration movements, NOT account balance.

    This is an internal pure Python service, never a publicly deployed endpoint.
    All cross-owner, unverified claims and uncertain balance remain unknown.
    """
    if not isinstance(primary_account_ref, str) or not 8 <= len(primary_account_ref) <= 80:
        raise CanonicalJournalBlocked("Invalid canonical account selector")
    if type(tax_year) is not int or not 2023 <= tax_year <= 2100:
        raise CanonicalJournalBlocked("Invalid canonical tax year")
    _guard(db, create=False)
    owner = "individual"
    # Until full account-authority/cutover reconciliation exists, validate
    # the ENTIRE bounded encrypted journal. A tampered blind account index
    # must never make one source silently disappear into an empty result.
    rows = db.scalars(select(CanonicalJournalEntry).limit(MAX_SCAN + 1)).all()
    if len(rows) > MAX_SCAN:
        raise CanonicalJournalBlocked("Incomplete journal source scan refused")
    receipt = []
    for row in rows:
        event = _verify_record(row)
        if event.legal_owner == owner and event.primary_account_ref == primary_account_ref and tax_year_of(event.posted_on) == tax_year:
            receipt.append(_receipt(row, event))
    return {
        "synthetic_only": True, "source_event_count": len(receipt),
        "balanced_source_events": len(receipt),
        "source_receipts": sorted(receipt, key=lambda x: x["id"]),
        "source_amounts_are_sealed": True,
        "account_balance_minor": None,
        "actual_income_or_tax_minor": None,
        "fbr_filed_confirmed": False,
        "legacy_ledger_cutover": False,
        "real_data_authorized": False,
    }
