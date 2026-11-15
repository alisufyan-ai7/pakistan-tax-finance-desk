# M2p — modular CFO planning and private-journal briefing (synthetic only)

## Scope implemented

New `backend/app/cfo_planning.py` and FastAPI routes:

- `POST /api/finance/advisor/scenarios`: deterministic, bounded, *explicitly synthetic* scenario: starting liquid cash, modeled essential monthly outgoings, target emergency reserve, up to 100 configurable recurring/one-off cash-flow rules over 1–60 months and up to 12 financial goals. Integer paisa calculations. Monthly breakdown, negative liquidity risk, target funding gaps, annotated rule IDs, evidence-required insights. Separate income/expense/goal domains extensible without new per-use-case tables. No access to actual bank or tax values.
- `GET /api/finance/advisor/briefing?tax_year=YYYY`: encrypted *private-event-journal-only* overview of observed event kinds, recorded income credit/expense debit observations, nonoperating events, July–June monthly events and missing observation months. It checks HMAC owner/year/source, decrypts authenticated payloads and refuses to return partial totals when >20k events. Legacy source summaries are NOT combined, preventing a duplicated financial picture. Outputs `tax_due_minor=null`, `net_worth_minor=null`, `coverage_verified=false`, advice status hypothetical/unverified.

**Not added:** account/tenant permissions beyond existing single-owner localhost auth; market prices, interest forecasts, tax liabilities, asset allocations, personalized stock purchases, legal/FBR determinations or autonomous payments. `APP_DATA_MODE=real` remains disabled. Rule names and output version are explicit to make future upgrades auditable.

## Domain-wide safeguards

- Financial scenarios take explicitly supplied assumptions. Zero essential cost does not imply verified free living; emergency coverage is unknown. All future values are hypothetical projections without inflation, rate changes, illness, taxes or investment returns.
- One-off investment contributions are **outflows**, not fees/returns/savings. Negative projected balance triggers shortfall review. No proactive trade suggestion.
- Only events from the separate encrypted journal are counted in CFO observed summaries. M2o legacy mirrors are included *once in that journal*, not merged with the old source-ledger metrics. Any missing month means **unknown source coverage**, never assumed zero.
- All advisory items include code, domain, priority, assumption/evidence status, a next owner-review step and `potential_tax_savings_minor=null`. Additional source completeness, investment suitability and final vs adjustable withholding are required before real planning.

## Tests / merge criteria

Test evidence: monthly cashflow recurrence, precise goal funding after reserve, one-time investment-induced shortfall, typed/invalid/duplicate scenario inputs, explicit nonoperating event exclusions, zero-event coverage gaps, unauthenticated access rejected. Exact-HEAD GitHub Actions all pytest and ephemeral PostgreSQL 18 schema check PASS before merge. This module changes no schema and uses no external services.

## What remains before personal CFO use

- Protect or remove old plaintext monetary/date/linkage fields via independently proven data migration and strict cutover/rollback. Provide new encrypted read-side projections with verified completeness and no double count.
- Implement real account-specific imports (bank PDFs/CSVs/XLSX, broker/NCCPL, historical IRIS return/wealth statement), time series integrity and evidence provenance.
- Full income/expense/obligation/portfolio bookkeeping, salary/business/rental/investment tax engines with legal source review, actual investment gains, insurance/debt/goal planning and verified benefit eligibility.
- Private MFA-secured application, backup/restore, key rotation, user-friendly corrections, reviewer permissions and production E2E validation.

See `docs/CFO_PLATFORM_ARCHITECTURE.md` and `docs/CURRENT_HANDOFF.md` for source of truth and the long-range extensibility contract.