"""Read-only synthetic financial position: observed components, NOT net worth/FBR.

There is no way to infer unobserved bank accounts, holdings, loans or physical cash
from a subset of statements. Missingness/staleness propagates as NULL, never 0.
"""
from __future__ import annotations

from datetime import date, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Account, CashHolding, LoanAccount, Transaction
from .cash_ledger import cash_view
from .financial_links import loan_view

BANK_OBSERVATION_MAX_AGE_DAYS = 35


def _bank_evidence(db: Session, account: Account, as_of: date) -> dict:
    latest = db.scalar(select(func.max(Transaction.posted_on)).where(
        Transaction.account_id == account.id, Transaction.posted_on <= as_of))
    base = {"account_id": account.id, "name": account.name, "currency": account.currency,
            "legal_owner": account.legal_owner, "observed_as_of": latest.isoformat() if latest else None,
            "observed_balance_minor": None, "included_balance_minor": None,
            "status": "NO_OBSERVED_BANK_ROW", "source_transaction_ids": [],
            "independently_bank_verified": False}
    if latest is None:
        return base
    rows = db.scalars(select(Transaction).where(
        Transaction.account_id == account.id, Transaction.posted_on == latest)).all()
    # Export files can overlap. Take the last row of *each document* for this
    # posting date; differing balances or unresolved overlap render evidence
    # ambiguous. Never guess an ordering between independent statement files.
    document_latest = {}
    for row in rows:
        prior = document_latest.get(row.document_id)
        if prior is None or (row.row_number, row.id) > (prior.row_number, prior.id):
            document_latest[row.document_id] = row
    candidates = list(document_latest.values())
    base["source_transaction_ids"] = sorted(row.id for row in candidates)
    if any(row.excluded or (row.overlap_possible and not row.overlap_resolved) for row in rows):
        base["status"] = "UNRESOLVED_BANK_SOURCE"
    elif any(row.balance_minor is None for row in candidates):
        base["status"] = "MISSING_LATEST_BANK_BALANCE"
    elif len({row.balance_minor for row in candidates}) > 1:
        base["status"] = "CONFLICTING_SAME_DAY_BALANCES"
    else:
        balance = candidates[0].balance_minor
        base["observed_balance_minor"] = balance
        age = (as_of - latest).days
        base["age_days"] = age
        if age > BANK_OBSERVATION_MAX_AGE_DAYS:
            base["status"] = "STALE_BANK_OBSERVATION"
        else:
            base["status"] = "OBSERVED_BANK_BALANCE_NOT_CERTIFIED"
            base["included_balance_minor"] = balance
    return base


def observed_position(db: Session, as_of: date) -> dict:
    if not date(1900, 1, 1) <= as_of <= date(2100, 12, 31):
        raise ValueError("Requested financial position date outside supported range")
    accounts = db.scalars(select(Account).where(
        Account.legal_owner == "individual", Account.currency == "PKR")).all()
    bank = [_bank_evidence(db, a, as_of) for a in accounts]
    bank_ok = bool(bank) and all(a["included_balance_minor"] is not None for a in bank)
    bank_total = sum(a["included_balance_minor"] for a in bank) if bank_ok else None

    cash_holdings = db.scalars(select(CashHolding).where(
        CashHolding.legal_owner == "individual", CashHolding.currency == "PKR")).all()
    cash = [cash_view(db, h, as_of) for h in cash_holdings]
    cash_ok = bool(cash) and all(c["cash_minor"] is not None for c in cash)
    cash_total = sum(c["cash_minor"] for c in cash) if cash_ok else None
    # Manual receipts remain unverified even when the subtotal is arithmetically available.
    unverified_cash_receipts_minor = sum(c["manual_receipts_unverified_minor"] for c in cash)

    loans = db.scalars(select(LoanAccount).where(
        LoanAccount.legal_owner == "individual", LoanAccount.currency == "PKR")).all()
    debt = [loan_view(db, loan, as_of) for loan in loans]
    loan_ok = all(l["outstanding_principal_minor"] is not None for l in debt)
    lent_total = sum(l["outstanding_principal_minor"] for l in debt if l["direction"] == "lent") if loan_ok else None
    borrowed_total = sum(l["outstanding_principal_minor"] for l in debt if l["direction"] == "borrowed") if loan_ok else None

    recorded_components_present = bank_ok and cash_ok and loan_ok
    recorded_net = (bank_total + cash_total + lent_total - borrowed_total) if recorded_components_present else None
    gaps = []
    if not bank:
        gaps.append("NO_REGISTERED_BANK_ACCOUNTS")
    gaps.extend(f"BANK:{a['account_id']}:{a['status']}" for a in bank
                if a["included_balance_minor"] is None)
    if not cash:
        gaps.append("NO_DECLARED_CASH_HOLDINGS")
    gaps.extend(f"CASH:{h['id']}:OPENING_MISSING" for h in cash if h["cash_minor"] is None)
    gaps.extend(f"LOAN:{l['id']}:OPENING_MISSING" for l in debt if l["outstanding_principal_minor"] is None)

    return {"as_of": as_of.isoformat(), "synthetic_only": True,
            "bank_accounts": bank, "cash_holdings": cash,
            "recorded_loans": debt,
            "bank_observed_minor": bank_total,
            "cash_declared_minor": cash_total,
            "loan_receivables_declared_minor": lent_total,
            "loan_liabilities_declared_minor": borrowed_total,
            "recorded_components_position_minor": recorded_net,
            "recorded_components_present": recorded_components_present,
            "missing_evidence": gaps,
            "unverified_manual_cash_receipts_minor": unverified_cash_receipts_minor,
            "source_scope": "REGISTERED_ACCOUNTS_AND_DECLARED_CASH_LOANS_ONLY",
            "net_worth_minor": None, "fbr_wealth_reconciled": False, "tax_due": None,
            "warning": "Recorded components omit unregistered bank accounts, stocks, property, gold, vehicles, other assets/liabilities and unsupported cash events; even complete recorded components are NOT full net worth or an FBR wealth statement."}


def annual_position(db: Session, tax_year: int) -> dict:
    if not 2023 <= tax_year <= 2100:
        raise ValueError("Tax year must begin at 2023")
    opening = observed_position(db, date(tax_year - 1, 7, 1) - timedelta(days=1))
    closing = observed_position(db, date(tax_year, 6, 30))
    old = opening["recorded_components_position_minor"]
    new = closing["recorded_components_position_minor"]
    return {"tax_year": tax_year,
            "opening_observed": opening,
            "closing_observed": closing,
            "recorded_component_change_minor": new - old if old is not None and new is not None else None,
            "status": "RECORDED_COMPONENTS_ONLY_NOT_FBR" if old is not None and new is not None else "INSUFFICIENT_SOURCE_COVERAGE",
            "synthetic_only": True, "fbr_wealth_reconciled": False, "tax_due": None,
            "warning": "Annual difference is not wealth reconciliation, taxable income, investment profit or tax due; it excludes unregistered/unrecorded holdings and transfers may straddle dates."}