"""B2: pure synthetic account-month source coverage and conflict detection.

No money, account owner identity, real statement parsing, persistence or tax
calculations. Never convert missing dates to zero transactions/balances.
This contract can run on fabricated source periods before G1-G3 pass.
"""
from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_SOURCES = 1200
MAX_MONTHS = 72


class CoverageBlocked(ValueError):
    """Coverage inventory would be incomplete, unsupported or ambiguous."""


class AccountScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_ref: str = Field(min_length=4, max_length=80)
    legal_owner: Literal["individual", "company", "aop"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class SourcePeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    source_ref: str = Field(min_length=6, max_length=100)
    account_ref: str = Field(min_length=4, max_length=80)
    period_start: date
    period_end: date
    source_state: Literal["accepted", "unsupported", "quarantined"]
    complete_declared: bool = False
    balances_verified: bool = False

    @model_validator(mode="after")
    def ordered(self):
        if (self.period_start > self.period_end or
            self.period_start < date(2022, 7, 1) or self.period_end > date(2100, 6, 30) or
            (self.period_end - self.period_start).days > 366):
            raise ValueError("Invalid or unsupported statement coverage period")
        if self.source_state != "accepted" and (self.complete_declared or self.balances_verified):
            raise ValueError("Rejected sources cannot claim verified balances or complete coverage")
        return self


def _first_day(y: int, m: int) -> date:
    return date(y, m, 1)


def _next_month(d: date) -> date:
    return date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def _year(d: date) -> int:
    return d.year + int(d.month >= 7)


def account_month_coverage(
    accounts: list[AccountScope], sources: list[SourcePeriod],
    *, start_month: date, end_month: date,
) -> dict:
    """Generate every requested account×month, including absent months.

    Priority: CONFLICTING if accepted sources overlap or a rejected source
    intersects accepted evidence; OBSERVED iff the entire calendar month is
    covered by nonoverlapping, complete, balance-verified accepted source(s);
    PARTIAL for less than complete/verified accepted coverage; UNSUPPORTED
    for only quarantined/unsupported input; MISSING for no dated source.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise CoverageBlocked("Real source coverage is prohibited")
    if (not accounts or len(accounts) > 100 or len(sources) > MAX_SOURCES or
        start_month.day != 1 or end_month.day != 1 or start_month > end_month or
        start_month < date(2022, 7, 1) or end_month > date(2100, 6, 1)):
        raise CoverageBlocked("Invalid bounded account/month coverage request")
    months = []
    point = start_month
    while point <= end_month:
        if len(months) == MAX_MONTHS:
            raise CoverageBlocked("Requested period exceeds complete-month horizon")
        months.append(point)
        point = _next_month(point)
    identities = [a.account_ref for a in accounts]
    if len(identities) != len(set(identities)):
        raise CoverageBlocked("Duplicate account reference; owner/currency boundary ambiguous")
    by_account = defaultdict(list)
    indexed = {}
    for source in sources:
        if source.account_ref not in identities:
            raise CoverageBlocked("Statement source references undeclared account")
        old = indexed.get(source.source_ref)
        if old is not None:
            if old != source:
                raise CoverageBlocked("Conflicting replay of same source identifier")
            continue  # exact idempotent replay, not a second bank period
        indexed[source.source_ref] = source
        by_account[source.account_ref].append(source)

    rows = []
    counts = defaultdict(int)
    for account in accounts:
        entries = by_account[account.account_ref]
        for first in months:
            last = date(first.year, first.month, monthrange(first.year, first.month)[1])
            relevant = [x for x in entries if x.period_start <= last and x.period_end >= first]
            accepted = [x for x in relevant if x.source_state == "accepted"]
            rejected = [x for x in relevant if x.source_state != "accepted"]
            collision = bool(rejected and accepted)
            periods = sorted(
                [(max(x.period_start, first), min(x.period_end, last), x) for x in accepted],
                key=lambda t: (t[0], t[1], t[2].source_ref),
            )
            previous_end = None
            complete_days = True
            cursor = first
            verified = True
            for start, end, source in periods:
                if previous_end is not None and start <= previous_end:
                    collision = True
                if start > cursor:
                    complete_days = False
                cursor = max(cursor, end + timedelta(days=1))
                previous_end = max(previous_end, end) if previous_end is not None else end
                if not source.complete_declared or not source.balances_verified:
                    verified = False
            complete_days = complete_days and cursor > last
            if collision:
                status = "CONFLICTING"
            elif accepted:
                status = "OBSERVED" if complete_days and verified else "PARTIAL"
            elif rejected:
                status = "UNSUPPORTED"
            else:
                status = "MISSING"
            counts[status] += 1
            rows.append({
                "account_ref": account.account_ref,
                "legal_owner": account.legal_owner, "currency": account.currency,
                "month": first.isoformat()[:7], "tax_year": _year(first),
                "status": status, "accepted_source_count": len(accepted),
                "unsupported_source_count": len(rejected),
                "financial_balance_minor": None,
                "transaction_count": None,
                "source_facts_verified": status == "OBSERVED",
            })
    return {
        "synthetic_only": True, "read_only": True,
        "coverage_rows": rows,
        "counts": {s: counts[s] for s in
                   ("OBSERVED", "PARTIAL", "MISSING", "CONFLICTING", "UNSUPPORTED")},
        "complete_account_month_coverage": bool(rows) and all(
            x["status"] == "OBSERVED" for x in rows
        ),
        "rejected_and_unobserved_are_not_zero": True,
        "fbr_ready": False, "tax_due_minor": None,
    }
