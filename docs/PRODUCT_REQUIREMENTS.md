# Product requirements (PRD)

**Stage:** planning, 2026-11-15. **Priority:** usable personal tool; productization deferred.

## User and goals

One owner who has salary, business, investment and other receipts in Pakistan; many bank accounts, potentially multiple currencies; has investment history since 2023 or 2024; wants low-effort uploading, continuous financial awareness, accurate FBR tax preparation and useful financial advice.

## Core jobs to be done

- Select tax year and accounts, upload a year or random months of PDF/CSV/XLSX statements; support batches, overlaps, changes and re-uploads.
- Read gross and net cashflow, income classifications, expenses by merchant/category, loans to/from others, donations/zakat, gifts, cash balances, investment activity, asset/liability balances and source gaps.
- Understand real tax position: verified YTD income and taxes paid, illustrative accrued allocation, estimated annual liability, projected balance payable/refundable, and confidence/completeness.
- See dated historic returns and wealth statements, how wealth changed each FY, and why transactions were classified the way they were.
- Ask plain-language questions: 'What did I spend?', 'Which loans are due?', 'What is my liquidity?', 'Which income is unverified?', 'How much might I owe FBR?', 'What options might fit my surplus cash?'
- Export auditable, FBR IRIS entry guidance and human-review-ready evidence package; never silently file or amend.

## Navigation

Overview; Accounts & Statements; Transactions; Income; Expenses; Investments; Loans & Receivables; Gifts & Donations; Cash & Assets; Taxes & FBR; Financial Planning; Review Queue; Settings/Tax Profile.

## Functional priorities

**P0**: sign-in with MFA; tax-year windows; multi-account CSV/XLSX and selectable-PDF parsing; source coverage; immutable documents; transaction dedup; money movements; category review; current/historical dashboard; export; audit logs.

**P1**: historic FY backfill; income/head & legal-entity tagging; loan and donation ledger; bank balance controls; personal cash ledger; opening and closing wealth; asset acquisition/disposal tracking; withholding supporting evidence; projected tax engine with year-specific rules.

**P2**: investments detailed lots/positions, cross-asset valuations, FBR wealth reconciliation, historic return comparison and tax schedule exports; goal-based financial planning assistant.

**P3**: richer integrations (broker exports, approved market pricing, FBR evidence, optional secure bank feeds when available), alerts, multi-user/SAAS only by separate future approval.

## Source quality/status taxonomy

`VERIFIED_SOURCE`, `RECONCILED`, `USER_CONFIRMED`, `ESTIMATED`, `INFERRED_REVIEW_NEEDED`, `MISSING`, `CONFLICT`, `NOT_APPLICABLE`. Prominently display. Only non-uncertain sources can satisfy release/filer readiness where appropriate.

## Non-functional requirements

Fast incremental recalculation after uploads; parsing progress; deterministic recomputation; `Decimal` money; PKR default/multi-currency preservation; timezone handling (`Asia/Karachi` display, original posting dates stored); encrypted storage and backups; scoped read-only AI context; secure single-user ownership; data export/delete; no hardcoded bank, plan or tax year.

## Deliberately excluded from initial personal release

Public signup, payments, bank credential scraping, unsupported IRS/FBR auto-submission, direct investing/trading, public individualized securities recommendations, corporate/sales tax compliance product, promises of automated legal advice.

## Added owner requirements 2026-11-15

- Proactive personalized **lawful tax minimization** guidance: show potentially available credits, exemptions, deductions, withholding offsets, proper income characterization and tax-year filing scenarios with statutory references, eligibility conditions, required evidence, confidence, limitations and estimated savings only when supportable. No concealment or fabrication. Tax AI explanation cannot replace legally verified calculations or expert review.
- Import three to four previous **filed FBR income tax returns and associated wealth statements** as confidential primary evidence for baseline opening/closing wealth, previously declared income and liabilities, paid taxes, carried values and cross-year audit; show filed-vs-observed-vs-estimated differences. Never auto-revise a return.
- GitHub code repo temporarily PUBLIC by owner instruction for development; remains source-code/docs/synthetic-only with no private finance documents. Real records remain behind secure private application upload, still unimplemented.
