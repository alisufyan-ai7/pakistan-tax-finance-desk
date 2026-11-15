"""Evidence-aware synthetic cash-in-hand ledger, never an FBR wealth certification.

Only reviewed, explicitly allocated bank movements affect cash. Manual receipts /
spending require a dated, reasoned owner entry and remain UNVERIFIED evidence.
This service never converts cash to salary or grants tax-deductible expenses.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from uuid import uuid4
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (Account, Transaction, LoanAllocation, TransferConfirmation,
                     CashHolding, CashMovement, CashMovementReversal)

MAX_CASH_MINOR = 10**14
CASH_EVENT_SIGN = {
    "bank_withdrawal": 1,
    "bank_deposit": -1,
    "manual_receipt": 1,
    "manual_spend": -1,
}


class CashOpeningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=2, max_length=80)
    opening_as_of: date
    opening_minor: StrictInt = Field(ge=0, le=MAX_CASH_MINOR)
    evidence_basis: str = Field(min_length=12, max_length=500)

    @field_validator("label", "evidence_basis")
    @classmethod
    def meaningful(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nonblank field required")
        return v


class CashMovementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["bank_withdrawal", "bank_deposit", "manual_receipt", "manual_spend"]
    amount_minor: StrictInt = Field(gt=0, le=MAX_CASH_MINOR)
    posted_on: date
    transaction_id: str | None = Field(default=None, min_length=36, max_length=36)
    evidence_note: str = Field(min_length=12, max_length=500)

    @field_validator("evidence_note")
    @classmethod
    def note_nonblank(cls, v: str) -> str:
        if len(v.strip()) < 12:
            raise ValueError("Meaningful evidence note required")
        return v.strip()

    @model_validator(mode="after")
    def consistency(self):
        from_bank = self.kind.startswith("bank_")
        if from_bank != (self.transaction_id is not None):
            raise ValueError("Bank cash events require transaction_id; manual events prohibit it")
        return self


class CashReversalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=12, max_length=500)

    @field_validator("reason")
    @classmethod
    def substantial_reason(cls, v: str) -> str:
        if len(v.strip()) < 12:
            raise ValueError("Meaningful reversal reason required")
        return v.strip()


def _conflict(message: str):
    raise HTTPException(status_code=409, detail=message)


def _commit(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _conflict("Concurrent or duplicated cash evidence link; refresh and review")


def _valid_date(d: date):
    if not date(1900, 1, 1) <= d <= date(2100, 12, 31):
        raise HTTPException(422, "Date outside supported historical range")


def create_cash_holding(db: Session, payload: CashOpeningInput) -> CashHolding:
    _valid_date(payload.opening_as_of)
    holding = CashHolding(id=str(uuid4()), label=payload.label,
        legal_owner="individual", currency="PKR", opening_as_of=payload.opening_as_of,
        opening_minor=payload.opening_minor, evidence_basis=payload.evidence_basis)
    db.add(holding)
    _commit(db)
    return holding


def _active_events(db: Session, holding: CashHolding, excluded: str | None = None,
                   extra: tuple[date, int] | None = None) -> list[tuple[date, int]]:
    moves = db.scalars(select(CashMovement).where(
        CashMovement.cash_id == holding.id, CashMovement.active.is_(True))).all()
    result = [(m.posted_on, CASH_EVENT_SIGN[m.kind] * m.amount_minor)
              for m in moves if m.id != excluded]
    if extra is not None:
        result.append(extra)
    return result


def _check_schedule(holding: CashHolding, events: list[tuple[date, int]]) -> int:
    daily: dict[date, int] = defaultdict(int)
    for date_posted, delta in events:
        if date_posted < holding.opening_as_of:
            raise HTTPException(422, "Cash posting predates explicitly declared opening")
        daily[date_posted] += delta
    remaining = holding.opening_minor
    for posting_day in sorted(daily):
        remaining += daily[posting_day]
        if remaining < 0 or remaining > MAX_CASH_MINOR:
            _conflict("Cash would be negative or above supported limit after this posting date")
    return remaining


def _check_bank_link(db: Session, holding: CashHolding, payload: CashMovementInput):
    tx = db.scalar(select(Transaction).where(
        Transaction.id == payload.transaction_id).with_for_update())
    if tx is None:
        raise HTTPException(404, "Source transaction not found")
    if not tx.reviewed or tx.excluded or (tx.overlap_possible and not tx.overlap_resolved):
        _conflict("Cash bank source must be reviewed, included and overlap-resolved")
    if tx.posted_on != payload.posted_on:
        raise HTTPException(422, "Posting date must equal bank source date")
    acc = db.get(Account, tx.account_id)
    if not acc or acc.legal_owner != holding.legal_owner or acc.currency != holding.currency:
        _conflict("Bank source does not belong to same individual and currency")
    if payload.kind == "bank_withdrawal":
        if (tx.category != "atm_cash" or tx.debit_minor != payload.amount_minor or tx.credit_minor):
            raise HTTPException(422, "Bank withdrawal must exactly match reviewed ATM/cash debit")
    elif (tx.category != "cash_deposit" or tx.credit_minor != payload.amount_minor or tx.debit_minor):
        raise HTTPException(422, "Bank deposit must exactly match reviewed cash deposit credit")
    if db.scalar(select(LoanAllocation.id).where(
        LoanAllocation.transaction_id == tx.id, LoanAllocation.active.is_(True)).limit(1)):
        _conflict("Transaction already actively linked to a loan")
    if db.scalar(select(TransferConfirmation.id).where(
        TransferConfirmation.active.is_(True), (
          (TransferConfirmation.debit_transaction_id == tx.id) |
          (TransferConfirmation.credit_transaction_id == tx.id))).limit(1)):
        _conflict("Transaction already actively linked to an own-account transfer")
    return tx


def add_cash_movement(db: Session, holding_id: str, payload: CashMovementInput):
    holding = db.scalar(select(CashHolding).where(CashHolding.id == holding_id).with_for_update())
    if holding is None:
        raise HTTPException(404, "Cash holding not found")
    _valid_date(payload.posted_on)
    if payload.posted_on < holding.opening_as_of:
        raise HTTPException(422, "Movement predates stated cash opening")
    if payload.transaction_id is not None:
        existing = db.scalar(select(CashMovement).where(
            CashMovement.transaction_id == payload.transaction_id,
            CashMovement.active.is_(True)))
        if existing:
            if (existing.cash_id == holding.id and existing.kind == payload.kind and
                existing.amount_minor == payload.amount_minor and existing.posted_on == payload.posted_on):
                return existing, True
            _conflict("Transaction already assigned to a cash movement")
        _check_bank_link(db, holding, payload)
    _check_schedule(holding, _active_events(db, holding,
        extra=(payload.posted_on, CASH_EVENT_SIGN[payload.kind] * payload.amount_minor)))
    movement = CashMovement(id=str(uuid4()), cash_id=holding.id,
        transaction_id=payload.transaction_id, kind=payload.kind,
        amount_minor=payload.amount_minor, posted_on=payload.posted_on,
        evidence_note=payload.evidence_note, active=True)
    db.add(movement)
    _commit(db)
    return movement, False


def cash_view(db: Session, holding: CashHolding, as_of: date):
    records = db.scalars(select(CashMovement).where(CashMovement.cash_id == holding.id)).all()
    reversed_ids = [m.id for m in records]
    reasons = {r.movement_id: r.reason for r in db.scalars(select(CashMovementReversal).where(
        CashMovementReversal.movement_id.in_(reversed_ids))).all()} if reversed_ids else {}
    applicable = [m for m in records if m.posted_on <= as_of]
    current = None if as_of < holding.opening_as_of else (holding.opening_minor + sum(
        CASH_EVENT_SIGN[m.kind] * m.amount_minor for m in applicable if m.active))
    manual_inflow = sum(m.amount_minor for m in applicable if m.active and m.kind == "manual_receipt")
    postings = [{"id": m.id, "kind": m.kind, "posted_on": m.posted_on.isoformat(),
                 "amount_minor": m.amount_minor, "transaction_id": m.transaction_id,
                 "evidence_note": m.evidence_note, "status": "ACTIVE" if m.active else "REVERSED",
                 "reversal_reason": reasons.get(m.id)}
                for m in sorted(applicable, key=lambda m: (m.posted_on, m.id))]
    return {"id": holding.id, "label": holding.label,
            "legal_owner": holding.legal_owner, "currency": holding.currency,
            "opening_as_of": holding.opening_as_of.isoformat(),
            "opening_minor": holding.opening_minor, "opening_basis": holding.evidence_basis,
            "as_of": as_of.isoformat(), "cash_minor": current,
            "manual_receipts_unverified_minor": manual_inflow,
            "evidence_status": "OWNER_DECLARED_UNVERIFIED" if current is not None else "OPENING_NOT_YET_REACHED",
            "fbr_wealth_verified": False, "tax_treatment_verified": False,
            "synthetic_only": True, "movements": postings}


def reverse_cash_movement(db: Session, holding_id: str, movement_id: str,
                          payload: CashReversalInput):
    holding = db.scalar(select(CashHolding).where(CashHolding.id == holding_id).with_for_update())
    if holding is None:
        raise HTTPException(404, "Cash holding not found")
    movement = db.scalar(select(CashMovement).where(
        CashMovement.id == movement_id, CashMovement.cash_id == holding.id).with_for_update())
    if movement is None:
        raise HTTPException(404, "Cash movement not found")
    if not movement.active:
        item = db.scalar(select(CashMovementReversal).where(
            CashMovementReversal.movement_id == movement.id))
        if item is None:
            _conflict("Cash reversal audit missing; manual investigation required")
        return item, True
    _check_schedule(holding, _active_events(db, holding, excluded=movement.id))
    movement.active = False
    reversal = CashMovementReversal(id=str(uuid4()), movement_id=movement.id,
                                    reason=payload.reason)
    db.add(reversal)
    _commit(db)
    return reversal, False


def cash_annual_bridge(db: Session, tax_year: int):
    if not 2023 <= tax_year <= 2100:
        raise HTTPException(422, "Tax year must be 2023 or later")
    begin = date(tax_year - 1, 7, 1)
    end = date(tax_year, 6, 30)
    opening_cutoff = begin - timedelta(days=1)
    holdings = db.scalars(select(CashHolding)).all()
    entries = []
    complete = bool(holdings)
    for h in holdings:
        opening = cash_view(db, h, opening_cutoff)
        closing = cash_view(db, h, end)
        can_reconcile = opening["cash_minor"] is not None and closing["cash_minor"] is not None
        complete = complete and can_reconcile
        entries.append({"holding_id": h.id, "label": h.label,
                        "opening_minor": opening["cash_minor"], "closing_minor": closing["cash_minor"],
                        "net_change_minor": closing["cash_minor"]-opening["cash_minor"] if can_reconcile else None,
                        "status": "OWNER_RECONCILED_UNVERIFIED" if can_reconcile else "MISSING_OPENING_EVIDENCE"})
    return {"tax_year": tax_year, "synthetic_only": True,
            "cash_accounts": entries,
            "opening_cash_minor": sum(x["opening_minor"] for x in entries) if complete else None,
            "closing_cash_minor": sum(x["closing_minor"] for x in entries) if complete else None,
            "net_cash_change_minor": sum(x["net_change_minor"] for x in entries) if complete else None,
            "cash_coverage_complete": complete,
            "fbr_wealth_verified": False, "tax_due": None,
            "warning": "Cash figures are owner declarations and reviewed bank links; undocumented spending/receipts and missing holdings may make wealth reconciliation incomplete. No deduction or income classification is inferred."}