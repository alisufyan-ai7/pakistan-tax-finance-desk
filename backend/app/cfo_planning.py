"""Versioned, evidence-first personal CFO *scenario* and recorded-event briefs.

A modular personal-finance domain, not a trading agent, broker execution,
regulated investment recommendation, independent valuation or FBR tax engine.
All inputs remain explicitly synthetic in this development-only application.
Do not use unreviewed bank movements to establish spendable cash or profit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PrivateFinancialEvent
from .private_events import blind_index, tax_year_of

MAX_MINOR = 10**15
MAX_FLOW_RULES = 100
MAX_BRIEF_EVENTS = 20_000
FLOW_CATEGORIES = (
    "salary", "business_receipt", "rental_receipt", "investment_income",
    "living_expense", "operating_expense", "loan_payment", "tax_reserve",
    "investment_contribution", "insurance", "education", "healthcare",
    "charity", "other_receipt", "other_payment",
)

class CashFlowRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{2,40}$")
    category: Literal[
        "salary", "business_receipt", "rental_receipt", "investment_income",
        "living_expense", "operating_expense", "loan_payment", "tax_reserve",
        "investment_contribution", "insurance", "education", "healthcare",
        "charity", "other_receipt", "other_payment",
    ]
    direction: Literal["in", "out"]
    amount_minor: StrictInt = Field(gt=0, le=MAX_MINOR)
    start_month: StrictInt = Field(default=1, ge=1, le=60)
    end_month: StrictInt = Field(default=12, ge=1, le=60)
    every_months: StrictInt = Field(default=1, ge=1, le=60)
    assumption_note: str = Field(min_length=12, max_length=300)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_month < self.start_month:
            raise ValueError("end_month precedes start_month")
        if self.direction == "in" and self.category not in {
            "salary", "business_receipt", "rental_receipt", "investment_income", "other_receipt"
        }:
            raise ValueError("Expense/obligation categories must be outflows")
        if self.direction == "out" and self.category in {
            "salary", "business_receipt", "rental_receipt", "investment_income", "other_receipt"
        }:
            raise ValueError("Income categories must be inflows")
        return self


class FinanceGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{2,40}$")
    amount_minor: StrictInt = Field(ge=0, le=MAX_MINOR)
    due_month: StrictInt = Field(ge=1, le=60)
    evidence_note: str = Field(min_length=12, max_length=300)


class CFOScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    currency: Literal["PKR"] = "PKR"
    opening_liquid_minor: StrictInt = Field(ge=0, le=MAX_MINOR)
    essential_monthly_outflow_minor: StrictInt = Field(ge=0, le=MAX_MINOR)
    reserve_target_months: StrictInt = Field(default=6, ge=1, le=24)
    forecast_months: StrictInt = Field(default=12, ge=1, le=60)
    flows: list[CashFlowRule] = Field(default_factory=list, max_length=MAX_FLOW_RULES)
    goals: list[FinanceGoal] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_unique_and_horizon(self):
        keys = [flow.rule_id for flow in self.flows]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate flow identifiers")
        goals = [goal.goal_id for goal in self.goals]
        if len(goals) != len(set(goals)):
            raise ValueError("Duplicate financial goal identifiers")
        if any(flow.end_month > self.forecast_months for flow in self.flows):
            raise ValueError("Cash-flow rule ends after forecast horizon")
        if any(goal.due_month > self.forecast_months for goal in self.goals):
            raise ValueError("Financial goal ends after forecast horizon")
        return self


def _insight(code: str, domain: str, priority: Literal["high", "review", "informational"],
             basis: str, next_step: str) -> dict:
    return {"code": code, "domain": domain, "priority": priority,
            "status": "HYPOTHETICAL_NOT_VERIFIED", "basis": basis,
            "next_step": next_step, "requires_owner_review": True,
            "potential_tax_savings_minor": None, "investment_return_forecast_minor": None}


def scenario_forecast(payload: CFOScenarioInput) -> dict:
    """Pure deterministic what-if projection (paisa integers; no AI guesses).

    Never inferred from actual transaction data: the user explicitly supplies
    every flow and opening amount, and the application keeps them hypothetical.
    """
    reserve_target = payload.essential_monthly_outflow_minor * payload.reserve_target_months
    if reserve_target > MAX_MINOR * 24:
        raise HTTPException(422, "Reserve target exceeds calculation limits")
    current = payload.opening_liquid_minor
    opening_runway_months = (
        str((Decimal(current) / Decimal(payload.essential_monthly_outflow_minor))
            .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        if payload.essential_monthly_outflow_minor else None
    )
    rows: list[dict] = []
    used_categories: dict[str, int] = defaultdict(int)
    first_negative: int | None = None
    below_reserve: int | None = None
    incomplete_essentials_month: int | None = None
    for month in range(1, payload.forecast_months + 1):
        credit = debit = modeled_essential = 0
        triggered: list[str] = []
        for flow in payload.flows:
            if flow.start_month <= month <= flow.end_month and (month - flow.start_month) % flow.every_months == 0:
                if flow.direction == "in":
                    credit += flow.amount_minor
                else:
                    debit += flow.amount_minor
                    if flow.category in {"living_expense", "loan_payment", "insurance",
                                         "healthcare", "education", "tax_reserve"}:
                        modeled_essential += flow.amount_minor
                triggered.append(flow.rule_id)
                used_categories[flow.category] += flow.amount_minor
        current += credit - debit
        if modeled_essential < payload.essential_monthly_outflow_minor and incomplete_essentials_month is None:
            incomplete_essentials_month = month
        if current < 0 and first_negative is None:
            first_negative = month
        if current < reserve_target and below_reserve is None:
            below_reserve = month
        rows.append({"month": month, "receipts_minor": credit,
                     "payments_minor": debit, "net_movement_minor": credit-debit,
                     "projected_liquid_minor": current, "reserve_target_met": current >= reserve_target,
                     "triggered_flow_ids": triggered})
    insights = []
    if not payload.flows:
        insights.append(_insight("MISSING_CASH_FLOW_ASSUMPTIONS", "cash_flow", "high",
            "No monthly cash-flow assumptions were supplied.",
            "Add recurring income and essential/optional spending assumptions."))
    if payload.essential_monthly_outflow_minor == 0:
        insights.append(_insight("UNKNOWN_RUNWAY", "liquidity", "review",
            "Essential outgoings are explicitly zero or not modeled; reserve coverage cannot be calculated.",
            "Establish recurring essential expenses and required debt payments."))
    if incomplete_essentials_month is not None:
        insights.append(_insight("ESSENTIAL_SPENDING_UNDERMODELLED", "data_quality", "high",
            f"Modeled essential costs in month {incomplete_essentials_month} are below the separately supplied monthly essentials assumption.",
            "Include those actual essential outflows as cash-flow rules; the reserve-target input is not automatically deducted a second time."))
    if payload.opening_liquid_minor < reserve_target:
        insights.append(_insight("OPENING_RESERVE_GAP", "liquidity", "review",
            "Hypothetical opening liquidity is below the supplied emergency-reserve target.",
            "Validate available cash, near-term bills, required debt payments, and emergency reserve before allocating surplus."))
    if first_negative is not None:
        insights.append(_insight("PROJECTED_SHORTFALL", "cash_flow", "high",
            f"Hypothetical liquid balance becomes negative during forecast month {first_negative}.",
            "Revisit timing, obligations and available funding; do not assume an overdraft or credit facility."))
    if payload.flows and any(f.category == "investment_contribution" for f in payload.flows) and below_reserve is not None:
        insights.append(_insight("INVESTMENT_VS_LIQUIDITY", "investments", "review",
            "Investment cash outflows are assumed while at least one month is below the configured reserve target.",
            "Review liquidity needs, investment horizon, risk tolerance and obligations before deciding to invest."))
    goals = []
    for goal in payload.goals:
        projected = rows[goal.due_month-1]["projected_liquid_minor"]
        available_above_reserve = max(0, projected-reserve_target)
        goals.append({"goal_id": goal.goal_id, "due_month": goal.due_month,
                      "goal_minor": goal.amount_minor,
                      "hypothetical_available_after_reserve_minor": available_above_reserve,
                      "funding_gap_minor": max(0,goal.amount_minor-available_above_reserve),
                      "on_track_in_scenario": available_above_reserve >= goal.amount_minor,
                      "evidence_verified": False})
    if any(item["funding_gap_minor"] for item in goals):
        insights.append(_insight("GOAL_FUNDING_GAP", "goals", "review",
            "One or more goals exceed the hypothetical surplus remaining after the emergency-reserve target.",
            "Review target dates, funding sources, other priorities and evidence before committing funds."))
    insights.append(_insight("TAX_AND_INVESTMENT_UNASSESSED", "tax_and_risk", "informational",
        "This projection excludes actual FBR tax treatment, inflation, returns, fees and investment losses.",
        "Validate tax status, withholding, financial obligations, suitability and licensed advice where appropriate."))
    return {"synthetic_only": True, "scenario_version": "cfo-cash-scenario-v1",
            "currency": payload.currency, "months": rows,
            "reserve_target_minor": reserve_target,
            "opening_essential_runway_months": opening_runway_months,
            "first_undermodelled_essentials_month": incomplete_essentials_month,
            "reserve_target_assumption_only": True,
            "opening_liquid_minor": payload.opening_liquid_minor,
            "ending_liquid_minor": current,
            "first_negative_month": first_negative,
            "first_below_reserve_month": below_reserve,
            "goals": goals,
            "insights": insights,
            "category_movement_minor": dict(sorted(used_categories.items())),
            "tax_due_minor": None,
            "fbr_filing_ready": False,
            "investment_advice_verified": False,
            "wealth_reconciled": False,
            "warning": "Illustrative owner-supplied cash-flow assumptions only. Not financial, investment or tax advice, market forecast, or proof of funds."}


def private_journal_briefing(db: Session, tax_year: int) -> dict:
    """Summarize *only* protected journal observations, never legacy totals.

    Missing months never mean zero receipts or verified full source coverage.
    "+legacy-m1" mirrors intentionally are NOT added into old-ledger summaries.
    """
    if not 2023 <= tax_year <= 2100:
        raise HTTPException(422, "Tax year outside supported synthetic history")
    rows = db.scalars(select(PrivateFinancialEvent).where(
        PrivateFinancialEvent.owner_hmac == blind_index("owner", "individual"),
        PrivateFinancialEvent.year_hmac == blind_index("year", f"individual:{tax_year}"),
    ).limit(MAX_BRIEF_EVENTS+1)).all()
    if len(rows) > MAX_BRIEF_EVENTS:
        raise HTTPException(409, "Entire financial journal exceeds bounded scan; no partial advisory total")
    counts: Counter = Counter()
    monthly: dict[str, dict[str,int]] = defaultdict(lambda: {"event_count":0,"observed_receipts_minor":0,"observed_spending_minor":0})
    recorded_income = recorded_expenses = ambiguous = mirrored = 0
    for row in rows:
        try:
            payload = json.loads(row.payload_json)  # Authenticated decrypt by ORM.
            posted = date.fromisoformat(payload["posted_on"])
            amount = payload["amount_minor"]
            kind = payload["event_kind"]
            direction = payload.get("direction", "none")
            source = payload["source_ref"]
        except (ValueError, TypeError, KeyError) as exc:
            raise HTTPException(409, "Protected journal has an invalid event envelope") from exc
        if (not isinstance(amount,int) or isinstance(amount,bool) or not 0 < amount <= MAX_MINOR or
            tax_year_of(posted) != tax_year or
            row.source_hmac != blind_index("source", "individual:"+source) or
            row.year_hmac != blind_index("year", f"individual:{tax_year}") or
            row.owner_hmac != blind_index("owner", "individual")):
            raise HTTPException(409, "Protected journal event or blind index integrity mismatch")
        counts[kind] += 1
        month = posted.isoformat()[:7]
        monthly[month]["event_count"] += 1
        if source.startswith("legacy-m1:"):
            mirrored += 1
        if kind == "income" and direction == "credit":
            recorded_income += amount
            monthly[month]["observed_receipts_minor"] += amount
        elif kind == "expense" and direction == "debit":
            recorded_expenses += amount
            monthly[month]["observed_spending_minor"] += amount
        else:
            ambiguous += 1  # transfers/debt/investments/withholding are not P&L.
    months = [f"{y:04d}-{m:02d}" for y,m in
              ((tax_year-1, m) for m in range(7,13))] + [f"{tax_year:04d}-{m:02d}" for m in range(1,7)]
    missing_months = [month for month in months if month not in monthly]
    return {"tax_year":tax_year, "source_scope":"PRIVATE_EVENT_JOURNAL_ONLY",
            "synthetic_only":True, "event_count":len(rows), "legacy_mirror_count":mirrored,
            "counts_by_event_kind":dict(sorted(counts.items())),
            "monthly_observations": [{"month":month, **monthly[month]} for month in months],
            "months_without_observations": missing_months,
            "observed_labeled_income_credits_minor":recorded_income,
            "observed_labeled_expense_debits_minor":recorded_expenses,
            "observed_labeled_difference_minor":recorded_income-recorded_expenses,
            "other_or_nonoperating_event_count":ambiguous,
            "coverage_verified":False, "classification_verified":False,
            "tax_due_minor":None,"net_worth_minor":None,
            "investment_profit_minor":None,"legal_tax_savings_minor":None,
            "recommendations": [
                _insight("COMPLETE_SOURCE_COVERAGE", "data_quality", "high",
                    "Recorded private-event observations do not certify complete months, accounts or income heads.",
                    "Review statements, cash, brokerage, invoices, transfers, withheld tax and previous FBR filings."),
                _insight("RECONCILE_WEALTH", "wealth", "review",
                    "Asset, loan and cash valuations are not independently reconciled to the private-event journal.",
                    "Reconcile liabilities, cash-in-hand, investments and opening/closing wealth with underlying evidence."),
            ],
            "warning":"Only currently stored synthetic private events are included. Does not include the old source ledger or establish real cashflow, taxes, personal CFO recommendations or investment suitability."}