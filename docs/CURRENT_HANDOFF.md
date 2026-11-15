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
