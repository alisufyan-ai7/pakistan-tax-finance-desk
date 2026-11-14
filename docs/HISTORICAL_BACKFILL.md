# Historical backfill: January 2023 to present and onward

## Scope and tax-year mapping

Import from **2023-01-01** by default because investments may have started in 2023; extend backward when an acquisition, loan, tax basis, ownership or opening wealth predates 2023. For Pakistan normal year July 1–June 30:

| Tax year | Period | Availability expectation |
|---|---|---|
| TY2023 | 2022-07-01 to 2023-06-30 | Only Jan-Jun 2023 by default, unless earlier records/opening balances supplied |
| TY2024 | 2023-07-01 to 2024-06-30 | Full upload target |
| TY2025 | 2024-07-01 to 2025-06-30 | Full upload target |
| TY2026 | 2025-07-01 to 2026-06-30 | Full upload target; last completed FY as of 2026-11-15 |
| TY2027 | 2026-07-01 to 2027-06-30 | In-progress, uploads monthly or randomly |

Special tax years must be configurable rather than treated as the norm.

## Backfill sequence

1. Create private owner/tax entity/profile. Maintain an account registry: bank, opaque masked account ID, owner/legal entity, currency, opened/closed date, statement coverage.
2. Collect existing filed returns and wealth statements (if available), beginning balances for assets, brokerage and loans, acquisition dates/cost basis, and opening cash. Store confidential docs encrypted, not in Git.
3. Bulk import each bank/account year by year; duplicates across overlaps must be recognized and traced; file fingerprint identifies originals.
4. Reconcile opening/closing balances when provided, identify missing months and inaccessible bank accounts; unknown ledger balance starts unknown.
5. Match own transfers across accounts, including currency conversion and delays. Do not infer own transfer merely from amounts without supported account relationship.
6. Identify loans received/made and schedule disbursements, repayments, agreed interest/profit, waivers and defaults. Confirm ownership/proof.
7. Reconstruct initial holdings and subsequent buys/sells through broker statements when available; bank funding flows alone do not prove tax gains or current holdings.
8. Reconcile tax-year income + personal expenses + asset/liability changes, identify unresolved wealth differences, and compare previously filed declarations rather than rewriting them.
9. Lock documented historic versions after review, allow corrections via audited event and new computed snapshot (no mutation of the raw statement).

## Tax filing safety

Historical analysis does **not** mean user should revise every past return. Show potential discrepancies as REVIEW; revision rights, deadlines, notice status and supporting evidence need current-law professional review before any action.

## Coverage indicators

For each account and FY show: months in range, statement present/missing/overlap, first/last posted dates, reconciliation discrepancy, transaction count, tax-proof gaps, filing-readiness flag. A partial FY must never masquerade as complete.
