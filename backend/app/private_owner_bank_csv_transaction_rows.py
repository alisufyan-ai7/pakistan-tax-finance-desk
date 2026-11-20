"""Owner-only, redacted transaction explorer projection from a proved bank CSV.

The bank report caller has already pinned the current read-only Google Drive
revision+SHA and reconciled *every* line against printed closing and running
balances. This projection independently verifies running balances again before
returning any row. It runs no PDF code and stores nothing on disk/DB.

Descriptions are bounded and account/IBAN references masked, but remain
sensitive owner-only evidence; never log or expose this payload anonymously.
"""
from __future__ import annotations

import csv
from datetime import datetime
import io
import re
from .private_bank_csv_reconciler import _amount, PrivateBankCsvBlocked
from .private_bank_csv_transaction_classifier import (
    _TRANSFER_LABEL, _BANK_FEE_EXACT, _TRANSACTION_CHARGE,
)

_HMAC = re.compile(r"^[0-9a-f]{64}$")
_IBAN = re.compile(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{8,32}\b", re.IGNORECASE)
_ACCOUNTS = re.compile(r"(?<![0-9])[0-9]{7,}(?![0-9])")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_MAX_PUBLIC_ROWS = 600
_CATEGORY = frozenset((
    "BANK_PROFIT", "BANK_WITHHOLDING", "BANK_CHARGE",
    "TRANSFER_CANDIDATE", "NEEDS_REVIEW",
))

def _safe_text(value):
    if type(value) is not str or len(value) > 1024:
        raise ValueError()
    # The owner's bank original may contain beneficiary names. Mask its
    # account and contact handles, preserving the description's purpose.
    text = " ".join(value.split())
    text = _IBAN.sub("[account]", text)
    text = _ACCOUNTS.sub("[account]", text)
    text = _EMAIL.sub("[contact]", text)
    text = "".join(c if c.isprintable() else " " for c in text)
    return text[:180] or "Bank entry (description not supplied)"

def _kind(text, credit, debit):
    if text == "Payment of Profit" and credit:
        return "BANK_PROFIT"
    if text.startswith("Withholding Tax Debit") and debit:
        return "BANK_WITHHOLDING"
    if debit and (text in _BANK_FEE_EXACT or _TRANSACTION_CHARGE.fullmatch(text)):
        return "BANK_CHARGE"
    if _TRANSFER_LABEL.match(text):
        return "TRANSFER_CANDIDATE"
    return "NEEDS_REVIEW"

def project_reconciled_bank_csv_transactions(
    data: bytes, *, report: dict, source_hmac: str, hmac_index,
) -> dict:
    """Return 1–600 dated rows ONLY after independent source proof.

    A transfer candidate does not become a confirmed own-account transfer,
    profit, expense or investment without additional verified evidence.
    Future longer histories require scoped pagination, not silent truncation.
    """
    if (type(data) is not bytes or not 0 < len(data) <= 4 * 1024 * 1024
        or type(report) is not dict
        or report.get("contract") != "personal_cfo_p6_reconciled_bank_csv_v1"
        or report.get("source_type") != "BANK_CSV_EXACT_RUNNING_BALANCES"
        or report.get("all_running_balances_reconciled") is not True
        or report.get("printed_closing_reconciled") is not True
        or type(source_hmac) is not str or _HMAC.fullmatch(source_hmac) is None
        or not callable(hmac_index)):
        raise PrivateBankCsvBlocked("Source proof required before owner row view")
    try:
        rows=list(csv.reader(io.StringIO(data.decode("utf-8-sig"),
                                         newline=""),strict=True))
        count=report["transaction_count"]
        if (type(count) is not int or not 1 <= count <= _MAX_PUBLIC_ROWS
            or len(rows)!=count+5):
            raise ValueError()
        original=report["opening_minor"]
        running=original
        credits=debits=0
        last_date=None
        events=[]
        counts={}
        for ordinal,row in enumerate(rows[5:],1):
            if len(row)!=7 or any(len(x)>1024 for x in row):
                raise ValueError()
            date=datetime.strptime(row[0].strip(),"%d %b %Y").date()
            if (last_date is not None and date<last_date
                or not report["statement_start"]<=date.isoformat()<=report["statement_end"]):
                raise ValueError()
            last_date=date
            debit=_amount(row[4],allow_empty=True)
            credit=_amount(row[5],allow_empty=True)
            balance=_amount(row[6])
            if (debit==0)==(credit==0) or running+credit-debit!=balance:
                raise ValueError()
            raw=row[3].strip()
            category=_kind(raw,credit,debit)
            if category not in _CATEGORY:
                raise ValueError()
            direction="INBOUND" if credit else "OUTBOUND"
            amount=credit or debit
            event_hmac=hmac_index(
                "p7-bank-csv-event",
                source_hmac+":"+str(ordinal)+":"+date.isoformat()+":"+
                direction+":"+str(amount)+":"+str(balance)+":"+raw)
            if type(event_hmac) is not str or _HMAC.fullmatch(event_hmac) is None:
                raise ValueError()
            events.append({
                "event_hmac":event_hmac,
                "source_hmac":source_hmac,
                "ordinal":ordinal,
                "date":date.isoformat(),
                "direction":direction,
                "amount_minor":amount,
                "balance_after_minor":balance,
                "description":_safe_text(raw),
                "category":category,
                "review_required":category in ("TRANSFER_CANDIDATE","NEEDS_REVIEW"),
                "classified_as_personal_income":False,
                "classified_as_personal_expense":False,
                "investment_purpose_verified":False,
            })
            counts[date.isoformat()[:7]]=counts.get(date.isoformat()[:7],0)+1
            running=balance
            credits+=credit
            debits+=debit
        if (running!=report["closing_minor"] or
            credits!=report["gross_bank_credits_minor"] or
            debits!=report["gross_bank_debits_minor"] or
            sum(counts.values())!=count or
            any(counts.get(m["month"],0)!=m["transaction_count"]
                for m in report["months"])):
            raise ValueError()
        return {
            "contract":"personal_cfo_p7_reconciled_bank_csv_rows_v1",
            "source_hmac":source_hmac,
            "transaction_count":count,
            "all_running_balances_reconciled":True,
            "source_pinned_by_parent":True,
            "source_description_account_references_masked":True,
            "historical_only":True,
            "current_available_balance_minor":None,
            "personal_income_minor":None,
            "personal_expenses_minor":None,
            "all_rows_returned":True,
            "rows":events,
        }
    except Exception:
        raise PrivateBankCsvBlocked(
            "Source transaction rows require full independent reconciliation"
        ) from None
