"""E2: synthetic cash buffer scenario, cleanly separating facts from assumptions.

Forecast is a hypothetical planning model, never a bank account, income/tax
return, guaranteed future balance, investment advice or payment instruction.
"""
from __future__ import annotations

from datetime import date
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class BufferScenarioBlocked(ValueError):
    """Non-synthetic, unbounded or incoherent liquidity scenario."""


class ScenarioFlow(BaseModel):
    model_config=ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    month_offset: StrictInt=Field(ge=1,le=24)
    kind: Literal["assumed_income","assumed_expense","assumed_loan_payment",
                  "assumed_tax_reserve","assumed_investment_contribution"]
    amount_minor: StrictInt=Field(gt=0,le=10**14)
    assumption_ref: str=Field(min_length=6,max_length=100)


class BufferScenario(BaseModel):
    model_config=ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    opening_month: date
    opening_balance_minor: StrictInt|None=Field(default=None,ge=-10**15,le=10**15)
    opening_source_verified_in_fixture: bool=False
    essential_monthly_spend_minor: StrictInt=Field(ge=0,le=10**14)
    reserve_target_months: StrictInt=Field(ge=1,le=24)
    horizon_months: StrictInt=Field(ge=1,le=24)
    flows: tuple[ScenarioFlow,...]=Field(default=(),max_length=400)

    @model_validator(mode="after")
    def bounds(self):
        if self.opening_month.day!=1 or not date(2022,7,1)<=self.opening_month<=date(2100,1,1):
            raise ValueError("Opening scenario month must be first day of calendar month")
        if self.opening_source_verified_in_fixture and self.opening_balance_minor is None:
            raise ValueError("Verified opening requires a known amount")
        if any(x.month_offset>self.horizon_months for x in self.flows):
            raise ValueError("Assumed cashflow after scenario horizon")
        refs=[x.assumption_ref for x in self.flows]
        if len(refs)!=len(set(refs)):
            raise ValueError("Duplicate scenario assumption reference")
        return self


def simulate_cash_buffer(scenario: BufferScenario,
                         *, month_coverage: dict[str,str]) -> dict:
    """A documented scenario; past gaps remain UNKNOWN even with a projection."""
    if os.getenv("APP_DATA_MODE","synthetic")!="synthetic":
        raise BufferScenarioBlocked("Real financial projections are not authorized")
    if not isinstance(scenario,BufferScenario) or not isinstance(month_coverage,dict):
        raise BufferScenarioBlocked("Invalid synthetic planning contract")
    if len(month_coverage)>24 or any(v not in
        ("OBSERVED","PARTIAL","MISSING","CONFLICTING","UNSUPPORTED") for v in month_coverage.values()):
        raise BufferScenarioBlocked("Unsupported source-coverage status")
    required=scenario.essential_monthly_spend_minor*scenario.reserve_target_months
    if required>10**15:
        raise BufferScenarioBlocked("Reserve amount exceeds supported bound")
    # Opening value is a fixture assertion; it is NOT bank-certified source evidence.
    known=scenario.opening_source_verified_in_fixture and scenario.opening_balance_minor is not None
    running=scenario.opening_balance_minor if known else None
    rows=[]
    y,m=scenario.opening_month.year,scenario.opening_month.month
    for offset in range(1,scenario.horizon_months+1):
        m+=1
        if m==13:
            m=1
            y+=1
        key=f"{y:04d}-{m:02d}"
        batch=[f for f in scenario.flows if f.month_offset==offset]
        incoming=sum(x.amount_minor for x in batch if x.kind=="assumed_income")
        outgoing=sum(x.amount_minor for x in batch if x.kind!="assumed_income")
        if running is not None:
            running+=incoming-outgoing
            if abs(running)>10**15:
                raise BufferScenarioBlocked("Hypothetical balance exceeds bounded range")
        verified_cov=month_coverage.get(key)=="OBSERVED"
        rows.append({
            "month":key,"coverage_status":month_coverage.get(key,"MISSING"),
            "scenario_balance_minor":running,
            "scenario_reserve_shortfall_minor":
                max(0,required-running) if running is not None else None,
            "observed_bank_balance_minor":None,
            "assumptions_used":len(batch),
            "source_backed_forecast":False,
            "source_coverage_complete_for_month":verified_cov,
        })
    return {
        "synthetic_only":True,"read_only":True,
        "scenario_only":True,"source_opening_verified_by_application":False,
        "reserve_target_minor":required,
        "months":rows,
        "missing_or_conflicting_coverage_months":sum(
            x["coverage_status"]!="OBSERVED" for x in rows),
        "all_months_observed":bool(rows) and all(
            x["source_coverage_complete_for_month"] for x in rows),
        "automatic_payment_or_investment_action":False,
        "realized_savings_minor":None,"tax_due_minor":None,
        "private_data_ready":False,
    }
