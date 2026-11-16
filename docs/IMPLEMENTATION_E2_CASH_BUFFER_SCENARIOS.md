# E2 — cautious cash-buffer what-if scenarios, synthetic only

Part of [CFO recurring/planning Issue #25](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/25) and [owner MVP blueprint](OWNER_MVP_COMPLETION_BLUEPRINT_2026-11-16.md).

`backend/app/cash_buffer_scenarios.py` models explicit hypothetical monthly cash flows, an opening balance asserted verified **in a fictional fixture** and an essential-spend reserve target in integer minor units. It produces only labelled scenario closing balances/shortfalls, never measured bank balances, tax due, realized savings, investment returns or payment instructions. Opening amount missing/unverified => all balances/shortfalls null, not zero. Incomplete/unsupported account-month coverage remains prominently flagged even if a fictional what-if projection exists. Strict horizon/duplicate assumption/type/range checks and real-mode refusal.

Future: independently authenticated G1 covered cash/bank balances, verified forecast provenance/assumptions, debt and goal projections, private dashboard UI. This is a pure model, no database, API, external service, transactions or genuine financial records.
