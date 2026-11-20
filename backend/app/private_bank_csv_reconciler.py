"""P6 owner private: strict source-reconciled bank CSV evidence, no invented CFO categories.

Pure parser; never writes to Drive/SQL. Only a separately MFA-gated caller may
fetch a pinned SHA256-verified approved-folder source. Source identity/account
numbers and transaction descriptions must never leave this module in results.
"""
from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import io
import re

_MAX_BYTES = 4 * 1024 * 1024
_MAX_ROWS = 5000
_MAX_MINOR = 10**15
_HEADER = ["Booking Date", "Value Date", "Doc No", "Description",
           "Debit", "Credit", "Available Balance"]
_MONTH = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")


class PrivateBankCsvBlocked(ValueError):
    """The source does not support a complete, reconciled bank observation."""


def _amount(raw: str, *, allow_empty: bool = False) -> int:
    if type(raw) is not str or len(raw) > 48:
        raise ValueError()
    stripped = raw.strip()
    if allow_empty and not stripped:
        return 0
    if not re.fullmatch(r"(?:PKR\s*)?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}", stripped):
        raise ValueError()
    value = Decimal(stripped.removeprefix("PKR").strip().replace(",", ""))
    minor = value * 100
    if not value.is_finite() or minor != minor.to_integral_value() or minor > _MAX_MINOR:
        raise ValueError()
    return int(minor)


def reconcile_private_bank_csv(data: bytes) -> dict:
    """Use ONLY the bank's own reported monetary columns and running balances.

    A gross debit is not automatically an expense; a gross credit is not
    automatically income. The CSV does not establish account ownership,
    completeness of every bank or the current balance on today's date.
    """
    if type(data) is not bytes or not 0 < len(data) <= _MAX_BYTES or b"\0" in data:
        raise PrivateBankCsvBlocked("Private bank CSV unavailable")
    try:
        decoded = data.decode("utf-8-sig", errors="strict")
        rows = list(csv.reader(io.StringIO(decoded, newline=""), strict=True))
        if (len(rows) < 6 or len(rows) > _MAX_ROWS + 5
            or len(rows[0]) != 2 or not rows[0][0].strip().isdigit()
            or len(rows[0][0].strip()) > 32
            or rows[1][0] != "Opening Balance"
            or rows[2][0] != "Closing Balance"
            or rows[3] != ["Currency", "Pakistan Rupee(PKR)"]
            or rows[4] != _HEADER):
            raise ValueError()
        opening = _amount(rows[1][1])
        expected_close = _amount(rows[2][1])
        monthly = {}
        last_date = None
        first_date = None
        running = opening
        gross_debits = gross_credits = 0
        count = 0
        for row in rows[5:]:
            if len(row) != 7 or any(len(x) > 1024 for x in row):
                raise ValueError()
            date = datetime.strptime(row[0].strip(), "%d %b %Y").date()
            value_date = datetime.strptime(row[1].strip(), "%d %b %Y").date()
            if (not 2020 <= date.year <= 2040
                or not 2020 <= value_date.year <= 2040
                or last_date is not None and date < last_date):
                raise ValueError()
            debit = _amount(row[4], allow_empty=True)
            credit = _amount(row[5], allow_empty=True)
            balance = _amount(row[6])
            if (debit == 0) == (credit == 0):
                raise ValueError()
            if running + credit - debit != balance:
                raise ValueError()
            if first_date is None:
                first_date = date
            last_date = date
            running = balance
            gross_debits += debit
            gross_credits += credit
            count += 1
            month = date.strftime("%Y-%m")
            if not _MONTH.fullmatch(month):
                raise ValueError()
            existing = monthly.setdefault(month, {
                "month": month, "transaction_count": 0,
                "gross_bank_debits_minor": 0, "gross_bank_credits_minor": 0,
                "last_reported_balance_minor": 0,
                "bank_labelled_profit_minor": 0,
                "bank_labelled_profit_tax_minor": 0,
            })
            existing["transaction_count"] += 1
            existing["gross_bank_debits_minor"] += debit
            existing["gross_bank_credits_minor"] += credit
            existing["last_reported_balance_minor"] = balance
            # Exact document-label observations, never a tax/income classifier.
            label = row[3].strip()
            if label == "Payment of Profit":
                existing["bank_labelled_profit_minor"] += credit
            if label.startswith("Withholding Tax Debit"):
                existing["bank_labelled_profit_tax_minor"] += debit
        if (count == 0 or count > _MAX_ROWS
            or len(monthly) > 120
            or running != expected_close
            or opening + gross_credits - gross_debits != running):
            raise ValueError()
        return {
            "contract": "personal_cfo_p6_reconciled_bank_csv_v1",
            "source_type": "BANK_CSV_EXACT_RUNNING_BALANCES",
            "statement_start": first_date.isoformat(),
            "statement_end": last_date.isoformat(),
            "opening_minor": opening,
            "closing_minor": running,
            "gross_bank_debits_minor": gross_debits,
            "gross_bank_credits_minor": gross_credits,
            "transaction_count": count,
            "months": [monthly[m] for m in sorted(monthly)],
            "all_running_balances_reconciled": True,
            "printed_closing_reconciled": True,
            "historical_only": True,
            "current_available_balance_minor": None,
            "personal_income_minor": None,
            "personal_expenses_minor": None,
            "investment_current_market_value_minor": None,
            "original_source_modified": False,
            "owner_review_required": True,
        }
    except (UnicodeError, ValueError, InvalidOperation, csv.Error, OverflowError):
        raise PrivateBankCsvBlocked(
            "Bank CSV layout or transaction balances require owner review"
        ) from None
