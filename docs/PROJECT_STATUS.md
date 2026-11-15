> **Latest owner policy (2026-11-16):** Every project conversation must leave a self-contained, verified GitHub handoff; a successor chat must read current `main` and proceed without the owner re-explaining decisions. [Mandatory protocol](CHAT_CONTINUITY_PROTOCOL.md) · [Owner scope/decisions](PROJECT_DECISIONS_AND_SCOPE.md) · [Daily Mail article assessment](RESEARCH_AI_HOUSEHOLD_BUDGETING_2026-11-16.md). This is a documentation/roadmap change **only**; it does not complete new spending/subscription functionality.

# Project status — personal CFO and Pakistan Tax & Wealth Desk

**Authoritative engineering checkpoint: 2026-11-16.** Read [AGENT_START_HERE](../AGENT_START_HERE.md), [current handoff](CURRENT_HANDOFF.md), [CFO platform architecture](CFO_PLATFORM_ARCHITECTURE.md), and [requirements coverage matrix](REQUIREMENTS_COVERAGE_MATRIX.md). This is the latest status index; historical handoff sections remain useful evidence but may describe superseded limitations.

## Vision / operating mode

**One private owner for now.** An extensible modular personal CFO and adviser: year-by-year Pakistan tax and FBR reconciliation; multiple banks; mixed salary/business/rent/investment income; expenses, gifts, zakat, donations, loans, cash, wealth and investments; then budgets, scenarios, reserves, portfolio risk, goals, obligations and recommendations. Source of truth = this GitHub repository. User's intermittent statement uploads should be the normal recurring input; other evidence and one-time corrections only as required. Optional later multiuser product **must not** impose complexity on this personal first release.

### Actual verified code

| Module | What was completed | Important limitation |
| --- | --- | --- |
| M1–M2l | Synthetic bank import, classification and dedup; loans/interest, own transfers and audit corrections; cash opening/reconciliation; registered wealth components, historical filed synthetic FBR records and assets; HMAC dedup; synthetic PDF previews; year-indexed source rules, narrow salary component | No actual document adapters certified; old financial numeric/date metadata exposed in dev DB; no complete mixed-income tax due |
| M2m–M2o | New encrypted finance-event payload and separate blind indexes; read-only migration review; encrypted backup-first offline **SQLite synthetic candidate** migration with parity and rollback tests | Old money/dates/linkages still plaintext in BOTH original and candidate; no production/cutover or PostgreSQL data-copy migration |
| **M2p — PR #23** | [CFO scenario engine and encrypted-event briefing](IMPLEMENTATION_M2P_CFO_PLANNING.md); pure hypothetical cash-flow forecasts, emergency reserve, goals, explainable evidence-required warnings. [Architecture](CFO_PLATFORM_ARCHITECTURE.md) and [coverage matrix](REQUIREMENTS_COVERAGE_MATRIX.md) | Only synthetic assumptions and private journal observations; not investment picks, live cash balances, tax liability, verified advice or FBR readiness |

**Latest tested baseline:** [PR #23](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/23) merged `21419ea`. Exact-head [CI run 43756223286](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43756223286) **136 tests passed, 2 warnings**, ephemeral PostgreSQL 18 Alembic/schema PASS. The main branch must be checked independently after documentation changes; docs-only changes do not validate backend behavior.

**Important:** The repository remains intentionally PUBLIC temporarily, for source, docs and synthetic fixtures ONLY. The application still **fails closed** on `APP_DATA_MODE=real`. Do NOT upload actual statements, CNIC/NTN, passwords, historical filings, balances or unredacted evidence into GitHub or this prototype.

## Ordered owner-independent next engineering

1. **P0 security and confidentiality.** Finish full encryption of older accounts/bank/loan/cash amounts, dates, source references and identifiers or replace with a confidential canonical projection; encrypted backup and *verified restore*, key rotation, no double counting, rollback, source retention and PostgreSQL data migration. Preserve append-only corrections.
2. **P0 safe deployment and documents.** Private TLS/MFA/recovery/rate-limited app, owner authorization, tenant/entity security boundaries for future use, isolated PDF/image conversions, per-bank and per-FBR-year validated fixtures and immutable encrypted originals. Only after E2E security QA enable real-data usage by explicit owner approval.
3. **P1 comprehensive finance.** Historical imported statements and broker records from 2023/24 onward; source completeness and reconciliation, recurring expenses, contracts/bills, debt schedule, investment acquisition lots and gains, FX/source provenance, unregistered asset/liability coverage, full FBR wealth continuity.
4. **P1/P2 legal tax correctness.** Year-effective TY2023+ Pakistan statutory salary/business/rent/property/securities/other income, tax withheld/final/adjustable, zakat/donation/credits, company vs person treatment, deterministic golden vectors, human/legal review; actual IRIS return/wealth exports and amendments. Never invent tax savings/refunds.
5. **P2 personal CFO experience.** Real evidence-led briefing, budget/autocategorization with review, liquidity/runway, debt, goals, insurance and investment concentration/suitability, cash allocation and scenario comparison, alerts and mobile-first experience. No automated transfer/trade/tax filing.
6. **Future product option.** Proper tenant/legal-entity scoped encryption/indexes/access, advisors/accountants with consent, foreign jurisdictions, subscriptions, commercial tax/advice and market-data rights; retain modular monolith until scale requires separation.

## Completion boundaries

- Historical user returns **are not needed to continue synthetic implementation**; original unredacted returns go only to protected private ingestion after security acceptance.
- No real tax computation from mixed income, investment gains, market allocations or wealth-statement figure should be certified by current prototype.
- Every developed capability needs acceptance tests, provenance, missing-vs-zero, source/interpretation separation, authenticated access and honest limits.
- Keep PR count minimal, merge validated work to main, and update this file, AGENT_START_HERE and CURRENT_HANDOFF after each milestone.

## M2q continuation — 2026-11-16

The latest validated implementation now includes M2q [investment cost-lot engine](IMPLEMENTATION_M2Q_INVESTMENT_COST_LOTS.md), [PR #24](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/24), squash `bf00c08`; [CI run 43757173920](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43757173920) **144 pytest PASS**, ephemeral PostgreSQL18 migration/schema PASS. Opening 2023+ fictional investment lots, partial FIFO trade matching, fees and realized *illustrative* result across tax years are now implemented in a pure, nonpersisted module. Not FBR gains, market values, NCCPL, verified holdings or investment advice.

**Current P0 unchanged:** existing bank/loan/cash money/date/linkage SQL columns remain plaintext; no trustworthy live finance app, private deployed service, production backup/restore or verified real-bank/IRIS parser. `APP_DATA_MODE=real` must stay fail-closed. The modular personal-CFO scope and requirements coverage remain in this repository. Continue owner-independent secure source migration and document adapter groundwork before requesting actual personal financial records.
