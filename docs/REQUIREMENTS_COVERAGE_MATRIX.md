# Owner requirements coverage and remaining gates — 2026-11-16

The application is for the owner only at present, with optional later productization; use GitHub as the source of truth. **Product Plan v2 (2026-11-16):** [The formal accountant-ready product plan](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md) adds product-level acceptance for ongoing statement-led bookkeeping, workbook/source diagnostics, tax-withholding reconciliation and a working accountant package. Existing partial technical foundations remain partial; these new workflows are **not built**.
 **No real personal records may be uploaded to the public repository or the synthetic prototype.** This matrix is an execution checklist; a checked engineering primitive is NOT synonymous with an end-to-end user-ready feature.

| Owner expectation / requirement | Current implementation | State and next acceptance gate |
| --- | --- | --- |
| Keep transaction/investment history from 2023/2024 onward | Historical TY2023+ records, immutable snapshots, reviewed source movement, protected-event store | **Partial**; real multi-year bank/broker/FBR import and true tax-year reconciliation untested |
| Occasional bank statement uploads, auto cumulative year-to-date | CSV synthetic imports, reconciliation, HMAC dedup, reviewed classifications | **Partial**; real-bank layouts/PDF sandbox, incremental cross-file completeness, app security, auto recompute pending |
| Multi-source personal salary, business, rent, investments, other income | Categories and narrow salary scenario; FBR year source registry | **Partial**; actual gross income reconciliation, business expense eligibility, separate/final/adjustable tax rules and tax credits pending |
| Lawful tax reduction and recommendation | Evidence-required source-indexed opportunity cards | **Partial**; tax-law eligibility, evidence and amounts cannot be claimed yet |
| Previous 3–4 years of filed returns/wealth | Synthetic prior filing records and continuity check | **Partial**; private FBR IRIS parser, versioned filed return reconciliation, amendments/limitations check pending |
| Loans borrowed/given; interest/markup and repayment tracking | Account-backed loan principal and markup, audited correction | **Partial**; real contracts, schedules, creditors, missed payments and end-to-end secure intake pending |
| Gifts, donations, Zakat, charitable payments | Reviewed categories, non-earnings movement distinctions, opportunity prompts | **Partial**; recipient proof, correct TY and applicable legal treatment needed |
| Cash-in-hand, bank transfers and wealth | Cash declared openings and corrections, cross-bank matching and partial observed wealth | **Partial**; complete asset inventory, money/date confidentiality, cost-lot & wealth reconciliation pending |
| Investments/crypto/gold/property/vehicle and returns | Encrypted declared asset snapshots | **Partial**; broker/NCCPL evidence, transactions, realized gains, holding cost lot, market data rights, tax determination pending |
| Adviser/CFO capabilities | M2p synthetic scenario and source-limited briefing, architecture roadmap | **Partial**; real personal suitability and consent, risk profile, obligations, insurance, goals, budget, retirement, adviser's evidence/state needed |
| Minimal owner manual work | Reviewed classifications and missingness flags | **Partial**; exception queue with auto learned rules, reminders and one-time onboarding pending |
| Privacy and secret handling | AES-GCM event/evidence storage, offline backup rehearsal, MFA groundwork | **BLOCKING**; old bank/loan/cash fields plaintext; production MFA recovery, private encryption, offsite recovery, no actual uploads yet |
| Access across devices/mobile | Prototype local UI | **Not delivered**; private deploy, responsive UX and browser acceptance pending |
| Eventual FBR IRIS income return/wealth export | Synthetic historic records and source index | **Not delivered**; deterministic mixed-income calculation, source completeness, FBR format and controlled manual filing pending |
| Future multi-user SaaS, accountants and households | Modular monolith/ownership concept + forward-looking contracts | **Design only**; strong tenant+entity isolation, regional laws, subscriptions, RBAC, lawful consent/deletion/export needed before public product |
| Performance, resilience and scale | PostgreSQL migration CI, bounded scanning, deterministic pure modules | **Partial**; large-fixture load tests, query indexes, jobs, read projections, observability, encryption key rotation and backpressure pending |

## Ordered, owner-independent engineering backlog

**P0 — complete real-data safeguards:** legacy field encryption / safe migration and active projection switch with rollback; tenant/owner scope architecture; key & backup disaster recovery; secure isolated document parsing and test coverage; product-grade auth and secure deployment tests. No bypass to `APP_DATA_MODE=real`.

**P1 — personal finance completeness:** genuine approved bank/FBR/broker adapters once safe, cross-statement coverage, source versioning, investment lots, obligations/recurring bills, cash-flow and wealth reconciliation, entity and FX boundaries. Build synthetic fixtures in advance of owner documents.

**P2 — tax/advisory correctness:** source-reviewed and effective TY2023+ salary/non-salary heads, tax withheld/final/adjustable, expenses/credits/Zakat/donation validation, what-if tax strategies and individual vs company treatment, legal review and exact golden vectors, filing readiness and exports, human approval.

**P3 — the full personal CFO UX:** financial briefing + budgets, liquidity alerts, goals, insurance coverage, debt decisions, investment suitability/concentration, scenario comparisons, recurring reminders, periodic personalized review, mobile apps if justified.

**Future product:** tenant-isolation redesign, accountant collaboration under invitation, commercial tax/advice/privacy review, regional tax jurisdiction plugins, scalable background processing, billing and market-data permissions. **Do not prematurely require these for the private owner rollout.**

## Definition of done

All domains must demonstrate provenance, reconciliation, unknown-vs-zero semantics, safe corrections, deterministic tests, security/permission acceptance, meaningful UI and usable exports where relevant. A future CFO recommendation must cite its evidence and assumptions, offer human-confirmable actions, avoid autonomous investment/tax moves and never assert guaranteed savings.
## M2q progress update — 2026-11-16

- The **investments/crypto/gold/property** row remains **PARTIAL**, not complete. Added an independently tested synthetic FIFO cost-lot pure engine (opening 2023/prior inventory, buys/sells, fees, partial quantities and year-grouped realized accounting results), [PR #24](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/24), [144-test CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43757173920). This does NOT import brokers/NCCPL or certify taxable gain; no account-bank-asset integration or complete wealth calculation yet.
- The **privacy and real-data** row remains **BLOCKING** because older bank/loan/cash metadata remain plaintext; adding private event and cost-lot simulators has not closed that gate.

## Added requirements from external budgeting research — 2026-11-16

| New requested/derived capability | Status as of this update | Evidence and acceptance / next step |
| --- | --- | --- |
| Recurring bills and subscriptions with upcoming due estimates | **PLANNED, NOT IMPLEMENTED** | Build synthetic reviewed-merchant cadence model; annualize only observed periods; missing statement coverage must lower confidence or return unknown. [Issue #25](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/25). |
| Duplicate services, rising merchant costs, and category leakage | **PLANNED** | Source-linked observations, account/legal-entity ownership, rule/version provenance, review of essentials vs discretionary. Savings are hypothesis only until verified. |
| Household/utility/telecom invoice explainer | **PLANNED after document security** | Real private PDFs sandboxed; date/amount/fee/withholding parsed with confidence and linked to reviewed bank payments, never invent tax credit. |
| Natural-language personal CFO household-spending questions | **PARTIAL FOUNDATION ONLY** | M2p synthetic planning/briefing exists; real source grounded queries/approval still not built. |
| Optional shopping, meal plan and administrative assistance | **IDEA / OPTIONAL FUTURE** | Explicit opt-in, Pakistan price provenance and privacy controls, no harm to core CFO/tax scope. |
| Cross-chat GitHub source-of-truth handoff | **DOCUMENTED STANDING RULE** | Root `AGENTS.md`, `docs/CHAT_CONTINUITY_PROTOCOL.md`, `docs/PROJECT_DECISIONS_AND_SCOPE.md` require agents to read current GitHub and commit all material decisions/CI/next tasks before ending or chat cap. |

The newspaper [source assessment](RESEARCH_AI_HOUSEHOLD_BUDGETING_2026-11-16.md) is an idea input, **not evidence of realized AI savings, local market demand or the completion of these features**. Core original requirements and P0 financial privacy remain higher priority.

## M2r and release-readiness coverage — 2026-11-16

- **Privacy:** PARTIAL (not done). M2r sealed-only archive contains no raw financial amount/date/linkage SQL fields, backed by independent encrypted source recovery, [PR #27](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/27) and [153-test CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43761634183). Active legacy source and candidate **still plaintext**; no real upload authority. Gate G1 still BLOCKED.
- **Private deployment:** BLOCKED. Current local-only host/client restrictions are intentional; a remote proxy deployment would fail or require a reviewed authorization design, not a trivial port change. Gate G2 [Issue #28](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/28).
- **Genuine bank/IRIS parsing:** BLOCKED. Synthetic fixed PDFs only; no authenticated real source layout certified. Gate G3 [Issue #29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29).
- **Owner completion outlook:** tracked by [G0–G6 objectively tested release criteria](DELIVERY_GATES_AND_RELEASE_READINESS.md), not synthetic test-count-based percentage or ungrounded promised date. Personal CFO/wealth/tax MVP requires verified G1–G5.

## Added: draft-accountant and private source-review requirements (2026-11-16)

| Requirement | Status | Implementation acceptance |
| --- | --- | --- |
| Private bank PDF unlock with ephemeral per-document passwords | **BLOCKED (G1–G3)** | No saved/logged password; never ask for login/PIN/OTP; synthetic encrypted-PDF tests, sandboxed conversion, encrypted originals |
| Multi-bank statement format detection, coverage and running balance | **PARTIAL synthetic / REAL BLOCKED** | Versioned adapters, XLS-vs-error-stub validation, account×period holes, page carry-forward, matched transfer sources and no duplicate import |
| Accountant working paper **DRAFT/REVIEWED/APPROVED**, separate from IRIS **FILED** | **PLANNED** | Workbook sheet/formula dependencies and sources, field confirmation, imported versions, final FBR acknowledgment provenance/revision |
| Filed wealth-to-next-year opening reconciliation | **PARTIAL synthetic** | Missing/nonbank assets and source revision evidence create review exceptions; draft mismatches not treated as legal filing errors |
| Third-party transfers, loans, property, investments, withholding review | **PARTIAL / source integration blocked** | Evidence-linked classification queue, owner/accountant answers and immutable audit; unsupported amounts excluded from certified tax |
| Secure communication/explanation queue | **PLANNED** | Private correspondence attachments are not bank/FBR evidence; owner approval, accountant collaboration optionally later; screenshots do not prove voice-message content |

See [`ACCOUNTANT_WORKING_PAPER_AND_EVIDENCE_WORKFLOW.md`](ACCOUNTANT_WORKING_PAPER_AND_EVIDENCE_WORKFLOW.md), [Issue #30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30). No authentic personal data is used in CI or committed; current real-data app remains disabled.

## v2 coverage — source-led accountant-ready features (2026-11-16)

| New or sharpened product requirement | Implementation as currently verified | State / gate |
| --- | --- | --- |
| Reliable intake of password-protected PDF, CSV, XLSX and fake legacy XLS exports by actual content signature | M2s synthetic CSV/XLSX preflight PR #32; synthetic text-PDF preview; no safe genuine encrypted-PDF intake | **Partial synthetic; real G1–G3 BLOCKED** |
| Multi-bank fiscal-year coverage, page/source-row original linkage, duplicate/replayed batch and balance carry-forward | M1 synthetic normalized import, overlap and balance checks, per-year coverage | **Partial**; real multi-layout and multi-year owner acceptance G3 |
| Independent accountant-workbook **draft diagnostics**: formula graph, broken refs, cached formula values, missing investment/wealth tabs, read-only comparison with financial ledger | None end-to-end | **PLANNED**; [#30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30) |
| Distinct draft, accountant-accepted, owner-approved and **officially acknowledged filed** income/wealth versions | Synthetic historical filing model and continuity preview | **Partial foundation**; real source versions + FBR acknowledgement G3/G4 |
| Tax withholding line evidence: unclaimed vs verified adjustable vs final/duplicate vs unknown | Source-indexed synthetic candidate opportunities only | **PLANNED COMPLETE ENGINE**; [#5](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/5) |
| Evidence-linked review inbox for transfers, uncertain credits, loans, investments, asset purchases and tax treatment | Synthetic classification/weak-overlap and reviewed financial link components | **Partial**; owner/accountant decision workflow not implemented |
| Accountant question, requested evidence, owner answer, resolution and exportable review working pack | No secure end-to-end service; requirements existing in accountant workflow spec | **PLANNED**; [#30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30) |
| Automatic cumulative income/expense/tax/wealth recomputation as irregular statements arrive | Synthetic totals and narrow demonstration salary component | **NOT verified as real tax or full wealth**; G4/G5 |
| True personal CFO financial planning (cash reserves, loans, goals, investments, savings/spend anomalies) with evidence and coverage-aware advice | Synthetic hypothetical CFO engine and investment FIFO primitive | **Partial synthetic**; G5 owner UX |

**Primary user value / definition of done:** Owner can securely upload statements, resolve a manageable evidence queue, see documented year-by-year financial and **legally validated** tax/wealth positions, and export an accountant-ready review package **without re-creating separate annual worksheets**. The accountant remains free to inspect/review and the owner approves filing. No guessed refunds, capital gains, net worth, source account ownership, expired deadlines or workbook-final statuses.

## G1-a/b tested security primitives — 2026-11-16

| Security expectation | Verified progress | Still outstanding |
| --- | --- | --- |
| Encrypted operational financial storage | G1-a [PR #34](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/34): authenticated synthetic operational encrypted bank-source batches, HMAC identity, key-loss detection; 205 tests + PG18 PASS | **Only a separate bank source subset.** Old active M1 bank/loan/cash monetary/date/relationship fields plaintext, no complete typed protected canonical ledger or app switch |
| Recoverable PostgreSQL financial data | G1-b [PR #35](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/35): encrypted synthetic full known-table data snapshot, independently migrated blank destination, verified all-table byte parity, transactional rollback and wrong-key checks; 209 tests + PG18 PASS | **Not production/offsite/PITR**, restored legacy SQL still plaintext; key rotation, live database cutover, recovery drill, full canonical migration and data retention policy pending |

**Blocking:** G1 overall is **not done**. No authenticated actual personal bank/FBR files until G1+G2+G3. Next P0 tracked by [G1-c Issue #21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21). The owner remains responsible only for later private infrastructure/real-data acceptance, not synthetic code development.

## Parallel synthetic execution coverage checkpoint (2026-11-16)

- [PR #38](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/38): six explicit **synthetic-only** versioned bank/IRIS layout contracts, format and declared kind gating; actual Pakistani bank/FBR acceptance **NOT implemented**.
- [PR #39](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/39): safe **synthetic-only DRAFT** XLSX cached formula diagnostic, no recalculation/FILED verification or accountant review queue yet.
- [PR #40](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/40): synthetic offline backup-first encrypted PostgreSQL **restored candidate mirror**, full row authentication and transactional rollback, no live canonical accounting source switch, legacy plaintext remains on restored candidate.
- [PR #41 exact-head CI](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43851527422) **253 pytest + PG18 success** proves combined synthetic regressions. G1 live encryption/cutover, G2 deployment and G3 actual formats **BLOCKED**, G4/FBR complete tax and G5 owner-first CFO **NOT CERTIFIED**. Continue independent tracks as per [parallel playbook](PARALLEL_ENGINEERING_EXECUTION.md) while preserving G1–G3 real-data gates and project-only context.

## Chat 3 batch 3 coverage delta — 2026-11-16

[Verified implementation/acceptance detail](CHAT3_PARALLEL_G1_G2_G3_2026-11-16.md). G1 A6: synthetic PostgreSQL-backed encrypted double-entry journal plus neutral confidential bank-source row replay, source-bounded exact balance checks and atomic commit; covered in #76/#79 and PostgreSQL18 CI. G2 F1/F2: independent ephemeral CI-only PostgreSQL restricted-role attestation and synthetic one-time owner recovery-code primitive in #77, **not** integrated persistent owner MFA or deployed Railway role. G3 B5: digest-pinned deny-network worker invocation and strict synthetic adapter protocol in #78, **not** a runtime-vetted production sandbox or certified authentic Pakistani bank/FBR source. G4 year-effective tax and G5 private verified owner monthly pulse remain blocked. All real-data gates require private security, official provenance and source verification before approval.

## Chat 3 A7/A8 source/owner/security coverage update — 2026-11-16

A7 source/provenance/no-double-count claims for bank and typed cash/loan/investment/assets/withholding/FBR draft/filed claims implemented synthetic-only (#81, 460 pytest+PG18). A8 block-only release matrix and PostgreSQL restored-clone read-only proof of remaining legacy SQL plaintext (#84, 476 pytest+PG18). G2 new encrypted persistent recoverable-state and chained audit model with transactional consumption/revocation, TOTP anti-replay CAS (#82, 482 pytest+PG18), not production owner login. G3 **actual Docker synthetic runtime** (no network, read-only/no caps nonroot, resource limits, no real documents), candidate-only bank/IRIS versioned acceptance registry (#83, 455 pytest+PG18 and live ephemeral Docker CI). No production authoritative ledger swap, official FBR proof, private owner bank format or actual dashboard financial source. Full [handoff](CHAT3_A7_A8_G2_G3_CHECKPOINT_2026-11-16.md).

## Nov17 coverage delta — #86–#89

G1 source-backed classification/reversal candidate contract (#86) and authenticated original-row candidate/inverse matching in economic graph (#89) now tested with safe synthetic data, **not a full write-side economic graph nor tax/expense verification**. G2 two simultaneous PostgreSQL connections compete for the same recovery code, exactly one accepted (#87), **not private owner MFA deployment**. G3 synthetic conservative PDF active action and OOXML decompression/links/macro checks plus isolated worker runtime integration (#88), **not actual malformed real-world parser/malware certification**. All three production gates remain BLOCKED. Test evidence and remaining requirements: [Nov 17 continuation](CHAT3_NOV17_CONTINUATION_2026-11-17.md).

## Nov17 synthetic coverage vs genuine release — #91–#94

[#91](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/91): encrypted-backup-first isolated PostgreSQL synthetic restore-clone TEMP pointer switch/real SQL rollback, injected failures; **NOT real application authority migration**. [#92](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/92): independent encrypted owner recovery audit/single-use restore, wrong-key denial; **NOT private MFA enrollment/offsite acceptance**. [#93](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/93): pypdf security floor and candidate-only private institution/IRIS formatting acceptance checklist; **NOT genuinely certified parsers**. [#94](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/94): source-unique owner-declared encrypted typed cash/loan/investment/asset opening/withholding proposals and bank transfer matching; **NOT verified complete economic authority, realized gains or tax due**. Exact tests/remaining gates: [Nov17 latest handoff](CHAT3_G1_G2_G3_PRIVATE_ACCEPTANCE_BOUNDARY_2026-11-17.md). G1/G2/G3 all still BLOCKED for real owner data.

## FINAL VERIFIED Google Drive ONE-drop-folder decision and safe engineering (2026-11-17)

**Owner requirement:** Fresh dedicated Personal CFO Google Drive account, **one private Upload Here folder**, owner simply uploads all old/new PDF, CSV, XLSX, screenshots, accountant working papers, FBR/IRIS filings and receipts without sorting or renaming. Personal CFO must virtually organize, detect revisions/duplicates, identify missing records, reconcile verified originals and request owner follow-up only for genuinely ambiguous facts. **Backblaze B2 deferred**; don't add paid/new storage, don't delete/move originals. Source-of-truth [full one-inbox plan](GOOGLE_DRIVE_SINGLE_INBOX_OWNER_WORKFLOW_2026-11-17.md).

**Merged verified [PR #96](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/96)** squash `af36c4255619650c3f423d5a068f470a018b091c`, [CI 44040683416](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44040683416) **586 pytest passed, 3 warnings + all PostgreSQL18 G1/G2/G3 source/recovery/rollback/restricted-role checks PASS**. Implemented synthetic-only bounded one-folder Drive metadata planner, HMAC private file/version identities, filename-only virtual collection hints, changed/unchanged revision and possible-duplicate warnings, strict MIME/size quarantine, and complete fixed-folder paginated fake Drive v3 listing. This is **NOT a live Google OAuth connector, original-file import, scheduler, certified tax/bank facts or ledger mutation.**

**Merged verified [PR #97](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/97)** squash `d78a50ba96abe7e2d67f3bba44ac15120d32af15`, [synthetic Apps Script CI 44041652333](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44041652333) **7/7 Node tests PASS**. Added [Google Apps Script optional owner-side hourly one-folder indexer](../integrations/google-drive-inbox/README.md): explicit Drive read-only, private Sheets and trigger scopes, owner-pinned folder only, private Inbox/Summary/Changes spreadsheet, no original file modification/content processing, no webhooks or credential export. **Script is only published in source control, NOT installed or running in the user's Google account.** It requires the owner to choose the new dedicated Drive account/folder, approve broad read scope on that *dedicated* account and activate script once. This offers metadata-only auto-indexing without extra server; later real reconciliation remains conditional on G1/G2/G3.

**Connection status:** Owner successfully installed/connected Google Drive **in ChatGPT for this request**, which is separate from the Personal CFO PWA's own OAuth and from the optional Apps Script activation. No authorized **fresh-account folder ID** or connected Drive file operations have been verified in this session; no personal Drive content inspected. Do not use a different existing Google Drive account or another ChatGPT project just because a connector is installed.

**All true real financial release gates remain BLOCKED:** G1 full owner/account/year encrypted authority, evidence-driven reconciliation, reversible production cutover and retiring legacy plaintext; G2 actual private MFA/session/roles and independent backup; G3 original encrypted vault, safe PDF password handling, authentic Pakistani bank/FBR/IRIS and accountant workbook certification. No real finance files, account names, access tokens or credentials were sent to GitHub/CI/Railway. `APP_DATA_MODE=real` still fails closed. **Next actionable user step:** Create/identify private upload folder in new dedicated Google account and supply its private folder link/ID in this project, without granting public access; authorize Apps Script separately if choosing hourly metadata scans. Only then design explicit source-limited OAuth, secure monitoring and private reconciliation.

## 2026-11-17 Chat 04 P1E scope — provenance-safe status

**Owner goal:** One unsorted Google Drive folder is continuously indexed by the app, with private phone Documents review and later source-backed financial reconciliation. **Current milestone being tested, not live:** separately keyed *fake-only* PostgreSQL cloud OAuth state/grant custody, 10-minute one-time PKCE state, replay and tamper denial, isolated concurrent database tests. **Still missing:** real cloud callback/MFA/key custody/security acceptance, approved one-folder scheduled sync, authenticated live review API and G1/G3-certified original content processing. No actual owner Drive connection or real financial amounts. See [P1E scope](CHAT4_P1E_CLOUD_OAUTH_CUSTODY_2026-11-17.md). Update after exact-head CI and merge.

## Final verified Chat 04 Priority 1E status (2026-11-17)

**[PR #108 MERGED](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/108)**, squash `59aadc02297a5615f717abffd9bdb30722058147`; tested head `5ad97b5e2aee8bd26e45e924d5ea1b6d6bfc3939`, [CI 44073123421](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44073123421): **659 pytest PASS, 3 warnings, PostgreSQL 18 encrypted fake OAuth custody/concurrent state, G1 clone rollback and independent restore, G2 recovery/restricted role ALL PASS**.

- **Implemented/tested (synthetic-only):** isolated fake Google consent state and fake refresh-grant records in PostgreSQL; encrypted AES-GCM with separate HMAC indexes, expiry, transactional two-worker one-time use, tamper denial and revocation; full G1 backup/source-table and G2 synthetic role/restore regressions preserved.
- **Still NOT delivered:** actual PWA Google Drive OAuth, owner-authenticated cloud callback, durable real token and key custody, scheduled single-folder metadata scanning, true private phone review queue, original financial document access, G1 encrypted financial authority, G2 owner MFA/recovery/live roles and G3 certified bank/FBR adapters; G4 actual tax and G5 source-backed financial pulse. Owner accountant's working workbook remains DRAFT and unknown remains unknown rather than zero. No real financial records or tokens in GitHub/CI/Railway.
- **Next acceptance:** true G2 independently reviewed restricted cloud auth/credential recovery and minimal exact-route callback, owner-scoped live activation approval, then verified one-folder metadata scheduling and evidence-linked document review. See [handoff](CURRENT_HANDOFF.md) and [issue #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98).

## Chat 04 P1F candidate requirement coverage — provisional 2026-11-17

- **Partially implemented, synthetic-only:** owner password/TOTP helper, session creation with hashed 15-minute cookie identity, Secure/HttpOnly/SameSite=Lax callback-compatible cookie policy, CSRF/Origin check, single-use encrypted OAuth state bound to initiating browser session; isolated exact-host private ASGI path contract. Pending exact-head verification: [P1F design](CHAT4_P1F_CLOUD_OWNER_GATEWAY_2026-11-17.md).
- **NOT delivered:** real owner onboarding/password route + cross-worker login throttling, independent credential custody/recovery/role approval, public callback proxy, owner Google Drive consent, scheduled one-folder metadata index, actual private Documents UI source data, real content parsers, G1 canonical authority, G2 security acceptance and real tax/wealth claims. No original owner data handled. G1/G2/G3 remain blocked.

## FINAL VERIFIED Chat 04 P1F coverage — 17 Nov 2026

**[PR #109 merged](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/109)** (squash `b2f1a6f787ebb5d21ef0a547fa3d616bd38b6fd6`), [CI 44077400351](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44077400351): **673 pytest PASS, 3 warnings, PostgreSQL18 session-bound fake OAuth replay/backup/clone/role PASS**.

**Now verified in synthetic tests:** 15-minute MFA-issued browser session stored as hashes, Secure/HttpOnly/Lax cookie policy, exact HTTPS Host and POST Origin+CSRF, sealed one-time fake OAuth PKCE state bound to initiating browser digest, alternate-session rejection, callback replay rejection, wrong host/HTTP/fake code refusal. Existing P1E fake encrypted state storage and G1/G2 PostgreSQL backup/role controls retained.

**Still not shipped as genuine owner functionality:** browser-accessible MFA login and cross-worker brute-force throttle; independently accepted recovery/auth/logging/limited DB role/key isolation; routed owner-safe public callback; Google OAuth consent/refresh token; reliable real one-folder scanner/heartbeat; real app Documents queue; originals and G3 certified formats; encrypted authoritative G1 financial ledger; trustworthy tax/wealth/returns and actionable real mobile financial pulse. All such real facts remain UNKNOWN, not synthetic or guessed. No owner action until separately approved deployment/consent. Detailed [handoff](CURRENT_HANDOFF.md), [issue #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98).
