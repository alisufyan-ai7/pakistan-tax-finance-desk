"""Strict owner-private bank CSV *counterparty candidate* matching.

Matches only user-declared bank beneficiary phrases in the same SHA-pinned
approved-folder ORIGINAL CSV that already passes every running balance.
A match proves a bank movement to/from the described counterparty, NOT a
capital contribution, repayable loan, investment refund, realized return,
income, or venture assignment. All of those remain UNKNOWN.
No raw narration, account id, counterparty name, or source bytes returned.
"""
from __future__ import annotations

import csv
from datetime import datetime
import io
import json
import os
import re

from .private_bank_csv_reconciler import PrivateBankCsvBlocked, _amount

_MAX_BYTES=4*1024*1024
_MAX_TX=5000
_MAX_CANDIDATES_PER_GROUP=100
_CONFIG_ENV="P6C_PRIVATE_BANK_MATCH_PHRASES_JSON"
_GROUP=re.compile(r"^[a-z][a-z0-9_]{2,39}$")
_PHRASE=re.compile(r"^(?:to|from) [A-Z][A-Z .'-]{4,58} $")
_HMAC=re.compile(r"^[a-f0-9]{64}$")
_CONTRACT="personal_cfo_p6_investment_bank_candidates_v1"


class PrivateBankInvestmentMatchBlocked(ValueError):
    """Candidate matching needs strict reviewed evidence and configuration."""


def _reject_duplicates(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError()
        result[key]=value
    return result


def private_investment_bank_match_config(*, groups:list)->dict:
    """User-provided phrases remain exclusively in sealed existing Railway vars."""
    raw=os.getenv(_CONFIG_ENV,"")
    if not raw:
        return {}
    try:
        if type(raw) is not str or len(raw)>3000:
            raise ValueError()
        obj=json.loads(raw,object_pairs_hook=_reject_duplicates)
        known={g["id"] for g in groups}
        if (type(obj) is not dict or len(obj)>10 or not obj
            or not set(obj).issubset(known)):
            raise ValueError()
        for group,items in obj.items():
            if (not _GROUP.fullmatch(group) or type(items) is not list
                or not 1<=len(items)<=4 or len(items)!=len(set(map(str,items)))):
                raise ValueError()
            for item in items:
                if type(item) is not str or not _PHRASE.fullmatch(item):
                    raise ValueError()
        return obj
    except (ValueError,TypeError,RecursionError):
        raise PrivateBankInvestmentMatchBlocked(
            "Owner-only bank beneficiary mapping invalid") from None


def match_reconciled_bank_csv_candidates(
    data:bytes, *, report:dict, source_hmac:str,
    matching:dict, hmac_index,
)->dict:
    """Accepts only SHA-pinned CSV and its independently reconciled proof.

    hmac_index is a server-only keyed HMAC function supplied by the existing
    source adapter. Identifies original rows without exposing references.
    """
    if (type(data) is not bytes or not 0<len(data)<=_MAX_BYTES
        or type(report) is not dict
        or report.get("contract")!="personal_cfo_p6_reconciled_bank_csv_v1"
        or report.get("all_running_balances_reconciled") is not True
        or report.get("printed_closing_reconciled") is not True
        or not isinstance(source_hmac,str) or not _HMAC.fullmatch(source_hmac)
        or type(matching) is not dict or not callable(hmac_index)):
        raise PrivateBankInvestmentMatchBlocked("Reconciled source needed")
    if not matching:
        return _empty()
    try:
        rows=list(csv.reader(io.StringIO(data.decode("utf-8-sig"),newline=""),strict=True))
        if len(rows)!=report["transaction_count"]+5 or not 1<=len(rows)-5<=_MAX_TX:
            raise ValueError()
        results={group:{"group_id":group,"outgoing_bank_movements_minor":0,
                        "incoming_bank_movements_minor":0,
                        "candidate_count":0,"rows":[]}
                 for group in matching}
        for ordinal,row in enumerate(rows[5:],1):
            if len(row)!=7 or any(len(cell)>1024 for cell in row):
                raise ValueError()
            desc=" ".join(row[3].strip().upper().split())
            debit=_amount(row[4],allow_empty=True)
            credit=_amount(row[5],allow_empty=True)
            if (debit==0)==(credit==0):
                raise ValueError()
            date=datetime.strptime(row[0],"%d %b %Y").date()
            if not report["statement_start"]<=date.isoformat()<=report["statement_end"]:
                raise ValueError()
            matches=[]
            for group,phrases in matching.items():
                if any(" "+p.upper() in " "+desc+" " for p in phrases):
                    matches.append(group)
            # Even two user mappings must never claim the same bank movement.
            if len(matches)>1:
                raise ValueError()
            if not matches:
                continue
            group_id=matches[0]
            output=results[group_id]
            if len(output["rows"])>=_MAX_CANDIDATES_PER_GROUP:
                raise ValueError()
            direction="OUTBOUND" if debit else "INBOUND"
            amount=debit or credit
            fingerprint=hmac_index(
                "p6-investment-bank-candidate",
                source_hmac+":"+str(ordinal)+":"+date.isoformat()+":"+
                direction+":"+str(amount))
            if not isinstance(fingerprint,str) or not _HMAC.fullmatch(fingerprint):
                raise ValueError()
            output["rows"].append({
                "event_hmac":fingerprint,
                "source_hmac":source_hmac,
                "date":date.isoformat(),
                "direction":direction,
                "amount_minor":amount,
                "interpretation":"COUNTERPARTY_BANK_MOVEMENT_NEEDS_PURPOSE_REVIEW",
            })
            output["candidate_count"]+=1
            if debit:
                output["outgoing_bank_movements_minor"]+=debit
            else:
                output["incoming_bank_movements_minor"]+=credit
        return {
            "contract":_CONTRACT,
            "groups":[results[g] for g in sorted(results)],
            "source_reconciliation_verified":True,
            "all_investment_sources_covered":False,
            "personal_investment_principal_verified":False,
            "repayments_verified":False,
            "outstanding_investment_balance_minor":None,
            "realized_investment_return_minor":None,
            "source_data_retained":False,
            "owner_review_required":True,
        }
    except (UnicodeError,ValueError,KeyError,TypeError,OverflowError,csv.Error):
        raise PrivateBankInvestmentMatchBlocked(
            "Bank candidate evidence or transaction matching needs review") from None


def _empty()->dict:
    return {
        "contract":_CONTRACT,
        "groups":[],
        "source_reconciliation_verified":False,
        "all_investment_sources_covered":False,
        "personal_investment_principal_verified":False,
        "repayments_verified":False,
        "outstanding_investment_balance_minor":None,
        "realized_investment_return_minor":None,
        "source_data_retained":False,
        "owner_review_required":True,
    }
