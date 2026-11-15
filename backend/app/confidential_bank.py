"""G1-a: an ACTIVE, synthetic-only, fully sealed bank-source write/read path.

Unlike the M2r archive, these source batches can be inserted and queried in the
operational SQLite/PostgreSQL database. They do not yet replace the M1 legacy
ledger or represent a tax/wealth projection. G1 is NOT certified complete.
"""
from __future__ import annotations

import base64
from datetime import date
import hashlib
import hmac
import json
import os
import uuid
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .ledger_crypto import LedgerKeyError, keyring
from .models import ConfidentialBankBatch, ConfidentialBankKeyState
from .private_events import _index_key as private_index_key
from .privacy_fingerprints import _key as bank_dedup_key

# Bounds are for a synthetic prototype, not a supported large-source importer.
MAX_BATCH_ROWS = 500
MAX_BANK_BATCHES = 200
MAX_MINOR = 10**14
SENTINEL = "taxfin:confidential-bank:v1:anchor"


class ConfidentialBankKeyError(ValueError):
    """A missing, reused or mismatched blind-index/encryption key."""


def _key() -> bytes:
    encoded = os.getenv("CONFIDENTIAL_BANK_HMAC_KEY", "")
    try:
        secret = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ConfidentialBankKeyError("Confidential bank HMAC key must be base64") from exc
    if len(secret) != 32:
        raise ConfidentialBankKeyError("Confidential bank HMAC key must contain 32 bytes")
    try:
        _, ring = keyring()
        other_keys = [*ring.values(), private_index_key(), bank_dedup_key()]
    except (ValueError, LedgerKeyError) as exc:
        raise ConfidentialBankKeyError("All independent confidential bank keys must be configured") from exc
    if secret in other_keys:
        raise ConfidentialBankKeyError("Confidential bank HMAC key cannot be reused from other domains")
    return secret


def _blind(domain: Literal["owner", "account", "source"], value: str) -> str:
    if domain not in {"owner", "account", "source"} or not 1 <= len(value) <= 300:
        raise ConfidentialBankKeyError("Invalid confidential bank index domain")
    return hmac.new(_key(), b"taxfin:g1a:bank:v1:" + domain.encode("ascii") + b"\x00" + value.encode("utf-8"), hashlib.sha256).hexdigest()


def _guard(db: Session, *, create: bool) -> None:
    check = _blind("owner", SENTINEL)
    state = db.get(ConfidentialBankKeyState, "v1")
    if state is None:
        if db.scalar(select(ConfidentialBankBatch.id).limit(1)) is not None:
            raise ConfidentialBankKeyError("Missing key anchor for existing bank records")
        if create:
            db.add(ConfidentialBankKeyState(id="v1", verifier_hmac=check, sentinel=SENTINEL))
        return
    if not hmac.compare_digest(state.verifier_hmac, check):
        raise ConfidentialBankKeyError("Confidential bank blind-index key mismatch: offline recovery required")
    try:
        sealed = state.sentinel  # authenticated decryption with external keyring
    except Exception as exc:
        raise ConfidentialBankKeyError("Confidential bank encryption key unavailable or mismatched") from exc
    if sealed != SENTINEL:
        raise ConfidentialBankKeyError("Confidential bank anchor integrity mismatch")


def require_confidential_bank_store(db: Session, *, create: bool = False) -> None:
    """Check key continuity before ANY keyed read/write, not a silent empty lookup."""
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise ConfidentialBankKeyError("Real bank data mode is prohibited")
    _guard(db, create=create)


class ConfidentialBankRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row_number: StrictInt = Field(ge=1, le=100000)
    posted_on: date
    description: str = Field(min_length=1, max_length=500)
    reference: str | None = Field(default=None, max_length=120)
    debit_minor: StrictInt = Field(default=0, ge=0, le=MAX_MINOR)
    credit_minor: StrictInt = Field(default=0, ge=0, le=MAX_MINOR)
    balance_minor: StrictInt = Field(ge=-MAX_MINOR, le=MAX_MINOR)

    @model_validator(mode="after")
    def check_movement(self):
        if (self.debit_minor > 0) == (self.credit_minor > 0):
            raise ValueError("Exactly one positive debit or credit is required")
        if not self.description.strip() or self.description != self.description.strip():
            raise ValueError("Source description cannot be empty or padded")
        return self


class ConfidentialBankInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    legal_owner: Literal["individual"] = "individual"
    currency: Literal["PKR"] = "PKR"
    account_ref: str = Field(min_length=8, max_length=80)
    institution: str = Field(min_length=2, max_length=100)
    source_ref: str = Field(min_length=8, max_length=80)
    period_start: date
    period_end: date
    opening_balance_minor: StrictInt = Field(ge=-MAX_MINOR, le=MAX_MINOR)
    closing_balance_minor: StrictInt = Field(ge=-MAX_MINOR, le=MAX_MINOR)
    rows: list[ConfidentialBankRow] = Field(min_length=1, max_length=MAX_BATCH_ROWS)

    @model_validator(mode="after")
    def validate_source(self):
        if (self.account_ref != self.account_ref.strip() or
            self.source_ref != self.source_ref.strip() or
            not self.institution.strip()):
            raise ValueError("Synthetic bank source identity must be canonical")
        if not date(2022, 7, 1) <= self.period_start <= self.period_end <= date(2100, 6, 30):
            raise ValueError("Unsupported statement period")
        last_date = self.period_start
        last_row = 0
        running = self.opening_balance_minor
        for row in self.rows:
            if (row.posted_on < last_date or row.posted_on > self.period_end or
                row.row_number <= last_row):
                raise ValueError("Statement row dates and original row numbers must increase")
            running += row.credit_minor - row.debit_minor
            if running != row.balance_minor:
                raise ValueError("Source running balance mismatch")
            last_date = row.posted_on
            last_row = row.row_number
        if running != self.closing_balance_minor:
            raise ValueError("Statement closing balance mismatch")
        return self


def _canon(payload: ConfidentialBankInput) -> str:
    return json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _display(payload: ConfidentialBankInput) -> dict:
    return {
        "source_ref": payload.source_ref,
        "account_ref": payload.account_ref,
        "period_start": payload.period_start.isoformat(),
        "period_end": payload.period_end.isoformat(),
        "row_count": len(payload.rows),
        "reconciliation": "source_running_balances_verified",
        "synthetic_only": True,
        "filing_ready": False,
        "tax_due_minor": None,
        "record_scope": "CONFIDENTIAL_BANK_SOURCE_ONLY",
        "not_in_legacy_totals": True,
    }


def _verified_payload(record: ConfidentialBankBatch) -> ConfidentialBankInput:
    try:
        payload = ConfidentialBankInput.model_validate_json(record.payload_json)
    except Exception as exc:
        raise HTTPException(409, "Unreadable protected bank statement or invalid source parity") from exc
    if (record.owner_hmac != _blind("owner", payload.legal_owner) or
        record.account_hmac != _blind("account", payload.legal_owner + ":" + payload.account_ref) or
        record.source_hmac != _blind("source", payload.legal_owner + ":" + payload.source_ref)):
        raise HTTPException(409, "Protected bank statement/index mismatch")
    return payload


def record_confidential_bank_source(db: Session, payload: ConfidentialBankInput) -> tuple[dict, bool]:
    """Explicit synthetic source write. No legacy ledger rows or filing statuses are changed."""
    require_confidential_bank_store(db, create=True)
    owner_hmac = _blind("owner", payload.legal_owner)
    account_hmac = _blind("account", payload.legal_owner + ":" + payload.account_ref)
    source_hmac = _blind("source", payload.legal_owner + ":" + payload.source_ref)
    old = db.scalar(select(ConfidentialBankBatch).where(ConfidentialBankBatch.source_hmac == source_hmac))
    canonical = _canon(payload)
    if old is not None:
        existing = _verified_payload(old)
        if _canon(existing) != canonical:
            raise HTTPException(409, "Conflicting protected bank source reference")
        # _guard might have staged a new key anchor. Commit only when new.
        db.rollback()
        return _display(existing), True
    item = ConfidentialBankBatch(
        id=str(uuid.uuid4()), owner_hmac=owner_hmac,
        account_hmac=account_hmac, source_hmac=source_hmac, payload_json=canonical,
    )
    db.add(item)
    try:
        db.commit()  # atomic statement + first-use key anchor
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ConfidentialBankBatch).where(ConfidentialBankBatch.source_hmac == source_hmac))
        if existing is not None and _canon(_verified_payload(existing)) == canonical:
            return _display(payload), True
        raise HTTPException(409, "Concurrent or conflicting protected bank source") from None
    return _display(payload), False


def list_confidential_bank_sources(db: Session, account_ref: str, tax_year: int) -> dict:
    if not 2023 <= tax_year <= 2100 or not 8 <= len(account_ref) <= 80:
        raise HTTPException(422, "Supported account reference or tax year required")
    require_confidential_bank_store(db)
    account_hmac = _blind("account", "individual:" + account_ref)
    rows = db.scalars(select(ConfidentialBankBatch).where(
        ConfidentialBankBatch.owner_hmac == _blind("owner", "individual"),
        ConfidentialBankBatch.account_hmac == account_hmac
    ).limit(MAX_BANK_BATCHES + 1)).all()
    if len(rows) > MAX_BANK_BATCHES:
        raise HTTPException(409, "Protected source scan exceeds bounded limit")
    selected = []
    for item in rows:
        payload = _verified_payload(item)
        if payload.account_ref != account_ref:
            raise HTTPException(409, "Confidential account identity mismatch")
        # A statement may span July/June; no invented annual completeness.
        fy_start, fy_end = date(tax_year - 1, 7, 1), date(tax_year, 6, 30)
        if payload.period_end >= fy_start and payload.period_start <= fy_end:
            selected.append(_display(payload))
    selected.sort(key=lambda v: (v["period_start"], v["source_ref"]))
    return {"tax_year": tax_year, "account_ref": account_ref,
            "source_count": len(selected), "sources": selected,
            "synthetic_only": True, "annual_coverage_verified": False,
            "income_or_tax_total": None,
            "warning": "Encrypted active source batches only; no complete ledger, no legacy projection merge, no real documents."}
