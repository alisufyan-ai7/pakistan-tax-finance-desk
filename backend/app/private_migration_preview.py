"""Read-only synthetic M1 -> encrypted M2m migration preflight.

Never writes or deletes legacy bank records, and never copies economic values
until a later explicit backed-up migration is independently accepted.
"""
from __future__ import annotations

from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Account, PrivateFinancialEvent, Transaction
from .private_events import PrivateEventInput, _canonical, blind_index

EVENT_TYPES = {
    "salary": "income", "business_income": "income", "investment_income": "income",
    "rental_income": "income", "other_income": "income", "personal_expense": "expense",
    "business_expense": "expense", "donation": "donation", "zakat": "donation",
    "loan_received": "loan_advance", "loan_given": "loan_advance",
    "loan_repayment_received": "loan_repayment", "debt_principal_paid": "loan_repayment",
    "loan_installment_received": "loan_repayment", "loan_installment_paid": "loan_repayment",
    "own_transfer": "bank_transfer", "atm_cash": "cash_adjustment", "cash_deposit": "cash_adjustment",
    "investment_purchase": "investment_trade", "gift_received": "gift",
    "tax_paid": "other", "other_outflow": "other", "refund": "other",
}


def legacy_source_ref(transaction_id: str) -> str:
    return "legacy-m1:" + transaction_id


def preview_legacy_migration(db: Session, tax_year: int, limit: int = 500) -> dict:
    if not 2023 <= tax_year <= 2100:
        raise HTTPException(422, "Tax year must be between 2023 and 2100")
    if not 1 <= limit <= 500:
        raise HTTPException(422, "Limit must be between 1 and 500")
    start, end = date(tax_year - 1, 7, 1), date(tax_year, 6, 30)
    # Explicit truncation: never certify a migration based on a partial scan.
    txs = db.scalars(select(Transaction).where(
        Transaction.posted_on.between(start, end)
    ).order_by(Transaction.posted_on, Transaction.id).limit(limit + 1)).all()
    truncated = len(txs) > limit
    accounts = {a.id: a for a in db.scalars(select(Account)).all()}
    statuses: dict[str, int] = {}
    results: list[dict] = []
    for tx in txs[:limit]:
        a = accounts.get(tx.account_id)
        if a is None or a.currency != "PKR" or a.legal_owner != "individual":
            status = "UNSUPPORTED_OWNERSHIP_OR_CURRENCY"
        elif tx.excluded:
            status = "EXCLUDED_SOURCE"
        elif tx.overlap_possible and not tx.overlap_resolved:
            status = "UNRESOLVED_OVERLAP"
        elif not tx.reviewed or tx.category == "unreviewed":
            status = "REVIEW_REQUIRED"
        elif tx.category not in EVENT_TYPES:
            status = "UNSUPPORTED_CATEGORY"
        elif (tx.debit_minor > 0) == (tx.credit_minor > 0):
            status = "INVALID_DIRECTION"
        else:
            direction = "debit" if tx.debit_minor > 0 else "credit"
            payload = PrivateEventInput(
                synthetic_fixture=True, legal_owner="individual", currency="PKR",
                source_ref=legacy_source_ref(tx.id), source_type="synthetic_bank",
                event_kind=EVENT_TYPES[tx.category], posted_on=tx.posted_on,
                amount_minor=tx.debit_minor or tx.credit_minor,
                account_ref=tx.account_id, counterparty=None,
                evidence_note="Explicit synthetic M1 reviewed ledger source for migration preview",
                reviewed=False, direction=direction,
            )
            tag = blind_index("source", f"individual:{payload.source_ref}")
            prior = db.scalar(select(PrivateFinancialEvent).where(PrivateFinancialEvent.source_hmac == tag))
            if prior is None:
                status = "READY_FOR_EXPLICIT_MIGRATION"
            elif prior.payload_json == _canonical(payload):
                status = "ALREADY_MIRRORED_UNVERIFIED"
            else:
                status = "SOURCE_CONTENT_CONFLICT"
        statuses[status] = statuses.get(status, 0) + 1
        results.append({"legacy_transaction_id": tx.id, "status": status})
    return {
        "tax_year": tax_year,
        "synthetic_only": True,
        "read_only": True,
        "migration_performed": False,
        "backed_up": False,
        "complete_scan": not truncated,
        "truncated": truncated,
        "scanned_count": len(results),
        "status_counts": statuses,
        "rows": results,
        "tax_due_minor": None,
        "fbr_ready": False,
        "warning": "Synthetic preflight only: no legacy rows rewritten, no private events inserted, no financial values copied or double counted.",
    }