"""E1: evidence/coverage-gated synthetic recurring outflow candidates.

No bank parser, merchant name storage, annualized savings claim, tax deduction,
investment recommendation or automatic transactions. Month coverage is supplied
by a separately verified inventory; this pure model cannot certify it alone.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
import os
from statistics import median_low
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class RecurringBlocked(ValueError):
    """Untrusted or incoherent recurrence input cannot yield a projection."""


class SyntheticOutflow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    source_ref: str = Field(min_length=6, max_length=100)
    account_ref: str = Field(min_length=4, max_length=80)
    merchant_key: str = Field(min_length=8, max_length=100)
    posted_on: date
    amount_minor: StrictInt = Field(gt=0, le=10**15)
    category: Literal[
        "subscription", "insurance", "education", "healthcare",
        "living_expense", "business_expense", "own_transfer",
        "loan_principal", "investment_purchase", "tax_paid", "other",
    ]
    reviewed: bool = False
    independently_source_verified: bool = False
    excluded: bool = False

    @model_validator(mode="after")
    def year(self):
        if not date(2022, 7, 1) <= self.posted_on <= date(2100, 6, 30):
            raise ValueError("Unsupported synthetic recurrence date")
        return self


_ELIGIBLE = frozenset({
    "subscription", "insurance", "education", "healthcare",
    "living_expense", "business_expense",
})


def _month(d: date) -> int:
    return d.year * 12 + d.month - 1


def _key(serial: int) -> str:
    return f"{(serial // 12):04d}-{(serial % 12) + 1:02d}"


def estimate_recurring_outflows(
    observations: list[SyntheticOutflow], *,
    observed_months_by_account: dict[str, set[str]],
) -> dict:
    """Estimate monthly/quarterly candidates ONLY on complete observed coverage.

    >1 charge for a merchant in any month, a gap in observed account coverage,
    missing review, unverified source, mismatched cadence or variable amounts
    results in REVIEW_REQUIRED/INSUFFICIENT_EVIDENCE, not an annualized assertion.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise RecurringBlocked("Real finance analytics must wait for G1–G3")
    if (len(observations) > 20_000 or
        not isinstance(observed_months_by_account, dict) or
        len(observed_months_by_account) > 100):
        raise RecurringBlocked("Invalid bounded recurrence inventory")
    for account, months in observed_months_by_account.items():
        if (not isinstance(account, str) or not isinstance(months, set) or
            len(months) > 240 or any(
                not isinstance(m, str) or len(m) != 7 or m[4] != "-" or
                not (m[:4].isdigit() and m[5:].isdigit()) or
                not 1 <= int(m[5:]) <= 12 for m in months
            )):
            raise RecurringBlocked("Coverage months must be complete YYYY-MM identifiers")
    seen = {}
    groups = defaultdict(list)
    excluded = 0
    for item in observations:
        prior = seen.get(item.source_ref)
        if prior is not None:
            if prior != item:
                raise RecurringBlocked("Conflicting duplicate source reference")
            continue
        seen[item.source_ref] = item
        if item.account_ref not in observed_months_by_account:
            raise RecurringBlocked("Missing account coverage provenance")
        if (item.category not in _ELIGIBLE or item.excluded or
            not item.reviewed or not item.independently_source_verified):
            excluded += 1
            continue
        groups[(item.account_ref, item.merchant_key, item.category)].append(item)

    rows = []
    for (account, merchant, category), entries in sorted(groups.items()):
        by_month = defaultdict(list)
        for row in entries:
            by_month[_month(row.posted_on)].append(row)
        months = sorted(by_month)
        interval = [b-a for a,b in zip(months,months[1:])]
        regular = (len(months) >= 3 and
                   len(set(interval)) == 1 and interval[0] in (1,3))
        duplicate_month = any(len(v) != 1 for v in by_month.values())
        prices = [x.amount_minor for x in entries]
        typical = median_low(prices)
        stable_price = all(abs(x-typical) * 10 <= typical for x in prices)
        range_months = range(months[0], months[-1]+1)
        coverage = observed_months_by_account[account]
        gap_count = sum(1 for m in range_months if _key(m) not in coverage)
        verified = regular and not duplicate_month and stable_price and not gap_count
        cadence = interval[0] if regular else None
        projected = typical * (12 // cadence) if verified else None
        if projected is not None and projected > 10**15:
            raise RecurringBlocked("Projected synthetic annual amount exceeds safe bounds")
        status = "RECURRING_CANDIDATE" if verified else (
            "INSUFFICIENT_EVIDENCE" if len(months) < 3 else "REVIEW_REQUIRED"
        )
        rows.append({
            "account_ref": account, "merchant_key": merchant,
            "category": category, "observed_charge_count": len(entries),
            "observed_month_count": len(months), "cadence_months": cadence,
            "observed_coverage_gap_count": gap_count, "status": status,
            "typical_charge_minor": typical if verified else None,
            "estimated_annual_minor": projected,
            "annual_estimate_is_observed_spending": False,
            "realized_savings_minor": None, "tax_deductibility_verified": False,
        })
    return {
        "synthetic_only": True, "read_only": True,
        "candidates": rows, "excluded_or_unverified_source_count": excluded,
        "coverage_is_external_and_must_be_verified": True,
        "actual_subscription_cancellation_not_performed": True,
        "realized_savings_minor": None, "tax_due_minor": None,
    }
