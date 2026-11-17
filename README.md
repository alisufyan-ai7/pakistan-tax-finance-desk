> **Project continuity rule:** GitHub `main` is the source of truth, including material owner discussions and the future direction. Every new chat/agent must begin with [AGENTS.md](AGENTS.md) and [docs/CHAT_CONTINUITY_PROTOCOL.md](docs/CHAT_CONTINUITY_PROTOCOL.md); every completed milestone must update [current status](docs/PROJECT_STATUS.md), [owner decisions](docs/PROJECT_DECISIONS_AND_SCOPE.md) when changed, [requirements coverage](docs/REQUIREMENTS_COVERAGE_MATRIX.md), and [handoff](docs/CURRENT_HANDOFF.md). This remains a **personal CFO first**, expandable later and synthetic-only while the repository is public.

# Pakistan Tax & Wealth Desk



> **Current product direction (2026-11-16):** [Personal CFO v2 — statement-led accounting, reconciliation, legal tax intelligence and accountant-ready workflow](docs/PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md). This plan is the primary product scope and user-journey source; the [latest implementation status](docs/PROJECT_STATUS.md), [release gates](docs/DELIVERY_GATES_AND_RELEASE_READINESS.md) and [handoff](docs/CURRENT_HANDOFF.md) distinguish planned versus implemented work.


**Current verified status (Chat 04, 2026-11-17; parallel batch 3):** [Merged integration #119](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/119) (squash `29154d57673e7ab0dd0bfd6e1bffac7ad69a4c7d`) passed exact-head [backend CI 44094000754](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44094000754) **719 pytest + PostgreSQL18 PASS** and [frontend CI 44094000675](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44094000675) **41 Node tests PASS**, after green independent [#116](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/116), [#117](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/117), [#118](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/118). Implemented only with fictional test data: an **unmounted owner MFA/login session HTTP contract** (#116), phone-friendly fictional Documents followups (#117), and transactionally locked fake one-folder scan leases with independently HMAC-sealed last-good receipts (#118, schema `0017`). Existing public Railway frontend is synthetic PWA; its private API still starts `app.preview_api:app` and Nginx exposes no real Google OAuth or owner-login callback. **No genuine Google Drive sync, scheduled worker, real financial records, real owner MFA/key custody, original parser certification or production encrypted ledger**. G1/G2/G3 private data security gates BLOCKED; no owner financial amounts or FBR tax claims from demos. Read [latest complete handoff](docs/CURRENT_HANDOFF.md), [batch3 full evidence](docs/CHAT4_PARALLEL_BATCH3_2026-11-17.md), [six-priority roadmap](docs/PRIORITIZED_PERSONAL_CFO_ROADMAP_2026-11-17.md), [requirements](docs/REQUIREMENTS_COVERAGE_MATRIX.md), [release gates](docs/DELIVERY_GATES_AND_RELEASE_READINESS.md). Older milestones below are historical, not current readiness.

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

> **Source repository visibility decision (2026-11-15):** The owner intentionally keeps this GitHub repository **PUBLIC temporarily** to facilitate development/Actions and plans to switch it to private after the development phase. This is not authorization to place real financial records or personal identifiers in GitHub. **Current application is synthetic-only**, unencrypted, and unsuitable for genuine bank or tax documents; private secure application storage/MFA/backup must be verified before real-data use. Public visibility does not prove that Actions runners work.

## Legal tax optimization and prior filed returns

The owner explicitly requires **proactive, lawful tax minimization**: identify legitimate opportunities, missing eligible withholding adjustments/credits, business deductions, exemptions and filing choices, with tax-year-specific verified law, sources, estimated benefit, required evidence, confidence and human review. Never hide income, fabricate expenses, backdate transactions, misstate loans/gifts/assets, or promise guaranteed tax savings. See `docs/TAX_OPTIMIZATION_AND_PRIOR_RETURNS.md`.

The owner intends to provide three to four years of **already-filed income tax returns and wealth statements**. These are confidential historical evidence for establishing filed positions, opening and closing wealth, carried balances, tax paid and previous classifications; no automatic correction or revision. The current M1 prototype cannot accept real tax returns. Secure ingestion will be added in M2 after encryption, MFA and backups, and source documents must **never be committed to this public GitHub repository**.

## M2a — Synthetic historical filing foundation (2026-11-15)

The application now contains **synthetic-only** TY2023+ income-return/wealth-statement record versions with encrypted test-evidence files (AES-256-GCM), idempotent ingest, immutable revision lineage, cross-year wealth continuity statuses, and read-only *evidence-required* tax optimization hints. API tests run locally: **18 passed**. Full details: [M2a implementation](docs/IMPLEMENTATION_M2_SYNTHETIC_FILINGS.md).

This **does not** accept real FBR returns or calculate tax yet. The prototype still stores structured values in unencrypted local SQLite and uses localhost Basic auth. Real document handling requires verified secure private application access, MFA, PostgreSQL migrations, encrypted structured data, backup recovery and parser validation. Your previous filed returns are **not required for development now**; they will serve as historical evidence once the secured application importer exists. Public GitHub is allowed temporarily for synthetic source-only development.

## Latest engineering progress — M2b/M2c (2026-11-15)

- [M2b: encrypted synthetic records, Alembic/PostgreSQL 18, synthetic bank layouts and encrypted backup/restore](docs/IMPLEMENTATION_M2B.md) — PR [#7](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/7) merged, 27 CI tests and PostgreSQL migration passed.
- [M2c: opt-in owner MFA session foundation](docs/IMPLEMENTATION_M2C.md) — PR [#8](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/8) merged, 31 CI tests and PostgreSQL migrations passed.
- Synthetic-only security features include an RFC6238 TOTP gateway, scrypt-hashed credentials, server-side hashed sessions, strict secure cookies, CSRF checks and logout revocation. **They are not certified for production**; current app still rejects real-data mode, and much of the M1 financial ledger is unencrypted at rest.
- Owner tax returns are NOT a development dependency. Continue the private-data encryption, key lifecycle, bank/FBR adapter validation, accounting and FBR rule engine with synthetic evidence. No genuine financial data or secrets may enter this temporarily public source repository.

## M2d-1 — Encrypted ledger text and rotation

[Implementation guide](docs/IMPLEMENTATION_M2D_ENCRYPTED_LEDGER.md) · [Merged PR #9](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/9) · [39-test GitHub Actions run](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43709171698)

Sensitive account labels, transaction descriptions/references/categories, and audit text are encrypted with randomized AES-GCM envelopes and externally configured versioned keys; read-only strict schema migration and offline rotation helper included. **Numeric amounts, balances, dates and stable metadata are still unencrypted; the application is synthetic-only and deliberately rejects real financial records.** Your historical returns are not needed for continued development.

## M2d-2 — Reviewed cross-account movements (2026-11-15)

Read-only [movement review endpoint](docs/IMPLEMENTATION_M2D2_MOVEMENTS.md) identifies *unverified* candidate matches between your own bank accounts only when both sides are already reviewed, have equal amounts and a unique opposite-side match within two days. Ambiguous and single-sided matches remain exceptions. Loan principal, cash withdrawals, donations, zakat, investments and tax payments are observed separately from salary/business receipts; this **does not** calculate verified debt balances, investment gains, deductions or FBR tax. [Merged PR #10](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/10), [44-test green CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43709644891). Real-data mode still disabled.

## M2e — Loan and transfer recording (2026-11-15)

[Implementation documentation](docs/IMPLEMENTATION_M2E_LOANS_TRANSFERS.md) · [Merged PR #11](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/11) · [55-test successful CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43712136211)

The synthetic-only backend now records loan obligations/receivables with explicitly stated opening balances, individual bank allocations of principal and markup, and owner-confirmed own-account transfer pairs. It never assumes loan disbursements are taxable income, treats markup as automatically deductible, or presents owner confirmation as independent evidence. No tax figures are certified. Loan/transfer links can now be corrected with a separate append-only encrypted audit; this remains a prototype. Real financial-record ingestion is **disabled** pending complete privacy/security and document-adapter acceptance.

## M2f — Audited corrections to financial links (2026-11-15)

[Implementation guide](docs/IMPLEMENTATION_M2F_REVERSALS.md) · [Merged PR #12](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/12) · [61-test GitHub Actions](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43713209678).

Incorrect synthetic loan allocations and owner-account transfer confirmations can now be reversed with a documented reason and immutable audit history; active-only uniqueness allows corrected relinking. The original financial documents/transactions are never silently deleted. All such records remain **synthetic only**; there is no certified tax savings, tax computation or secure real-user upload workflow.

## M2g — Historical cash-in-hand records (2026-11-15)

[Documentation](docs/IMPLEMENTATION_M2G_CASH_WEALTH.md) · [Merged PR #13](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/13) · [68-test hosted CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43714829408).

The synthetic app now maintains owner-declared dated cash openings, reviewed bank withdrawal/deposit allocations, unverified manual cash spending/receipts, audited corrections and a July–June cash wealth movement bridge. It returns **null rather than zero** when historical opening evidence is missing. This is **not** complete net worth, a verified FBR wealth statement, a tax deduction, or an invitation to upload actual private documents.

## M2h — Historical partial financial position (2026-11-15)

[Implementation details](docs/IMPLEMENTATION_M2H_RECORDED_WEALTH.md) · [Merged PR #14](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/14) · [76-test CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43715555529).

The synthetic-only backend combines observed bank balances, declared cash and recorded borrowed/lent loan principal into a *registered-component position* as of any date, with historical FY opening/closing comparisons. Missing, conflicting or stale bank data propagates NULL, not fabricated money. This is **not verified net worth or an FBR wealth statement**, and legally verified tax calculations are not yet implemented.

## Current engineering checkpoint — M2i–M2l (2026-11-15)

Four further owner-independent PRs are merged: [#15 keyed bank import IDs](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/15), [#16 synthetic bank/IRIS PDF preview](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/16), [#17 encrypted historic asset snapshots](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/17), and [#18 official Pakistan tax-year source registry / narrow TY2026/TY2027 salary slab preview](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/18). Latest hosted validation [108 tests passed, PostgreSQL 18 PASS](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43748625041).

**Synthetic-only development milestone, not production readiness.** Real Pakistani bank and FBR PDF formats are NOT yet supported: only fixed synthetic previews. **Existing bank amounts, balances, dates and metadata remain plaintext** despite keyed fingerprints and separately encrypted asset snapshots. Mixed-income FBR tax due, capital gains and deductible amounts are NOT computed or certified. Official tax references, historical filing reconciliation, full private storage + MFA + backups, and prior returns require later acceptance before real uploads. The owner explicitly keeps source GitHub PUBLIC during development; it may hold code/docs/synthetic data only. See [latest handoff](docs/CURRENT_HANDOFF.md).

## M2m — Encrypted financial-event journal groundwork (2026-11-16)

[Implementation](docs/IMPLEMENTATION_M2M_PRIVATE_EVENT_VAULT.md) · [Merged PR #19](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/19) · [116-test PostgreSQL 18 CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43750827782).

The **new, separate synthetic financial-event table** encrypts all meaningful economic fields including amounts and posting dates in one authenticated payload, and uses a dedicated keyed blind index to retrieve events by tax year and source. This is **not** a migration of the pre-existing bank/loan/cash tables; those numeric/date/relationship columns remain readable in the old development schema. Real financial data remains prohibited and `APP_DATA_MODE=real` still fails closed.

## M2n — Read-only encrypted migration review (2026-11-16)

[Implementation guide](docs/IMPLEMENTATION_M2N_MIGRATION_PREFLIGHT.md) · [PR #20 merged](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/20) · [121-test green CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43751406602).

The application can now *preview*, but does **not execute**, conversion of reviewed synthetic legacy bank transactions into M2m's encrypted event journal. Missing classifications, unreviewed overlaps and source conflicts are surfaced explicitly, with no automatic writes or double-counting. **Legacy monetary amounts and dates remain plaintext**. Real finance documents remain prohibited.

## M2o — Verified backup-first migration rehearsal (2026-11-16)

[Implementation documentation](docs/IMPLEMENTATION_M2O_VERIFIED_CANDIDATE_MIGRATION.md) · [Merged PR #22](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/22) · [129-test green CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43754350890).

An explicit offline synthetic-only CLI now **backs up, independently restores, and transactionally migrates reviewed bank transaction mirrors** into a new encrypted candidate database, with tax-year/account amount parity and rollback protection. It NEVER replaces the source ledger or mixes v2 entries into original tax totals. **Legacy bank/loan/cash amount, date and relationship SQL fields remain PLAINTEXT in source and candidate; actual private documents are not permitted yet.** The copy tool is SQLite-only; hosted PostgreSQL18 verification covers schema integrity, not live Postgres data migration.

## M2p — Broader personal CFO direction (2026-11-16)

**The scope is not limited to a tax calculator.** The application is designed as a single-user private **personal CFO and evidence-based adviser** first, with an eventual optional product for families, self-employed professionals and accountants. Domain boundaries allow expansion across bank/credit/cash, investments, loans, property, insurance, cashflow, goals, Pakistan FBR tax, long-term planning and evidence-backed advice.

**New code:** [PR #23](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/23) merged [136-test CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43756223286) — hypothetical cashflow/reserve/goal forecasting and private encrypted-journal-only CFO briefing. [Current status](docs/PROJECT_STATUS.md) · [Architecture](docs/CFO_PLATFORM_ARCHITECTURE.md) · [Coverage matrix](docs/REQUIREMENTS_COVERAGE_MATRIX.md).

**Still synthetic-only:** no real documents or professional financial advice; earlier financial amounts/dates/links remain plaintext until protected migration. `APP_DATA_MODE=real` must remain disabled. Public GitHub holds no genuine owner financial/identity data.

## M2q — Investment holdings and cost basis (2026-11-16)

[PR #24 merged](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/24) · [144-test green CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43757173920) · [implementation](docs/IMPLEMENTATION_M2Q_INVESTMENT_COST_LOTS.md).

New synthetic FIFO cost-lot calculations can account for documented **opening investment holdings acquired before the first statement**, purchases, partial sales, fees and illustrative July–June realized arithmetic gain/loss, without automatically counting bank transfers or investment contributions as profit. They do not verify NCCPL/broker records, market values, applicable FBR capital-gains tax or suitability. Source financial information remains fictional, legacy monetary confidentiality is still incomplete and real-data mode remains disabled.

## M2r — progress toward confidential real-data readiness (2026-11-16)

[PR #27 merged](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/27) · [153-test PostgreSQL schema CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43761634183) · [sealed archive guide](docs/IMPLEMENTATION_M2R_ENCRYPTED_ONLY_ARCHIVE.md) · [delivery gates](docs/DELIVERY_GATES_AND_RELEASE_READINESS.md).

Offline *synthetic-only* encrypted archival export can now preserve all recognized SQL tables/rows without exposing old bank/loan/cash amounts/dates/linkages in the archive. Source remains intact, including original PLAINTEXT columns; **this is not an operational encrypted PostgreSQL database or authorized real-data intake**. G1 active confidentiality, G2 private MFA/deployment and G3 genuine bank/IRIS parsing are next. No fabricated launch date based on initial development hours; release readiness is evidenced through G0–G5 acceptance.

### Real-document readiness and accountant workflow (2026-11-16)

[Design requirements for private working-paper evidence](docs/ACCOUNTANT_WORKING_PAPER_AND_EVIDENCE_WORKFLOW.md) · [Issue #30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30). The future private CFO must support encrypted password-protected bank statements, independent **filed vs accountant draft** source states, Excel formula provenance, account-period coverage and reviewer-confirmed transactions/wealth discrepancies. **Not implemented for real data.** This repository contains no private passwords, owner documents, bank figures or accountant communications; current `APP_DATA_MODE=real` remains prohibited.

## Product-plan v2 update — accountant-ready statement-led owner experience (2026-11-16)

The owner requested a comprehensive plan revision based on generalized lessons from private bank, filed FBR, unfinished accountant-workbook, tax withholding and evidence-request **document types**. The [new formal product plan](docs/PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md) specifies one-time 2023+ onboarding, irregular ongoing bank statement uploads, account×period coverage, reliable transfer/loan/investment classification, linked exception resolution, lawful year-specific FBR calculations, verified-vs-unknown wealth, read-only draft workbook audits and an accountant-ready report/export.

**The system is a personal CFO, not an autonomous accountant or only a tax calculator.** Owner and accountant retain decisions and signoff; filed source status requires official evidence. Existing privacy and release gates remain unchanged: this PUBLIC GitHub contains only synthetic code/design, not actual private financial documents, passwords or confidential messages. All v2 features beyond existing synthetic primitives remain **planned**, and `APP_DATA_MODE=real` still refuses startup until the G1–G3 security/source gates pass.

Latest verified executable milestone: [M2s PR #32](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/32) (178 tests, PG18 PASS). [Historical and actual feature status](docs/PROJECT_STATUS.md). Next owner-independent code work: [Issue #21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21) canonical confidential finance, then [#28](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/28) private MFA, [#29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29) genuine sources and [#30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30) accountant-workbook/exception workflow.

## Current engineering progress — G1-a/G1-b (2026-11-16)

- **G1-a [PR #34 merged](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/34)**: distinct active AES-GCM synthetic bank-source storage, purpose-separated keyed indexes, key continuity, strict balance/row validation and replay; [205-test+PG18 hosted CI PASS](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43775409962). [Implementation](docs/IMPLEMENTATION_G1A_CONFIDENTIAL_BANK_SOURCE.md).
- **G1-b [PR #35 merged](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/35)**: bounded encrypted PostgreSQL18 synthetic data snapshots, independently migrated **empty** recovery DB, transactional restore with all-table row parity, wrong-key and rollback verification; [209-test hosted CI + PG18 restore PASS](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43776281073). [Implementation](docs/IMPLEMENTATION_G1B_PG_RECOVERY.md).

**Security status:** The encrypted backup artifact is **not the live database** and the new confidential bank source is not a complete ledger migration. Legacy original/restored bank/loan/cash financial amounts, dates and links remain plaintext; real-data mode remains explicitly disabled. Next priority [G1-c full PostgreSQL canonical encryption/migration, verified parity, independent recovery and reversible source switch](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21). This project remains private owner-first; GitHub remains temporarily public for only code/docs/synthetic tests. No authentic personal FBR or banking data has been ingested into the app.
