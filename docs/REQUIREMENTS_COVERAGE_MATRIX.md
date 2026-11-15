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
