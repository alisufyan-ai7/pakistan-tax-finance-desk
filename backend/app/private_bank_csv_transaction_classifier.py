"""P6 CFO facts from ORIGINAL reconciled bank CSV labels only.

This is deliberately not a model-inferred income/expense classifier. A debit
can represent transfer, property purchase, loan, cash draw, or consumption.
A credit can represent income, reimbursement, own transfer, loan, or sale.

Only definite bank-labelled profit, its specific withholding, and exact
bank fees/combined levies count as verified components. Every other movement
remains review-required; no private narration is returned to browsers or logs.
"""
from __future__ import annotations

import csv
from datetime import datetime
import io
import re

from .private_bank_csv_reconciler import _amount, PrivateBankCsvBlocked

_KNOWN_CONTRACT="personal_cfo_p6_reconciled_bank_csv_v1"
_SELF_CONTRACT="personal_cfo_p6_bank_cashflow_classification_v1"
_TRANSACTION_CHARGE=re.compile(r"^Charges Taxes Plus FED STAN\([0-9]{1,16}\)$")
_TRANSFER_LABEL=re.compile(
    r"^(?:Raast P2P Fund transfer(?:\s|$)|Money Transferred to(?:\s|$)"
    r"|Money Received from(?:\s|$)|Outward Clearing Cheque(?:\s|$))",
    re.IGNORECASE,
)
_BANK_FEE_EXACT=frozenset((
    "FED on Cheque Book Issuance.",
    "Cheque Book Issuance Charges",
))
_ROW_MAX=5000


def classify_reconciled_private_bank_csv(data:bytes, *, report:dict)->dict:
    """Immutable source-backed monthly *components*, not household P&L.

    Caller MUST have already run full printed-total and every-running-balance
    reconciliation on the SAME original bytes. We independently account for
    every debit/credit and compare monthly source totals. No descriptions,
    owner/account IDs, counterparties, or row-level hashes escape.
    """
    if (type(data) is not bytes or not 0<len(data)<=4*1024*1024
        or type(report) is not dict
        or report.get("contract")!=_KNOWN_CONTRACT
        or report.get("source_type")!="BANK_CSV_EXACT_RUNNING_BALANCES"
        or report.get("all_running_balances_reconciled") is not True
        or report.get("printed_closing_reconciled") is not True
        or report.get("current_available_balance_minor") is not None
        or report.get("personal_income_minor") is not None
        or report.get("personal_expenses_minor") is not None):
        raise PrivateBankCsvBlocked("Source reconciliation required before classification")
    try:
        rows=list(csv.reader(io.StringIO(data.decode("utf-8-sig"),
                                         newline=""),strict=True))
        if len(rows)<6 or len(rows)>_ROW_MAX+5:
            raise ValueError()
        monthly={}
        totals={k:0 for k in (
            "bank_profit_received_minor",
            "bank_profit_withholding_tax_minor",
            "bank_fees_and_combined_levies_minor",
            "unclassified_credit_minor",
            "unclassified_debit_minor",
            "pending_review_count",
            "transfer_candidate_count",
            "confirmed_bank_event_count",
        )}
        for row in rows[5:]:
            if len(row)!=7 or any(len(x)>1024 for x in row):
                raise ValueError()
            month=datetime.strptime(row[0],"%d %b %Y").strftime("%Y-%m")
            if month not in {m["month"] for m in report["months"]}:
                raise ValueError()
            debit=_amount(row[4],allow_empty=True)
            credit=_amount(row[5],allow_empty=True)
            if (debit==0)==(credit==0):
                raise ValueError()
            desc=row[3].strip()
            if len(desc)>1024:raise ValueError()
            sub=monthly.setdefault(month,{
                "month":month,
                "bank_profit_received_minor":0,
                "bank_profit_withholding_tax_minor":0,
                "bank_fees_and_combined_levies_minor":0,
                "unclassified_credit_minor":0,
                "unclassified_debit_minor":0,
                "pending_review_count":0,
                "transfer_candidate_count":0,
                "confirmed_bank_event_count":0,
                "source_transaction_count":0,
            })
            sub["source_transaction_count"]+=1
            if desc=="Payment of Profit" and credit:
                kind="bank_profit_received_minor"
                value=credit
            elif desc.startswith("Withholding Tax Debit") and debit:
                kind="bank_profit_withholding_tax_minor"
                value=debit
            elif debit and (desc in _BANK_FEE_EXACT or
                            _TRANSACTION_CHARGE.fullmatch(desc)):
                kind="bank_fees_and_combined_levies_minor"
                value=debit
            else:
                kind="unclassified_credit_minor" if credit else "unclassified_debit_minor"
                value=credit or debit
                sub["pending_review_count"]+=1
                totals["pending_review_count"]+=1
                if _TRANSFER_LABEL.match(desc):
                    sub["transfer_candidate_count"]+=1
                    totals["transfer_candidate_count"]+=1
            sub[kind]+=value;totals[kind]+=value
            if kind not in ("unclassified_credit_minor","unclassified_debit_minor"):
                sub["confirmed_bank_event_count"]+=1
                totals["confirmed_bank_event_count"]+=1
        actual_by_month={row["month"]:row for row in report["months"]}
        if len(monthly)!=len(actual_by_month):
            raise ValueError()
        for month,m in monthly.items():
            source=actual_by_month[month]
            if (m["source_transaction_count"]!=source["transaction_count"]
                or m["bank_profit_received_minor"]+m["unclassified_credit_minor"]
                   !=source["gross_bank_credits_minor"]
                or (m["bank_profit_withholding_tax_minor"]
                    +m["bank_fees_and_combined_levies_minor"]
                    +m["unclassified_debit_minor"])
                   !=source["gross_bank_debits_minor"]
                or m["bank_profit_received_minor"]!=source["bank_labelled_profit_minor"]
                or m["bank_profit_withholding_tax_minor"]!=source["bank_labelled_profit_tax_minor"]):
                raise ValueError()
        if (totals["confirmed_bank_event_count"]+totals["pending_review_count"]
            !=report["transaction_count"]
            or (totals["bank_profit_received_minor"]+totals["unclassified_credit_minor"]
                !=report["gross_bank_credits_minor"])
            or (totals["bank_profit_withholding_tax_minor"]
                +totals["bank_fees_and_combined_levies_minor"]
                +totals["unclassified_debit_minor"]!=report["gross_bank_debits_minor"])):
            raise ValueError()
        return {
            "contract":_SELF_CONTRACT,
            "classification_basis":"EXACT_BANK_LABELS_AFTER_FULL_BALANCE_RECONCILIATION",
            "months":[monthly[m] for m in sorted(monthly)],
            "transaction_count":report["transaction_count"],
            **totals,
            "all_movements_accounted_for":True,
            "all_personal_income_classified":False,
            "all_personal_expenses_classified":False,
            "all_account_coverage_verified":False,
            "personal_monthly_income_minor":None,
            "personal_monthly_expenses_minor":None,
            "owner_review_required":True,
            "original_source_modified":False,
        }
    except (UnicodeError,ValueError,KeyError,TypeError,csv.Error):
        raise PrivateBankCsvBlocked("Bank classification cannot reconcile original source") from None
