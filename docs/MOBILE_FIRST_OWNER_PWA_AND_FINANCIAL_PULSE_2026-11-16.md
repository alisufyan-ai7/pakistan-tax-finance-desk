# Mobile-first owner dashboard and installable PWA — accepted product direction

**Owner request: 2026-11-16.** This document is the binding **Personal CFO project-only** UX roadmap, not broader account memory. Refer to [project scope isolation](PROJECT_CONTEXT_AND_INFRASTRUCTURE_ISOLATION.md), [owner MVP plan](OWNER_MVP_COMPLETION_BLUEPRINT_2026-11-16.md) and [release gates](DELIVERY_GATES_AND_RELEASE_READINESS.md).

## Definition of a useful Personal CFO home screen

**Five-second understanding:** on opening a phone-installed app, the owner should immediately know (1) how **this calendar month** is going, (2) whether expenses are actually rising against the comparable period, (3) which **recurring bills** are outstanding or have only *unverified* payment status, (4) **which investments** are owned and their maturities/expected return dates, and (5) the concrete **follow-ups** due now. Use plain language and clear evidence state, not accountant or database jargon. Eye-catching means strong hierarchy and legible contrast, not hiding missing evidence or decorating guessed figures.

**Proposed home-screen priority order:**
1. **Today/month pulse:** month-to-date spend, comparable previous month's same days, coverage confidence, income/cash *only if verified*, near-term bill count and pending follow-ups
2. **Bills to check:** named merchant, amount, due date, cadence, source of schedule, whether payment is bank-matched, and owner task (confirm/pay/review). Never label an unmatched candidate “unpaid” as fact, never pay automatically
3. **Investments:** instrument type, source-backed principal and current value as independent concepts, maturity, contractual expected coupon/dividend/interest, last receipt and next review date. A term quote is not actual interest or guaranteed future yield. Variable investments have unknown/unbounded returns; actual posted receipts require evidence. Withholding/tax classification remains separate
4. **Expense changes:** exact comparable month-to-date windows; category movements; recurring vs one-offs; distinguish own transfers, principal investment, taxes, cash withdrawals, and actual spend. Detect spikes only with source-complete windows and reviewed classifications
5. **Follow-ups:** missing statements, accountant draft discrepancies, invoices to verify, return date elapsed without evidence, tax evidence due, unmatched transfers. Owner can choose to mark tasks done only with audited, authenticated actions after G1/G2/G3

**Data sources and trust:** every money field must carry amount in exact integer PKR paisa, legal-owner scope, source IDs, date range, completeness and validation state. Unknown must be `null`, never zero. User-facing confidence labels:
- **Verified from source** — approved canonical ledger, complete account/date coverage and reconciled evidence
- **Awaiting confirmation** — candidate or owner-reported without bank/contract evidence
- **Estimate/contract quote** — source-supported assumption but not realized or guaranteed return
- **Missing information** — no inference or manufactured confidence
- **Illustrative preview** — public static fictional figures, never owner's information

Calendar months (expense and bill management) and Pakistani tax years **July–June** are different views. A tax-year selector must never silently change a separately dated month pulse. Finance/IRIS “DRAFT” vs “FILED” must stay sharply separated.

## Completed development slices (synthetic only)

- [**PR #64**](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/64) installable PWA, squash `f6624e673376431d82f46dd067373f3c1c7744ad`, [Node CI 43895296481](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43895296481): **16 tests PASS**. HTTPS `manifest.webmanifest`, 192/512 PNG icons, install help, iPhone Safari Share/Add to Home Screen and Android browser install guidance, bottom thumb nav with safe-area. Service worker **does not handle fetch, Cache API, financial offline data, push or sync**. Requires network when opened.
- [**PR #65**](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/65) source-gated owner-action contract, squash `6f7058ae0c1d20a2cc167c44acaa02e7dc5596d5`, [CI 43896186521](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43896186521): **381 pytest + PostgreSQL18 encrypted-bank/backups/candidate/typed-parity/readonly PASS**. `backend/app/owner_action_brief.py` models comparable coverage, bills, dated quoted returns, and due follow-ups with strict synthetic-only and cross-owner checks. **NOT deployed as a true owner financial API**.
- [**PR #66**](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/66) glanceable owner dashboard, squash `e8fc8c55777a13b4fb3d8a5294ec332f5ec582ba`, [CI 43898274720](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43898274720): **23 Node PASS**. Dark high-contrast month pulse, spend sample vs prior, category bars, due bills/payment status, investment next quoted returns and review tasks, detail drill-down via Transactions and Planning. `DEMO.monthPulse` is an entirely **fictional snapshot as of November 16, 2026**, not current owner money. Older FY transaction samples are separate fabricated illustrative data.
- [**PR #67**](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/67) closed unmerged as redundant: #66's exact-head CI subsequently passed on the combined PWA/backend baseline, and #66 merged.

## Verified Railway live status

The same owner-approved `personal-cfo-dev-sandbox` / `development` Railway Hobby setup is retained. Public URL [Personal CFO PWA preview](https://personal-cfo-frontend-preview-development.up.railway.app/) runs on existing unprivileged Nginx. Latest frontend deploy SHA `e8fc8c55777a13b4fb3d8a5294ec332f5ec582ba`, deployment `88c29222-cb25-4a8b-bcec-467f994ecb9c` **SUCCESS**. The backend private FastAPI and PostgreSQL18 remain **SUCCESS** with **no public domain/TCP**; only one same-origin synthetic status route is proxied. External HTTP checks fetched PWA manifest, no-cache service-worker script, and `/api/preview/status` (back end says connected, canonical finance schema **NOT CERTIFIED**). Live browser QA confirmed five pulse sections, bills in Transactions, expected dates and variable/quoted return separation in Planning, install guidance, correct fictional warnings and private status. Real mobile device installation and full accessibility/device-loss/offline testing **still pending**.

**Privacy/cost:** one publicly accessible synthetic website, private API + Postgres in the same approved project. Not free per-service: Railway Hobby $5 plan has metered usage. Do not infer authentication or private owner safety from a PWA install and private routing. All real financial input/return/payment/filing remains disabled. No current account-level or other-project memory used.

## Next independent engineering work packages

**P0 – G1**: authoritative active encrypted canonical economic PostgreSQL write/read store with bank, loan, cash, asset, investment, withheld tax and filed/draft evidence; source and year parity, double count prevention, backup-first reversible cutover, active plaintext retirement, independent offsite recovery and key lifecycle. **Release gate unchanged.**

**P0 – G2**: private owner MFA/recovery, session/device revocation, rate limits, CSRF, provider-scoped secrets, read-only/minimally privileged DB roles, TLS, audit and security testing; no real public data before acceptance.

**P0 – G3**: genuinely validated bank, broker/FBR documents and immutable source files in private isolated converters, source-month gap detection, recurring bill schedule owner confirmation and matched payment evidence, investment contract and coupon receipt evidence. Unknown formats quarantined.

**P1 – Owner functional UI**: connect authenticated server-side `owner_action_brief_v1` data only after G1/G2/G3, period filters for real months, detail and provenance click-through, recurring schedule approval, investment maturity + actual received return timelines, notices and responsible actions. Keep the front-end mobile-first and PWA capable, with disabled real inputs until secure.

**P1 – G4 & accountant**: independently verified effective-year Pakistan tax statutes, WHT treatment, mixed income, wealth and draft-vs-filed review/export source links.

**Optional future PWA features** (only after security and owner opt-in): push notifications for due bills/coupons/missing evidence, encrypted offline mode with device-lost/logout invalidation plan, biometrics through WebAuthn where supported, store packaging. **Do not silently enable background notifications or cache private account data.**

## Definition of done

A real owner dashboard is NOT done because synthetic cards render or Android shows an install button. Real completion requires source-linked verified figures, audited private user actions, live secure host, recovery proof, genuine statement reconciliation, month/bill/investment correctness vectors and successfully tested physical-device install/accessibility. G1–G5 release gates must independently PASS before `APP_DATA_MODE=real` is considered.
