"""Source-layout-specific Bank AL Habib PDF statement reconciliation candidate.

PRIVATE parser used only after approved direct-folder source-byte verification
and an isolated document reader. This normalizes bank-reported gross movements,
not classified personal income/expense/ownership/tax treatment.

No original source, real account ID or private statement text is stored in
public fixtures. Parsing errors fail closed and keep all reported amounts
UNKNOWN rather than inventing or rounding them.
"""
from __future__ import annotations

from datetime import datetime,date
from decimal import Decimal,InvalidOperation
import re

_MAX_PAGES=100
_MAX_TRANSACTIONS=5000
_MAX_TEXT=1_000_000
_MONEY=re.compile(r"(?<!\d)(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}(?!\d)")
_ROW=re.compile(r"^\d{2}/\d{2}/\d{4}\b")
_PERIOD=re.compile(r"From (\d{2}/\d{2}/\d{4}) To (\d{2}/\d{2}/\d{4})")
_OPEN=re.compile(r"Opening Balance\s+([0-9,]+\.\d{2})")
_CLOSE=re.compile(r"\b(\d{2}/\d{2}/\d{4})\s+([0-9,]+\.\d{2})Closing Balance")
_MAX_MINOR=10**15


class PrivateBahlStatementBlocked(ValueError):
    """A BAHL bank statement could not be reconciled from source evidence."""


def _date(raw: str) -> date:
    return datetime.strptime(raw,"%d/%m/%Y").date()


def _minor(raw: str) -> int:
    value=Decimal(raw.replace(",",""))
    cents=value*100
    if (not value.is_finite() or cents!=cents.to_integral_value()
        or abs(cents)>_MAX_MINOR):
        raise ValueError()
    return int(cents)


def reconcile_bahl_pdf_pages(*, pages: tuple[str, ...]) -> dict:
    """Accept only internally extracted pages from an approved BAHL source.

    Validates line-by-line closing balances AND bank-stated gross totals and
    statement coverage. The ending balance is historical, not CURRENT.
    """
    if (type(pages) is not tuple or not 1<=len(pages)<=_MAX_PAGES
        or any(type(x) is not str or len(x)>_MAX_TEXT for x in pages)
        or sum(len(x) for x in pages)>_MAX_TEXT):
        raise PrivateBahlStatementBlocked("Bounded original statement pages required")
    try:
        opening=None
        closing=None
        printed_totals=None
        period=None
        transactions=[]
        for page_number,page in enumerate(pages,1):
            lines=[line.strip() for line in page.splitlines() if line.strip()]
            if "Bank AL Habib Limited" not in page or "STATEMENT OF ACCOUNT" not in page:
                raise ValueError()
            periods=_PERIOD.findall(page)
            if len(periods)!=1:
                raise ValueError()
            current_period=(_date(periods[0][0]),_date(periods[0][1]))
            if period is not None and current_period!=period:
                raise ValueError()
            period=current_period
            if period[0]>period[1] or (period[1]-period[0]).days>366:
                raise ValueError()
            for line in lines:
                found=_OPEN.search(line)
                if found:
                    if opening is not None:raise ValueError()
                    opening=_minor(found.group(1))
                found=_CLOSE.search(line)
                if found:
                    if closing is not None or _date(found.group(1))!=period[1]:
                        raise ValueError()
                    closing=_minor(found.group(2))
                if line.startswith("Totals:"):
                    if printed_totals is not None:raise ValueError()
                    vals=_MONEY.findall(line)
                    if len(vals)!=2:raise ValueError()
                    printed_totals=(_minor(vals[0]),_minor(vals[1]))
            blocks=[]
            current=[]
            for line in lines:
                if _ROW.match(line) and "Closing Balance" not in line:
                    if current:blocks.append(current)
                    current=[line]
                elif current:
                    current.append(line)
            if current:blocks.append(current)
            for block in blocks:
                match=_ROW.match(block[0])
                if not match:
                    continue
                date_value=_date(match.group(0))
                if not period[0]<=date_value<=period[1]:
                    raise ValueError()
                final=[]
                for line in block:
                    if any(stop in line for stop in (
                        "Carried Forward","Brought Forward",
                        "Closing Balance","Totals:","Page ",
                    )):
                        break
                    amounts=_MONEY.findall(line)
                    if amounts and not _ROW.match(line):
                        final=amounts
                if len(final)!=2:
                    raise ValueError()
                amount=_minor(final[0])
                balance=_minor(final[1])
                if amount<=0:
                    raise ValueError()
                transactions.append((date_value,amount,balance,page_number))
                if len(transactions)>_MAX_TRANSACTIONS:
                    raise ValueError()
        if opening is None or closing is None or printed_totals is None or not transactions:
            raise ValueError()
        running=opening
        debit=credit=0
        last=None
        for when,amount,balance,page in transactions:
            if last is not None and when<last:
                raise ValueError()
            last=when
            if running+amount==balance:
                credit+=amount
            elif running-amount==balance:
                debit+=amount
            else:
                raise ValueError()
            running=balance
        if (running!=closing or (debit,credit)!=printed_totals
            or opening+credit-debit!=closing):
            raise ValueError()
        return {
            "contract":"personal_cfo_bahl_reconciled_statement_v1",
            "bank":"Bank AL Habib Limited",
            "statement_start":period[0].isoformat(),
            "statement_end":period[1].isoformat(),
            "opening_minor":opening,
            "closing_minor":closing,
            "gross_bank_debits_minor":debit,
            "gross_bank_credits_minor":credit,
            "transaction_count":len(transactions),
            "page_count":len(pages),
            "printed_closing_matches_transactions":True,
            "printed_gross_totals_match_transactions":True,
            "transaction_running_balances_match":True,
            "current_available_balance_minor":None,
            "income_minor":None,
            "expenses_minor":None,
            "own_transfers_identified":False,
            "source_independent_account_ownership_verified":False,
            "all_account_coverage_verified":False,
            "real_file_sha256_bound_by_caller":False,
            "original_source_modified":False,
            "owner_review_required":True,
        }
    except Exception:
        raise PrivateBahlStatementBlocked(
            "Bank statement amounts or source coverage require private review"
        ) from None
