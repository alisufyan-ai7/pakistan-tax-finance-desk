# Pakistan Tax & Wealth Desk

**Status:** Requirements and engineering handoff established on 2026-11-15. **No application has been built, deployed, or tax returns filed.**

A **private, single-owner-first** Pakistan tax preparation, lifetime transaction ledger and personal wealth intelligence application. **GitHub is the source of truth for code, requirements, decisions, test fixtures and engineering handoffs; never for real statements or confidential financial data.**

## Mission

1. Upload bank statements at any cadence, from any supported bank, beginning **2023-01-01** (earlier opening balances/evidence may be required), and continuously track subsequent financial years.
2. Maintain a durable, reconcilable ledger of income, spending, savings, investments, loans both given and taken, gifts, donations/zakat, transfers, tax payments, cash-in-hand, receivables, liabilities, owned assets, and net worth.
3. Calculate documented **Pakistan FBR tax-year-specific** year-to-date position and full-year projections for salary, personal/sole-proprietor business, investments, property and other income; do not invent tax conclusions.
4. Prepare **FBR IRIS-ready return and wealth statement schedules**, with withholding evidence, asset reconciliation and unresolved-item tracking. Human-reviewed submission via IRIS initially; no unsupported automatic filing.
5. Offer **educational, suitability-aware financial planning and scenario analysis** using real financial history; no auto-trading, guaranteed returns or unlicensed advisory service.
6. Ship privately for one owner now, but retain a carefully bounded path to optional multi-user commercialization.

## Non-negotiable product decisions

- **Personal first; commercialization is exploratory only.** No subscription, public signup or payment gateway in v1.
- **Routine input: statements only.** One-time baseline and occasional requested evidence/corrections are allowed and necessary when bank statements cannot establish tax or holdings.
- **Historical coverage from Jan 2023**, including Tax Year 2023 partial coverage (Jan-Jun), Tax Year 2024 onward; extend earlier if required for asset cost basis and wealth opening balance.
- **Explicit provenance and honest uncertainty:** never guess origin, beneficial ownership, nature of deposit, investment gain, cash balance, tax credit, filing status, or loan outstanding.
- **Financial records are not in GitHub.** Private encrypted database and object storage; redacted or synthetic fixtures only in repo.
- **No blending distinct legal entities.** Individual tax ledger separate from incorporated companies, partnership/AOP, and other persons.
- **No tax-law constants without reviewed source and effective dates.** Maintain per-year statutory rules and calculation audit trail.

## Documents and navigation

- `AGENT_START_HERE.md` — read first in every agent session
- `docs/PRODUCT_REQUIREMENTS.md` — product scope, journeys and priorities
- `docs/HISTORICAL_BACKFILL.md` — 2023 onward import and opening wealth
- `docs/DOMAIN_AND_DATA_MODEL.md` — entities, classifications and ledger contracts
- `docs/IMPORT_PIPELINE.md` — parsing, duplicates, own transfers, reconciliation
- `docs/PAKISTAN_TAX_AND_FBR.md` — historic rules, projections, IRIS and tax credits
- `docs/WEALTH_INVESTMENTS_AND_ADVICE.md` — asset, liability, loan, cash and advice module
- `docs/TECHNICAL_ARCHITECTURE.md` — technical direction and development standards
- `docs/SECURITY_PRIVACY.md` — protection, retention and threat model
- `docs/PRODUCTIZATION.md` — prospective audience and safe commercialization gates
- `docs/ROADMAP_AND_ACCEPTANCE.md` — prioritized execution and tests
- `docs/DECISION_LOG.md` — binding current decisions vs assumptions
- `docs/OPEN_QUESTIONS.md` — nonblocking unknowns to resolve at right time
- `docs/REGULATORY_SOURCES.md` — official references (verify current versions)
- `docs/CURRENT_HANDOFF.md` — state and immediate next actions
- `.gitignore` — blocking sensitive local files from entering Git
- `samples/README.md` — synthetic-only fixture policy

## Working agreement

Implement sequential vertical slices, keep docs synchronized with each architectural or product decision, run repeatable tests against synthetic data, track blockers explicitly, and never assert production readiness from mock screenshots. Avoid unnecessary cost or deployment complexity. No tax numbers, rules, or financial forecasts are certified by this planning repository.

## Implementation status — M1 local synthetic ledger (2026-11-15)

A **working synthetic-only local prototype** is now present in `backend/` and `frontend/index.html`: authenticated localhost UI, account onboarding, normalized CSV/XLSX uploads, balance checks, import deduplication and ambiguous overlap review, transaction categorization with audit, and historical tax-year summaries. See [`docs/IMPLEMENTATION_M1.md`](docs/IMPLEMENTATION_M1.md) for the exact run/test commands and limitations. Synthetic demo fixture: `samples/synthetic_bank_normalized.csv`.

**Do not use with real financial data yet:** local SQLite is unencrypted and Basic authentication is localhost-only. Real statements need MFA, encrypted private storage, backups/restore and bank-specific import acceptance first. This version does **not** compute actual FBR tax or file returns. Long-term target remains Next.js/FastAPI/PostgreSQL; M1 uses a simple local browser UI to ship the core import/ledger vertical slice safely.
