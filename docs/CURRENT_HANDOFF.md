# Current state and next chat / agent handoff — 2026-11-15

## What is known

- Product is an owner-only private Pakistan FBR tax and personal wealth desk.
- Primary normal workflow is bank statement uploads at irregular times; system must dedup and recalculate incrementally.
- Historic coverage starts 2023-01-01 (initial), with optional earlier source data if investment cost basis or opening wealth requires.
- Mixed income: salary, business, investments and other sources.
- Every material financial item: loans owed/owing, donations/zakat, gifts, cash, investments, property/assets, debts, transfers, expenses and tax evidence.
- Annual tax engine for applicable historic tax years, return + wealth statement preparation, investment planning assistant with no execution.
- Private, owner-first; maybe public SaaS later but no commitment.
- GitHub is engineering source of truth; never store real financial records in GitHub.

## Actions completed

- Brainstorming and engineering documents prepared; official source entry points recorded.
- Private GitHub repository `alisufyan-ai7/pakistan-tax-finance-desk` created by owner; authenticated connected GitHub access and **private** visibility verified.
- Initial 22-file planning/documentation package is committed on `main` in the project initialization. No application code, real import tests, financial data uploads, deployment, or verified tax calculations yet.

## Next concrete action

1. Verify initial planning package commit and 22 expected files on `main`; repo must remain private. Never use any unrelated repository.
2. Start skeleton: Next.js + Python FastAPI + PostgreSQL, security baseline and automated test harness.
3. Build an end-to-end synthetic import through normalized, idempotent financial ledger, cross-account transfers, loans, gifts and cashflow snapshots.
4. Add verified effective-date FBR tax rules and historical calculation test cases before user tax estimates.
5. Request anonymized/redacted bank layout only after protected upload route exists; never request real statements via GitHub issues.
6. Maintain this handoff at every milestone with actual commit hashes, test evidence, blockers and next action.

## Practical definition of done for MVP

Owner signs in; uploads a synthetic statement; importer reports exact source balance and duplicates; finance dashboard updates for selected FY; amount classification and exception queue work; no bogus tax or market value claims. Production financial data and FBR-ready output require later gates.
