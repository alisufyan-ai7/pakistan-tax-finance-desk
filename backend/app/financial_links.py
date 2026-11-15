"""Explicit, synthetic-only loan principal ledger and owner-account transfer links.

These are owner-reviewed accounting facts, not bank-certified statements, tax
returns, legal ownership proof, verified loan agreements, or tax deductions.
The source transactions remain immutable; all links are append-only.
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Account, LoanAccount, LoanAllocation, Transaction, TransferConfirmation
from .movement_analysis import MAX_TRANSFER_DAYS

MAX_MINOR = 10**15


class LoanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    direction: Literal["borrowed", "lent"]
    counterparty_label: str = Field(min_length=1, max_length=120)
    opening_as_of: date
    opening_principal_minor: StrictInt = Field(ge=0, le=MAX_MINOR)
    opening_basis: str = Field(min_length=8, max_length=500)

    @field_validator("counterparty_label", "opening_basis")
    @classmethod
    def nonblank(cls, value: str):
        if not value.strip():
            raise ValueError("A meaningful nonblank description is required")
        return value.strip()


class LoanAllocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: str = Field(min_length=36, max_length=36)
    principal_minor: StrictInt = Field(ge=0, le=MAX_MINOR)
    markup_minor: StrictInt = Field(ge=0, le=MAX_MINOR)
    evidence_note: str = Field(min_length=8, max_length=500)

    @field_validator("evidence_note")
    @classmethod
    def note_required(cls, value: str):
        if len(value.strip()) < 8:
            raise ValueError("Evidence note must be meaningful")
        return value.strip()


class TransferConfirmationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    debit_transaction_id: str = Field(min_length=36, max_length=36)
    credit_transaction_id: str = Field(min_length=36, max_length=36)
    evidence_note: str = Field(min_length=12, max_length=500)

    @field_validator("evidence_note")
    @classmethod
    def transfer_note_required(cls, value: str):
        if len(value.strip()) < 12:
            raise ValueError("Confirm the independent transfer evidence")
        return value.strip()


def _eligible(tx: Transaction) -> bool:
    return bool(tx.reviewed and not tx.excluded and
                (not tx.overlap_possible or tx.overlap_resolved))


def _conflict(message: str):
    raise HTTPException(409, message)


def _commit_or_conflict(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _conflict("Concurrent duplicate financial link; refresh and review")


def create_loan(db: Session, payload: LoanInput) -> LoanAccount:
    if payload.opening_as_of < date(1900, 1, 1) or payload.opening_as_of > date(2100, 12, 31):
        raise HTTPException(422, "Opening date outside supported historical range")
    loan = LoanAccount(
        id=str(uuid4()), legal_owner="individual", currency="PKR", direction=payload.direction,
        counterparty_label=payload.counterparty_label, opening_as_of=payload.opening_as_of,
        opening_principal_minor=payload.opening_principal_minor, opening_basis=payload.opening_basis,
    )
    db.add(loan)
    _commit_or_conflict(db)
    return loan


def _loan_event_type(loan: LoanAccount, tx: Transaction, principal: int, markup: int) -> str:
    if not _eligible(tx):
        _conflict("Transaction must be reviewed, included and overlap-resolved")
    debit, credit = tx.debit_minor, tx.credit_minor
    if loan.direction == "borrowed":
        advance, repayment, installment = "loan_received", "debt_principal_paid", "loan_installment_paid"
        full = credit if credit else debit
        expected_in = bool(credit)
    else:
        advance, repayment, installment = "loan_given", "loan_repayment_received", "loan_installment_received"
        full = debit if debit else credit
        expected_in = bool(debit)
    if tx.category == advance and expected_in and principal == full and markup == 0 and full > 0:
        return "advance"
    if tx.category == repayment and not expected_in and principal == full and markup == 0 and full > 0:
        return "repayment"
    if tx.category == installment and not expected_in and principal + markup == full and full > 0:
        return "repayment"
    raise HTTPException(422, "Direction, category or principal/markup split conflicts with source transaction")


def _active_schedule(db: Session, loan: LoanAccount, extra: tuple[date, int] | None = None):
    """Check end-of-day outstanding >=0 for every date; intraday order not inferred."""
    allocations = db.scalars(select(LoanAllocation).where(LoanAllocation.loan_id == loan.id)).all()
    deltas: dict[date, int] = {}
    for allocation in allocations:
        tx = db.get(Transaction, allocation.transaction_id)
        if tx is None:
            _conflict("Referenced transaction missing; ledger cannot be reconciled")
        delta = allocation.principal_minor * (1 if allocation.event_kind == "advance" else -1)
        deltas[tx.posted_on] = deltas.get(tx.posted_on, 0) + delta
    if extra:
        posted, delta = extra
        deltas[posted] = deltas.get(posted, 0) + delta
    outstanding = loan.opening_principal_minor
    for posted in sorted(deltas):
        outstanding += deltas[posted]
        if outstanding < 0 or outstanding > MAX_MINOR:
            _conflict("Loan principal schedule would become negative or exceed supported range")
    return outstanding


def add_allocation(db: Session, loan_id: str, payload: LoanAllocationInput) -> tuple[LoanAllocation, bool]:
    loan = db.scalar(select(LoanAccount).where(LoanAccount.id == loan_id).with_for_update())
    if loan is None:
        raise HTTPException(404, "Loan not found")
    tx = db.scalar(select(Transaction).where(Transaction.id == payload.transaction_id).with_for_update())
    if tx is None:
        raise HTTPException(404, "Source transaction not found")
    existing = db.scalar(select(LoanAllocation).where(LoanAllocation.transaction_id == tx.id))
    if existing:
        if (existing.loan_id == loan.id and existing.principal_minor == payload.principal_minor and
            existing.markup_minor == payload.markup_minor):
            return existing, True
        _conflict("Transaction already linked to another loan or a different allocation")
    if tx.posted_on < loan.opening_as_of:
        raise HTTPException(422, "Transaction predates the explicitly stated opening balance")
    account = db.get(Account, tx.account_id)
    if not account or account.legal_owner != loan.legal_owner or account.currency != loan.currency:
        _conflict("Loan and source account must have the same supported legal owner/currency")
    if db.scalar(select(TransferConfirmation.id).where(
        (TransferConfirmation.debit_transaction_id == tx.id) |
        (TransferConfirmation.credit_transaction_id == tx.id)
    ).limit(1)):
        _conflict("Transaction already confirmed as an own-account transfer")
    event_type = _loan_event_type(loan, tx, payload.principal_minor, payload.markup_minor)
    delta = payload.principal_minor * (1 if event_type == "advance" else -1)
    _active_schedule(db, loan, extra=(tx.posted_on, delta))
    allocation = LoanAllocation(
        id=str(uuid4()), loan_id=loan.id, transaction_id=tx.id,
        event_kind=event_type, principal_minor=payload.principal_minor,
        markup_minor=payload.markup_minor, evidence_note=payload.evidence_note,
    )
    db.add(allocation)
    _commit_or_conflict(db)
    return allocation, False


def loan_view(db: Session, loan: LoanAccount, as_of: date) -> dict:
    allocations = db.scalars(select(LoanAllocation).where(LoanAllocation.loan_id == loan.id)).all()
    outstanding = loan.opening_principal_minor if as_of >= loan.opening_as_of else None
    markup_minor = 0
    principal_advanced = 0
    principal_repaid = 0
    entries = []
    for allocation in allocations:
        tx = db.get(Transaction, allocation.transaction_id)
        if tx is None:
            _conflict("Loan source transaction missing")
        if tx.posted_on > as_of:
            continue
        if outstanding is not None:
            if allocation.event_kind == "advance":
                principal_advanced += allocation.principal_minor
            else:
                principal_repaid += allocation.principal_minor
            markup_minor += allocation.markup_minor
        entries.append({
            "allocation_id": allocation.id, "transaction_id": tx.id,
            "posted_on": tx.posted_on.isoformat(), "event_kind": allocation.event_kind,
            "principal_minor": allocation.principal_minor, "markup_minor": allocation.markup_minor,
            "evidence_note": allocation.evidence_note,
        })
    if outstanding is not None:
        outstanding += principal_advanced - principal_repaid
    entries.sort(key=lambda v: (v["posted_on"], v["transaction_id"]))
    return {
        "id": loan.id, "direction": loan.direction, "counterparty_label": loan.counterparty_label,
        "legal_owner": loan.legal_owner, "currency": loan.currency,
        "opening_as_of": loan.opening_as_of.isoformat(),
        "opening_principal_minor": loan.opening_principal_minor,
        "opening_basis": loan.opening_basis,
        "as_of": as_of.isoformat(), "outstanding_principal_minor": outstanding,
        "principal_advanced_minor": principal_advanced,
        "principal_repaid_minor": principal_repaid,
        "markup_observed_minor": markup_minor,
        "balance_kind": "liability" if loan.direction == "borrowed" else "receivable_asset",
        "opening_evidence_verified": False, "tax_treatment_verified": False,
        "synthetic_only": True, "allocations": entries,
    }


def confirm_transfer(db: Session, payload: TransferConfirmationInput) -> tuple[TransferConfirmation, bool]:
    if payload.debit_transaction_id == payload.credit_transaction_id:
        raise HTTPException(422, "Transfer requires two different source transactions")
    debit = db.scalar(select(Transaction).where(Transaction.id == payload.debit_transaction_id).with_for_update())
    credit = db.scalar(select(Transaction).where(Transaction.id == payload.credit_transaction_id).with_for_update())
    if not debit or not credit:
        raise HTTPException(404, "One or both transfer transactions not found")
    previously = db.scalar(select(TransferConfirmation).where(
        TransferConfirmation.debit_transaction_id == debit.id
    ))
    if previously:
        if previously.credit_transaction_id == credit.id:
            return previously, True
        _conflict("Debit transaction was already confirmed in another transfer")
    if db.scalar(select(TransferConfirmation.id).where(
        TransferConfirmation.credit_transaction_id == credit.id
    ).limit(1)):
        _conflict("Credit transaction was already confirmed in another transfer")
    if not _eligible(debit) or not _eligible(credit):
        _conflict("Both transactions must be included, reviewed and overlap-resolved")
    if debit.category != "own_transfer" or credit.category != "own_transfer":
        _conflict("Both transactions must be reviewed as own transfers")
    da = db.get(Account, debit.account_id)
    ca = db.get(Account, credit.account_id)
    if (not da or not ca or da.id == ca.id or da.legal_owner != "individual" or
        ca.legal_owner != "individual" or da.currency != ca.currency or da.currency != "PKR"):
        _conflict("Transfers require distinct accounts with identical individual ownership and currency")
    if not (debit.debit_minor > 0 and debit.credit_minor == 0 and
            credit.credit_minor == debit.debit_minor and credit.debit_minor == 0):
        _conflict("Transfer sides must have equal and opposite monetary movements")
    if abs((credit.posted_on - debit.posted_on).days) > MAX_TRANSFER_DAYS:
        _conflict("Transfer dates exceed the supported review window")
    if db.scalar(select(LoanAllocation.id).where(LoanAllocation.transaction_id.in_([debit.id, credit.id])).limit(1)):
        _conflict("A transaction is already linked to a loan")
    confirmation = TransferConfirmation(
        id=str(uuid4()), debit_transaction_id=debit.id,
        credit_transaction_id=credit.id, evidence_note=payload.evidence_note,
    )
    db.add(confirmation)
    _commit_or_conflict(db)
    return confirmation, False


def confirmed_transfers(db: Session, start: date, end: date) -> list[dict]:
    confirmations = db.scalars(select(TransferConfirmation)).all()
    result = []
    for confirmation in confirmations:
        debit = db.get(Transaction, confirmation.debit_transaction_id)
        credit = db.get(Transaction, confirmation.credit_transaction_id)
        if not debit or not credit:
            _conflict("Linked transfer source transaction is missing")
        if not (start <= debit.posted_on <= end or start <= credit.posted_on <= end):
            continue
        result.append({
            "id": confirmation.id, "debit_transaction_id": debit.id,
            "credit_transaction_id": credit.id,
            "debit_posted_on": debit.posted_on.isoformat(),
            "credit_posted_on": credit.posted_on.isoformat(),
            "amount_minor": debit.debit_minor,
            "evidence_note": confirmation.evidence_note,
            "status": "OWNER_CONFIRMED_NOT_INDEPENDENTLY_VERIFIED",
            "no_tax_claim": True,
        })
    return sorted(result, key=lambda x: (x["debit_posted_on"], x["id"]))


def source_locked(db: Session, transaction_id: str) -> bool:
    return bool(
        db.scalar(select(LoanAllocation.id).where(LoanAllocation.transaction_id == transaction_id).limit(1))
        or db.scalar(select(TransferConfirmation.id).where(
            (TransferConfirmation.debit_transaction_id == transaction_id) |
            (TransferConfirmation.credit_transaction_id == transaction_id)
        ).limit(1))
    )
