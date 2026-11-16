# Verified independent engineering batch 2 — five parallel synthetic lanes

**Date:** 2026-11-16. **Plan:** [Owner-MVP completion blueprint](OWNER_MVP_COMPLETION_BLUEPRINT_2026-11-16.md). **Truth:** This document only records code/testing in the PUBLIC synthetic repository, not true financial-source/private production acceptance. Existing optimized PR-head GitHub Actions and one PostgreSQL18 test job; **no Docker, cloud provider or genuine owner evidence**.

| Lane | Exact merged PR | Verified separate CI | What exists / what is still missing |
| --- | --- | --- | --- |
| **A5b G1 typed source-fact parity** | [#49](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/49) | [CI 43861269152](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43861269152): **297 pytest + PG18 encrypted candidate typed fact parity PASS** | Authenticates AES source mirror and keyed account/TY movement facts, plus loan/cash/transfer/asset/filing *claims*. **NOT live encrypted authority or G1 closure**; old SQL plaintext remains |
| **B3 source batch evidence** | [#50](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/50) | [CI 43860814802](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43860814802): **301 pytest + PG18 PASS** | Synthetic candidate replays, complete running balances, overlap/quarantine. **NOT real Pakistani bank parser certification/import or source identity authentication** |
| **C4 accountant review manifest** | [#51](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/51) | [CI 43860821053](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43860821053): **299 pytest + PG18 PASS** | Counts and keyed case references from in-memory draft/review cases and provisional coverage, no financial data. **NOT actual export, source-file authentication, encrypted persistence or RBAC** |
| **E2 cash reserve scenarios** | [#52](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/52) | [CI 43860828093](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43860828093): **299 pytest + PG18 PASS** | Unknown opening stays null, hypothetical buffer and expense/income assumptions, no actual balances or action |
| **D1 tax year/source coverage** | [#53](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/53) | [CI 43861143632](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43861143632): **303 pytest + PG18 PASS** | TY2023–27 existing registry coverage and 16-domain gap matrix. **NOT new official law verification, final/adjustable WHT, mixed-income due or savings** |

Each PR used separate files/tests and only fabricated fixtures. PR #49 first failed on a synthetic test-helper name collision, corrected; its exact validated head passed both 297 pytest and the actual PostgreSQL18 typed-fact parity smoke. All five feature PRs merged after verifying exact-head success.

## Combined checkpoint — VERIFIED merged

`backend/tests/test_parallel_batch2_integration.py` exercises all five together on the merged tree: an arithmetically consistent fictional statement is still not authoritative financial evidence; missing account-months stay unknown, accountant source review remains unverified, a forecast with unknown opening stays null, legal mixed-income tax remains unsupported, and typed canonical facts have no active cutover. All five code paths reject `APP_DATA_MODE=real`.

**VERIFIED:** [PR #54 MERGED](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/54) with squash `deae7048c33ac05ce2bb29720e92bfe02a87c807`; exact-head [CI 43861939976](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43861939976) **325 pytest PASS + PostgreSQL18 encrypted bank, independent backup/restore, census, candidate encrypted copy/rollback, A5a sealed read and A5b typed fact parity PASS**. [Handoff](CURRENT_HANDOFF.md) and [scorecard](OWNER_MVP_DELIVERY_SCORECARD_2026-11-16.md) updated. G1–G5 real owner release gates remain unchanged.

## Critical path and next parallel work

**G1 #21** remains the limiting release dependency: full typed authoritative **encrypted write model**; private economic source ingest; ledger account×TY / cash/loans/assets/filings parity; independent backup/restore; guarded single-store cutover; active plaintext retirement; key rotation, offsite/PITR and authenticated recovery. A sealed candidate mirror is not a live secure ledger.

**G2 #28:** private host/protected TLS + MFA/recovery/CSRF/rate limit, isolated document worker, private original-storage security; owner-approved hosting and secrets still absent. **G3 #29:** genuine bank/FBR signed/acknowledged source formats, multiple overlapping uploads, quarantine/source fidelity privately accepted after G1/G2. **Accountant #30:** encrypted case persistence, review question workflow, safe output with official IRIS proof distinct from draft. **G4 #5:** independent official rule-year vectors for 2023 onward and mixed-income/wealth/withholding, no guessed tax. **G5 #25:** source-linked owner dashboard and complete E2E backfill/recovery.

No real record imported, no tax return filed and no payments/transfers/trades executed. Product remains **synthetic engineering only**, not an owner-ready private Personal CFO app. `APP_DATA_MODE=real` MUST continue to reject.
