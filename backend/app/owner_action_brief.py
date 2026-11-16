"""E3: owner-facing month, bill, investment and follow-up signals.

Pure SYNTHETIC source-contract projection, not an authenticated real-data API.
No legacy SQL reads; no invoice payment, trading, investment advice, predicted
market yield, legal tax due or real bank/FBR evidence certification.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class OwnerSignalsBlocked(ValueError):
    """Unverified, cross-owner, inconsistent or genuine financial input."""


def _guard() -> None:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise OwnerSignalsBlocked("Real-data owner signal mode is not authorized")


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    synthetic_fixture: Literal[True]
    legal_owner: Literal["individual","company","aop"] = "individual"


class CoveredSpending(_Record):
    """Amounts are comparable only with a complete through-date source window."""
    month_start: date
    through_date: date
    total_expenses_minor: StrictInt | None = Field(default=None, ge=0, le=10**14)
    coverage_complete: bool = False
    classification_confirmed_in_fixture: bool = False
    own_transfers_excluded: bool = False
    source_attested_in_fixture: bool = False

    @model_validator(mode="after")
    def validate_window(self):
        if self.month_start.day != 1:
            raise ValueError("Spending starts at first day of a calendar month")
        if not self.month_start <= self.through_date <= date(
            self.month_start.year,self.month_start.month,
            monthrange(self.month_start.year,self.month_start.month)[1]):
            raise ValueError("Spending window outside calendar month")
        return self


class ScheduledBill(_Record):
    bill_ref: str = Field(min_length=4,max_length=80)
    name: str = Field(min_length=2,max_length=80)
    amount_minor: StrictInt | None = Field(default=None,ge=0,le=10**14)
    due_on: date
    recurrence: Literal["monthly","quarterly","annual","one_time"]
    schedule_state: Literal["OWNER_CONFIRMED_FIXTURE","CANDIDATE","UNKNOWN"]
    payment_state: Literal["MATCHED_SOURCE_FIXTURE","OWNER_MARKED","UNMATCHED"]
    payment_posted_on: date | None = None

    @model_validator(mode="after")
    def validate_payment(self):
        if self.payment_state == "MATCHED_SOURCE_FIXTURE" and not self.payment_posted_on:
            raise ValueError("Source-matched payment date is required")
        if self.payment_state != "MATCHED_SOURCE_FIXTURE" and self.payment_posted_on:
            raise ValueError("Unverified payment cannot claim a posted date")
        return self


class InvestmentTerm(_Record):
    investment_ref: str = Field(min_length=4,max_length=80)
    name: str = Field(min_length=2,max_length=80)
    principal_minor: StrictInt | None = Field(default=None,ge=0,le=10**14)
    principal_source_attested_in_fixture: bool = False
    type: Literal["fixed_deposit","savings_certificate","fund","equity","other"]
    next_expected_return_on: date | None = None
    return_terms: Literal["FIXED_CONTRACT","VARIABLE","UNKNOWN"]
    quoted_return_minor: StrictInt | None = Field(default=None,ge=0,le=10**14)
    return_quote_attested_in_fixture: bool = False
    maturity_on: date | None = None

    @model_validator(mode="after")
    def validate_quote(self):
        if self.return_terms != "FIXED_CONTRACT" and self.quoted_return_minor is not None:
            raise ValueError("Variable/unknown investments cannot quote fixed payable returns")
        if self.return_quote_attested_in_fixture and (
            self.quoted_return_minor is None or self.next_expected_return_on is None):
            raise ValueError("Source-attested quote requires value and return date")
        return self


class FollowUp(_Record):
    followup_ref: str = Field(min_length=4,max_length=80)
    title: str = Field(min_length=2,max_length=100)
    kind: Literal["bill","investment","accountant","source","tax","other"]
    due_on: date | None = None
    status: Literal["OPEN","DONE"]
    source_state: Literal["CONFIRMED_FIXTURE","CANDIDATE","UNKNOWN"]


def _spend(period: CoveredSpending | None, *, month_start: date, through: date,
           legal_owner: str) -> int | None:
    if period is None:
        return None
    if period.legal_owner != legal_owner:
        raise OwnerSignalsBlocked("Mixed legal-owner spending scope")
    if period.month_start != month_start or period.through_date != through:
        raise OwnerSignalsBlocked("Noncomparable month-to-date evidence windows")
    if not (period.coverage_complete and period.classification_confirmed_in_fixture
            and period.own_transfers_excluded and period.source_attested_in_fixture):
        return None
    return period.total_expenses_minor


def _pct_change(current: int | None, previous: int | None) -> int | None:
    if current is None or previous is None or previous == 0:
        return None
    return int((Decimal(current-previous)*Decimal(100)/Decimal(previous)).
               quantize(Decimal("1"),rounding=ROUND_HALF_UP))


def build_owner_action_brief(
    *, as_of: date, legal_owner: Literal["individual","company","aop"] = "individual",
    synthetic_fixture: bool,
    current_spend: CoveredSpending | None = None,
    prior_spend: CoveredSpending | None = None,
    bills: tuple[ScheduledBill,...] = (),
    investments: tuple[InvestmentTerm,...] = (),
    followups: tuple[FollowUp,...] = (),
) -> dict:
    """Only fabricated source-attested rows can produce illustrative movement stats.

    Without verified complete comparable evidence, change and expense amounts
    remain NULL, never $0. Return terms are *quotes*, never guaranteed yield.
    """
    _guard()
    if synthetic_fixture is not True or legal_owner not in ("individual","company","aop"):
        raise OwnerSignalsBlocked("Unverified synthetic owner scope")
    if not isinstance(as_of,date) or not 2023 <= as_of.year <= 2035:
        raise OwnerSignalsBlocked("Unsupported observation date")
    if len(bills)>200 or len(investments)>200 or len(followups)>200:
        raise OwnerSignalsBlocked("Bounded owner brief exceeded")
    if any(row.legal_owner!=legal_owner for row in (*bills,*investments,*followups)):
        raise OwnerSignalsBlocked("Cross-owner record is prohibited")
    refs=[*(x.bill_ref for x in bills),*(x.investment_ref for x in investments),
          *(x.followup_ref for x in followups)]
    if len(set(refs))!=len(refs):
        raise OwnerSignalsBlocked("Duplicate action/source reference")

    month_start=date(as_of.year,as_of.month,1)
    prior_end=month_start-timedelta(days=1)
    prior_start=date(prior_end.year,prior_end.month,1)
    prior_through=prior_start.replace(
        day=min(as_of.day,monthrange(prior_start.year,prior_start.month)[1]))
    now=_spend(current_spend,month_start=month_start,through=as_of,legal_owner=legal_owner)
    before=_spend(prior_spend,month_start=prior_start,through=prior_through,legal_owner=legal_owner)
    growth=_pct_change(now,before)
    bill_items=[]
    for x in bills:
        if x.payment_state=="MATCHED_SOURCE_FIXTURE":
            status="PAID_SOURCE_MATCHED_SAMPLE"
        elif x.schedule_state!="OWNER_CONFIRMED_FIXTURE":
            status="SCHEDULE_REVIEW"
        elif x.payment_state=="OWNER_MARKED":
            status="PAYMENT_REVIEW"
        elif x.due_on<as_of:
            status="OVERDUE_NOT_VERIFIED_PAID"
        elif x.due_on<=as_of+timedelta(days=7):
            status="DUE_WITHIN_SEVEN_DAYS"
        else:
            status="UPCOMING"
        bill_items.append({
            "bill_ref":x.bill_ref,"name":x.name,"due_on":x.due_on.isoformat(),
            "amount_minor":x.amount_minor if x.schedule_state=="OWNER_CONFIRMED_FIXTURE" else None,
            "status":status,"payment_confirmed_in_fixture":x.payment_state=="MATCHED_SOURCE_FIXTURE",
            "automatic_payment_authorized":False,
        })
    bill_items.sort(key=lambda x:(x["due_on"],x["bill_ref"]))

    investment_items=[]
    for x in investments:
        quote=(x.quoted_return_minor if (
            x.return_terms=="FIXED_CONTRACT" and x.return_quote_attested_in_fixture
            and x.next_expected_return_on is not None) else None)
        investment_items.append({
            "investment_ref":x.investment_ref,"name":x.name,"type":x.type,
            "principal_minor":x.principal_minor if x.principal_source_attested_in_fixture else None,
            "next_expected_return_on":x.next_expected_return_on.isoformat()
                                       if x.next_expected_return_on else None,
            "quoted_return_minor":quote,
            "return_state":("CONTRACT_QUOTE_NOT_GUARANTEED" if quote is not None else
                            "VARIABLE_OR_UNVERIFIED_RETURN"),
            "maturity_on":x.maturity_on.isoformat() if x.maturity_on else None,
            "actual_return_received_minor":None,
            "tax_due_or_withholding_minor":None,
            "automatic_trade_authorized":False,
        })
    investment_items.sort(key=lambda x:(x["next_expected_return_on"] is None,
                                      x["next_expected_return_on"] or "9999-12-31",
                                      x["investment_ref"]))
    followup_items=[{
        "followup_ref":x.followup_ref,"title":x.title,"kind":x.kind,
        "due_on":x.due_on.isoformat() if x.due_on else None,
        "status":("OVERDUE" if x.due_on and x.due_on<as_of else
                  "DUE_SOON" if x.due_on and x.due_on<=as_of+timedelta(days=7)
                  else "OPEN"),
        "verified_owner_action":False,
    } for x in followups if x.status=="OPEN"]
    followup_items.sort(key=lambda x:(x["due_on"] is None,x["due_on"] or "9999-12-31",
                                       x["followup_ref"]))
    alert_bills=sum(x["status"] in ("OVERDUE_NOT_VERIFIED_PAID","DUE_WITHIN_SEVEN_DAYS","PAYMENT_REVIEW")
                    for x in bill_items)
    return {
        "contract":"owner_action_brief_v1","synthetic_only":True,
        "read_only":True,"as_of":as_of.isoformat(),"legal_owner":legal_owner,
        "financial_source_ready":False,"actual_wealth_or_tax_ready":False,
        "month_to_date":{
            "month_start":month_start.isoformat(),
            "comparison_prior_through":prior_through.isoformat(),
            "expense_minor":now,"prior_same_window_expense_minor":before,
            "expense_growth_pct":growth,
            "growth_state":"UNKNOWN_INCOMPLETE_COVERAGE" if growth is None else
                           "RISING" if growth>0 else "FALLING" if growth<0 else "FLAT",
            "own_transfers_excluded_if_available":True,
            "estimated_year_end_spend_minor":None,
        },
        "bills":{"items":bill_items,"needs_attention_count":alert_bills,
                 "payment_actions_enabled":False},
        "investments":{"items":investment_items,"returns_guaranteed":False,
                       "real_yield_or_forecast_available":False},
        "followups":{"items":followup_items,"open_count":len(followup_items),
                     "notifications_sent":False},
    }
