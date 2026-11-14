"""Synthetic historic FBR filings: durable revisions and conservative interpretation.

This module deliberately does NOT parse or accept genuine FBR PDFs. It offers a
small, exact schema to exercise versioned intake and reconciliation with fixtures.
"""
from __future__ import annotations
from hashlib import sha256
import json
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import HistoricalFiling
from .field_crypto import protect_fields, reveal_fields

FIELD_NAMES = frozenset({
    "salary_income_minor", "business_income_minor", "investment_income_minor",
    "rental_income_minor", "other_income_minor", "declared_taxable_income_minor",
    "declared_tax_minor", "adjustable_withholding_minor", "tax_paid_minor",
    "opening_wealth_minor", "closing_wealth_minor", "cash_in_hand_minor",
    "assets_minor", "liabilities_minor", "personal_expenses_minor",
    "donations_minor", "loans_given_minor", "loans_taken_minor",
})

class SyntheticFilingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Explicit fixture marker avoids an accidental path for real submissions.
    synthetic_fixture: Literal[True]
    tax_year: int = Field(ge=2023, le=2100)
    kind: Literal["income_return", "wealth_statement"]
    filing_status: Literal["filed_original", "filed_revision"]
    revision_of_id: str | None = None
    fields: dict[str, StrictInt | None] = Field(min_length=1, max_length=len(FIELD_NAMES))
    legal_entity: Literal["individual"] = "individual"

    @model_validator(mode="after")
    def validate_filing(self):
        if (self.filing_status == "filed_original") != (self.revision_of_id is None):
            raise ValueError("Only a filed revision may reference an existing filing")
        for key, value in self.fields.items():
            if key not in FIELD_NAMES:
                raise ValueError("Unknown historical filing field")
            if value is not None and (type(value) is not int or abs(value) > 10**15):
                raise ValueError("Amounts must be integer PKR paisa values within bounds")
        return self

def _as_public(filing: HistoricalFiling, vault):
    return {
        "id": filing.id, "tax_year": filing.tax_year, "kind": filing.kind,
        "legal_entity": filing.legal_entity, "filing_status": filing.filing_status,
        "revision_number": filing.revision_number, "revision_of_id": filing.revision_of_id,
        "source_sha256": filing.source_sha256,
        "fields": reveal_fields(vault, filing.id, filing.tax_year, filing.kind, filing.fields_json), "synthetic_only": True,
        "not_fbr_verified": True,
    }

def find_latest(db: Session, tax_year: int, kind: str):
    return db.scalar(select(HistoricalFiling).where(
        HistoricalFiling.tax_year == tax_year, HistoricalFiling.kind == kind
    ).order_by(HistoricalFiling.revision_number.desc()).limit(1))

def register_filing(db: Session, payload: SyntheticFilingInput, vault):
    import uuid
    raw = json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = sha256(raw).hexdigest()
    duplicate = db.scalar(select(HistoricalFiling).where(
        HistoricalFiling.tax_year == payload.tax_year,
        HistoricalFiling.kind == payload.kind,
        HistoricalFiling.source_sha256 == digest,
    ))
    if duplicate:
        return _as_public(duplicate, vault), True
    latest = find_latest(db, payload.tax_year, payload.kind)
    if payload.filing_status == "filed_original" and latest:
        raise HTTPException(409, "Original filing exists; submit a linked synthetic revision")
    if payload.filing_status == "filed_revision":
        if not latest or latest.id != payload.revision_of_id:
            raise HTTPException(409, "Revision must reference latest filing of same year and kind")
    identifier = str(uuid.uuid4())
    aad = f"historical:{payload.tax_year}:{payload.kind}:{payload.legal_entity}:{identifier}".encode()
    vault.put(identifier, raw, aad)
    filing = HistoricalFiling(
        id=identifier, tax_year=payload.tax_year, legal_entity=payload.legal_entity,
        kind=payload.kind, filing_status=payload.filing_status,
        revision_number=0 if not latest else latest.revision_number + 1,
        revision_of_id=payload.revision_of_id, source_sha256=digest,
        fields_json=protect_fields(vault, identifier, payload.tax_year, payload.kind, payload.fields),
    )
    try:
        db.add(filing)
        db.commit()
    except Exception:
        db.rollback()
        vault.discard(identifier)
        raise
    return _as_public(filing, vault), False

def wealth_continuity(db: Session, tax_year: int, vault):
    """Compare prior TY closing vs current TY opening, unknown != zero."""
    prior = find_latest(db, tax_year - 1, "wealth_statement")
    current = find_latest(db, tax_year, "wealth_statement")
    before = None if prior is None else reveal_fields(vault, prior.id, prior.tax_year, prior.kind, prior.fields_json).get("closing_wealth_minor")
    after = None if current is None else reveal_fields(vault, current.id, current.tax_year, current.kind, current.fields_json).get("opening_wealth_minor")
    difference = None if before is None or after is None else after - before
    return {"tax_year": tax_year, "previous_closing_wealth_minor": before,
            "current_opening_wealth_minor": after, "difference_minor": difference,
            "status": "MISSING_EVIDENCE" if difference is None else ("MATCH" if difference == 0 else "DISCREPANCY"),
            "synthetic_only": True, "fbr_ready": False}
