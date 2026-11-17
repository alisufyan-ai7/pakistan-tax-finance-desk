# P1H — Single-folder metadata scan health and cadence rehearsal, parallel lane B

**Project:** Personal CFO · 17 Nov 2026 · after verified PR #109.

Existing `drive_folder_pages`, `drive_private_sync` and `drive_inbox_store` already provide fake-only bounded complete pagination, retries and atomic encrypted review snapshots. **Do not rebuild those components or claim real scans.** This independently deliverable lane provides the **missing deterministic schedule/heartbeat semantics** for a future owner-approved scanner; there are no new tables, external transports, timers or background jobs.

## Test-only capability
- `backend/app/drive_scan_cadence.py`: explicit injected timezone-aware clock, 24-hour baseline cadence, 36-hour staleness warning and bounded delays (5/15/45/120 minutes) after retryable failures.
- A failed or incomplete scan cannot overwrite the last verified successful timestamp; a permission denial halts scheduling and requires owner reauthorization. Monotonic timestamps, state/outcome consistency and invalid configuration are rejected.
- This state machine returns privacy-safe statuses only. It cannot contact Google or run in real mode. Separate `P1H_FAKE_SCAN_CADENCE_ONLY=1` plus `DRIVE_FAKE_TRANSPORT_ONLY=1` and `APP_DATA_MODE=synthetic` are required. Its simulated heartbeat is explicitly labeled **not real**, and no data processing is triggered.
- Unit tests cover first scan, due/stale logic, backoff, denial, missing flags, naive/future timestamps, timezone conversion and absence of live account assertions.

## Remaining hard gates
No cron/scheduler installed, no persistent latest-success heartbeat backed by live owner-index provenance, no Google credentials or actual PWA connection. Existing registered Google callback remains disabled. Only after G2 production owner auth/credential lifecycle and explicit owner approval can a reviewed background scheduler be implemented and tested end-to-end. Original bytes/financial facts still require G1/G2/G3.

No shared schema or OAuth/session files are modified here; this lane can run alongside P1G owner-login throttling. Final acceptance requires exact-head CI and combined-main integration proof before marking the milestone merged.

## Final CI acceptance — 17 November 2026

[PR #112](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/112) squash `3f31a68a5762d84ce80beb485d6e58026b416554`, tested head `18138aeb67d83268d16870cf958dc3b75e958563`, [CI 44084245982](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44084245982): **683 backend pytest passed, 3 warnings + PostgreSQL18 PASS**. [Combined integration #113](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/113) **697 tests + PostgreSQL18 PASS**. Strict malformed never-scanned-but-success state check was corrected before acceptance. **Pure simulated health only:** no live Google API/cron, private owner heartbeat, real file names or actual one-folder sync. G1/G2/G3 real data gates remain BLOCKED. [Full handoff](CURRENT_HANDOFF.md).
