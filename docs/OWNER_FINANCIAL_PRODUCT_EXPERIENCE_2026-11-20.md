# Personal CFO — End-user experience and priority roadmap

Date: 20 November 2026. Status: binding product specification. Owner: one authenticated individual. This replaces the document-verification portal as the primary experience. The existing source-first security rules remain in force.

## What success means to the owner

Within ten seconds of signing in, understand: money across bank accounts (only as of a supported date), where money came from and went this month or year, actual personal income/spending (not own transfers), capital invested with each person and venture, repayments and profit actually received, outstanding obligations, upcoming bills, tax-year position, and what needs clarification. Every meaningful financial figure opens dated supporting transactions and original-source evidence.

Current reality: there is an authenticated mobile PWA and connected read-only Google Drive. SHA-verified monthly bank CSV flows, historical offline PDF statement receipts, dated investment payment candidates and verified property-register costs/sale-profit allocations exist. But source coverage is incomplete; the current Home is technical; Spending, Bills and Tax are placeholders. Current cash, classified income/expenses, full outstanding capital and verified ROI remain unknown. A deployed source feature is not proof that the signed-in user sees it.

## Main navigation

**Home:** clear selected period, four core money answers, financial movement trends only where proven, investments due, recurring bills and a prioritized review inbox. A small provenance note under figures; document processing belongs in secondary pages. Missing ≠ zero, stale ≠ current.

**Accounts:** bank/account picker, historical balance and statement date, coverage/gap warnings, source-backed month/year movement details, transfers, individual rows. Do not combine overlapping statements, mix bank accounts, or call gross debits expenses. Any balance is historical until all relevant recent accounts have reconciled coverage.

**Transactions:** searchable/filterable rows by month, year, Pakistani tax year, person/description, bank source, direction, amount, category and review state. Each event traces to SHA-verified source and stable HMAC without leaking source references. Mobile stacked rows, desktop table, owner review action. Intra-owner transfers excluded from income/spending until independently matched.

**Spending & bills:** real categorized monthly spend, income, recurring bill due dates, expense changes, comparisons and follow-up. Display unknown when coverage/transfer classification missing. Bank-labelled profit, tax and fees can be shown as narrowly verified separate categories.

**Investments:** partner → distinct ventures → dated bank candidate movements → principal invested, capital repaid, profit received, outstanding principal and future expected payment. These last fields must stay unknown until individually verified; candidate outgoing/incoming transfers and workbook sale-profit share are NOT automatically returns or cash. Preserve distinct ventures with a common person.

**Tax & wealth:** Pakistan tax year 1 July–30 June, year-on-year filed-versus-accountant-draft comparisons, bank withholding and source evidence, wealth register and accountant review. The filed 2024–25 return is not the unfinished 2025–26 working paper; do not claim an unverified tax amount.

**Review inbox:** ambiguous transactions, unmatched own transfers, missing periods, changes to Drive documents, expected repayments, accountant questions. Open original evidence, choose purpose and add a note. Persistent append-only encrypted comments require independent contemporary full encrypted off-device database backup + disposable restore and migration acceptance; UI must never falsely claim a note was saved before activation.

**Documents:** original files remain read-only. Display exact source revision/SHA, coverage, gaps/duplicates and review. A separate organized copy folder, if authorized, never changes the originals.

## Global date context and financial semantics

One consistent control for **month (YYYY-MM), calendar year (January–December), Pakistan tax year (July–June), all available evidence**. Where useful, a **latest verified historical snapshot** may remain independently labelled as-of. Period switches filter real dated CSV month records, dated candidate payment rows and dated property-sale evidence; a whole-year statement PDF cannot be apportioned into unverified monthly rows. A property currently held in the register cannot be assigned a market value in an earlier month. Show covered months and missing months; zero coverage is not a zero transaction amount. No chart or year-over-year claim without sufficient data. Client keeps period context in memory only and clears sensitive observations at session expiry/source invalidation.

## Visual and interactive definition of done

Mobile-first tap targets >=44px, readable PKR and dates, bottom navigation and desktop sidebar, source coverage/date under figures, accessible labels and keyboard navigation. Home amount → account/person → source row → evidence/review. A period switch updates every supported view without making unverified amounts current. No decorative synthetic graph in production. Loading, source stale, partial coverage and missing evidence must be visible and distinct. No private info in public code/CI, logs or untrusted HTML; render all Drive text as textContent. Original content not stored in browser persistent storage.

## Implementation order — tracked and dependency aware

| Priority | GitHub issue | First meaningful user-visible acceptance | Constraint |
|---|---|---|---|
| P0 | [#265](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/265) | Shared month/year/Jul–Jun tax-year selection, source-scoped monthly bank activity, historical account drilldown, dated investment candidate filtering | No invented complete-year income or current cash |
| P1 | [#266](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/266) | Real source-reconciled CSV transactions, search and filters, review state | Pinned source SHA, every running balance checked, no unsupported PDF parsing |
| P2 | [#267](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/267) | Partner/venture evidence ledger with dates and distinctions between candidate money, principal, repayments, profits and outstanding | Actual purpose/repayment still needs confirmation |
| P3 | [#268](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/268) | One-screen ambiguous event review and persistent encrypted notes when safe | Full off-device database backup/disposable restore and live schema gate |
| P4 | [#269](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/269) | Classified spend, recurring bills, real charts, tax-year/wealth comparison and follow-ups | Multiple complete bank histories and accountant evidence |
| P5 | [#270](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/270) | All-bank account-opening history, WhatsApp conversation evidence, source/transaction/venture matching | Additional original statements/screenshots arrive incrementally; messages are claims not settlement |

P0–P2 can deliver partial factual results now; P5 is not an artificial prerequisite. Do not create more VMs or ask for repeated OAuth, token, owner Terminal commands or new paid services to complete the UI.

## Release gates

Source-supported money only, full strict frontend/backend CI, zero fabricated figures, guard missing/duplicate years and June 30/July 1 tax boundary, stale session/source invalidation, owner MFA same-origin no-store endpoints, mobile/desktop legibility, existing Railway services online. Distinguish **code merged**, **deployed**, **authenticated owner UI observed**, and **complete financial evidence**. Mark individual tasks complete only when proven, and keep unknown answers explicit.

Keep prior source-first lessons LL-01, LL-05, LL-08, LL-09 and LL-11. This document is the canonical UX roadmap and should not be duplicated into another giant dated handoff.

## Verified implementation checkpoint — 20 November 2026

**Product work deployed to the existing Railway frontend/API, with no extra VM or new permanent service:**

- [#271](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/271) **P0:** global month, calendar year, Pakistan tax year (July–June), all available; RAM-only source evidence and clear missing-month coverage, Home/Accounts/Investments period panels.
- [#272](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/272) **P1:** owner-MFA and current original SHA-bound bank CSV row projection, stable HMAC, masked account references, exact running balances, private activation flag P7_OWNER_TRANSACTION_ROWS_ENABLED=1, searchable mobile Activity with bank/period/direction/status filters.
- [#273](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/273) **P2/P3/P4 factual slices:** grouped partner → ventures, unverified principal/repayment/profit/outstanding fields, source-backed review queue, exact bank-labelled charges/profit/tax withholding for selected period. Persistent owner transaction classifications/notes **NOT active**.
- [#274](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/274) **P4 trend:** one-source-at-a-time monthly gross bank movement chart for selected period; missing months explicitly UNKNOWN and no double-counted across accounts.
- [#275](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/275) **UX correctness:** Home bank profit and recorded property-sale share follow selected source-supported period. Dated historical closing balance and latest property purchase-cost basis are explicitly not current cash/historic valuation.
- [#276](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/276) **Mobile navigation:** financial-first order and reachable Tax & Wealth / Documents with 44px tap targets.

All six PRs merged with exact-head green applicable GitHub Actions; latest frontend deployment SUCCESS at `d79c4e700eae3c8dee88aa3ffe3a666fe8977927`, backend source/row projection at `dfb6d15e92cfe924aa9eda5eb91a58e3ea0321fa` SUCCESS, existing Postgres ONLINE. No additional VM/cost-bearing service and approved original Drive files unchanged.

**Not completed and kept OPEN in tracking issues:** full all-bank/current balance, true monthly household income/expenses/bills, venture-specific verified principal/repayments/realized ROI, transaction-level saved notes and category corrections (need restored encrypted full DB backup and reviewed schema), verified filed-vs-accountant-draft tax analysis, all-bank history and WhatsApp contextual matching. Data for future bank periods and people may be uploaded later; supported source gaps must remain explicit. **Actual signed-in owner browser interaction has not been observed by tools**, so these are CI+deployed features, not final end-to-end personal acceptance. Do not invent a completion claim or schedule more VM tests.

## P8 audited UI and remaining financial truth — 20 November 2026

**Deployed owner-facing work:** [PR #278](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/278) full self-contained responsive UI styling, private MFA brand treatment, modern financial-first Home hierarchy, compact mobile navigation with complete More menu, readable period cards and audit evidence disclosure; source-backed transaction detail modal with safe masked row narration and reset on source/session expiry. [PR #279](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/279) one-tap unclear-row filter and three-distinct-month SAME-source repeating-bank-movement candidates, NEVER called due bills, expected repayments or expenses. Existing owner session and Drive read-only boundaries, source SHA and offline PDF safety unchanged.

**Proof levels:** #278 exact PR-head frontend CI SUCCESS, merged `4b0546be`, existing Railway frontend SUCCESS; #279 exact PR-head frontend CI SUCCESS, merged `66164a01`, existing frontend SUCCESS; existing backend, Postgres online with no pending work. Static audit checked every literal source renderer element ID exists once in HTML, all navigation targets valid, CSS block delimiters balanced, dialog/source disclosure well paired; no new browser persistence. External read-only browser audit confirmed /app is gated behind owner-password + MFA and visually saw ONLY the unauthenticated login. **No authenticated owner dashboard screenshot, interactive browser traversal, or signed-in visual acceptance has been obtained; CI/styled source alone is not a human usability sign-off.**

**Source inventory:** the approved read-only Drive connector already exposes a draft 2025–26 accountant Excel workbook, a prior-year tax-return PDF, historical bank Excel/CSV/PDF records and other private material. These are not newly uploaded in P8, and no source content, private amounts, file hashes, account identities or screenshots were committed to GitHub. Source-specific adapters remain required before showing unsupported periods/account activity; a draft is NOT a filed tax return.

**Outstanding and not falsely marked complete:**

1. [#268](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/268): save real per-event purpose/classifications and encrypted comments only after independent contemporary FULL encrypted owner PostgreSQL backup, verified off-device copy, disposable restore and reviewed live migration/source-event HMAC acceptance. Current transaction modal is read-only and says so.
2. [#269](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/269): confirmed household spend, actual due/overdue recurring bills, full tax-year filed-vs-accountant-draft calculation and wealth/ROI need complete statement coverage, ownership/transfer mapping, cash settlement and accountant-source audit. The live repeating patterns are **unverified payment clues**, not outstanding bills.
3. [#267](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/267) and [#270](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/270): complete original account-opening-to-present bank histories and future investment-counterparty WhatsApp screenshots will be supplied incrementally by the owner. Safe source-specific import, gaps/overlaps, cross-account matching and venture-purpose clarification then enable confirmed invested principal, repayments, profits and outstanding balances. Do not silently synthesize missing records or re-request originals already in the approved Drive folder.
4. [#265](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/265) and [#266](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/266): core implementation is deployed; authenticated owner UX acceptance, additional bank-format coverage and source-row review-save acceptance remain open.

**Next changes must stay on this contract:** improve only verified source-backed owner insights and outstanding purpose review, no repeat of paid VM probes, no extra external hosting or dummy dashboard amounts. Original Drive read-only. Unknown financial claims display unknown.
