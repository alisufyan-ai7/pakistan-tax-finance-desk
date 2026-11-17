# Chat 04 — Parallel batch 3: P1G HTTP, P1I mobile Documents and P1J scan leases

**Date:** 17 November 2026
**Source of truth:** `alisufyan-ai7/pakistan-tax-finance-desk` GitHub `main`, latest `docs/CURRENT_HANDOFF.md`. Owner instructed us to maximize *independent* parallel engineering with separate branches, exact-head CI and one integrated regression, without sacrificing G1/G2/G3 real-data release gates.

## Independently accepted implementation branches

| Issue / lane | PR / accepted SHA | Exact-head validation | Capability actually built | Not built |
|---|---|---|---|---|
| **#110 P1G owner security** | [#116](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/116), squash `869052756df8d158b00d6d4e7b98dc1175025647` | [backend CI 44093121188](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44093121188), **704 pytest + PG18 PASS** | **Unmounted, fake-only** isolated HTTPS owner login/session/rotate/logout ASGI contract. Reuses existing P1G serialized 5-failure synthetic throttle, scrypt+TOTP, 15m Secure/HttpOnly/SameSite=Lax cookie, exact Origin and CSRF on mutations; rejects malformed/large JSON and untrusted host/forwarding | Real owner identity/provisioning, device MFA recovery, audited public rate controls, genuine cloud key lifecycle, production G2 acceptance |
| **#114 P1I mobile UX** | [#117](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/117), squash `3c83f66b3ff73c9a26e72b66d18850981947a5f2` | [frontend CI 44093129424](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44093129424), **39 Node tests PASS** | Six **fictional** mobile Documents review-state examples (never, stale, revoked, changed, missing, duplicates) with accessible min 44px controls, plain-language next actions, no raw filenames, no live API fetch, no financial assertions | Real Google Drive status, original file import, owner review queue, verified expense/balance/tax facts |
| **#115 P1J Drive robustness** | [#118](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/118), squash `b30cd0ba7a1c4cc18551403aae65c070c5ec4d06` | [backend CI 44093139087](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44093139087), **710 pytest + PG18 PASS** | Additive migration `0017_drive_scan_leases`, synthetic-only PostgreSQL advisory-serialized lease, expired worker takeover, anti-replay, committed one-folder index proof, last-good HMAC receipt, failure/permission-denied preservation and tamper detection. Full G1 census, independent restore, G2 restricted-role regressions preserved | Installed cron, live Google access, real scan heartbeat, genuine key recovery/owner authorization or real Financial Data approval |

All three initially branched from the same verified baseline after #113, and were tested independently. **Schema changes were owned solely by #118**; #116 created only new backend module/tests and #117 touched only static frontend files/tests. Merges were sequential after green exact heads. Combined branch `integration/chat04-issues110-114-115-20261117` adds explicit real-mode/route-denial backend and frontend regression tests; final CI, merge SHA and outcome are **PENDING** until verified and appended below.

## Owner roadmap and safe concurrency

The six owner-approved priorities and real-data gates remain unchanged. Priority 1 Google Drive metadata-only connection is the active objective; the new modules reduce future integration risks but **do not connect a real Google account**. The existing exact Railway Google callback was registered by the owner but remains **unrouted** in Nginx. The real owner folder is private and unsorted: Personal CFO must virtually organize it, never move/delete originals. Google metadata-only scope can expose broad Drive metadata via consent; eventual application must pin strictly one folder and verify owner provenance. No Backblaze B2 or new paid provider.

Further independent work can proceed in (A) owner MFA/rate/secure-key/recovery audit, (B) bounded fake Drive metadata scheduler and private queue integrity, (C) synthetic G3 bank/FBR/Excel format fixtures, (D) accountant workbook **DRAFT vs filed** evidence rules, (E) mobile financial source-coverage/unknown states and pure tax/investment scenarios. Shared schema/CI/key/recovery changes require a single coordinator. **Release dependency:** accepted G2 private owner authentication, restricted keys/roles/restore and narrowly logged OAuth ingress → explicit owner consent and one-folder metadata sync → authenticated mobile review queue. G1 canonical encrypted real finance authority + G2 + G3 genuine certified formats are additionally required for source-original parsing and true account/expense/investment/tax conclusions. Missing data is UNKNOWN, not zero or fictional.

## Deployment and privacy boundaries

- Public GitHub and GitHub Actions use fabricated names and fake tokens only. No real financial source, secret, Google identity or document byte was uploaded.
- Backend new login app is **not imported by** `app.preview_api:app`. Public Nginx must still proxy only `GET /api/preview/status` to the private Railway backend.
- New scan lease code and migration `0017` have been tested on disposable PostgreSQL18 CI. **No claim it was applied to existing Railway PostgreSQL** or that a background scanner was deployed.
- Frontend Documents states are demonstrative, not a live service.
- G1/G2/G3 private data acceptance remains **BLOCKED**; production MFA/recovery/token custody and exact callback security review still pending, and authentic Google consent requires separately scoped owner approval.

## Required completion/handoff

Once combined exact-head backend+frontend checks pass, merge the PR and commit true numbers/SHAs, project status/roadmap/requirements/security/architecture and next independent tasks to GitHub. Update issues #98, #110, #114 and #115 to reflect *synthetic code delivered versus genuine live functionality*. No future chat must depend on pasted historical transcripts.
