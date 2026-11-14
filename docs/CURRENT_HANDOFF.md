# Current project handoff — 2026-11-15 — M1 implementation

## Source of truth

Repository: `alisufyan-ai7/pakistan-tax-finance-desk` (private), default `main`. Read `AGENT_START_HERE.md` and `README.md` first; then `docs/IMPLEMENTATION_M1.md`, this handoff, `docs/SECURITY_PRIVACY.md`, `docs/IMPORT_PIPELINE.md` and `docs/ROADMAP_AND_ACCEPTANCE.md`.

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
