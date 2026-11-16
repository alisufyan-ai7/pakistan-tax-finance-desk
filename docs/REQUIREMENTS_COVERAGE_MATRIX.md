# Owner requirements coverage and remaining gates — 2026-11-16

The application is for the owner only at present, with optional later productization; use GitHub as the source of truth. **Product Plan v2 (2026-11-16):** [The formal accountant-ready product plan](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md) adds product-level acceptance for ongoing statement-led bookkeeping, workbook/source diagnostics, tax-withholding reconciliation and a working accountant package. Existing partial technical foundations remain partial; these new workflows are **not built**.
 **No real personal records may be uploaded to the public repository or the synthetic prototype.** This matrix is an execution checklist; a checked engineering primitive is NOT synonymous with an end-to-end user-ready feature.

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

## Added: draft-accountant and private source-review requirements (2026-11-16)

| Requirement | Status | Implementation acceptance |
| --- | --- | --- |
| Private bank PDF unlock with ephemeral per-document passwords | **BLOCKED (G1–G3)** | No saved/logged password; never ask for login/PIN/OTP; synthetic encrypted-PDF tests, sandboxed conversion, encrypted originals |
| Multi-bank statement format detection, coverage and running balance | **PARTIAL synthetic / REAL BLOCKED** | Versioned adapters, XLS-vs-error-stub validation, account×period holes, page carry-forward, matched transfer sources and no duplicate import |
| Accountant working paper **DRAFT/REVIEWED/APPROVED**, separate from IRIS **FILED** | **PLANNED** | Workbook sheet/formula dependencies and sources, field confirmation, imported versions, final FBR acknowledgment provenance/revision |
| Filed wealth-to-next-year opening reconciliation | **PARTIAL synthetic** | Missing/nonbank assets and source revision evidence create review exceptions; draft mismatches not treated as legal filing errors |
| Third-party transfers, loans, property, investments, withholding review | **PARTIAL / source integration blocked** | Evidence-linked classification queue, owner/accountant answers and immutable audit; unsupported amounts excluded from certified tax |
| Secure communication/explanation queue | **PLANNED** | Private correspondence attachments are not bank/FBR evidence; owner approval, accountant collaboration optionally later; screenshots do not prove voice-message content |

See [`ACCOUNTANT_WORKING_PAPER_AND_EVIDENCE_WORKFLOW.md`](ACCOUNTANT_WORKING_PAPER_AND_EVIDENCE_WORKFLOW.md), [Issue #30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30). No authentic personal data is used in CI or committed; current real-data app remains disabled.

## v2 coverage — source-led accountant-ready features (2026-11-16)

| New or sharpened product requirement | Implementation as currently verified | State / gate |
| --- | --- | --- |
| Reliable intake of password-protected PDF, CSV, XLSX and fake legacy XLS exports by actual content signature | M2s synthetic CSV/XLSX preflight PR #32; synthetic text-PDF preview; no safe genuine encrypted-PDF intake | **Partial synthetic; real G1–G3 BLOCKED** |
| Multi-bank fiscal-year coverage, page/source-row original linkage, duplicate/replayed batch and balance carry-forward | M1 synthetic normalized import, overlap and balance checks, per-year coverage | **Partial**; real multi-layout and multi-year owner acceptance G3 |
| Independent accountant-workbook **draft diagnostics**: formula graph, broken refs, cached formula values, missing investment/wealth tabs, read-only comparison with financial ledger | None end-to-end | **PLANNED**; [#30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30) |
| Distinct draft, accountant-accepted, owner-approved and **officially acknowledged filed** income/wealth versions | Synthetic historical filing model and continuity preview | **Partial foundation**; real source versions + FBR acknowledgement G3/G4 |
| Tax withholding line evidence: unclaimed vs verified adjustable vs final/duplicate vs unknown | Source-indexed synthetic candidate opportunities only | **PLANNED COMPLETE ENGINE**; [#5](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/5) |
| Evidence-linked review inbox for transfers, uncertain credits, loans, investments, asset purchases and tax treatment | Synthetic classification/weak-overlap and reviewed financial link components | **Partial**; owner/accountant decision workflow not implemented |
| Accountant question, requested evidence, owner answer, resolution and exportable review working pack | No secure end-to-end service; requirements existing in accountant workflow spec | **PLANNED**; [#30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30) |
| Automatic cumulative income/expense/tax/wealth recomputation as irregular statements arrive | Synthetic totals and narrow demonstration salary component | **NOT verified as real tax or full wealth**; G4/G5 |
| True personal CFO financial planning (cash reserves, loans, goals, investments, savings/spend anomalies) with evidence and coverage-aware advice | Synthetic hypothetical CFO engine and investment FIFO primitive | **Partial synthetic**; G5 owner UX |

**Primary user value / definition of done:** Owner can securely upload statements, resolve a manageable evidence queue, see documented year-by-year financial and **legally validated** tax/wealth positions, and export an accountant-ready review package **without re-creating separate annual worksheets**. The accountant remains free to inspect/review and the owner approves filing. No guessed refunds, capital gains, net worth, source account ownership, expired deadlines or workbook-final statuses.

## G1-a/b tested security primitives — 2026-11-16

| Security expectation | Verified progress | Still outstanding |
| --- | --- | --- |
| Encrypted operational financial storage | G1-a [PR #34](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/34): authenticated synthetic operational encrypted bank-source batches, HMAC identity, key-loss detection; 205 tests + PG18 PASS | **Only a separate bank source subset.** Old active M1 bank/loan/cash monetary/date/relationship fields plaintext, no complete typed protected canonical ledger or app switch |
| Recoverable PostgreSQL financial data | G1-b [PR #35](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/35): encrypted synthetic full known-table data snapshot, independently migrated blank destination, verified all-table byte parity, transactional rollback and wrong-key checks; 209 tests + PG18 PASS | **Not production/offsite/PITR**, restored legacy SQL still plaintext; key rotation, live database cutover, recovery drill, full canonical migration and data retention policy pending |

**Blocking:** G1 overall is **not done**. No authenticated actual personal bank/FBR files until G1+G2+G3. Next P0 tracked by [G1-c Issue #21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21). The owner remains responsible only for later private infrastructure/real-data acceptance, not synthetic code development.

## Parallel synthetic execution coverage checkpoint (2026-11-16)

- [PR #38](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/38): six explicit **synthetic-only** versioned bank/IRIS layout contracts, format and declared kind gating; actual Pakistani bank/FBR acceptance **NOT implemented**.
- [PR #39](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/39): safe **synthetic-only DRAFT** XLSX cached formula diagnostic, no recalculation/FILED verification or accountant review queue yet.
- [PR #40](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/40): synthetic offline backup-first encrypted PostgreSQL **restored candidate mirror**, full row authentication and transactional rollback, no live canonical accounting source switch, legacy plaintext remains on restored candidate.
- [PR #41 exact-head CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43851527422) **253 pytest + PG18 success** proves combined synthetic regressions. G1 live encryption/cutover, G2 deployment and G3 actual formats **BLOCKED**, G4/FBR complete tax and G5 owner-first CFO **NOT CERTIFIED**. Continue independent tracks as per [parallel playbook](PARALLEL_ENGINEERING_EXECUTION.md) while preserving G1–G3 real-data gates and project-only context.

## Chat 3 batch 3 coverage delta — 2026-11-16

[Verified implementation/acceptance detail](CHAT3_PARALLEL_G1_G2_G3_2026-11-16.md). G1 A6: synthetic PostgreSQL-backed encrypted double-entry journal plus neutral confidential bank-source row replay, source-bounded exact balance checks and atomic commit; covered in #76/#79 and PostgreSQL18 CI. G2 F1/F2: independent ephemeral CI-only PostgreSQL restricted-role attestation and synthetic one-time owner recovery-code primitive in #77, **not** integrated persistent owner MFA or deployed Railway role. G3 B5: digest-pinned deny-network worker invocation and strict synthetic adapter protocol in #78, **not** a runtime-vetted production sandbox or certified authentic Pakistani bank/FBR source. G4 year-effective tax and G5 private verified owner monthly pulse remain blocked. All real-data gates require private security, official provenance and source verification before approval.
