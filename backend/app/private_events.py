"""Synthetic-only encrypted financial-event journal foundation.

Every meaningful economic field (date, amount, source ref, account ref,
notes, event kind) is inside one authenticated encrypted JSON column.
Only keyed HMAC equality indexes and random UUID/timestamp are visible.

This does NOT migrate or protect the older plaintext transaction/loan/cash
schema; real-data mode must stay disabled until a controlled migration passes.
"""
from __future__ import annotations

import base64
from datetime import date
from hashlib import sha256
import hmac
import json
import os
from typing import Literal
import uuid

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PrivateFinancialEvent

MAX_AMOUNT_MINOR = 10**15
MIN_EVENT_DATE = date(2022, 7, 1)
MAX_EVENT_DATE = date(2100, 6, 30)


class PrivateEventKeyError(ValueError):
    """Invalid or absent independent blind-index key."""


def _index_key() -> bytes:
    encoded = os.getenv("PRIVATE_EVENT_HMAC_KEY", "")
    if not encoded:
        raise PrivateEventKeyError("Private event HMAC key not configured")
    try:
        raw = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeError) as exc:
        raise PrivateEventKeyError("Malformed private event HMAC key") from exc
    if len(raw) != 32:
        raise PrivateEventKeyError("Private event HMAC key must be 32 bytes")
    return raw


def require_private_index_key() -> None:
    """Fail closed without a separate key; never fall back to an unkeyed hash."""
    _index_key()


def blind_index(domain: Literal["owner", "year", "source"], value: str) -> str:
    if domain not in ("owner", "year", "source"):
        raise ValueError("Unknown blind-index domain")
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError("Invalid blind-index value")
    msg = b"taxfin:private-event:v1:" + domain.encode("ascii") + b"\0" + value.encode("utf-8")
    return hmac.new(_index_key(), msg, sha256).hexdigest()


def tax_year_of(posted_on: date) -> int:
    return posted_on.year + (1 if posted_on.month >= 7 else 0)


class PrivateEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    legal_owner: Literal["individual"] = "individual"
    currency: Literal["PKR"] = "PKR"
    source_ref: str = Field(min_length=8, max_length=80)
    source_type: Literal["synthetic_bank", "synthetic_return", "owner_declared"]
    event_kind: Literal[
        "income", "expense", "bank_transfer", "loan_advance", "loan_repayment",
        "investment_trade", "asset_revaluation", "cash_adjustment", "withholding",
        "donation", "gift", "other"
    ]
    posted_on: date
    amount_minor: StrictInt = Field(gt=0, le=MAX_AMOUNT_MINOR)
    account_ref: str | None = Field(default=None, max_length=80)
    counterparty: str | None = Field(default=None, max_length=160)
    evidence_note: str = Field(min_length=12, max_length=500)
    direction: Literal["debit", "credit", "none"] = "none"
    reviewed: Literal[False] = False

    @model_validator(mode="after")
    def validate_event(self):
        if not (MIN_EVENT_DATE <= self.posted_on <= MAX_EVENT_DATE):
            raise ValueError("Only synthetic tax-year 2023+ financial events supported")
        if self.source_ref != self.source_ref.strip() or not self.source_ref.strip():
            raise ValueError("Source reference cannot have surrounding whitespace")
        if not self.evidence_note.strip():
            raise ValueError("Evidence note cannot be blank")
        if self.counterparty is not None and not self.counterparty.strip():
            raise ValueError("Counterparty must not be blank")
        return self


def _canonical(payload: PrivateEventInput) -> str:
    data = payload.model_dump(mode="json")
    # Preserve byte-for-byte canonical replay semantics for pre-M2n synthetic
    # events which lacked the optional direction field.
    if data.get("direction") == "none":
        data.pop("direction")
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _display(record: PrivateFinancialEvent) -> dict:
    # SQLAlchemy's EncryptedText yields plaintext ONLY after authenticated decrypt.
    value = json.loads(record.payload_json)
    value.update({
        "id": record.id,
        "tax_year": tax_year_of(date.fromisoformat(value["posted_on"])),
        "synthetic_only": True,
        "owner_reviewed": False,
        "tax_treatment_verified": False,
        "fbr_wealth_reconciled": False,
        "tax_due_minor": None,
    })
    return value


def record_private_event(db: Session, payload: PrivateEventInput) -> tuple[dict, bool]:
    # Blind indexes reveal neither original source_ref nor economic fields.
    source = blind_index("source", payload.legal_owner + ":" + payload.source_ref)
    existing = db.scalar(select(PrivateFinancialEvent).where(PrivateFinancialEvent.source_hmac == source))
    canonical = _canonical(payload)
    if existing is not None:
        if existing.payload_json == canonical:
            return _display(existing), True
        raise HTTPException(409, "A different event already uses that source reference")
    record = PrivateFinancialEvent(
        id=str(uuid.uuid4()),
        owner_hmac=blind_index("owner", payload.legal_owner),
        year_hmac=blind_index("year", f"{payload.legal_owner}:{tax_year_of(payload.posted_on)}"),
        source_hmac=source,
        payload_json=canonical,
    )
    db.add(record)
    db.commit()
    return _display(record), False


def list_private_events(db: Session, tax_year: int, limit: int = 200) -> dict:
    if not 2023 <= tax_year <= 2100:
        raise HTTPException(422, "Tax year must be between 2023 and 2100")
    if not 1 <= limit <= 500:
        raise HTTPException(422, "Limit must be between 1 and 500")
    rows = db.scalars(select(PrivateFinancialEvent).where(
        PrivateFinancialEvent.owner_hmac == blind_index("owner", "individual"),
        PrivateFinancialEvent.year_hmac == blind_index("year", f"individual:{tax_year}"),
    )).all()
    decoded = [_display(item) for item in rows]
    decoded.sort(key=lambda row: (row["posted_on"], row["id"]), reverse=True)
    return {
        "tax_year": tax_year,
        "synthetic_only": True,
        "events": decoded[:limit],
        "count": len(decoded),
        "tax_due_minor": None,
        "fbr_ready": False,
        "warning": "Confidential synthetic event store is separate from the legacy plaintext ledger. No tax calculation or filing readiness asserted.",
    }