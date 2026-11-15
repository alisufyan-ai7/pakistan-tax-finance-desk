# Owner requirements coverage and remaining gates — 2026-11-16

The application is for the owner only at present, with optional later productization; use GitHub as the source of truth. **No real personal records may be uploaded to the public repository or the synthetic prototype.** This matrix is an execution checklist; a checked engineering primitive is NOT synonymous with an end-to-end user-ready feature.

| Owner expectation / requirement | Current implementation | State and next acceptance gate |
| --- | --- | --- |
| Keep transaction/investment history from 2023/2024 onward | Historical TY2023+ records, immutable snapshots, reviewed source movement, protected-event store | **Partial**; real multi-year bank/broker/FBR import and true tax-year reconciliation untested |
| Occasional bank statement uploads, auto cumulative year-to-date | CSV synthetic imports, reconciliation, HMAC dedup, reviewed classifications | **Partial**; real-bank layouts/PDF sandbox, incremental cross-file completeness, app security, auto recompute pending |
| Multi-source personal salary, business, rent, investments, other income | Categories and narrow salary scenario; FBR year source registry | **Partial**; actual gross income reconciliation, business expense eligibility, separate/final/adjustable tax rules and tax credits pending |
| Lawful tax reduction and recommendation | Evidence-required source-indexed opportunity cards | **Partial**; tax-law eligibility, evidence and amounts cannot be claimed yet |
| Previous 3–4 years of filed returns/wealth | Synthetic prior filing records and continuity check | **Partial**; private FBR IRIS parser, versioned filed return reconciliation, amendments/limitations check pending |
| Loans borrowed/given; interest/markup and repayment tracking | Account-backed loan principal and markup, audited correction | **Partial**; real contracts, schedules, creditors, missed payments and end-to-end secure intake pending |
| Gifts, donations, Zakat, charitable payments | Reviewed categories, non-earnings movement distinctions, opportunity prompts | **Partial**; recipient proof, correct TY and applicable legal treatment needed |
| Cash-in-hand, bank transfers and wealth | Cash declared openings and corrections, cross-bank matching and partial observed wealth | **Partial**; complete asset inventory, money/date confidentiality, cost-lot & wealth reconciliation pending |
| Investments/crypto/gold/property/vehicle and returns | Encrypted declared asset snapshots | **Partial**; broker/NCCPL evidence, transactions, realized gains, holding cost lot, market data rights, tax determination pending |
| Adviser/CFO capabilities | M2p synthetic scenario and source-limited briefing, architecture roadmap | **Partial**; real personal suitability and consent, risk profile, obligations, insurance, goals, budget, retirement, adviser's evidence/state needed |
| Minimal owner manual work | Reviewed classifications and missingness flags | **Partial**; exception queue with auto learned rules, reminders and one-time onboarding pending |
| Privacy and secret handling | AES-GCM event/evidence storage, offline backup rehearsal, MFA groundwork | **BLOCKING**; old bank/loan/cash fields plaintext; production MFA recovery, private encryption, offsite recovery, no actual uploads yet |
| Access across devices/mobile | Prototype local UI | **Not delivered**; private deploy, responsive UX and browser acceptance pending |
| Eventual FBR IRIS income return/wealth export | Synthetic historic records and source index | **Not delivered**; deterministic mixed-income calculation, source completeness, FBR format and controlled manual filing pending |
| Future multi-user SaaS, accountants and households | Modular monolith/ownership concept + forward-looking contracts | **Design only**; strong tenant+entity isolation, regional laws, subscriptions, RBAC, lawful consent/deletion/export needed before public product |
| Performance, resilience and scale | PostgreSQL migration CI, bounded scanning, deterministic pure modules | **Partial**; large-fixture load tests, query indexes, jobs, read projections, observability, encryption key rotation and backpressure pending |

## Ordered, owner-independent engineering backlog

**P0 — complete real-data safeguards:** legacy field encryption / safe migration and active projection switch with rollback; tenant/owner scope architecture; key & backup disaster recovery; secure isolated document parsing and test coverage; product-grade auth and secure deployment tests. No bypass to `APP_DATA_MODE=real`.

**P1 — personal finance completeness:** genuine approved bank/FBR/broker adapters once safe, cross-statement coverage, source versioning, investment lots, obligations/recurring bills, cash-flow and wealth reconciliation, entity and FX boundaries. Build synthetic fixtures in advance of owner documents.

**P2 — tax/advisory correctness:** source-reviewed and effective TY2023+ salary/non-salary heads, tax withheld/final/adjustable, expenses/credits/Zakat/donation validation, what-if tax strategies and individual vs company treatment, legal review and exact golden vectors, filing readiness and exports, human approval.

**P3 — the full personal CFO UX:** financial briefing + budgets, liquidity alerts, goals, insurance coverage, debt decisions, investment suitability/concentration, scenario comparisons, recurring reminders, periodic personalized review, mobile apps if justified.

**Future product:** tenant-isolation redesign, accountant collaboration under invitation, commercial tax/advice/privacy review, regional tax jurisdiction plugins, scalable background processing, billing and market-data permissions. **Do not prematurely require these for the private owner rollout.**

## Definition of done

All domains must demonstrate provenance, reconciliation, unknown-vs-zero semantics, safe corrections, deterministic tests, security/permission acceptance, meaningful UI and usable exports where relevant. A future CFO recommendation must cite its evidence and assumptions, offer human-confirmable actions, avoid autonomous investment/tax moves and never assert guaranteed savings.
## M2q progress update — 2026-11-16

- The **investments/crypto/gold/property** row remains **PARTIAL**, not complete. Added an independently tested synthetic FIFO cost-lot pure engine (opening 2023/prior inventory, buys/sells, fees, partial quantities and year-grouped realized accounting results), [PR #24](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/24), [144-test CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43757173920). This does NOT import brokers/NCCPL or certify taxable gain; no account-bank-asset integration or complete wealth calculation yet.
- The **privacy and real-data** row remains **BLOCKING** because older bank/loan/cash metadata remain plaintext; adding private event and cost-lot simulators has not closed that gate.

## Added requirements from external budgeting research — 2026-11-16

| New requested/derived capability | Status as of this update | Evidence and acceptance / next step |
| --- | --- | --- |
| Recurring bills and subscriptions with upcoming due estimates | **PLANNED, NOT IMPLEMENTED** | Build synthetic reviewed-merchant cadence model; annualize only observed periods; missing statement coverage must lower confidence or return unknown. [Issue #25](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/25). |
| Duplicate services, rising merchant costs, and category leakage | **PLANNED** | Source-linked observations, account/legal-entity ownership, rule/version provenance, review of essentials vs discretionary. Savings are hypothesis only until verified. |
| Household/utility/telecom invoice explainer | **PLANNED after document security** | Real private PDFs sandboxed; date/amount/fee/withholding parsed with confidence and linked to reviewed bank payments, never invent tax credit. |
| Natural-language personal CFO household-spending questions | **PARTIAL FOUNDATION ONLY** | M2p synthetic planning/briefing exists; real source grounded queries/approval still not built. |
| Optional shopping, meal plan and administrative assistance | **IDEA / OPTIONAL FUTURE** | Explicit opt-in, Pakistan price provenance and privacy controls, no harm to core CFO/tax scope. |
| Cross-chat GitHub source-of-truth handoff | **DOCUMENTED STANDING RULE** | Root `AGENTS.md`, `docs/CHAT_CONTINUITY_PROTOCOL.md`, `docs/PROJECT_DECISIONS_AND_SCOPE.md` require agents to read current GitHub and commit all material decisions/CI/next tasks before ending or chat cap. |

The newspaper [source assessment](RESEARCH_AI_HOUSEHOLD_BUDGETING_2026-11-16.md) is an idea input, **not evidence of realized AI savings, local market demand or the completion of these features**. Core original requirements and P0 financial privacy remain higher priority.

## M2r and release-readiness coverage — 2026-11-16

- **Privacy:** PARTIAL (not done). M2r sealed-only archive contains no raw financial amount/date/linkage SQL fields, backed by independent encrypted source recovery, [PR #27](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/27) and [153-test CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43761634183). Active legacy source and candidate **still plaintext**; no real upload authority. Gate G1 still BLOCKED.
- **Private deployment:** BLOCKED. Current local-only host/client restrictions are intentional; a remote proxy deployment would fail or require a reviewed authorization design, not a trivial port change. Gate G2 [Issue #28](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/28).
- **Genuine bank/IRIS parsing:** BLOCKED. Synthetic fixed PDFs only; no authenticated real source layout certified. Gate G3 [Issue #29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29).
- **Owner completion outlook:** tracked by [G0–G6 objectively tested release criteria](DELIVERY_GATES_AND_RELEASE_READINESS.md), not synthetic test-count-based percentage or ungrounded promised date. Personal CFO/wealth/tax MVP requires verified G1–G5.
