# AGENT START HERE — 2026-11-15

## Single authoritative context

This repository is the project source of truth. Read `README.md`, `docs/CURRENT_HANDOFF.md`, `docs/DECISION_LOG.md`, `docs/ROADMAP_AND_ACCEPTANCE.md`, `docs/SECURITY_PRIVACY.md` and then the domain-specific document for your task. Do not transfer assumptions from unrelated repositories or chats.

## Product identity and user intent

A private Pakistan FBR tax-and-wealth desk for **one owner**, with optional commercialization later. Salary + business + investments + other income; historical records from **2023 onward**; unpredictable statement upload cadence; auto-updated tax year and wealth dashboards; loans received/given, donations, gifts, cash and investments; planning assistant.

## Critical architectural invariants

1. Raw evidence is immutable, encrypted, retained outside Git. Every derived number traces to source/version and date.
2. Import is replayable and idempotent; exact and near duplicates require correct handling.
3. Bank debit/credit is not a tax category. Inter-account movement is not income/expense. Principal repayment is not taxable yield. Capital gains are not inferred from contributions.
4. Statutory calculation is deterministic and year-specific. AI suggestions never directly produce unreviewed tax liabilities or filings.
5. Dataset completeness visible. No precision without records; balance estimates/holdings need separate proof.
6. A historical filed return is a baseline source; software does not silently revise it.
7. Return and wealth statement must reconcile, or readiness stays HOLD.
8. No investment trades or public personalized advisory until relevant legal/regulatory requirements are cleared.
9. No deployment without basic MFA, encryption, tested restore and secure configuration.

## What has been done

Requirements analysis, design decisions, proposed documents, high-level technical plan. The source repository exists. The synthetic-only M1 implementation is merged; no production app or genuine tax computation exists. Owner approved temporarily public GitHub, with a future change back to private.

## Immediate next tasks

- Continue source-only development in the intentionally public repository; never commit financial documents or secrets.
- Implement focused skeleton: Next.js + Python FastAPI + Postgres, test harness, encrypted local file adapter.
- Deliver one end-to-end import using a synthetic CSV: raw document -> parsed rows -> reconciled immutable ledger -> categorized cashflow -> fiscal-year dashboard.
- Add one real bank layout adapter only after receiving an approved **redacted** sample via secure input.
- Build per-year tax rule registry and test cases before applying actual legal rates.
- Design onboarding for previous filed returns and opening wealth, with explicit prompts for unknowns.

## How to report progress

State actual tested behavior, URLs/commit hashes, remaining work, safeguards, and next action. Never claim live production, file submission or legal certainty without evidence. Keep `docs/CURRENT_HANDOFF.md` up to date.

## Implemented local M1 (2026-11-15)

Read `docs/IMPLEMENTATION_M1.md` and `docs/CURRENT_HANDOFF.md` for local synthetic-only implementation, exact pytest commands, honest limitations and next priorities. Preserve the local-only no-real-data restriction until MFA, encrypted storage, migrations and recovery are verified. Do not declare FBR calculations implemented from the synthetic year-to-date summary.

## Owner decision: temporary PUBLIC source repository (2026-11-15)

The owner explicitly chose to keep this GitHub repository **PUBLIC while developing**, hoping to make Actions work, and intends to switch it to PRIVATE later. This is authorized and not itself a blocker for code-only development. Keep public GitHub strictly source-code, architecture, documentation and synthetic-fixture only. **Never push actual tax returns, wealth statements, bank statements, secrets, personally identifiable records, raw file dumps or copied figures from the owner's documents**, including through issues/PRs/CI artifacts or error logs. The private *application* and encrypted storage must be separately secured before handling genuine data. Runner availability remains unconfirmed despite public visibility.

## Binding new goals

Build a proactive **lawful tax minimization** advisor (not tax evasion): year-effective law-backed exemptions, deductions, credits, adjustable withholding, business-expense opportunities and scenario comparisons with auditable source references and required evidence. The owner will provide **3–4 years of already-filed FBR returns and wealth statements** for confidential historical baseline/reconciliation. They must be stored only via secure private upload paths, with immutable original documents and explicit revision review. Read `docs/TAX_OPTIMIZATION_AND_PRIOR_RETURNS.md` before implementing tax/return processing.

## Current implementation status — M2a (2026-11-15)

Historical uploaded returns are **not required to proceed**. M2a adds strictly synthetic FY2023+ historical income-return/wealth-statement records, encrypted synthetic evidence files, idempotent original/revision tracking, prior-to-current FY wealth continuity status, and tax-optimization *evidence-required* candidate API with **no calculated savings**. Local test suite: **18 passed**. Read `docs/IMPLEMENTATION_M2_SYNTHETIC_FILINGS.md` and `docs/CURRENT_HANDOFF.md`.

**Current synthetic-only restrictions remain non-negotiable:** local Basic auth, unencrypted structured SQLite data, incomplete MFA, backup/restore, migrations and real FBR parsing. Do NOT solicit genuine unredacted user returns into GitHub or prototype. Owner will supply 3–4 years of historical returns later; they will be reconciled after real-data security gates. Repository intentionally PUBLIC during development.

## M2b / M2c merged engineering state (2026-11-15)

- PR [#7](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/7) (M2b, merge `7745afb`) delivered immutable Alembic ledger baseline, PostgreSQL 18 schema verification, authenticated encrypted *synthetic* filed-return fields, synthetic-only encrypted backup/restore and two bank-like sample CSV adapters. Hosted CI: **27 tests passed**, PostgreSQL18 schema/check PASS.
- PR [#8](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/8) (M2c, merge `8cf1abc`) delivered opt-in scrypt + RFC6238 TOTP owner MFA login, authenticated server-side hashed session cookies, CSRF/Origin checks, logout revocation, expiry and migration `0002_owner_mfa`. Hosted CI: **31 tests passed**, PostgreSQL18 schema/check PASS.
- Read `docs/IMPLEMENTATION_M2B.md` and `docs/IMPLEMENTATION_M2C.md` alongside `docs/CURRENT_HANDOFF.md`. Current prototype still has **local synthetic-only** restriction, `APP_DATA_MODE=real` refuses startup. Original M1 transaction descriptions/audit notes are not fully encrypted, and production authentication/deployment/backups/keys not audited. **Never request or process genuine bank statements/returns through this prototype.**
- Next owner-independent code: full field encryption and migrations, distributed-login throttling/session hardening, key rotation/off-site backup design/testing, synthetic FBR/bank PDF adapters, accounting for loans/transfers and tested year-specific FBR rules. User will provide historic returns later for protected integration validation; do not block development on that.

## M2d-1 integrated on main (2026-11-15)

PR [#9](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/9) merged (commit `7d0ddd8`); hosted [CI run 43709171698](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43709171698) PASS (**39 tests**, PostgreSQL 18 Alembic `0003_ledger_text` + schema check). Read `docs/IMPLEMENTATION_M2D_ENCRYPTED_LEDGER.md` for encrypted account/transaction/audit text, keyring, offline synthetic-only rotation, legacy plaintext refusal and limits. Still **NOT real-data ready**: amounts/dates/metadata, non-keyed fingerprints, multiworker auth, independent backups, FBR-bank format extraction and law verified tax engine remain incomplete. No user action or prior FBR returns needed to continue synthetic development. Public GitHub contains only source/docs/synthetic evidence.

## M2d-2 completed (2026-11-15)

[PR #10](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/10) merged (commit `14f1fbd`); [CI 43709644891](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43709644891) PASSED **44 tests** and PostgreSQL 18 migration/schema check. New `GET /api/finance/movement-review` uses `app/movement_analysis.py`: strictly reviewed, one-to-one, cross-individual-account synthetic transfer candidates, no automatic pairing, notes ambiguous/unmatched and separates non-earnings movement categories. Read `docs/IMPLEMENTATION_M2D2_MOVEMENTS.md` and `docs/CURRENT_HANDOFF.md`. Continue with security/privacy of numeric/date/metadata, fully evidenced loan/cash financial graph, synthetic bank/FBR layout adapters and verified year-specific Pakistan tax logic. **Do not solicit owner documents or enable real-data ingestion before private security gates.**

## M2e — 55 tests green, synthetic loan and transfer accounting (2026-11-15)

PR [#11](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/11) merged at `d637d9a`. [Hosted CI run 43712136211](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43712136211) passed **55 tests** and PostgreSQL18 `0004_finance_links` migrations with no drift. Read `docs/IMPLEMENTATION_M2E_LOANS_TRANSFERS.md`: new `/api/finance/loans` and `/api/finance/transfers/confirm` APIs link **explicitly reviewed** bank transactions to principal/markup liabilities/receivables and to owner-confirmed own-account transfers. They do not automatically classify source transactions or assert tax/legal evidence. Link records are immutable; audited reversal/reassignment is NOT yet available and is a future gate. Counterparty labels/notes encrypted; amounts/dates/metadata still not. No real data uploads, deployed app, or FBR tax calculation; APP_DATA_MODE=real fail closed. Continue owner-independent work with synthetic fixtures. Public GitHub source contains no actual financial/taxpayer information.

## M2f merged: audited corrections (2026-11-15)

[PR #12](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/12), merge commit `05d601a`; [CI run 43713209678](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43713209678) **61 tests passed** plus PostgreSQL18 Alembic `0005_link_reversals` PASS. Read `docs/IMPLEMENTATION_M2F_REVERSALS.md`: financial links can now be revoked by authenticated, reasoned correction while preserving the original link/transaction and an encrypted append-only audit row. Uniqueness applies only to ACTIVE links, so corrected reassignment is possible. Prevent reversing loan advances that would leave recorded principal negative. No taxable amounts or law are inferred; REAL data mode prohibited, public repo synthetic only. Next actions are encryption of residual monetary/date/meta, wealth/cash and supported financial-document adapters plus verified FBR rules. Previous user returns are not a development blocker.

## M2g merged — cash-in-hand synthetic evidence (2026-11-15)

[PR #13](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/13) merged, `8384784`. [CI run 43714829408](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43714829408) **68 tests passed**, PostgreSQL18 migration `0006_cash_wealth` and schema check PASS. New module `app/cash_ledger.py`, routes `/api/finance/cash`, `/api/finance/cash/annual` and M2g design `docs/IMPLEMENTATION_M2G_CASH_WEALTH.md`. Reviewed bank cash debit/deposit links and manual cash activity remain owner declarations, with null historical balances on missing openings; reclassification source locks and encrypted audited reversals. No FBR evidence/tax eligibility verified, and dates/amounts/metadata not protected. Real mode disabled, temporary public repo synthetic only. Historical owner tax returns are NOT required for continued engineering.
