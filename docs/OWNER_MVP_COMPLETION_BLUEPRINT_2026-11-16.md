# Personal CFO owner-MVP completion blueprint, dependency graph and parallel execution

**Owner decision 2026-11-16:** design the end state first, then maximize owner-independent parallel code/test execution. **Canonical repository:** `alisufyan-ai7/pakistan-tax-finance-desk`. This document is a forward-looking execution baseline, not a claim that the listed tasks have been delivered. It refines the [owner-approved v2 plan](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md), [release gates](DELIVERY_GATES_AND_RELEASE_READINESS.md), [parallel playbook](PARALLEL_ENGINEERING_EXECUTION.md) and [requirements coverage](REQUIREMENTS_COVERAGE_MATRIX.md).

**Project-isolation condition:** use only THIS Personal CFO ChatGPT project + this GitHub repository as project facts, NEVER cross-project or account-wide memory/resources. No Docker/remote development provision; existing optimized GitHub Actions (single ephemeral PG18 runner for backend PRs) is authorized. Public GitHub must remain synthetic-only. `APP_DATA_MODE=real` must stay denied until full G1–G3 and explicit private owner acceptance. No auto FBR filing, transfers, trading, unauthorized integrations or unsupported tax advice.

## A. Precisely what "finished" means

**Release target = single-owner private Pakistani Personal CFO** with a verified end-to-end journey on a secure owner-authorized runtime:

1. **Onboard:** owner authenticates via MFA, records PKR/multi-currency accounts and correct legal person; securely imports 2023-onward supported bank/FBR evidence, older asset acquisition references, prior filed returns and immutable revisions; all originals encrypted, provenance and coverages visible.
2. **Daily intermittent ingestion:** owner uploads random 1–20 supported files (replays/overlap across periods). Supported versions parse in restricted runtime with exact source/account/period/running balance and dedup checks. Unknown, partial or suspicious files are quarantined, **never guessed**.
3. **Unified source of truth:** one confidential authoritative PostgreSQL graph preserving raw source rows, legal person, cash/loan principal vs earnings, transfer links, investments, property/assets, withholding, filings, amendments, reversals and human decisions; no active plaintext financial amounts/dates/account links in raw DB dumps. Year×account and source row parity is reproducible.
4. **Review and uncertainty:** account×month coverage is observed/partial/missing/conflicting/unsupported rather than treating missing as zero; own-account transfers not income; source ambiguities become evidence-linked review cases; review history append-only.
5. **Accountant:** owner can inspect a versioned DRAFT workbook with formula/cache/source evidence uncertainty, ask/answer accountant questions and export a review package. A separate verified IRIS acknowledgment and lineage is mandatory to call anything FILED; workbook approval cannot silently file a return.
6. **Tax/wealth:** supported TY-effective Pakistan income heads, withholding final-vs-adjustable and cross-year wealth snapshots reconcile with filed sources. Independently reviewed law vectors and source links support any payable/refund estimate; unsupported dimensions show UNKNOWN/null and never manufactured tax savings.
7. **CFO:** secure mobile-first overview, bank balances and coverage, cash flow, spend groups/recurring items, loans and liquidity, investments/assets, goals, scenario analysis, audit-linked recommendations and accountant export; clear observed vs estimated vs unverified state.
8. **Operability:** private TLS/network/MFA/CSRF/session rotation/rate limiting, secrets outside code, secure document conversion, privacy-preserving logs, encrypted independently restorable backups and key continuity/rotation. Owner can complete a restore drill and recovery acceptance.
9. **Acceptance:** 20 adversarial v2 synthetic scenarios plus independent private owner E2E acceptance pass. The release is NOT considered finished from CI alone; owner approves the controlled private-data and legal evidentiary steps, not the design of synthetic code.

**Explicit non-goals for owner MVP:** family/accountant multi-login, SaaS/billing, automated FBR submission or payments/investment trades, universal unsupported bank formats, guaranteed deductions/investment returns.

## B. Gate-by-gate definition of done (DoD)

| Gate | Required proof, not just written claims | Current truth (2026-11-16) |
| --- | --- | --- |
| **G0 synthetic engineering** | CI on exact PR head, deterministic fabricated fixtures, schema upgrades/rejections, traceable commits | Existing baseline proven, combined 253 pytest + PostgreSQL18 at PR #41 |
| **G1 confidential canonical finance** | All economic source/event/loan/cash/asset/filing/revision columns encrypted or protected, externally scoped blind indexes; boot/read/write on authoritative protected graph; complete account×tax-year parity and no double count; reversible, backup-first PostgreSQL migration; raw SQL leak scan; independent offsite encrypted restore/rotation drill and key-loss handling; plaintext retired safely | **BLOCKED:** G1-a bank source, G1-b encrypted full-table backup, G1-c inventory and **restored-only sealed mirror** validated; legacy original and restored candidate economic tables still plaintext, no live cutover |
| **G2 private owner security** | Approved private hosting/network/TLS, MFA + recovery, multiworker/session/CSRF, rate limits/lockout, external secrets, vulnerability scan, trusted-host/browser session tests, isolated document workers, privacy logs and backup drill | **BLOCKED**; local synthetic gateway only. Provider/hosting owner authorization required for actual deployment |
| **G3 actual evidence adapters** | Approved bank/IRIS format versions and fixture-to-private real sample validation; no guessed parse; malware/zip/pdf/OCR isolation, encrypted immutable originals, source provenance; 20-file overlapping batches and idempotency, page carry forwards, missing/partial periods, correct company/owner segregation | **BLOCKED:** marker-gated synthetic six-layout registry only |
| **G4 year-effective tax/wealth** | Official effective-year TY2023+ rule registry and immutable source citations, independently reviewed golden vectors, mixed income/FX/gains/withholding, legal entity boundary, wealth/year continuity; unsupported due/credits remain null | **PARTIAL** narrow illustrative salary plus foundational wealth/lot math |
| **G5 complete owner UI/journey** | Browser E2E: onboarding → batch upload → account×period coverage → review → source-linked tax/wealth/accountant pack → spending/planning → secure export/logout/recovery, responsive and accessible; owner acceptance and monitoring | **PARTIAL** backend demos/scenarios, no private end-to-end app |
| **G6 commercial multiuser** | Separate authorization after owner MVP; not part of definition of finished | Out of scope |

**Important independence:** code for G2/G3/G4/G5 can be developed with fake data NOW, but **production acceptance is gated** by G1/G2/G3 and official owner/legal verification.

## C. Parallel work breakdown — executable acceptance criteria

The labels below are **units of work**, not assertions of delivered features. Keep one branch/PR per independent module. Shared schema changes have one integration owner; never run two competing Alembic migrations on the same base without explicit coordination.

### Lane A — P0 data confidentiality & recovery (critical path, #21)

- **A1 DONE synthetic:** AES bank source, blind HMAC, replay/key sentinel (PR #34).
- **A2 DONE synthetic:** encrypted PostgreSQL DATA backup, independent empty-db restore, full row parity, injected rollback (PR #35).
- **A3 DONE synthetic:** exact 19/20-table source census and source/account/year keyed parity (PR #37, extended #40).
- **A4 DONE synthetic foundation:** Alembic 0011 restored-clone encrypted source mirror and rollback/reconciliation; **not authoritative** (PR #40).
- **A5 NEXT:** typed protected operational canonical events + evidence/position/source contracts. All sensitive dimensions inside AES, query keys blind, source uniqueness and complete revisions/reversals. Never treat mirror as live ledger.
- **A6 NEXT:** deterministic converter from source graph to canonical protected positions/events with **explicit** account×TY debit/credit/opening/closing, cash, loan principal+markup, asset, investment lots and filing revisions. Unknown remains unknown. No legacy summary double count.
- **A7:** live read/write adapter selection and safe replay/idempotency; enforce **exactly one authoritative store** and reject unrecognized/mixed-mode input.
- **A8:** independently backed-up/restored-clone dry run → verified candidate → guarded cutover/revert; audit transaction rollback, duplicate, corrupt key, missing field, concurrent writes, key rotation. No destructive source until audited retention acceptance.
- **A9:** encrypted current database raw-SQL leak checks; verify no plaintext active finance amounts/dates/source links; external-key lifecycle, tested offsite encryption/restore with declared RPO/RTO; supervised G1 acceptance. No real-mode change in synthetic PRs.

### Lane B — P0/P1 source adapters and reconciliation (#29)

- **B1 DONE synthetic:** version-pinned six-layout bank/IRIS capability contracts (PR #38); not actual banks.
- **B2 NEXT independent:** account×month coverage model with observed/partial/missing/conflicting/unsupported, duplicate/non-contiguous periods and source references, **never missing=0**.
- **B3 NEXT:** accepted statement batch registry and overlap/duplicate evidence; source-row immutable identity, running balances, transfer candidate vs owner-confirmed linkage, review statuses.
- **B4:** isolated converter design and code for PDF/ZIP/XLSX/legacy XLS/OCR with CPU/memory/time/page caps, network isolation, malware policy and no macros; unknown formats quarantined; synthetic attack files first.
- **B5:** typed adapter registry and synthetic variants for other Pakistani banks/IRIS return/wealth/acknowledgement layouts, broker/NCCPL/payroll; cap unsupported automatically.
- **B6:** genuine supported bank/FBR acceptance in secure PRIVATE runtime only, after owner approval and G1/G2. No real inputs into public GitHub/Actions.

### Lane C — P1 accountant working papers and reviews (#30)

- **C1 DONE synthetic:** bounded DRAFT XLSX formula/cached-value diagnostics, external-reference refusal (PR #39).
- **C2 NEXT independent:** append-only review-case state transitions and evidence references: OPEN → EVIDENCE_REQUESTED → OWNER_RESPONDED → REVIEWED → ACCEPTED/REJECTED, authorized actors, reason and immutable audit. No assumption a reply is bank/source proof.
- **C3 NEXT:** accountant workbook version ancestry and DRAFT → UNDER_REVIEW → OWNER_APPROVED; separate acknowledgements/revisions; never promote to FILED without genuine IRIS evidence.
- **C4:** source sheet/cell/formula dependencies, discrepancies against authoritative ledger, withholding duplicate candidates, wealth discontinuity and question priority; no workbook modification or automatic legal conclusions.
- **C5:** owner evidence request/reply queue, export/download of redacted review package and source citations; optional accountant login separately consented, not required.
- **C6:** private workbook parser/audit acceptance after G1/G2/G3, with genuine file only inside owner-authorized host.

### Lane D — P1 statutory tax and wealth correctness (#5)

- **D1 NEXT independent:** inspect existing TY legal registry and create a **rule-coverage/unknown-state matrix** (by TY, legal owner, income head, final-vs-adjustable WHT, effective date, source and verification state); do not calculate unsupported due.
- **D2:** independently retrieved official FBR Finance Act/rates/IRIS instructions TY2023–present with published/effective date, amendment and exact legal references; reviewer/legal signoff before verified status.
- **D3:** typed income/withholding/capital/gains/deductions projections and confidence/evidence rules. Tests for mixed salary+business, property, dividend, markup, foreign, cash, asset disposals, short-term and tax-year boundary.
- **D4:** deterministic wealth bridge source-of-funds, changes in bank/cash/investments/property/loan, filed wealth prior-year continuity; missing/source conflict remain REVIEW_REQUIRED.
- **D5:** legally evidence-supported tax/savings cards only. If statute, eligibility, withholding character or external verified evidence is absent, estimated liability/savings = **null**; no filing automation.

### Lane E — P2 personal CFO intelligence (#25 and G5)

- **E1 NEXT independent:** owner coverage-aware recurring expense detector: source-supported merchant key, cadence and observed months, **annual projection labeled estimate**, no asserted realized saving or income tax relevance; avoid transfers/principal as spending.
- **E2:** cash buffer, budget variance, expense categories, liquidity, debt paydown, goals and scenario analysis. Keep unobserved=unknown, forecast vs facts explicit.
- **E3:** investments holdings/cost/FX, risk/liquidity/rebalancing candidates with sources, no auto trades, never invent quotes or returns.
- **E4:** normalized read-only owner dashboard API contract with current source/coverage/review flags and data provenance, all financial values behind G1/G2 authorization.
- **E5:** mobile-first accessible owner UI, account coverage, accountant review, tax/wealth, plans/export, security/restore; end-to-end browser acceptance on private approved host.

### Lane F — P0 G2 privacy/platform scaffolding (#28)

- **F1 independent:** owner threat model, auth/API/session/cookie/CSRF rate limit and failure-mode test matrix (code and synthetic CI only); no deployment.
- **F2:** safe document quarantine/converter worker and encrypted immutable source/document storage contract; no genuine samples until G1–G3.
- **F3:** infrastructure-as-code / environment and secrets policy as **templates only**, never deploy to unapproved provider; private ingress, TLS/MFA, recovery, least-privilege and audit.
- **F4:** synthetic browser security acceptance; then privately deployed MFA/backup restoration and owner-controlled real-data acceptance on approved host.

### Lane I — integration, acceptance, release (single accountable merge lane)

- **I1:** versioned domain contract ownership. Merge independent PRs only after exact-head green tests, synthetic adverse fixtures and data/permission boundary checks. Run one combined PR-based integration check after grouped merges, not uncontrolled parallel CI.
- **I2:** replay all [20 v2 adversarial scenarios](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md#6-acceptance-and-adversarial-scenarios-synthetic-only-during-development), including 20-file overlap, missing month, unknown credit, owner-vs-business, stale spreadsheet, filed-vs-draft, withholding, wealth gap, wrong key and restore fail.
- **I3:** private host/security/adapters acceptance and approved evidence review. No production testing with public GitHub fixtures that embed personal records; no accidental access to other projects' data/services.
- **I4:** full one-owner historical 2023+ backfill, latest TY review/export, accountant package, dashboard, restore drill and documented operator recovery. Confirm owner acceptance and legal/statutory reviewer signoff.
- **I5:** mark G1–G5 DONE **only with recorded evidence**, not green test counts alone. Release branch/tag with deployment and rollback runbook.

## D. Dependency edges and critical path

```text
A5 protected schema -> A6 canonical ledger & parity -> A7 single authority
             -> A8 restore-backed reversible cutover -> A9 G1 acceptance
F1/F2/F3 private runtime design -> F4 G2 deployment acceptance (owner-approved host)
B1 -> B2 coverage -> B3 batching -> B4/B5 safe conversion -> B6 G3 genuine format acceptance
C1 -> C2 review cases -> C3 draft/filed lifecycle -> C4 diff -> C5 accountant pack
D1/D2 legal verification -> D3 tax engine -> D4 wealth continuity -> D5 lawful opportunities
E1/E2/E3 financial intelligence -> E4 dashboard contract -> E5 private UI

      G1 + G2 + G3 --> owner-authorized private real-document E2E
                 + G4 rule/wealth verification + G5 interface --> OWNER MVP RELEASE
```

**True blockers, not parallel work:** owner-approved private host/provider/secrets/region and external key lifecycle; privately supplied authentic source format validation after G1/G2; independent legal review; explicit private-data and owner E2E acceptance. No owner action needed for the synthetic items below.

## E. Development batches to minimize critical path and CI waste

**Batch 1 (start immediately, separate files and PRs):**
- **A5a:** confidential canonical **typed read-only event projection contract** from independently verified sealed candidate; no authority cutover, no ciphertext-to-public output.
- **B2:** account×month coverage analysis from fictional normalized statement periods only.
- **C2/C3:** append-only review-case and draft-versus-filed lifecycle domain rules on fake IDs.
- **E1:** recurring spending estimates on source-supported fake transactions, gated by coverage and exclusion of transfers/loans.

**Batch 2 (can follow Batch 1 while other workstreams continue):**
- A5b/A6 canonical write/path ledger and full source/projection parity; B3 document acceptance/overlap handling; C4/C5 accountant question queue + redacted pack; F1 auth/security tests; D1 official-rule coverage registry.
- Avoid overlapping edits to `backend/app/models.py`, Alembic and `.github/workflows/backend-ci.yml`; do one schema-migration PR and dependent replay on current main.

**Batch 3:** A7/A8 single authority and reversible cutover, B4/B5 sandboxed conversion, D2–D4 independently sourced official law-year calculations, E4/E5 UI contract and synthetic journey.
**Release staging:** A9 G1 then G2 private environment + G3 genuine adapters accepted, D5 reviewed legal outputs and full owner E2E. G6 optional later.

**No fixed time claims:** throughput depends on code complexity, CI failures, provider/secret approvals, real-format evidence and tax expert review. Do not promise overnight background work. A conversational run executes only while invoked; each session records completed PRs, open branches, exact SHA/CI and next independent slices.

## F. Quality bar, reviewer artifacts and CI optimization

- **PR ownership:** one feature per branch, no shared file edits without conscious integration. PR description must state whether "unit only", "PostgreSQL18 verified", "private-host accepted" and "real-data-ready" explicitly.
- **Tests:** deterministic synthetic data only. Invariant and negative/chaos cases are mandatory; failed cases fail closed without partial DB commits. For financial arithmetic, use exact integer minor units/Decimal, never float or guessed FX. Year = Pakistan July–June tax year.
- **Security:** no genuine bank/FBR data, account identifiers, passwords or receipts in public GitHub, artifacts, logs or CI. Keys are fake synthetic CI placeholders, not production keys. No platform/provider changes without explicit approval. `APP_DATA_MODE=real` must reject every new source/test lane.
- **CI:** existing `backend-ci` PR-only path filter, one PG18 job, pip cache, cancellation of superseded PR-head runs, manual dispatch. Prefer **one finished PR-head run per lane**; rerun only after actionable fix, then merge exact green head; run **one consolidated integration PR** after grouped merges. Do not run automatic duplicate post-squash main checks unless branch protection requires them. Docs-only decisions need source review, not paid PG CI.
- **Release evidence scorecard:** `current/main SHA`, PR exact-head SHA, pytest count and real PG18 output, schema migration version, source-data invariant results, full sample acceptance, private security/browser/restore evidence, legal reviewer signoff, owner acceptance, outstanding issue/gates.
- **Privacy/data handling:** protect full originals and account/entity/counterparty/date/money; do not log named entities or secrets. Source cases marked FILED or tax-credit eligible only with separately verified evidence. Accountant drafts never overwrite filed history.
- **Rollback:** independently encrypted source backup BEFORE migration; clone migration with injected failure; validated restore and separate credentials; no unapproved deletion/retirement. Audit full provenance.

## G. Progress and completion reporting

Every engineering summary must use these four labels:
1. **Implemented (not yet tested)** — code exists but proof absent.
2. **Synthetic CI verified** — exact SHA/job/logs and contract tests pass.
3. **Private acceptance verified** — secure owner-authorized environment, backup/restore and actual supported documents verified.
4. **Owner MVP complete** — G1–G5 acceptance and owner workflow signoff recorded.

A green CI run can never promote status from (2) to (3)/(4). Track issues [#21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21), [#28](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/28), [#29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29), [#30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30), [#5](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/5), [#25](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/25). No false percentages of completion without measured acceptance coverage.

## H. Execution checkpoint after initial completion-first plan (2026-11-16)

The first independent batch was implemented and green: B2 [PR #43](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/43), C2/C3 [#44](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/44), E1 [#45](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/45), A5a [#46](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/46), then combined [#47](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/47): [CI 43856233389](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43856233389) **285 pytest and PG18 PASS**. Added independent D4 [#48](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/48) prior filed-vs-draft wealth continuity, [CI 43857422279](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43857422279) **294 pytest + PG18 PASS**. This is an **implementation checkpoint only**, not a change to the G1/G2/G3 live real-data cutover gates or G4/G5 acceptance. [Live scorecard](OWNER_MVP_DELIVERY_SCORECARD_2026-11-16.md), [latest handoff](CURRENT_HANDOFF.md). The defined next independent slices and actual release blocking edges remain unchanged.

