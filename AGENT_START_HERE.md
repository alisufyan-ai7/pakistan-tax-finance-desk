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

Requirements analysis, design decisions, proposed documents, high-level technical plan. **No repo creation, app implementation, infrastructure creation, uploads, or live tax computations are assumed complete.** The owner requested GitHub as source of truth; publish this package to a newly created **private** repository when permissions permit.

## Immediate next tasks

- Establish private repository; commit initial planning documents, verify visibility and links.
- Implement focused skeleton: Next.js + Python FastAPI + Postgres, test harness, encrypted local file adapter.
- Deliver one end-to-end import using a synthetic CSV: raw document -> parsed rows -> reconciled immutable ledger -> categorized cashflow -> fiscal-year dashboard.
- Add one real bank layout adapter only after receiving an approved **redacted** sample via secure input.
- Build per-year tax rule registry and test cases before applying actual legal rates.
- Design onboarding for previous filed returns and opening wealth, with explicit prompts for unknowns.

## How to report progress

State actual tested behavior, URLs/commit hashes, remaining work, safeguards, and next action. Never claim live production, file submission or legal certainty without evidence. Keep `docs/CURRENT_HANDOFF.md` up to date.

## Implemented local M1 (2026-11-15)

Read `docs/IMPLEMENTATION_M1.md` and `docs/CURRENT_HANDOFF.md` for local synthetic-only implementation, exact pytest commands, honest limitations and next priorities. Preserve the local-only no-real-data restriction until MFA, encrypted storage, migrations and recovery are verified. Do not declare FBR calculations implemented from the synthetic year-to-date summary.
