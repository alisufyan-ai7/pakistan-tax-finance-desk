"""Conservative read-only financial movement analysis (synthetic-only).

Matching account-to-account transfers is strictly a REVIEW CANDIDATE, never an
immutable economic event or proof of beneficial ownership. Loan principal is
not automatically considered salary/business income or a deductible expense.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

MAX_TRANSFER_DAYS = 2
NON_EARNINGS_CATEGORIES = frozenset({
    "own_transfer", "loan_received", "loan_given", "loan_repayment_received",
    "debt_principal_paid", "atm_cash", "investment_purchase", "gift_received",
    "donation", "zakat", "tax_paid", "cash_deposit",
})


def _eligible(tx) -> bool:
    return bool(tx.reviewed and not tx.excluded and (
        not tx.overlap_possible or tx.overlap_resolved
    ))


def _pairable(debit, credit, owners: dict[str, str]) -> bool:
    if debit.account_id == credit.account_id:
        return False
    if owners.get(debit.account_id) != "individual" or owners.get(credit.account_id) != "individual":
        return False
    if debit.debit_minor <= 0 or credit.credit_minor != debit.debit_minor:
        return False
    if abs((debit.posted_on - credit.posted_on).days) > MAX_TRANSFER_DAYS:
        return False
    # A reference mismatch does not rule out own transfer; banks may show
    # different payment references. Pairing still needs human verification.
    return True


def analyze_movements(transactions, owners: dict[str, str], start: date, end: date):
    """Produce conservative transfer/loan review snapshots; no writes or tax claims.

    Input includes an extra two days around the requested year for boundary
    matching. Category totals only include records posted *inside* that year.
    """
    approved = [t for t in transactions if _eligible(t)]
    transfers = [t for t in approved if t.category == "own_transfer"]
    debits = [t for t in transfers if t.debit_minor > 0]
    credits = [t for t in transfers if t.credit_minor > 0]

    forward = {d.id: [c for c in credits if _pairable(d, c, owners)] for d in debits}
    backward = {c.id: [d for d in debits if _pairable(d, c, owners)] for c in credits}
    matched_ids = set()
    pairs = []
    for d in sorted(debits, key=lambda t: (t.posted_on, t.id)):
        options = forward[d.id]
        if len(options) != 1 or len(backward[options[0].id]) != 1:
            continue
        c = options[0]
        if d.id in matched_ids or c.id in matched_ids:
            continue
        matched_ids.update((d.id, c.id))
        if start <= d.posted_on <= end or start <= c.posted_on <= end:
            pairs.append({
                "debit_transaction_id": d.id,
                "credit_transaction_id": c.id,
                "debit_account_id": d.account_id,
                "credit_account_id": c.account_id,
                "amount_minor": d.debit_minor,
                "amount_pkr": f"{Decimal(d.debit_minor) / 100:.2f}",
                "status": "UNVERIFIED_TRANSFER_CANDIDATE",
                "requires_owner_review": True,
            })

    ambiguous, unmatched = set(), set()
    for d in debits:
        if d.id in matched_ids or not start <= d.posted_on <= end:
            continue
        if forward[d.id]:
            ambiguous.add(d.id)
        else:
            unmatched.add(d.id)
    for c in credits:
        if c.id in matched_ids or not start <= c.posted_on <= end:
            continue
        if backward[c.id]:
            ambiguous.add(c.id)
        else:
            unmatched.add(c.id)

    totals = defaultdict(int)
    for t in approved:
        if start <= t.posted_on <= end and t.category in NON_EARNINGS_CATEGORIES:
            totals[t.category] += t.credit_minor + t.debit_minor

    return {
        "transfer_candidates": pairs,
        "ambiguous_transfer_transaction_ids": sorted(ambiguous),
        "unmatched_transfer_transaction_ids": sorted(unmatched),
        "reviewed_non_earnings_movement_pkr": {
            category: f"{Decimal(amount) / 100:.2f}" for category, amount in sorted(totals.items())
        },
        "unreviewed_record_count": sum(1 for t in transactions if not _eligible(t) and start <= t.posted_on <= end),
        "loan_balance_verified": False,
        "tax_eligibility_verified": False,
        "warning": "Candidates require owner and source verification; classification does not prove a loan balance, transfer, allowable expense or FBR tax treatment.",
    }