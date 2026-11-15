# Product plan v2 — statement-led Personal CFO, legal tax intelligence and accountant-ready year-end

**Approved direction recorded:** 2026-11-16. **Status:** product specification and prioritized implementation plan, **NOT a claim of delivered features**. **Authority:** owner decisions, document-format review summarized in [accountant evidence workflow](ACCOUNTANT_WORKING_PAPER_AND_EVIDENCE_WORKFLOW.md), and the maintained [source of truth](../AGENTS.md). This document contains **only reusable, non-personal design requirements**. No authentic files, unique counts from a private financial portfolio, financial values, taxpayer identifiers, names, messages, document passwords, transactions or quotations are published.

## 1. Why this changes product emphasis

The personal finance system should **not merely emulate an income-tax calculator or recreate an accountant's annual workbook**. The opportunity exposed by a heterogeneous, confidential set of banking, FBR and accountant document **types** is an **evidence-backed, continuously reconciled financial ledger** that proactively produces the underlying schedules and unresolved questions an accountant otherwise reconstructs from separate statements, documents and spreadsheets every year.

**Owner's outcomes:** (a) statement uploads remain the ordinary recurring activity, whenever available; (b) transactions, income/expenses, tax withholdings, assets, liabilities, loans, cash and investments are maintained from 2023 onward; (c) legally reviewed TY-specific tax estimates and lawful optimization guidance are continuously updated; (d) only unresolved exceptions require attention; (e) an accountant receives a traceable, clearly provisional or approved working package; (f) the owner sees verified wealth, liquidity, planning scenarios and missing evidence in one place.

**Not the intended outcome:** an autonomous accountant, automatic FBR submission/revision, inventing taxable treatment from a credit or declaring a draft filed, guaranteed savings, trading or bank-login scraping. Human owner approval and professional review remain possible/necessary.

## 2. Source-derived problems versus product recommendations

| Generalized document-type observation | Inference / design requirement | Feature status |
| --- | --- | --- |
| Multiple banks, document layouts, overlap periods, PDF/CSV/XLSX and content-protected PDFs | Private source intake with verified MIME/signature, bank-profile/version, temporary document password, bounded isolated PDF parsing, original-page/row provenance; account×period coverage; duplicate and balance controls | Synthetic import/preflight foundations; **genuine adapters blocked G1–G3** |
| Workbook with distinct bank/income/tax/wealth/investment sheets, many formulas, incomplete cells or invalid references | Read-only, versioned **accountant working-paper audit**: sheet/cell/formula lineage, cached vs formula result, broken/external/dependent references, missing schedules, rounding/sign mismatches and discrepancy list | **Planned** |
| FBR filed record/acknowledgment coexists with provisional workbook | Separate **filed income return, filed wealth statement, receipt and amendment** from mutable **draft working paper**; draft never changes historical filed baseline | Synthetic history partial; real versions **planned** |
| Tax-withholding schedule includes unclaimed/unverified lines | Source-linked withholding ledger; tie bank/employer/broker/FBR entries by section and TY; distinguish verified adjustable, final, disputed, duplicate and **eligibility unknown** | Partial source-indexed opportunities; legally complete WHT **planned** |
| Accountant requests explanations of asset buys, loans, transfers and unidentified inflows | Explainable exception queue with possible categories, **never automatically assume deposit = taxable income**, document request, owner answer, accountant disposition, audit | Partial synthetic categorization; end-to-end queue **planned** |
| Previous-year wealth and next-year opening figures can disagree for legitimate reasons | Wealth bridge, revisions, non-bank assets, valuation, liabilities, missing periods and evidence; disclose discrepancy as **review**, not automatically a filed error | Partial synthetic bridge; full asset/IRIS **planned** |
| Correspondence/screenshot may show a request but not source proof | Confidential evidence request management; correspondence is context, not certified statement; audio screenshot is not a transcript | **Planned** |

These observations do **not** establish correct legal tax treatment or detect a specific taxpayer's mistake. Underlying private figures and document passwords belong solely in approved private analysis, **not public GitHub**.

## 3. Core product journeys (one-owner-first)

### J1 — One-time historical onboarding (2023 onward)

1. Create owner profile; keep individual versus company/AOP/sole-proprietor boundaries. Register known banks/accounts, currencies, historical opening dates and whether source coverage is complete.
2. Securely ingest bank statement batches and previously **filed** IRIS income, wealth, revision and acknowledgment evidence when G1–G3 pass; optionally import broker/payroll/NCCPL, ownership, loan and asset opening records. Older acquisition dates are allowed.
3. Reconcile account opening/closing balances and fiscal periods; show coverage as **observed, partially observed, missing, conflicting or unsupported**; no missing month silently becomes zero.
4. Show prior-year filed closing wealth versus following year's declared/draft opening wealth with separate source versions and explainable gaps. Permit explicit owner-approved corrections without rewriting original evidence.
5. Only ask the owner targeted questions about missing evidence or ambiguous classifications. No mass manual bookkeeping by default.

### J2 — Everyday intermittent statement upload

1. Upload 1–20 files at any time, covering random or overlapping date ranges; automatically detect supported bank/profile, period, account and format rather than trusting extension.
2. Preserve immutable encrypted originals + parser/version and row/page provenance; run balance checks, HMAC dedup and safe cross-account transfer candidates. On unsupported/source conflicts, **quarantine or review**, never guess or partially certify.
3. Categorize into salary, business, rent, deposit profit, dividend, disposal proceeds, transfer, loan principal/markup, cash movement, investment purchase, property, gift, donation/Zakat, tax withheld/paid and expense. Separate **economic fact** from **classification hypothesis** and legally validated tax treatment.
4. Update historical/cumulative income, spending, loans, investments, partial wealth and legally supported tax-year projection **after accepted changes**. Explicitly label verified/estimated/unavailable, account×month coverage and source completeness. Never convert a capital contribution or movement into income/gain by default.
5. Present a small review inbox sorted by fiscal and tax impact; no prompts for well-evidenced routine transactions.

### J3 — Accountant working paper and collaboration

1. Import versioned multi-sheet workbook **as DRAFT**. Inspect formulas in a restricted worker without executing macros, external links or data connections. Preserve source cell/sheet, literal formula, cached result and calculation engine metadata. Do not present stale caches as true recalculations.
2. Compare financial rows and totals with independently computed ledgers. Surface categories: broken references; missing supporting sources; period mismatch; debit/credit or sign reversal; duplicate withholding; incomplete wealth/investment schedules; cross-year continuity gap. **No auto-edit of accountant file**.
3. Record each review item as `OPEN -> EVIDENCE_REQUESTED -> OWNER_RESPONDED -> REVIEWED -> ACCOUNTANT_ACCEPTED/REJECTED` with immutable evidence citations, assignment only if authorized, notes and reasoned audit.
4. Support `DRAFT -> UNDER_REVIEW -> OWNER_APPROVED` for an accountant's work version. **FBR FILED requires distinct official submission/acknowledgment evidence**; owner approval of a draft is not a filing. Draft amendments retain versions; filed revisions follow distinct IRIS lineage.
5. Generate a **review package** (once data security and projections exist): category summaries, tax-year coverage gaps, FBR entry preparation, evidence links/redacted references, questions/answers, tax-withholding reconciliation and wealth bridge. Deliver via download/export first; optional accountant role/remote collaboration needs separate consent and security gates.

### J4 — Tax, wealth, planning and legal savings

1. Show recorded YTD amounts separately from annual estimates, projected liability, eligible verified tax payments, resulting possible payable/refundable and confidence. Require exact TY-year effective FBR statute/rule, independently reviewed test vectors, evidence and treatment of salary/business/property/other/investment, foreign receipts, adjustable vs final WHT and individual/entity boundaries.
2. Evaluate **candidate lawful** deductions/exemptions/credits/tax treatment or alternate permitted planning. Each opportunity lists TY, official legal reference/effective date, eligibility conditions, required proof, reasons it may not apply, comparison assumptions, human signoff and **estimated savings only after verified model**. Otherwise `unknown`/`null`; no evasion.
3. Explain wealth: bank, cash, securities, mutual funds, gold/crypto, property, vehicles, deposits, loans given/received, liabilities and reconciliation. Source valuation date/cost vs market estimate; never equate partial observed balances with official net worth.
4. Assist cash allocation/reserve, debt repayment, subscription/merchant price leakage, investment mix, risk/liquidity, upcoming tax obligations, goals and scenario trade-offs with uncertainties. No automatic payments, orders or trades.

## 4. Canonical source and workflow contracts

**Minimal source graph (models may be implemented incrementally):**
- `EvidenceDocument` + immutable `DocumentVersion`: owner/entity, document type, encrypted original, HMAC content identity, period, capture time, parser profile/version, password-unlock event without stored password, access and source page/row.
- `Account`, `StatementCoverage`, `ObservedBankRow` and `EconomicEvent`: separate source facts, original posting date, currency/FX provenance and source-backed debit/credit/balance; reviewed classification and corrections appended, not destructive.
- `ReviewCase` + `EvidenceRequest` + `OwnerResolution`: candidate classification, evidence references, priority/confidence, status, aging, related source conflicts and decision history. Consider an accountant's answer **context**, not original bank/FBR proof.
- `AccountantWorkbookVersion` + `SheetCellEvidence` + `FormulaDiagnostic`: draft lifecycle, source sheet-cell, formula vs cache, unresolved dependencies, comparison to ledger; macros/external data never executed.
- `FilingOriginalOrRevision`, `FbrAcknowledgment`, `TaxWithholdingEvidence`, `TaxRuleVersion`: claims and legally verified status independent of draft. Filed status requires authenticated acknowledgment/verification.
- `PositionSnapshot`, `AssetAcquisition`, `DebtOrReceivable`, `LoanSchedule`, `WealthBridge` and `TaxProjectionSnapshot`: source timestamps, cost/market distinctions, missing vs zero semantics and deterministic recomputation.
- `AdviceOpportunity`: explanation, source IDs, rule version, applicability, required human review, non-executing action and benefit `null` unless validated.

**Source precedence:** official filed+verified IRIS acknowledgement is authoritative for *what was filed* (not automatically economic truth); original bank/broker/payroll record authoritative for its source facts; reviewed source interpretation for categorization; accountant working book is an *opinionated mutable draft*; correspondence is supporting context; AI is a non-authoritative hypothesis generator. Conflicting sources remain visible and reviewable.

**Workflow state invariants:** never treat `UNKNOWN` as zero; never infer approved tax credit from `claimed = no`; never treat money transfer/loan principal as earned income; never assume opening wealth from an unapproved draft is filed; preserve revision history; no silent editing/re-filing.

## 5. Product navigation and priority

**First usable owner experience (target information architecture):** Overview / Accounts & Coverage / Transactions & Review / Income & Expenses / Loans & Cash / Investments & Assets / FBR Tax & Wealth / Accountant Workspace / Planning / Settings & Security.

A new **Accountant Workspace** is a first-class owner-facing module (private draft and exception review, reconciliation, export), not a separate multiuser product at MVP. A separate accountant login, invitations and shared workspaces are optional later. The objective is to **reduce accountant manual spreadsheet reconstruction and owner interruptions**, not to replace expert review.

**Near-term build order (dependency-aware; not delivery dates):**

| Slice | Gate/priority | Specific deliverable | Definition of done |
| --- | --- | --- | --- |
| S0 — secure canonical finance foundation | **P0 G1** | Active operational confidential bank/loan/cash/asset/source linkage + PostgreSQL migration, blind indexes, key lifecycle and independently restored encrypted backup | Database raw dump shows no plaintext sensitive economic fields, migration parity across years/accounts, no double-count, rollback and replay tests; real mode remains closed until all gates |
| S1 — secure owner runtime and source intake | **P0 G2/G3 parallel** | Private TLS/MFA/recovery, safe upload storage, isolated PDF and workbook inspect worker, synthetic bank/FBR adapters; later authorized authentic format acceptance | E2E security/browser/restore and source provenance; malformed/unknown/quarantined; no real upload until explicit owner approval |
| S2 — statement-driven reconciliation & review | **P1** | Historical onboarding, account×period coverage, overlap/transfer/loan/investment classification, exceptions and corrections | Irregular 20-file bulk and same-file retry are idempotent; correct balances, transfer not revenue, missing months unknown; prior corrections retained |
| S3 — accountant draft diagnostics & evidence queue | **P1** | Versioned draft/workbook formula graph, source-cell diff, requested-proof queue and export starter package | Broken references, stale caches, missing sheets, WHT candidates and wealth discontinuity flagged with evidence; draft never declared filed |
| S4 — TY legal tax and wealth package | **P1/G4** | Reviewed TY2023+ mixed-head statutes, true cash/asset/debt position, prior filed continuity, adjustable/final WHT and lawful opportunity cards | Independent golden vectors, multi-year correct tax differences; unsupported due/savings remain null; no filing without explicit signoff |
| S5 — private owner CFO experience | **P2/G5** | Mobile-first dashboard, refreshed partial vs verified tax, recurrent spend, debt, goals, investment scenario, accountant-ready reports | Owner completes end-to-end upload → review → reconcile → accountant pack on a private instance; secure restore and usability acceptance |
| S6 — productization | **Future G6 only** | Multiple people/advisers, RBAC, pricing, region/legal/SECP constraints, scalable jobs | Separate owner authorization; never a prerequisite for personal release |

**Parallelization:** after protective foundations exist, plan synthetic S2/S3 domain implementation without waiting for real documents. S4 statutory rules can be researched/tested independently with official sources but **must not be exposed as confident live liabilities** until reviewed. The owner has explicitly said additional historical returns and accountant workbook completion are NOT current code dependencies.

## 6. Acceptance and adversarial scenarios (synthetic-only during development)

1. Upload same statement twice, shuffled batches and overlapping account periods → **one economic event per real source fact**, exact duplicate trace, unresolved near-duplicates review.
2. Same-date/same-amount different references → distinct events; same cash transfer across two own accounts → one transfer relation, zero net external revenue and no double expense.
3. Loan disbursement/repayment → principal and markup separate; loan provided to another person remains receivable; no false taxable income.
4. Cash withdrawal to owned cash vs real cash expense → distinct; unknown physical cash opening remains null.
5. Input disguised as .xls/.xlsx/CSV, malformed Office package, encrypted PDF, scanner-image PDF, malicious embedded PDF actions → reject/quarantine/isolate, no partial ledger write and no leaked password.
6. Text PDF page carry-forward and opening/closing balances → exact row/page parity, no header counted as transaction.
7. Statement covers part of a month or skips months → coverage unknown; annualized cash-flow/tax explicitly provisional.
8. Legacy multi-bank statement and third-party ambiguous credit → review queue, not default salary/business income.
9. Workbook broken formula/circular/external link/stale cached result, missing investments/wealth sheets, changed version → cited diagnostics; no macro execution or automatic workbook mutation.
10. Draft opening wealth differs from prior *filed* closing wealth → review gap and possible revision/evidence; no allegation that filed return is wrong.
11. Separate filed income return, wealth and acknowledgement vs mutable draft → no state contamination or false `FILED` flag.
12. Withholding line marked unclaimed, duplicated across source records or applicable to final rather than adjustable regime → show candidate + eligibility question, not automatically refundable.
13. Property purchase/loan/gift/donation/investment contribution → correct asset/liability/wealth movement and income/tax uncertainty rather than false deduction/gain.
14. Mixed income TY2023–future, taxable and final receipts, separately owned company → correct statutory version and legal person segregation; independent golden-law tests.
15. Withholding or income source arrives later, draft version changes, new bank statement retroactively posted → deterministic historical recalculation, immutable filed baseline preserved, diff explained.
16. Encrypted backup corrupted, lost key, multiworker replay, unauthorized access, source tampering, rollback → fail-closed with no misleading success; restore must be verified independently.
17. AI confidence lower than threshold, changed model, unsupported statute or external feeds unavailable → review or null calculation, no fabricated tax saving/investment yield.
18. Owner-approved draft → export review package; FBR filing state still pending without official verified acknowledgement; optional accountant access requires explicit permission.
19. Fee/subscription spending detected only in observed months → annual estimate shown with coverage caveat, no asserted savings without owner review.
20. Private report exported → no secrets, CNIC, full account IDs or raw bank statements exposed to public logs/CI/URLs; owner can inspect access trail.

## 7. Release measures, boundary and dependencies

**Success metrics:** percentage of source rows accepted with verified balance parity; dedup/transfer non-double-count rate; account×month coverage; proportion of exceptions with cited evidence, time to review, number of missing-source questions at year end, filed-versus-draft state correctness, reproducibility of tax/wealth snapshot, backup/restore test pass and owner completion of one full year-end package.

**Current truth (verify at each chat):** synthetic bank/dedup/cash/loans/wealth previews, encrypted journal/archive, narrow FBR salary illustration, hypothetical CFO scenarios and safe CSV/XLSX preflight exist. **No real owner-data application exists yet; G1 active legacy money/date/linkages plaintext, G2 remote MFA deployment absent, G3 authentic document adapters absent, G4 mixed-income FBR/wealth certification incomplete, G5 real owner UI not delivered.** `APP_DATA_MODE=real` must remain disabled.

**Owner dependency:** **none for synthetic implementation, product planning or CI.** Later: explicit approval of private hosting/secrets and protected real document intake, source/filing verification, owner acceptance, expert review of tax-law outcomes. Do not ask for historical returns or accountant drafts to proceed with code now. Public GitHub receives only code, synthetic test fixtures and generalized requirements.

## 8. Links and ownership

- Engineering: [Current handoff](CURRENT_HANDOFF.md), [requirements matrix](REQUIREMENTS_COVERAGE_MATRIX.md), [release gates](DELIVERY_GATES_AND_RELEASE_READINESS.md) and [architecture](CFO_PLATFORM_ARCHITECTURE.md).
- Execution: [P0 confidentiality #21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21), [private deployment #28](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/28), [bank/IRIS source adapters #29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29), [draft workbook/review #30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30), [FBR law and savings #5](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/5), [recurring bills #25](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/25).
- Role: owner supplies private acceptance and approves financial/legal decisions only when required. Development agents implement/test synthetic slices, verify exact CI, merge reviewed PRs and update GitHub continuously. Accountant reviews draft figures/evidence and files only at owner's direction; the application does not assume an accountant is an integrated user.
