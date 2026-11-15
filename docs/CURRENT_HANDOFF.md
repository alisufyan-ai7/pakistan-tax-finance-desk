# Current project handoff — 2026-11-15 — M1 implementation

## Source of truth

Repository: `alisufyan-ai7/pakistan-tax-finance-desk` (**temporarily PUBLIC by explicit owner decision** for source development), default `main`. Read `AGENT_START_HERE.md` and `README.md` first; then `docs/IMPLEMENTATION_M1.md`, this handoff, `docs/SECURITY_PRIVACY.md`, `docs/IMPORT_PIPELINE.md` and `docs/ROADMAP_AND_ACCEPTANCE.md`.

## Product requirements (binding)

Private owner-only Pakistan tax and wealth management software. Historical records start January 2023 (earlier evidence permitted). Mixed salary, business, investment and other income; full ledger for loans taken and given, donations/zakat, gifts, cash, transfers, debts, holdings, expenses, tax evidence, wealth and planning. Routine input is irregular bank statement uploads. Multiple financial years, correct FBR year-specific taxes and wealth statement will be added only with legally reviewed rules and adequate evidence. Potential future SaaS is not approved scope. GitHub stores **code/documentation and synthetic fixtures only**, never real financial records.

## What was implemented in this milestone

- Local synthetic-only FastAPI browser dashboard and APIs (private local loopback Basic auth, fail closed when owner password absent).
- SQLite-backed relational financial accounts, provenance document hashes, normalized transactions, category review and audit events.
- Normalized CSV and one-sheet XLSX importer (up to 4 MiB / 5000 rows) with explicit date format, PKR integer minor units, exclusive debit/credit, running balance check, declared periods, exact file replay and strong-reference cross-file dedup.
- Weak ambiguous overlap queue with explicit confirmation/exclusion via audited corrections; never pretend ambiguous overlaps are resolved.
- FY2023+ July–June selector; income/expense/nonincome category totals and month coverage observations; tax values explicitly **unavailable**, not guessed.
- Responsive mobile-width UI, documented local run, synthetic CSV, backend CI and pytest regression tests.

## Verification

Local synthetic pytest executed: **11 tests passed** on local Python 3.13. CI must run against PR and/or main before treating the change as merged/released. No production deployment, user data access, financial tax calculations, encrypted storage, owner MFA or disaster restore has occurred. The local SQLite file is unencrypted; **DO NOT UPLOAD REAL BANK STATEMENTS**.

## Next engineering milestone (M2)

1. Establish PostgreSQL/Alembic migrations, encrypted document storage + key rotation, approved deployment and tested encrypted backup/restore; protect owner access with MFA, TLS/session/CSRF, and logging controls.
2. Add first Pakistani bank-specific PDF/CSV adapters using synthetic format fixtures; safe handling of scanned/password-protected PDFs and non-deterministic layout failure.
3. Fully model own-account transfers across accounts, loan receivables/payables and principal vs interest, gifts/donations/cash, legal entity separation and reconciliation.
4. Add a verified FBR ruleset by tax year with official sources and independently reviewed calculations; no rates or credits invented.
5. Build polished Next.js client atop stable API only after core data integrity and security gates, or preserve local UI until then.
6. Update this handoff, implementation evidence and roadmap after each milestone, keeping open PRs minimal and test gates visible.

## Operational note

Current frontend is deliberately server-rendered by FastAPI, not a deployed Next.js app. This is a pragmatic local vertical slice, not a change to the approved long-term target (Next.js + FastAPI + PostgreSQL). No bank-specific Pakistani statement format is certified. Data has to be synthetic in the current prototype.

## M1 PR validation addendum

- PR: https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/1
- Local regression suite: **11 passed** (Python 3.13, synthetic-only).
- Synthetic smoke: 5 accepted; opening and running balances verified; FY2024 summary correct; re-upload 0 accepted / 5 duplicates.
- GitHub-hosted CI run [43652595185](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43652595185) returned `failure` before any steps ran; job has `runner_id=0`, steps=[], logs unavailable. **Do not claim CI passed.** The precise infrastructure/billing cause is unconfirmed and should be investigated. This is not evidence of a failing pytest assertion.
- Production release and real bank-statement onboarding remain disallowed until security, migration, and bank-format gates are passed.

## M1 merge and immediate blocker (verified 2026-11-15)

- PR #1 **merged** to `main`, merge commit [`13480f5`](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/commit/13480f5593ceb88216abcb682f8ff36cf939b720). Synthetic import code and test suite are available on main.
- **Critical repository visibility mismatch:** GitHub API returned `visibility=public` and `private=false` after merge. Original owner requirement is PRIVATE. GitHub file connector cannot change visibility. Owner must change Settings → General → Danger Zone → Change repository visibility → Private; reverify before handling sensitive data.
- CI remains NOT GREEN: the new PR run also returned failure without executed steps, consistent with runner assignment/platform restriction. Underlying cause unverified. Local tests passed; merge was a consciously documented local-only exception, not release readiness.
- Next tasks: verify visibility private, fix Actions runner availability, then M2 security foundations before real bank statements.

## New owner decisions — 2026-11-15 (supersede earlier privacy alert)

- The owner **intentionally keeps GitHub PUBLIC during development**, stating this was to try to enable GitHub Actions. They intend to switch it to private after work is finished. Earlier language treating PUBLIC GitHub as an accidental security emergency is **superseded**. Continue development using code/docs/synthetic fixtures only. A public source repo cannot hold financial records, actual previous returns, secrets or customer documents. A hardened private *application* must handle those.
- Actions remains unverified/failed (latest previously observed runs never received runners); public status alone did not demonstrate a green workflow. Investigate separately without reclassifying public visibility as an accidental blocker.
- Owner explicitly requires **proactive LEGAL tax minimization suggestions** (tax planning, not evasion) with documented law, appropriate TY, eligibility evidence, estimated impact, constraints and human approval. Never recommend concealment, fake donations/expenses, misclassification, illegal backdating or artificial historic revisions.
- Owner will supply their **last three to four already-filed FBR income tax returns**, preferably with corresponding wealth statements and tax/withholding schedules, to establish the year-by-year filed baseline and compare against bank/investment activity from 2023 onward. The M1 synthetic-only application must NOT ingest real returns. `docs/TAX_OPTIMIZATION_AND_PRIOR_RETURNS.md` contains the future secure intake contract and optimization backlog.
- No real personal files received or processed as part of this documentation change; no tax benefit calculated or legal eligibility certified.

## Next engineering tasks after this decision

1. Keep M2 development running despite temporary public GitHub. Repair GitHub Actions separately and keep all fixtures synthetic.
2. Build secure private historical-return import and document store after encryption, MFA, recoverability and correct account segregation; include return + wealth schedules and source fields with conflict marking.
3. Build verified TY2023–TY2027 tax-rule registry and safe opportunity-detection workflow; initially show only opportunities requiring review, not computed savings from unverified law.
4. Reconcile each filed tax-year return and opening/closing wealth with normalized historical ledger; preserve immutable filed-original and amendment history; highlight unexplained differences.

## Documentation milestone verification — 2026-11-15

- [PR #4](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/4) merged on `main` (`8dc9b250ec02c4a06351d29367f0b023031a17eb`), adding `docs/TAX_OPTIMIZATION_AND_PRIOR_RETURNS.md` and recording lawful tax planning and historical filed-return intake.
- [Issue #2](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/2) now tracks GitHub Actions runner failures; public-source status is an intentional owner choice, not an accidental visibility incident.
- [Issue #3](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/3) includes secure private historic-return ingestion; [Issue #5](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/5) covers evidence-based legal optimization and historical wealth reconciliation.
- Keep real returns, statements, CNIC/NTN, account data and secrets out of GitHub and CI. Secure application importer for actual files is NOT yet built. No user tax records received in this milestone.

## Engineering continuation — M2a synthetic historical filing foundation (2026-11-15)

Owner confirmed previous income tax returns will be supplied later; **they are not a dependency for continuing development**. Proceed with synthetic fixtures and secure-by-design architecture without asking for genuine records. Public GitHub remains intentional for code/docs/synthetic data; never upload user files, identifiers, or secrets.

**Implemented on feature branch** `implementation/m2-historical-synthetic-intake-20261115`:

- `backend/app/evidence_vault.py`: AES-256-GCM encrypted synthetic evidence bytes with fresh nonce, document-context authenticated data, 0600 restrictive files, safe UUID filenames and no overwrite. Encryption key must come from environment; no key in GitHub.
- `backend/app/historical.py`, `models.HistoricalFiling`: strictly normalized synthetic income-return/wealth-statement fixtures; TY>=2023, immutable originals, idempotent replay and same-TY/kind revision chain with no silent overwrite. Structured synthetic fields currently reside in **unencrypted SQLite**.
- Read-only reconciliation endpoint compares prior TY closing wealth to current TY opening wealth, distinguishes missing from zero, and surfaces discrepancies without claiming a valid FBR wealth statement.
- Read-only tax opportunity endpoint flags potential eligible-document reviews from verified transaction categories; every candidate has **NULL savings** and **not legally verified**. No tax calculation or real deductibility is asserted.
- A synthetic-only API; **not a PDF importer, and not an approved real-file upload path**.
- Local Python 3.13 `cd backend && pytest -q`: **18 passed** (11 original plus 7 M2a tests). `compileall` passed. GitHub-hosted CI still needs independent verification.

Implementation and execution details: `docs/IMPLEMENTATION_M2_SYNTHETIC_FILINGS.md`.

**Next:** complete PostgreSQL/Alembic migrations, encrypted structured financial data strategy, owner MFA/TLS/session security, key rotation and private encrypted backup/restore. Add safe synthetic Pakistani bank/FBR layout adapters; only then can true documents be uploaded securely and their historic return values reconciled. User plans to provide 3–4 years of returns later, not in this engineering step.

## M2a merged and CI verified — 2026-11-15

- [PR #6](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/6) **MERGED** into `main`; squash merge commit `4bd7820f5fc04d941e7d9dfa42a76949350fa855`.
- GitHub Actions **success** on PR head: [run 43654581161](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43654581161) with actual assigned runner and pytest output **18 passed, 1 warning** (Python 3.12). Local Python 3.13 suite also **18 passed**. This supersedes previous pre-execution runner failures for this validated run; do not claim unrelated CI runs are fixed retroactively.
- Code: synthetic-only historical filed return/wealth statement model; encrypted test evidence vault (AES-256-GCM), revisions, exact replay dedup, prior/current TY wealth continuity and tax opportunity candidate endpoint. `docs/IMPLEMENTATION_M2_SYNTHETIC_FILINGS.md` has routes and limitations.
- **No historical personal FBR documents needed yet.** Owner expects to share 3–4 years of returns later. Do not solicit them for engineering. Real return documents MUST NOT enter current prototype or public GitHub/CI; local SQLite structured fields are unencrypted, and MFA/backups/secure private production storage do not yet exist.
- **M2b next:** PostgreSQL/Alembic migrations and encrypted structured fields, proper owner MFA/TLS secure sessions, encrypted backup+restore verification, and synthetic Pakistani bank/FBR document parsing. After these gates, enable private upload of the user's real statements/returns for historical reconciliation and verified tax-year-specific lawful tax optimization.

## Final M2a main validation (2026-11-15)

- GitHub Actions also **PASSED on `main`** after merge: [run 43654657148](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43654657148); PR [run 43654581161](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43654581161) confirmed `18 passed, 1 warning`. Earlier no-runner issue [#2](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/2) closed as resolved. Source remains intentionally public, synthetic-only. M2b security before real records remains pending.

## M2b merged & independently validated — 2026-11-15

- **PR #7 merged** to `main`, commit [`7745afb`](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/commit/7745afb12312194880779da85cc8670e2cc15a7b).
- GitHub Actions [run 43655878445](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43655878445) **PASS**: **27 pytest passed, 1 warning**, and ephemeral PostgreSQL **18** Alembic migration + `alembic check` **PASS** with `POSTGRES_18_SYNTHETIC_SCHEMA=PASS`. Duplicate PR run 43655882368 also concluded success. Earlier packaging error corrected by explicit `app` package discovery.
- Code delivered: immutable Alembic baseline; synthetic structured return fields encrypted at rest (AES-GCM), encrypted synthetic-only SQLite + evidence archive with bounded verified restore, two strict synthetic CSV bank-like import profiles in API/UI, `APP_DATA_MODE=real` fail-closed startup guard.
- Documentation: [`docs/IMPLEMENTATION_M2B.md`](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/blob/main/docs/IMPLEMENTATION_M2B.md) with instructions and exact limitations. No real bank, FBR, tax or personal data was used.
- **Important:** this is NOT production secure. Local Basic auth persists; SQLite M1 transaction descriptions and audit notes are plaintext; no complete MFA, cloud key management, remote backup, actual bank/FBR PDF adapters or certified income-tax calculations. Genuine files must NOT be uploaded.
- **Next owner-independent engineering:** MFA / browser-session groundwork, encrypted sensitive transaction fields and migrations, synthetic PDF layout adapters, robust loan/transfer accounting, 2023+ verified FBR rule reference registry and valuation-ready model. No need to request owner returns now. GitHub remains temporarily public intentionally with only synthetic content.

## M2c merged and verified (2026-11-15) — current source-of-truth milestone

- [PR #8](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/8) **MERGED**, squash merge `8cf1abc6294297aa1e43cbf102631641b03cbbc5`, after host-runner [CI run 43656607289](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43656607289) reported **31 pytest passed, 1 warning** and `POSTGRES_18_SYNTHETIC_SCHEMA=PASS`. This validates migration `0001_initial -> 0002_owner_mfa`; another PR run 43656625224 concluded success.
- `backend/app/auth_mfa.py` and API: scrypt owner password hash, RFC6238 TOTP ±1 step and persisted anti-replay counter, optional HTTPS/local-only MFA session mode, secure HttpOnly SameSite=Strict `__Host-` cookie with hashed token in DB, CSRF/Origin checks for writes, expiry and logout revocation. `frontend/login.html` exists, and local UI fetches its session-specific CSRF. Default local Basic mode remains for synthetic testing.
- This is **NOT** full production MFA: no distributed brute-force throttling, recovery enrollment, session/device management, full sensitive transaction field encryption, key rotation/remote disaster recovery or deployed TLS acceptance yet. `APP_DATA_MODE=real` continues to fail closed. Real bank and FBR return documents must not be uploaded to the public repository, logs, CI or synthetic application.
- **No owner action required now**; previous returns can arrive later for actual private-app format/reconciliation acceptance. Proceed with M2d independent work: encrypted transaction text/notes/key rotation, safe bank/FBR-format adapters and a fully reconciled loan/gift/transfer domain ledger; use synthetic fixtures. Subsequent FBR tax-year-specific laws must be verified before any tax due/optimizations are stated numerically.

## Final merged-main validation and next gate (2026-11-15)

- After M2c merge `8cf1abc6294297aa1e43cbf102631641b03cbbc5`, [GitHub Actions main run 43656708834](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43656708834) concluded **success**; PR run 43656607289 logged **31 passed, 1 warning**, and PostgreSQL 18 schema check PASS.
- [Issue #3](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/3) is the maintained M2d owner-independent engineering backlog: complete encryption/key lifecycle, production MFA hardening, robust backups, real-format adapters on synthetic layouts, full loans/transfers accounting and independently validated FBR rule engine. **Do not wait for owner tax returns to code any of these.**
- Repository is intentionally PUBLIC for code development. Current app remains local, synthetic-only, and refuses real-data mode. No unredacted bank statements or tax returns are authorized in GitHub or the app.

## M2d-1 merged — authenticated encrypted ledger text (2026-11-15)

- [PR #9](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/9) **merged into main**, squash commit `7d0ddd81384c3bec7843053baf85bc01c5da4148`.
- [GitHub Actions PR run 43709171698](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43709171698) **PASS**: `39 passed, 1 warning`, ephemeral **PostgreSQL 18** Alembic `0003_ledger_text` upgrade plus `alembic check` **PASS**, `POSTGRES_18_SYNTHETIC_SCHEMA=PASS`.
- Encrypted at rest under an external multi-key `LEDGER_FIELD_KEYS_JSON` keyring: account name/bank institution; transaction description/reference/category; audit old/new classification and review notes. Uses randomized AES-GCM ciphertext with per-column AAD, envelope version+key IDs. Added atomic synthetic-only offline key rotation, dry-run, wrong-key/tamper and pre-existing plaintext rejection tests.
- Key security caveat: **not full data-at-rest encryption**. Dates, monetary amounts, balances, stable identifiers and file hashes remain plaintext; fingerprint hashes are unsalted/non-keyed. Source data has not been processed. `APP_DATA_MODE=real` still rejects startup. Existing *synthetic* databases with plaintext ledger values require explicit backup and synthetic-data reimport after schema migration; **never silently convert or discard actual records**.
- Read [`docs/IMPLEMENTATION_M2D_ENCRYPTED_LEDGER.md`](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/blob/main/docs/IMPLEMENTATION_M2D_ENCRYPTED_LEDGER.md) for key and rotation instructions; no actual keys or bank data in this public source repository.
- Next owner-independent work: design full confidential numeric/date storage and keyed dedup indexes without breaking reconciliation; implement double-sided transfers/loans/cash and FBR-format synthetic import; harden multiworker auth, backup recovery and private deployment. User FBR returns remain **not needed** for engineering.

## M2d-2 merged — owner-independent transfer and non-earnings movement analysis (2026-11-15)

- [PR #10](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/10) **merged**, commit `14f1fbdc1db0fa0ea2f4f13a1114eb1a89d4edfa`.
- Hosted [CI run 43709644891](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43709644891) **PASS** with **44 pytest tests**, PostgreSQL 18 Alembic upgrade/check **PASS**, `POSTGRES_18_SYNTHETIC_SCHEMA=PASS`. This includes 5 new synthetic movement-analysis tests.
- Delivered `backend/app/movement_analysis.py` and read-only `GET /api/finance/movement-review?tax_year=YYYY`: one-to-one candidate matching of already reviewed individual-owned cross-account transfer debits/credits within two days, all ambiguous/single-sided transfers flagged, FY boundary-safe pairing, loan principal/cash/donation/investment/tax movement observations separate from earned income. `UNVERIFIED_TRANSFER_CANDIDATE` never constitutes a booked transfer or tax conclusion. No automatic ledger mutation, withholding claim or outstanding loan balance.
- New [`docs/IMPLEMENTATION_M2D2_MOVEMENTS.md`](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/blob/main/docs/IMPLEMENTATION_M2D2_MOVEMENTS.md) lists assumptions and tests. Current app synthetic-only. User historical FBR documents not required for this engineering task.
- **Next owner-independent priorities:** protect remaining financial amounts/dates/metadata and key-safe dedup before genuine records; create verified cash/loan counterparty and installment lifecycle model; securely sandbox bank/FBR statement/PDF adapters using synthetic formats; harden MFA and private backups; implement audited TY2023+ tax rule engine and legal opportunity review without invented savings. GitHub remains intentionally PUBLIC for source, code/docs/synthetic only. `APP_DATA_MODE=real` must remain blocked.

## M2e merged — owner-reviewed loan posting, installments and confirmed own-account transfers (2026-11-15)

- [PR #11](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/11) **merged to main** (squash commit [`d637d9a`](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/commit/d637d9a56d1a4f41c68fb3faef1dda382845a764)).
- Exact-PR-head GitHub Actions [run 43712136211](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43712136211) **PASS**: **55 pytest passed, 1 warning**, ephemeral PostgreSQL 18 `0004_finance_links` Alembic upgrade and `alembic check` **PASS** (`POSTGRES_18_SYNTHETIC_SCHEMA=PASS`).
- Added `app/financial_links.py`, loan/loan-allocation/transfer-confirmation SQLAlchemy models and Alembic revision `0004_finance_links`. Loan principal schedules distinguish borrowed liabilities and lent receivables; require explicit opening date/basis, reviewed bank transaction and exact amount allocation. Principal and markup are separate, with negative-outstanding and duplicate-source guards.
- Owner-confirmed own-account transfers need two distinct individual-owned PKR accounts, matching opposite reviewed transaction amounts and dates within two days, plus an encrypted evidence note; confirmed links are not independent bank verification or a tax conclusion. Linked source transactions are locked from reclassification; cross-year links appear in both tax years. Loan/transfer link records are append-only at this stage.
- Owner names, basis, and evidence notes encrypted via existing AES-GCM keyring; synthetic offline key rotation now handles new tables and older database subsets. See [`docs/IMPLEMENTATION_M2E_LOANS_TRANSFERS.md`](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/blob/main/docs/IMPLEMENTATION_M2E_LOANS_TRANSFERS.md).
- **Not real-data ready**: numeric amounts, dates, reference IDs and other metadata still stored unencrypted; account opening evidence remains owner-declared; no audited reversal/reassignment API, counterparty supporting uploads, bank/FBR genuine-format adapter, product-grade MFA/backup, legally certified tax computation or FBR filing. `APP_DATA_MODE=real` remains disabled; current GitHub intentionally PUBLIC with synthetic fixtures only.
- **Next owner-independent priorities:** audited correction/reversal workflow for confirmed links, comprehensive cash-in-hand/loan lifecycle reconciliation, protection of remaining sensitive numeric/date/metadata, secure private document-ingestion design and synthetic FBR/bank PDF adapters, then TY2023+ versioned official-law tax rules and opportunity certification. The owner's previous returns are **not a blocker**.

## M2f merged — audited and reversible loan/transfer links (2026-11-15)

- [PR #12](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/12) **MERGED** to main (squash commit `05d601a6459492e9fe5bb03497ae3b19dc3f3a16`). PR [GitHub Actions run 43713209678](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43713209678) **PASS**: **61 tests passed, 1 warning**, PostgreSQL 18 Alembic `0005_link_reversals` upgrade and no-drift `alembic check` PASS.
- `LoanAllocation` and `TransferConfirmation` gain active-only uniqueness and encrypted immutable correction/revocation audit records, with explicit reason/identity. Original bank rows, original financial links and classification audit remain. Reversed links stop affecting loan balances or active transfer lists. A corrected transaction can be linked again without deleting its prior history; exact replay idempotent.
- Guard rejects reversal of loan disbursement if remaining repayment entries would cause negative historical principal. Reverse dependent repayments first. Verified tests cover this, source lock behavior, amended own transfers, fully encrypted correction notes, and unknown tax liability staying `null`.
- Routes: `POST /api/finance/loans/{loan_id}/allocations/{allocation_id}/reverse`, `POST /api/finance/transfers/{transfer_id}/reverse`, `GET /api/finance/links/audit`. Full contract: [`docs/IMPLEMENTATION_M2F_REVERSALS.md`](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/blob/main/docs/IMPLEMENTATION_M2F_REVERSALS.md).
- This **supersedes the M2e limitation** stating no audited correction interface. Still **NOT real-data ready**: no verified owner financial evidence, no full encrypted numeric/date/metadata storage, no private production deployment, no bank/FBR PDF parsing or independently verified TY2023+ tax engine. `APP_DATA_MODE=real` remains fail closed; GitHub is temporarily PUBLIC intentionally but holds synthetic-only code/fixtures. Owner's previous tax returns are not needed for this development milestone.
- Next owner-independent priorities: private-data encryption of monetary/date/metadata and keyed import dedup; bank/FBR synthetic document adapters, cash-in-hand and assets/wealth timeline, actual evidence provenance, production MFA/backup/restore controls and year-effective statutory tax engine with legitimate optimization eligibility review.

## Final M2e/M2f main-branch verification (2026-11-15)

- M2e [main CI 43712268265](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43712268265) **success** after merge; M2f [main CI 43713347679](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43713347679) **success** after merge. Exact PR head for M2f had **61 pytest tests passed** and PostgreSQL 18 migration/schema PASS.
- Verified main contains both PR #11 and PR #12, associated code and handoff files. All development occurred with synthetic-only data; no owner input requested. GitHub visibility remains PUBLIC by explicit owner choice, real app mode disabled.
