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
