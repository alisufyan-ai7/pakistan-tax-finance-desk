"""B3: synthetic statement batches — source replay, balances, overlaps and quarantine.

This is a pure *candidate* gate, not actual import or real bank certification.
No database writes, no auto-acceptance of overlapping records and no hidden
taxable classification. Return only structural counts/review flags, never money.
"""
from __future__ import annotations

from datetime import date
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class BatchEvidenceBlocked(ValueError):
    """Source evidence cannot be accepted without further independent checks."""


class SourceLine(BaseModel):
    model_config=ConfigDict(extra="forbid")
    row_number: StrictInt = Field(ge=1,le=100000)
    posted_on: date
    debit_minor: StrictInt = Field(ge=0,le=10**15)
    credit_minor: StrictInt = Field(ge=0,le=10**15)
    balance_minor: StrictInt = Field(ge=-10**15,le=10**15)
    source_row_ref: str = Field(min_length=6,max_length=90)

    @model_validator(mode="after")
    def direction(self):
        if (self.debit_minor > 0)==(self.credit_minor > 0):
            raise ValueError("Exactly one movement direction required")
        return self


class SyntheticStatementBatch(BaseModel):
    model_config=ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    account_ref: str = Field(min_length=6,max_length=100)
    legal_owner: Literal["individual","company","aop"]
    currency: Literal["PKR"]
    source_ref: str = Field(min_length=6,max_length=100)
    digest_hmac: str = Field(min_length=64,max_length=64,pattern=r"^[0-9a-f]{64}$")
    parser_version: str = Field(min_length=3,max_length=40)
    period_start: date
    period_end: date
    opening_balance_minor: StrictInt = Field(ge=-10**15,le=10**15)
    closing_balance_minor: StrictInt = Field(ge=-10**15,le=10**15)
    rows: tuple[SourceLine,...] = Field(min_length=1,max_length=2000)
    candidate_status: Literal["candidate","quarantined"] = "candidate"

    @model_validator(mode="after")
    def consistent_period_and_rows(self):
        if (self.period_start > self.period_end or
            (self.period_end-self.period_start).days > 366 or
            self.period_start < date(2022,7,1) or self.period_end > date(2100,6,30)):
            raise ValueError("Invalid synthetic statement period")
        if (len({r.row_number for r in self.rows}) != len(self.rows) or
            len({r.source_row_ref for r in self.rows}) != len(self.rows)):
            raise ValueError("Duplicate source row")
        if any(not self.period_start <= r.posted_on <= self.period_end for r in self.rows):
            raise ValueError("Source row outside declared coverage")
        ordered=sorted(self.rows,key=lambda r:r.row_number)
        if any(b.posted_on < a.posted_on for a,b in zip(ordered,ordered[1:])):
            raise ValueError("Out-of-order source posting date")
        return self


def validate_synthetic_batch_registry(batches: list[SyntheticStatementBatch]) -> dict:
    """Checks all full batches; returns review-only manifest, never imports.

    Verified running balance requires statement's exact recorded row order
    and an explicit opening/closing figure. Overlapping statements (even with
    valid balances) must be independently resolved; no double counting.
    """
    if os.getenv("APP_DATA_MODE","synthetic") != "synthetic":
        raise BatchEvidenceBlocked("Real bank sources are not authorized")
    if not isinstance(batches,list) or len(batches)>100 or sum(len(x.rows) for x in batches)>10000:
        raise BatchEvidenceBlocked("Candidate registry exceeds bounded limits")
    unique={}
    digests={}
    for batch in batches:
        if not isinstance(batch,SyntheticStatementBatch):
            raise BatchEvidenceBlocked("Unvalidated source candidate")
        previous=unique.get(batch.source_ref)
        if previous is not None:
            if previous != batch:
                raise BatchEvidenceBlocked("Conflicting source replay")
            continue
        key=(batch.account_ref,batch.digest_hmac)
        if key in digests and digests[key] != batch.source_ref:
            raise BatchEvidenceBlocked("Identical account content under different source reference")
        unique[batch.source_ref]=batch
        digests[key]=batch.source_ref
    selected=list(unique.values())
    valid={}
    for source in selected:
        running=source.opening_balance_minor
        balanced=True
        for row in sorted(source.rows,key=lambda r:r.row_number):
            running += row.credit_minor-row.debit_minor
            if running != row.balance_minor:
                balanced=False
        if running != source.closing_balance_minor:
            balanced=False
        valid[source.source_ref]=balanced
    conflict=set()
    for i,a in enumerate(selected):
        for b in selected[i+1:]:
            if a.account_ref != b.account_ref:
                continue
            if (a.legal_owner,a.currency)!=(b.legal_owner,b.currency):
                raise BatchEvidenceBlocked("Conflicting account legal-owner/currency scope")
            if a.period_start <= b.period_end and b.period_start <= a.period_end:
                conflict.add(a.source_ref)
                conflict.add(b.source_ref)
    reasons={}
    for batch in selected:
        codes=[]
        if batch.candidate_status=="quarantined":
            codes.append("QUARANTINED")
        if not valid[batch.source_ref]:
            codes.append("RUNNING_BALANCE_MISMATCH")
        if batch.source_ref in conflict:
            codes.append("SOURCE_PERIOD_OVERLAP")
        reasons[batch.source_ref]=codes
    return {
        "synthetic_only":True,"read_only":True,"import_performed":False,
        "accounting_accepted":False,
        "unique_source_batch_count":len(selected),
        "total_source_row_count":sum(len(x.rows) for x in selected),
        "verified_running_balance_batch_count":sum(valid.values()),
        "review_required_batch_count":sum(bool(v) for v in reasons.values()),
        "issue_counts":{code:sum(code in codes for codes in reasons.values())
                        for code in ("QUARANTINED","RUNNING_BALANCE_MISMATCH","SOURCE_PERIOD_OVERLAP")},
        "full_source_data_preserved_in_input_only":True,
        "cross_bank_transfer_not_income":True,
        "tax_due_minor":None,"fbr_ready":False,
    }
