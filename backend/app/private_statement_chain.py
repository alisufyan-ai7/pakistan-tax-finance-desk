"""P2C synthetic-only cross-document bank statement balance and period proof.

Consumes bounded SHA-256/normalized preflight reports, not real file bytes.
Rejects unsafe overlap, gap, carry-forward conflict and uncertain source
periods rather than falsely reporting finance totals or covered months.
"""
from __future__ import annotations

from datetime import date, timedelta
import json
import os
import re

from .drive_inbox_planner import _index

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_SOURCES = 120
_MAX_MINOR = 10**15


class PrivateStatementChainBlocked(ValueError):
    """Cannot certify a bounded synthetic statement chain."""


def _date(value: object) -> date:
    if type(value) is not str or len(value) != 10:
        raise ValueError()
    parsed = date.fromisoformat(value)
    if not date(2022, 7, 1) <= parsed <= date(2100, 6, 30):
        raise ValueError()
    return parsed


def _minor(value: object) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_MINOR:
        raise ValueError()
    return value


def _report(raw: object) -> dict:
    if type(raw) is not dict:
        raise ValueError()
    required = {
        "contract": "personal_cfo_synthetic_statement_evidence_v1",
        "synthetic_only": True,
        "opening_balance_verified": True,
        "balance_check": "opening_and_running_verified",
        "content_hash_from_actual_bytes": True,
        "bank_or_owner_identity_verified": False,
        "financial_ledger_mutated": False,
        "source_original_modified": False,
        "google_drive_content_access_enabled": False,
        "real_financial_data_enabled": False,
    }
    if any(raw.get(k) != v for k,v in required.items()):
        raise ValueError()
    if (type(raw.get("source_sha256_hmac")) is not str
        or _HEX64.fullmatch(raw["source_sha256_hmac"]) is None
        or type(raw.get("file_sha256")) is not str
        or _HEX64.fullmatch(raw["file_sha256"]) is None
        or type(raw.get("source_row_count")) is not int
        or not 1 <= raw["source_row_count"] <= 5000):
        raise ValueError()
    credit = _minor(raw.get("synthetic_candidate_credit_minor"))
    debit = _minor(raw.get("synthetic_candidate_debit_minor"))
    closing = raw.get("synthetic_candidate_closing_minor")
    if type(closing) is not int or abs(closing)>_MAX_MINOR:
        raise ValueError()
    opening = closing-credit+debit
    if abs(opening)>_MAX_MINOR:
        raise ValueError()
    start,end=_date(raw.get("period_start")),_date(raw.get("period_end"))
    if start>end:
        raise ValueError()
    return {
        "file": raw["source_sha256_hmac"], "start":start,"end":end,
        "opening":opening,"closing":closing,"credit":credit,"debit":debit,
        "rows":raw["source_row_count"],
    }


def reconcile_synthetic_statement_chain(
    *, account_hmac: str, sources: tuple[dict, ...],
    declared_periods: tuple[tuple[str,str], ...],
    independently_declared_complete: tuple[bool, ...],
    approved_synthetic_fixture: bool,
) -> dict:
    """Assess one account, never infer statement coverage from transaction dates.

    Declared periods require independent statement-header/document evidence.
    Same-byte same-metadata replay is idempotent; other overlaps are conflicts.
    """
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or approved_synthetic_fixture is not True
        or type(account_hmac) is not str
        or _HEX64.fullmatch(account_hmac) is None
        or type(sources) is not tuple or not 1<=len(sources)<=_MAX_SOURCES
        or type(declared_periods) is not tuple or len(declared_periods)!=len(sources)
        or type(independently_declared_complete) is not tuple
        or len(independently_declared_complete)!=len(sources)):
        raise PrivateStatementChainBlocked("Approved bounded synthetic statement chain required")
    try:
        entries={}
        for raw,period,complete in zip(sources,declared_periods,
                                       independently_declared_complete):
            if (type(period) is not tuple or len(period)!=2
                or type(complete) is not bool):
                raise ValueError()
            candidate = _report(raw)
            first,last=_date(period[0]),_date(period[1])
            if (first>last or (last-first).days>366
                or not first<=candidate["start"]<=candidate["end"]<=last):
                raise ValueError()
            candidate.update({"declared_start":first,"declared_end":last,
                              "complete":complete})
            key=candidate["file"]
            if key in entries:
                if entries[key]!=candidate:
                    raise ValueError()
                continue
            entries[key]=candidate
        rows=sorted(entries.values(),key=lambda x:(x["declared_start"],
                                                    x["declared_end"],x["file"]))
        conflict=False
        gap=False
        carry=False
        for prior,current in zip(rows,rows[1:]):
            if current["declared_start"]<=prior["declared_end"]:
                conflict=True
            elif current["declared_start"]!=prior["declared_end"]+timedelta(days=1):
                gap=True
            elif current["opening"]!=prior["closing"]:
                carry=True
        complete=all(r["complete"] for r in rows)
        verified=not (conflict or gap or carry) and complete
        status=("OVERLAP_REVIEW" if conflict else
                "CARRY_FORWARD_MISMATCH_REVIEW" if carry else
                "MISSING_PERIOD_REVIEW" if gap else
                "UNCONFIRMED_STATEMENT_PERIOD_REVIEW" if not complete else
                "SYNTHETIC_CHAIN_RECONCILED")
        total_credits=sum(r["credit"] for r in rows) if verified else None
        total_debits=sum(r["debit"] for r in rows) if verified else None
        if (total_credits is not None and total_credits>_MAX_MINOR
            or total_debits is not None and total_debits>_MAX_MINOR):
            raise ValueError()
        source_proof=_index("p2c-statement-chain-sources",json.dumps(
            [[r["file"],r["declared_start"].isoformat(),
              r["declared_end"].isoformat(),r["complete"]] for r in rows],
            separators=(",",":")))
        return {
            "contract":"personal_cfo_synthetic_statement_chain_v1",
            "synthetic_only":True,
            "account_hmac":account_hmac,
            "source_chain_hmac":source_proof,
            "distinct_sources":len(rows),
            "idempotent_replays":len(sources)-len(rows),
            "status":status,
            "period_start":rows[0]["declared_start"].isoformat(),
            "period_end":max(r["declared_end"] for r in rows).isoformat(),
            "chain_coverage_verified_synthetically":verified,
            "candidate_opening_minor":rows[0]["opening"] if verified else None,
            "candidate_closing_minor":rows[-1]["closing"] if verified else None,
            "candidate_bank_credits_minor":total_credits,
            "candidate_bank_debits_minor":total_debits,
            "real_income_minor":None,
            "real_expenses_minor":None,
            "own_transfers_classified":False,
            "genuine_bank_and_owner_verified":False,
            "real_financial_data_enabled":False,
            "source_originals_modified":False,
            "ledger_mutated":False,
        }
    except Exception:
        raise PrivateStatementChainBlocked(
            "Statement chain requires period/account/balance review"
        ) from None
