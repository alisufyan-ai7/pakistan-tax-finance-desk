"""Pure synthetic investment lot arithmetic (FIFO), NOT FBR tax certification.

Designed for future evidence-backed broker/NCCPL imports: separates trade-source
identity, FIFO cost, trade proceeds, explicit fees and missing opening holdings.
Never combines this what-if ledger with asset snapshots or bank balances.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

MAX_MINOR = 10**15
ASSET_CLASSES = {"equity", "mutual_fund", "crypto", "gold", "other_traded_asset"}


def _qty(value: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("Quantity must be a canonical decimal string")
    try:
        n = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid decimal quantity") from exc
    if not n.is_finite() or n <= 0 or n > Decimal("1000000000000") or n.as_tuple().exponent < -8:
        raise ValueError("Quantity must be positive, finite and have at most eight decimal places")
    return n


def _format_qty(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _round_minor(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class OpeningLotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_ref: str = Field(pattern=r"^[a-zA-Z0-9_-]{4,60}$")
    asset_ref: str = Field(pattern=r"^[a-zA-Z0-9_.:-]{3,80}$")
    asset_class: Literal["equity", "mutual_fund", "crypto", "gold", "other_traded_asset"]
    acquired_on: date
    quantity: str
    cost_basis_minor: StrictInt = Field(ge=0, le=MAX_MINOR)
    evidence_note: str = Field(min_length=12, max_length=300)

    @model_validator(mode="after")
    def valid(self):
        _qty(self.quantity)
        if not (date(1900, 1, 1) <= self.acquired_on <= date(2100, 12, 31)):
            raise ValueError("Opening lot acquisition date is outside supported range")
        return self


class TradeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_ref: str = Field(pattern=r"^[a-zA-Z0-9_.:-]{8,80}$")
    asset_ref: str = Field(pattern=r"^[a-zA-Z0-9_.:-]{3,80}$")
    asset_class: Literal["equity", "mutual_fund", "crypto", "gold", "other_traded_asset"]
    kind: Literal["buy", "sell"]
    executed_on: date
    sequence: StrictInt = Field(ge=0, le=1000000)
    quantity: str
    unit_price_minor: StrictInt = Field(ge=0, le=MAX_MINOR)
    fees_minor: StrictInt = Field(default=0, ge=0, le=MAX_MINOR)
    evidence_note: str = Field(min_length=12, max_length=300)

    @model_validator(mode="after")
    def valid(self):
        _qty(self.quantity)
        if not (date(2022, 7, 1) <= self.executed_on <= date(2100, 12, 31)):
            raise ValueError("Synthetic trade date outside TY2023+ range")
        if self.unit_price_minor == 0:
            raise ValueError("Trade unit price cannot be zero")
        if _round_minor(_qty(self.quantity) * Decimal(self.unit_price_minor)) > MAX_MINOR:
            raise ValueError("Trade exceeds synthetic maximum amount")
        return self


class LotScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic_fixture: Literal[True]
    currency: Literal["PKR"] = "PKR"
    as_of: date
    opening_lots: list[OpeningLotInput] = Field(default_factory=list, max_length=100)
    trades: list[TradeInput] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def valid(self):
        if not (date(2022, 7, 1) <= self.as_of <= date(2100, 12, 31)):
            raise ValueError("Valuation date outside supported range")
        if any(t.executed_on > self.as_of for t in self.trades):
            raise ValueError("A historical report cannot include future trade events")
        if any(l.acquired_on > self.as_of for l in self.opening_lots):
            raise ValueError("An opening holding cannot be acquired in the future")
        sources = [t.source_ref for t in self.trades]
        lots = [l.lot_ref for l in self.opening_lots]
        if len(sources) != len(set(sources)) or len(lots) != len(set(lots)):
            raise ValueError("Duplicate original trade or opening-lot references")
        ordering = [(t.asset_ref, t.executed_on, t.sequence) for t in self.trades]
        if len(ordering) != len(set(ordering)):
            raise ValueError("Ambiguous same-day trade ordering for a holding")
        first_trade_dates: dict[str, date] = {}
        for trade in self.trades:
            first_trade_dates[trade.asset_ref] = min(
                trade.executed_on, first_trade_dates.get(trade.asset_ref, trade.executed_on)
            )
        for opening in self.opening_lots:
            if opening.asset_ref in first_trade_dates and opening.acquired_on > first_trade_dates[opening.asset_ref]:
                raise ValueError("An opening lot must predate recorded trades for that holding")
        identities: dict[str, str] = {}
        for p in [*self.opening_lots, *self.trades]:
            prior = identities.setdefault(p.asset_ref, p.asset_class)
            if prior != p.asset_class:
                raise ValueError("Holding asset class cannot vary between source records")
        return self


@dataclass
class _Lot:
    source_ref: str
    acquired_on: date
    quantity: Decimal
    cost_minor: int


def _tax_year(on: date) -> int:
    return on.year + (1 if on.month >= 7 else 0)


def calculate_lot_scenario(payload: LotScenarioInput) -> dict:
    """FIFO lot matching with exact remaining cost preservation.

    Only the arithmetic of owner-supplied synthetic trades is returned. The
    accounting result may differ from FBR/NCCPL taxable gain treatments.
    """
    lots: dict[str, list[_Lot]] = defaultdict(list)
    asset_class: dict[str, str] = {}
    realized_by_asset: dict[str, int] = defaultdict(int)
    realized_by_year: dict[int, int] = defaultdict(int)
    fees_by_asset: dict[str, int] = defaultdict(int)
    sale_count: dict[str, int] = defaultdict(int)
    for opening in sorted(payload.opening_lots, key=lambda l: (l.acquired_on, l.lot_ref)):
        asset_class[opening.asset_ref] = opening.asset_class
        lots[opening.asset_ref].append(_Lot(opening.lot_ref, opening.acquired_on,
                                           _qty(opening.quantity), opening.cost_basis_minor))
    for trade in sorted(payload.trades, key=lambda t: (t.executed_on, t.sequence, t.source_ref)):
        asset_class[trade.asset_ref] = trade.asset_class
        quantity = _qty(trade.quantity)
        gross = _round_minor(quantity * Decimal(trade.unit_price_minor))
        fees_by_asset[trade.asset_ref] += trade.fees_minor
        if trade.kind == "buy":
            cost = gross + trade.fees_minor
            if cost > MAX_MINOR:
                raise HTTPException(422, "Synthetic purchase total exceeds calculation limit")
            lots[trade.asset_ref].append(_Lot(trade.source_ref, trade.executed_on, quantity, cost))
            continue
        # No short/negative holding and no guessing of holdings before first import.
        available = sum(l.quantity for l in lots[trade.asset_ref])
        if available < quantity:
            raise HTTPException(422, "Sale exceeds owner-supplied lots; opening/broker evidence required")
        remaining = quantity
        allocated_cost = 0
        for lot in lots[trade.asset_ref]:
            if remaining == 0:
                break
            if lot.quantity == 0:
                continue
            taken = min(lot.quantity, remaining)
            used_cost = (lot.cost_minor if taken == lot.quantity else
                         _round_minor(Decimal(lot.cost_minor) * taken / lot.quantity))
            allocated_cost += used_cost
            lot.cost_minor -= used_cost
            lot.quantity -= taken
            remaining -= taken
        if remaining:
            raise HTTPException(422, "Unmatched lot quantity")
        realized = gross - trade.fees_minor - allocated_cost
        realized_by_asset[trade.asset_ref] += realized
        realized_by_year[_tax_year(trade.executed_on)] += realized
        sale_count[trade.asset_ref] += 1
    holdings = []
    for asset_ref in sorted(asset_class):
        remaining = [lot for lot in lots[asset_ref] if lot.quantity > 0]
        qty = sum((lot.quantity for lot in remaining), Decimal(0))
        cost = sum(lot.cost_minor for lot in remaining)
        holdings.append({"asset_ref": asset_ref, "asset_class": asset_class[asset_ref],
                         "remaining_quantity": _format_qty(qty),
                         "remaining_fifo_cost_minor": cost,
                         "synthetic_realized_result_minor": realized_by_asset[asset_ref],
                         "matched_sale_count": sale_count[asset_ref],
                         "total_recorded_fees_minor": fees_by_asset[asset_ref],
                         "open_lot_count": len(remaining),
                         "market_value_minor": None,
                         "unrealized_gain_minor": None,
                         "taxable_capital_gain_minor": None,
                         "evidence_verified": False})
    return {"synthetic_only": True, "method": "FIFO_ACCOUNTING_ILLUSTRATION_V1",
            "as_of": payload.as_of.isoformat(), "currency": payload.currency,
            "holding_count": len(holdings), "holdings": holdings,
            "synthetic_realized_result_by_tax_year_minor":
                {str(year): realized_by_year[year] for year in sorted(realized_by_year)},
            "historical_holdings_completeness_verified": False,
            "cost_basis_independently_verified": False,
            "market_prices_verified": False,
            "fbr_tax_method_approved": False,
            "tax_due_minor": None,
            "taxable_capital_gains_minor": None,
            "fbr_ready": False,
            "warning": "FIFO arithmetic on fictional supplied trade/lot data only. Not verified holdings, NCCPL cost basis, taxable capital gain, tax advice, investment valuation or market recommendation."}