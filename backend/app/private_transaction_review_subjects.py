"""P5J synthetic-only stable transaction review target candidate from pinned rows.

A bank PDF summary is NOT an authenticated row import. Only a separately
trusted normalized *complete* statement row set could ever satisfy this
contract. No public route, SQL writes, Drive reads or financial classifications.
"""
from __future__ import annotations

from datetime import date
import hmac
import os
import re

from .drive_inbox_planner import _index

_HEX=re.compile(r"^[a-f0-9]{64}$")
_MAX_MINOR=10**15
_MAX_ROWS=5000
_KEYS=frozenset({"page_number","source_row_ordinal","posted_on",
                 "debit_minor","credit_minor","running_balance_minor"})

class PrivateTransactionSubjectBlocked(ValueError):
    """Cannot trust a transaction review target without complete original proof."""

def plan_synthetic_pinned_transaction_subjects(
    *, owner_hmac:str, account_hmac:str,
    original_file_hmac:str, verified_source_content_hmac:str,
    statement_start:str, statement_end:str,
    opening_minor:int, printed_closing_minor:int,
    printed_gross_debits_minor:int, printed_gross_credits_minor:int,
    rows:tuple[dict,...], source_sha_verified:bool,
    statement_layout_reconciled:bool,
    approved_synthetic_fixture:bool,
)->dict:
    if (os.getenv("APP_DATA_MODE")!="synthetic"
        or os.getenv("P5J_SYNTHETIC_TRANSACTION_SUBJECTS_ONLY")!="1"
        or approved_synthetic_fixture is not True
        or source_sha_verified is not True
        or statement_layout_reconciled is not True
        or any(type(v) is not str or _HEX.fullmatch(v) is None for v in (
            owner_hmac,account_hmac,original_file_hmac,verified_source_content_hmac))
        or type(rows) is not tuple or not 1<=len(rows)<=_MAX_ROWS
        or any(type(v) is not int or not 0<=v<=_MAX_MINOR for v in (
            opening_minor,printed_closing_minor,
            printed_gross_debits_minor,printed_gross_credits_minor))):
        raise PrivateTransactionSubjectBlocked("Complete pinned transaction proof required")
    try:
        start,end=date.fromisoformat(statement_start),date.fromisoformat(statement_end)
        if (not 1900<=start.year<=2100 or not start<=end
            or (end-start).days>366):
            raise ValueError()
        running=opening_minor
        debit=credit=0
        targets=[]
        last_date=None
        last_source_row=None
        seen=set()
        for row in rows:
            if type(row) is not dict or set(row)!=_KEYS:
                raise ValueError()
            page,ordinal=row["page_number"],row["source_row_ordinal"]
            if (type(page) is not int or type(ordinal) is not int
                or not 1<=page<=100 or not 1<=ordinal<=_MAX_ROWS
                or (page,ordinal) in seen
                or (last_source_row is not None and (page,ordinal)<=last_source_row)):
                raise ValueError()
            seen.add((page,ordinal))
            last_source_row=(page,ordinal)
            when=date.fromisoformat(row["posted_on"])
            if (not start<=when<=end or (last_date is not None and when<last_date)):
                raise ValueError()
            last_date=when
            d,c,b=row["debit_minor"],row["credit_minor"],row["running_balance_minor"]
            if (any(type(x) is not int or not 0<=x<=_MAX_MINOR for x in (d,c,b))
                or (d==0)==(c==0) or running+c-d!=b):
                raise ValueError()
            running=b
            debit+=d
            credit+=c
            if debit>_MAX_MINOR or credit>_MAX_MINOR:
                raise ValueError()
            key=_index("p5j-source-row-review-target","|".join((
                owner_hmac,account_hmac,original_file_hmac,
                verified_source_content_hmac,str(page),str(ordinal),
                when.isoformat(),str(d),str(c),str(b),
            )))
            targets.append({
                "transaction_hmac":key,
                "original_file_hmac":original_file_hmac,
                "review_state":"NEEDS_OWNER_CONTEXT",
                "owner_comment_verified":False,
                "classification_resolved":False,
            })
        if (running!=printed_closing_minor or debit!=printed_gross_debits_minor
            or credit!=printed_gross_credits_minor
            or opening_minor+credit-debit!=printed_closing_minor):
            raise ValueError()
        keys=[t["transaction_hmac"] for t in targets]
        if len(keys)!=len(set(keys)):
            raise ValueError()
        return {
            "contract":"personal_cfo_synthetic_trusted_transaction_review_targets_v1",
            "synthetic_only":True,
            "source_sha_proof_required":True,
            "statement_running_balances_verified":True,
            "source_total_reconciled":True,
            "review_targets":targets,
            "transaction_count":len(targets),
            "income_minor":None,
            "expenses_minor":None,
            "current_available_balance_minor":None,
            "cross_bank_transfers_verified":False,
            "original_source_modified":False,
            "real_financial_ledger_mutated":False,
            "owner_comments_live":False,
        }
    except Exception:
        raise PrivateTransactionSubjectBlocked(
            "Source row identity or balances require independent review") from None
