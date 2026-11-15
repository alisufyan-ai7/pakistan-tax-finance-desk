# Delivery roadmap and acceptance tests

> **Current priority and sequencing (2026-11-16):** The [v2 statement-led accountant-ready Personal CFO product plan](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md) and [objective G0–G6 release gates](DELIVERY_GATES_AND_RELEASE_READINESS.md) govern NEW implementation. The P0–P4 and M1–M2 historical sections below remain a chronological record, NOT evidence that unchecked historical checklist items are still entirely unimplemented. The most recent tested code is M2s PR #32 (178 pytest, PostgreSQL18 PASS); G1 active finance confidentiality remains BLOCKED.


## P0 — Establish repository and safe skeleton

- [x] Source repository created, admin/default branch/docs verified; temporarily PUBLIC by owner's choice for development, revert PRIVATE afterward.
- [ ] App skeleton (frontend, API, DB migrations) and basic tests/CI.
- [ ] MFA and protected storage/tested basic encrypted backup; use synthetic inputs only until verified.
- [ ] Synthetic statement upload: import, source hashes, normalized transaction, account balance reconciliation, bulk re-upload idempotency.
- [ ] Year-range selector for TY2023–TY2027 including partial-history markers.

**Acceptance:** same fixture uploaded twice yields same economic ledger, with two source records if appropriate and no duplicate postings. Reconciled account statement balances are exact to currency minor units.

## P1 — Personal finance core and historical backfill

- [ ] Multi-bank adapters, coverage calendar, month-gap report, human exception queue.
- [ ] Categorized income and personal/business expenses, entity ownership and own-account transfer detection.
- [ ] Loan taken/given, installments, due dates, receivables, interest separate from principal.
- [ ] Gifts/donations/zakat, cash ledger, acquisitions and other net-worth changes.
- [ ] Audit of corrections and versioned recomputation.

**Acceptance:** unit test with salary, loan received, loan given, principal repayments, bank transfer, donation, investment contribution and ATM withdrawal has no false income or double-spend and yields balanced wealth progression.

## P2 — Pakistan tax-year engine and current-year estimates

- [ ] Legal reference registry for TY2023–2027; verified deterministic rules and statutory tests.
- [ ] Income head, relevant withholding status, credits and special regimes.
- [ ] Actual YTD vs full-year projection vs eligible balance due, source completeness and what-if scenarios.
- [ ] FY2026 retrospective return readiness and TY2027 incremental upload updates.

**Acceptance:** tax fixtures match independently reviewed expected output for each year; no unverified guessed rates used for filing; user-visible uncertainty on missing statements.

## P3 — Investments, FBR wealth and advice

- [ ] Lot/holding reconciliations with broker exports; cost basis, realized/unrealized P/L and stale prices.
- [ ] Net worth and FBR wealth statement reconciliation with evidence flags.
- [ ] IRIS-ready output package, manual signoff, filing history records.
- [ ] Planning assistant: liquidity, debt, goals, portfolio diversification, scenario comparisons with risks, no trade execution.

**Acceptance:** every reported wealth change reconciles to evidenced movements or is surfaced as variance; every investment recommendation discloses assumptions and remains non-executing.

## P4 — Optional product exploration (not authorized build)

Audience research, data/privacy/compliance validation, multi-tenant architecture gate, finance regulation analysis; no public SaaS deployment without an explicit owner decision.

## First engineering milestone (M1)

**One working private local app**: signed-in owner uploads synthetic CSV, sees transaction rows, FY2023+ fiscal window and spending/income totals, duplicate check, reconciliation receipt and source links. It has no invented actual FBR amounts. Document all evidence and commit SHA.

## Regression suite (must include)

- Upload old FY statement after current FY; historic dependency recomputes predictably.
- Gap between monthly statements does not produce zero-income false certainty.
- Two distinct same-amount same-day transactions do not collapse.
- Two sides of transfer count once as transfer, not as income and expense.
- Borrowing and lending do not inflate earned income.
- Principal vs markup/interest on installment distinguished.
- Donation is spending, but tax relief only with documented eligible treatment.
- Investment transfer does not generate invented realized gain.
- Cash withdrawals do not automatically equal expenses.
- Different legal entities not consolidated into personal earnings.
- Income tax rule for TY2024 cannot be overwritten by a TY2027 update.
- Unreconciled wealth => filing status HOLD.
- Tax estimates retain law version, audit trace, and source-completeness flags.


## Actual M1 progress (2026-11-15)

- [x] GitHub repository established; **temporarily PUBLIC by owner's explicit decision** for development, no sensitive data; planned switch to PRIVATE later (track separately).
- [x] Local synthetic-only account/import/transaction/summary web + API and unit/integration tests.
- [x] CSV/XLSX normalized import; exact replay dedup, running balances, weak duplicate review, transaction corrections.
- [x] Historic FY selector and month-observed/missing coverage, without false completeness.
- [ ] MFA, encryption at rest, backup/restore proof, deployment readiness: **NOT DONE**.
- [ ] PostgreSQL migrations and bank-specific PDF adapters: **NOT DONE**.
- [ ] Independent full tax-year rule verification and FBR projections: **NOT DONE**.
- [ ] Product-scale Next.js frontend and advisory engine: **NOT DONE**.

M1 is a **development prototype**, not a live financial-data app. Refer to `docs/IMPLEMENTATION_M1.md` and `docs/CURRENT_HANDOFF.md`.

## New requirements prioritized 2026-11-15

- [ ] Historical filed-return import: original files (private encrypted store), TY2023–TY2026 coverage, wealth statements and income/schedule extraction, field provenance, source confidence, confirmed filed values, no silent changes.
- [ ] Historical reconciliation: prior-year closing wealth becomes next-year opening baseline; confirm assets, cash, bank balances, liabilities and tax withheld against bank/investment ledger; flag mismatches.
- [ ] Legal tax optimization advisor: sourced, year-specific opportunity cards with evidence status, legal constraints, what-if scenarios, tax effect estimate only if verified, human review, and audit log.
- [ ] Opportunity test fixtures: eligible vs ineligible donation; adjustable vs final withholding; bank-transfer vs income; personal vs legitimate business expense; refund/revision statute and timing guardrails; TY-specific provisions; multiple entity isolation; no invented savings.
- [ ] Retest/review 2023–2027 rule sources against FBR official versions and amendments, independent fixture verification; no actual tax numbers until done.
- [ ] Restore GitHub repository PRIVATE after development, as owner intends. This is distinct from immediate requirements to secure application/actual financial data; **never leak financial data to source control in any visibility state**.

## M2a tested incremental milestone (2026-11-15)

- [x] Synthetic filed return + wealth statement structured import; TY2023+; original/revision chain and exact replay idempotency.
- [x] Encrypted original **synthetic test evidence** with authenticated encryption (not an end-to-end real-data compliance claim).
- [x] Cross-tax-year opening/closing wealth discrepancy state with missing != zero.
- [x] Candidate tax-planning review flags from categorized transactions; `potential_tax_savings=null` and no unverified statutory conclusions.
- [x] Local **18 pytest tests passed** for combined M1+M2a.
- [ ] Genuine PDF historic returns, real personal numbers, MFA, Postgres/Alembic, encrypted structured DB, restore certification, audited FBR rule versions: **NOT implemented**.
- [ ] Hosted GitHub Actions green run: **NOT verified**; code-only development permitted in intentionally public repository.

User will provide prior filed returns in the future; there is **no development dependency** on seeing them before M2b security and adapter work.

## M2b / M2c implementation acceptance — 2026-11-15

- [x] Baseline Alembic migration + PostgreSQL18 CI upgrade/schema check; M2c migration `0002_owner_mfa` verified in ephemeral PostgreSQL.
- [x] Authenticated-encrypted historical *synthetic* filed-return numerical fields and encrypted synthetic SQLite/evidence archive with strict new-location restore; tamper, key mismatch and overwrite refusal.
- [x] Two synthetic bank-layout CSV adapters in API/UI; strict date/balance/dedup assertions. **No actual bank adapter yet certified.**
- [x] Owner-only synthetic MFA session gateway: scrypt password hash, TOTP, persisted anti-replay counter, hashed session tokens, Secure/HttpOnly/SameSite=Strict cookie, CSRF, logout/expiry; local and HTTPS restricted. **Not production-ready**.
- [x] PR #7 hosted CI 27 passed + PostgreSQL migration PASS; PR #8 hosted CI 31 passed + PostgreSQL migration PASS.
- [ ] MFA provisioning/recovery and rate limiting for multiworker deployment; production TLS/session audit; encrypted all-sensitive ledger values, key rotation, off-site backup/restore evidence, actual bank/FBR parsing; genuine documents remain **PROHIBITED** in synthetic app.
- [ ] Deterministic verified FBR rules for TY2023 onward and legal tax optimization estimates; monetary tax due must remain `null` until review.

## M2d-1 validation — 2026-11-15

- [x] Key-ID-bound AES-GCM encryption of synthetic account names/institutions, transaction descriptions/references/categories, audit classifications/notes, with safe ORM treatment and crypto-aware overlap checks.
- [x] Non-destructive schema upgrade `0003_ledger_text`; fail closed on legacy plaintext, no automatic backfill; offline synthetic-only atomic key rotation with dry-run.
- [x] GitHub Actions run 43709171698: **39 tests passed**; PostgreSQL 18 upgrade and Alembic schema validation PASS.
- [ ] Monetary fields, balances/dates, identifiers and keyed dedup indexes remain unencrypted; no genuine bank/FBR ingestion permitted.
- [ ] Multiworker MFA hardening, private production deployment, key recovery/rotation operations, confidential off-site backups, bank/FBR PDFs and legally reviewed TY2023+ calculations remain pending.

## M2d-2 acceptance — 2026-11-15

- [x] Read-only unique own-account transfer candidates across two individual-owned accounts within two days, preserving financial-year crossing pairs and preventing ambiguous auto-match.
- [x] Distinct reviewed non-earnings cash movement summaries for loans, cash, taxes, gifts, zakat/donations and investment contributions; no assertion of loan balances, tax eligibility or gains.
- [x] Hosted CI **44 passed, PostgreSQL18 schema PASS** ([run 43709644891](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43709644891)).
- [ ] Audited counterparty/loan principal schedules and authoritative transfer confirmation, wealth evolution and complete secure document import remain pending.

## M2e acceptance — 2026-11-15

- [x] Explicit borrowed loan liability and lent loan receivable with stated opening date/balance and encrypted counterparty/evidence notes, never automatically treated as verified.
- [x] Reviewed-bank-transaction-backed advance, principal repayment and principal/markup installment with exact paisa reconciliation, no negative end-of-day balance or double allocation.
- [x] Explicit two-sided owner-account transfer confirmations with equal amounts, different accounts, same legal owner/currency, maximum 2-day lag and cross-FBR-year query support; no tax/income statement inferred.
- [x] Source transactions locked once linked; append-only evidence events, exact replay idempotency.
- [x] Key rotation covers newly encrypted financial text and legacy test schemas.
- [x] GitHub Actions [run 43712136211](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43712136211): **55 pytest passed** and ephemeral PostgreSQL 18 Alembic `0004` + schema check PASS.
- [ ] Corrections/reversal/relinking workflow with permanent audit, full loan amortization evidence and bank-supplied contractual documents.
- [ ] Cash-in-hand and wealth provenance; confidentiality of amounts/dates/IDs; real secure document import, MFA recovery/production hosting, actual bank/FBR formats and audited TY2023+ tax rules.

## M2f validation — 2026-11-15

- [x] Authenticated, evidence-reasoned loan-allocation and own-transfer reversals leave originals and encrypted append-only correction records intact.
- [x] Partial DB unique indexes enforce one *active* assignment per source transaction, including after corrected relinking; audited inactive records remain.
- [x] Reversing an advance fails if historical principal would go negative, until dependent repayments are reversed; replayed reversals are idempotent.
- [x] Source classification locks follow active links only; actual tax due and filing readiness remain unverified.
- [x] Exact GitHub Actions [run 43713209678](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43713209678): **61 pytest passed** and PostgreSQL 18 migration `0005` / Alembic schema PASS.
- [ ] End-to-end secure real financial data acceptance, private deploy and genuine evidence processing, protected amounts/date/IDs, verified FBR tax-year rules, commercial adviser licensing as needed.

## M2g acceptance — 2026-11-15

- [x] Dated PKR cash-in-hand holding opening with positive or explicitly zero source/evidence, encrypted label and notes.
- [x] Reviewed `atm_cash` withdrawal → cash increase, reviewed `cash_deposit` → cash decrease, separate unverified manual receipt/spend; exact bank source owner/date/amount checks.
- [x] Reject bank source duplicate active assignment across cash, loans and own-account transfers; lock source categorization until reasoned correction and allow corrected reassignment.
- [x] End-of-day cash balance schedule rejects negative/backdated inconsistencies; preserved historical reversal audit and replay idempotency.
- [x] Historical FY cash opening and closing, clear missing-vs-zero semantics; no tax benefit and no FBR wealth validation claimed.
- [x] Hosted [CI 43714829408](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43714829408): **68 tests pass**, PostgreSQL18 `0006_cash_wealth` migration/check PASS.
- [ ] Complete wealth: property, gold, investments, bank closing coverage, loan receivable/liability, cash missing records, ownership/evidence and signed filing versions.
- [ ] Real files blocked by residual unencrypted financial amounts/dates/metadata, unsupported bank/FBR PDFs, production MFA/backup/security and audited statutory tax rules.

## M2h acceptance — 2026-11-15

- [x] Registered individual PKR bank/cash/lent-loan/borrowed-loan **recorded-components** position with explicit as-of date and separate reported sources.
- [x] Bank evidence rejects no rows, missing last balance, unresolved overlap, same-day export conflict and observations >35 days stale; reports provenance without invented balance.
- [x] Annual FY opening/closing recorded component movement returns NULL when either side missing; full net worth and FBR wealth reconciliation remain explicitly unknown.
- [x] Manual cash receipts flagged unverified; asset/liability categories not yet represented remain excluded with warnings, never claimed as known zero.
- [x] [GitHub Actions run 43715555529](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43715555529): **76 tests PASS**; PostgreSQL 18 Alembic schema check PASS.
- [ ] Protect numeric/date/reference metadata; implement assets beyond banks/cash/loans, independent source completeness and wealth reconciliation against secure prior actual filed FBR returns; production security.

## M2i–M2l accepted synthetic-only engineering — 2026-11-15

- [x] Keyed document and transaction HMAC fingerprints, explicit legacy scheme marker and refuse-mix; PR #15, **82 tests + PG18**.
- [x] Synthetic text PDF bank/FBR IRIS preview-only strict format/parsing/unsupported rejection; PR #16 **89 tests + PG18**. This is NOT real-bank/FBR support or sandboxed production conversion.
- [x] Encrypted immutable synthetic investments/property/vehicle/gold/crypto/other liability snapshot payloads (including valuations and dates), no unverified market values; PR #17 **95 tests + PG18**.
- [x] TY2023–2027 official FBR version registry; narrow TY2026/TY2027 salary component based on independently checked legal schedule, no full tax claim; evidence-required lawful optimization source cards; PR #18 **108 tests + PG18**.
- [ ] Protect ALL pre-existing account/transaction/loan/cash amounts, dates and associated identifiers at rest; design keyed query indexes and safe migration/backup.
- [ ] Secure actual documents through sandboxed real bank and FBR IRIS layouts with proven provenance, malware controls, MFA/private hosting and encrypted offsite restore.
- [ ] Complete holdings lot/basis/valuation source links and 2023–2027 historic income-tax engine for mixed income plus legit reductions, eligibility and proper withholding treatment, independently reviewed.
- [ ] Real filing-ready FBR return + wealth reconciliation and export, human approval; no real data acceptance or automatic filing until complete.

## M2m synthetic confidential journal acceptance — 2026-11-16

- [x] Fully authenticated-encrypted payload for new synthetic event amount/date/source/account/kind/counterparty/notes, and independent owner/year/source blind indexes only.
- [x] Strict synthetic input, owner-PKR scope, July–June TY boundary, source replay vs conflict, identical values/different source IDs distinction, key absence refusal.
- [x] Alembic `0009_private_events`, [GitHub CI 43750827782](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43750827782) **116 tests PASS, PostgreSQL 18 schema PASS**.
- [ ] Legacy financial numeric/date/metadata migration/reconciliation into protected store, including source fingerprint/index key rotation and no-double-count controls: NOT COMPLETE.
- [ ] Private production MFA/key management, real-doc parser sandbox, secure offsite restore and verified FBR tax engine: NOT COMPLETE. `APP_DATA_MODE=real` must stay disabled.

## M2n synthetic migration-preflight acceptance (2026-11-16)

- [x] Read-only reviewed bank-source eligibility preview and stable purpose-separated HMAC source identity; fiscal-year windows and missing evidence never interpreted as zero.
- [x] Separate statuses for excluded, unreviewed, unresolved overlap, unsupported and conflicting mirror; immutable original source remains authoritative.
- [x] Optional encrypted debit/credit direction in M2m payload, canonical replay compatibility for pre-M2n default.
- [x] Exact-head [CI 43751406602](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43751406602) **121 tests passed**, ephemeral PostgreSQL18 migration/schema check PASS.
- [ ] Full, audited and recoverable migration of existing plaintext numeric/date/bank/loan/cash relationships into an encrypted query model; no record migration has occurred.
- [ ] Production secure private app/MFA/keys/backups, isolated real-document parsers and complete year-effective FBR tax computation; still blocked.

## M2o offline synthetic candidate migration acceptance (2026-11-16)

- [x] Explicit, never automatic, strictly synthetic offline SQLite migration into NEW restored candidate; original ledger stays authoritative and unchanged.
- [x] Encrypted SQLite+evidence recovery backup created and independently restored before all writes; protected against reused keys, bad paths, partial/unreviewed source, unresolved overlap and source conflicts.
- [x] Transactional encrypted source mirror creation with stable HMAC source refs; full scanned count and year/account debit-credit parity, committed ciphertext integrity, original-source HMAC unchanged.
- [x] Injected mid-batch failure removes candidate and preserves original+encrypted backup; optional 0600 redacted audit receipt; no double count or tax claim.
- [x] [CI run 43754350890](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43754350890): **129 pytest passed**, PostgreSQL18 **schema migration** check PASS (not PostgreSQL data-copy migration).
- [ ] Encrypt/cut over remaining original bank/cash/loan amounts, dates, balances and relationships; dedicated Postgres backup/restore and schema migration work; genuine private app and FBR legal tax readiness. Source remains plaintext and real data prohibited.

## M2p — extensible CFO planning and requirements completeness (2026-11-16)

- [x] Domain boundary/ownership/tenant-ready architecture covering tax, personal finance, household/business, investments/loans/cash/assets, insurance, wealth/retirement/goals, financial scenarios and evidence-based advice without premature microservices.
- [x] Versioned pure synthetic CFO scenario (income/expense/loan/tax-reserve/investment flows, one-off/recurring and goals) with integer paisa, 1–60 month bounds, reserve gap, negative liquidity, missing-essential-flow detection, hypothetical insights and null tax/savings.
- [x] Protected-journal-only CFO briefing with July–June gaps, separate nonoperating flows, validated HMAC source indexes, bound full scan, no legacy double count and honest owner/source completeness gaps.
- [x] Requirements coverage matrix marks every owner goal as done/partial/blocked with acceptance gates (not a claim of end-to-end delivery).
- [x] [CI run 43756223286](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43756223286) **136 tests PASS**, PostgreSQL 18 schema no-drift PASS.
- [ ] Complete real-data security + private encrypted old bank/loan/cash schema, real PDF/bank/FBR/broker adapter acceptance, full tax/wealth/investment/obligation reconciliation, actual CFO advisory suitability and personal usable mobile UI.

## M2q investment lot arithmetic acceptance — 2026-11-16

- [x] Pure, versioned synthetic FIFO trade calculation with optional evidence-declared preexisting opening lots (from 2023 or earlier), exact buy-cost/fee and sell-proceeds arithmetic, 8-decimal units, partial-lot cost balance preservation.
- [x] Multiasset classes, source IDs, same-day sequence, chronological opening source and July/June tax-year grouping; reject short/unsupported/malformed/future/duplicate entries.
- [x] Explicit separation of illustrated realized accounting gains from FBR-taxable gains, verified brokerage holdings, unrealized valuations and net worth. Tax due/savings remain `null`.
- [x] [CI run 43757173920](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43757173920) **144 tests passed** and ephemeral PostgreSQL18 Alembic schema PASS (no migration).
- [ ] Real broker/NCCPL evidence adapters, purchase/transfer matching to bank/asset records, corporate actions/rights/splits and FX, live holdings/market data rights, legally verified applicable investment capital-gains treatment and FBR annual reconciliation.

## Research-backed spending intelligence and continuity acceptance (2026-11-16)

- [x] Read exact user-shared Daily Mail Australia article and document which practical budget use cases it reports versus unverified anecdotal earnings/market claims. [Research note](RESEARCH_AI_HOUSEHOLD_BUDGETING_2026-11-16.md).
- [x] Add future coverage-aware subscription/recurring-bill and household expense intelligence design, with provenance, uncertainty and human action controls. [Issue #25](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/25). **No code implementation or acceptance test yet.**
- [x] Write **mandatory project-wide GitHub continuity rule** at root `AGENTS.md`, `docs/CHAT_CONTINUITY_PROTOCOL.md`, `docs/PROJECT_DECISIONS_AND_SCOPE.md`, and surface it in agent-start, status, handoff and README.
- [ ] Implement deterministic synthetic recurring cost detection only with reviewed ledger inputs and explicit coverage-gap handling, after risk-relevant P0 security scheduling.
- [ ] Actual Pakistani bank/FBR PDF integration, complete privacy and real finance ingestion, registered financial advice/tax/wealth legal controls, and genuine household bill extraction remain pending.

## M2r — full-table encrypted-only synthetic archive (2026-11-16)

- [x] Explicit offline synthetic SQLite source export, independent encrypted backup and restore, full recognized SQL table/row inventory and source HMAC parity, bounded values and row counts, no source modifications.
- [x] Sealed-only database with no old plaintext account/loan/cash/FBR amount/date/linkage fields and just two archive tables, authenticated AES-GCM row/manifest encryption plus blind HMAC row IDs.
- [x] In-memory recovery/FK verification and reject unknown source table, tampering, missing row, reused or invalid key, real mode, output overwrite, injected failure; 0600 archive + receipt, redacted audit.
- [x] Exact-head GitHub [CI 43761634183](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43761634183) **153 tests passed**, PostgreSQL18 Alembic check PASS (NO PostgreSQL data-copy test).
- [ ] **Production blocking**: active legacy DB still plaintext; no authoritative encrypted read/write model, private web access/MFA/recovery, encrypted source PDF vault, actual bank and IRIS adapters, or complete mixed-income tax. Refer to [release gates](DELIVERY_GATES_AND_RELEASE_READINESS.md).

## Formal v2 delivery order — accountant-ready owner MVP (2026-11-16)

| Priority | Next slice | Technical contract and acceptance | Dependency |
| --- | --- | --- | --- |
| **P0 / G1** | Active encrypted canonical finance ledger | Confidential bank/loan/cash/asset numbers, dates, links and indexes; PostgreSQL source migration parity/no-double-count, sealed backup + independent restore, reversible rollout | Owner-independent synthetic code; [#21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21) |
| **P0 / G2 + G3** | Protected owner app + real-evidence ingress | MFA/TLS/recovery/secrets and sandbox, encrypted originals and safe document signature; synthetic PDF/CSV/XLSX/FBR adapters first, later approved private real-layout acceptance | Host/real evidence later, not needed for synthetic planning; [#28](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/28), [#29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29) |
| **P1** | Historical and incremental statement-led reconciliation | Account×period gaps, opening/closing and per-row parity, own-transfers, reviewed income/expense/loans/investment/property/cash, immutable corrections. Replayed files no duplicate events; unknown months not zero | G1 for actual data; synthetic domain code can proceed in parallel |
| **P1** | Accountant Workspace and evidence exception queue | Draft multi-sheet XLSX formula/source-cell diagnostics and versions; question → evidence → reviewed → approved history; private safe PDF/password handling, clear distinction between draft/approved/acknowledged filed; accountant-ready draft exports | [#30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30); no automatic workbook mutation or submission |
| **P1 / G4** | Full mixed-income FBR tax + annual wealth bridge | Verified TY2023+ statutory golden vectors, adjustable/final WHT, filed-vs-draft, investment/wealth/loan reconciliation, evidence-required legal savings, conditional due/refund; accountant-ready FBR working pack | [#5](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/5); legal source review |
| **P2 / G5** | Personal CFO dashboard and end-to-end owner experience | Mobile-first upload→review→tax/wealth dashboard→reconciling pack, with goals, liquidity, spending intelligence, subscriptions, loans, investments and advisory explanations | No commercial/public launch without private browser/restore acceptance |
| **Future G6** | Optional family/accountant/SaaS version | Only explicit authorization; permissions, tenant/entity boundaries and relevant regulatory review | Do not delay private owner version |

**Synthetic regression requirements:** Use the [v2 20-scenario acceptance matrix](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md#6-acceptance-and-adversarial-scenarios-synthetic-only-during-development). Tests cover fake/unsafe documents, stale formula caches, historical wealth discontinuity, unknown incoming payments, duplicates, transfers, income-vs-principal, withholding, versioned drafts vs filed originals, complete vs partial coverage, deterministic law-year recalculation, privacy/leak and backup restore. Never substitute a spreadsheet or previous assistant claim for source-proven bank/FBR facts.

**No change to security release requirements:** code planning is owner-independent; `APP_DATA_MODE=real` remains disabled until approved G1–G3 security acceptance. The owner expects accountant documents to remain provisional until explicitly finalized; no deadline reminders or guessed legal extension checks needed as part of this feature work.
