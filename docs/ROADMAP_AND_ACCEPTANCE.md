# Delivery roadmap and acceptance tests

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
