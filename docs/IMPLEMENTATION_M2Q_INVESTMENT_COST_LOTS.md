# M2q — source-aware investment cost-lot illustration (synthetic only)

## Why

Investment holdings may date back to 2023 or earlier, while available bank statements may begin later. A proper CFO system must distinguish **cash contributed**, **open units/holdings**, **purchase cost**, **sale proceeds**, **fees**, **realized arithmetic gain/loss** and **FBR-taxable gain**. They must not be equated or double-counted with asset snapshots, bank cash withdrawals, dividends or investment income. FBR capital-gains treatment can vary by source, asset class, acquisition date and statute.

## Implementation

A new pure module `backend/app/investment_lots.py` with an authenticated `POST /api/finance/investments/lot-scenario` route. Input requires `synthetic_fixture=true`, PKR and explicit investment source references. Optional **opening lots** with acquired date, units and documented cost permit a scenario to include investments before the first available trade/bank statement. Subsequent buy/sell events have asset identity/class, trade date, per-day ordering, original source ID, 8-decimal precision quantity, paisa-per-unit price and fees. The model supports equities, mutual funds, cryptocurrency, gold and generic traded assets.

The engine matches sells **FIFO for accounting illustration only**, maintains cost (fees included), subtracts sell fees from proceeds, prorates partial-cost consumption with exact final-lot cleanup and rejects short/negative holdings or sales beyond supplied evidence. Events are deterministic across separate assets and tax-year July/June boundaries. Output includes outstanding units, remaining FIFO cost, fictional realized arithmetic P&L and aggregated year. All output explicitly states `taxable_capital_gains_minor=null`, `tax_due_minor=null`, `market_value_minor=null`, `fbr_tax_method_approved=false`, `historical_holdings_completeness_verified=false`.

**No persistence, broker connectivity, real market prices, stock splits, rights issues, FX, tax credit, realized withholding, loss carryforward or tax filing is implemented here.** No source data is copied into real financial stores and no personal investments are inferred. The inputs are hypothetical, but the pure engine is a reusable domain primitive for a future evidence-backed cost-lot importer.

## Security and scale

Strict type validation, bounded maximum of 100 opening lots and 500 trades, unique source refs and deterministic same-day ordering; no current private user data. Future real holdings require instrument/exchange identifiers, legal ownership, currencies+FX/date/source, corporate actions and acquisition-lot provenance plus NCCPL/broker reports as applicable. A future calculation service should keep per-account holdings separate and use scoped indexes; never store real client investment records in the public repository or in this synthetic application. Avoid microservices until load requires them.

## Regression checks

- Opening 2023 lot + subsequent partial sell consumes FIFO cost and leaves remaining cost precisely.
- Fractional crypto units and fee rounding conserve book cost after the final sale.
- Multi-asset independence, as-of date and July/June synthetic realized P&L grouping.
- Reject sale exceeding supplied lots, ambiguous same-day order, repeated source ref, class mismatch, future/opening-lot dates, invalid quantity precision and wrong currency.
- Owner-authenticated API, all figures not certified FBR capital gains or investment advice.

Run GitHub Actions all pytest + PostgreSQL18 schema/no-drift CI; this milestone changes **no database schema**. Track next steps in `docs/PROJECT_STATUS.md`, `docs/REQUIREMENTS_COVERAGE_MATRIX.md` and `docs/CFO_PLATFORM_ARCHITECTURE.md`.