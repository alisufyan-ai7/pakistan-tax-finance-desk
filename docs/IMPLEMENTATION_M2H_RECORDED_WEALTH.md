# M2h — Recorded-component wealth position (synthetic only)

**Scope:** Read-only demonstration of *observed*, *registered* Pakistan-rupee financial components. Not actual net worth, FBR-verified wealth, tax due, or investment advice. No real data or secret keys in public GitHub. `APP_DATA_MODE=real` remains prohibited.

## Why this exists

Bank statements, owner-declared cash, and reviewed loan allocations can be combined, but only with strong missing-evidence semantics. A bank export can omit periods; bank running balances can be missing, contradictory across exports, or stale. Cash records are owner assertions and prior balances require dated evidence. Recorded loans exclude unknown obligations. Investment, property, vehicle, gold, business equity and external assets are not yet integrated. We MUST NEVER present a partial recorded subtotal as complete net worth or an FBR-fileable wealth statement.

## Routes

- `GET /api/finance/wealth/observed?as_of=YYYY-MM-DD` returns registered individual PKR bank source observations, owner-declared cash snapshots, recorded loan receivables/liabilities, missing-evidence diagnostics and an *optional* `recorded_components_position_minor`.
- `GET /api/finance/wealth/annual?tax_year=YYYY` samples June 30 before the beginning of the fiscal year and June 30 at its end. `recorded_component_change_minor` is null unless both ends have registered component evidence; it is **not** taxable income, profit, or a finalized wealth reconciliation.

No mutation endpoints or automatic FBR filing are provided.

## Bank observations

The most recent posted transaction **on/before** the requested date is the observation anchor; no balance is extrapolated. The *last row of each distinct source document* for that date is considered. If its running balance is missing, if multiple documents disagree, or if any same-day row is excluded / has an unresolved possible overlap, the observation is **unknown**. If the observation is older than 35 days, it is shown with date and stale flag but **excluded from the partial calculation**. Stale balances cannot masquerade as current wealth.

No accounts registered is unknown, not Rs. 0. No cash account declared is unknown, not Rs. 0. Loans are taken as owner-asserted, and periods before their opening date remain unknown. Even when all **recorded components** have observations, unregistered accounts/assets and missing historical cash still make complete net worth unknown.

The only allowable derived amount is `recorded_components_position_minor` = observed PKR bank balances + declared cash + recorded lending receivables − recorded borrowed liabilities. Outputs always carry `net_worth_minor=null`, `fbr_wealth_reconciled=false` and `tax_due=null`. Potential manually declared cash receipts are explicitly marked unverified. Currency mixing and non-individual ownership are excluded from this first milestone; report scope remains limited to registered individual PKR resources.

## Synthetic regression evidence

Test cases cover zero registered components; one FY across two bank observations; cash+borrowed+lent loan arithmetic; stale bank observations; missing latest balance; contradictory same-day exports; proper same-document row order; unverified manual cash receipts; annual null instead of fabricated negative or zero wealth. Hosted CI validates unchanged PostgreSQL18 migration `0006_cash_wealth` and `alembic check` without production infrastructure.

## Remaining development

- Full account and statement-period coverage, partial uploads, bank reconciliation/undocumented transactions; rich register of property, gold, equity, vehicles, gifts and liabilities; FX rates and independently evidenced holdings.
- Encrypted amounts/date and metadata, keyed fingerprints/source hashes, secure private storage/MFA/remote backup and real bank/FBR adapters before real personal records can be accepted.
- FBR wealth statement reconciliation with actual filed previous years, linked tax-year-specific statutes and legally supportable tax minimization is not implemented. Historical user returns remain a later validation input, not an implementation blocker.