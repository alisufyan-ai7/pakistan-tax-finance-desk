# Chat 04 / Issue #115 — fake-only one-folder scan lease and last-good receipt

**Date:** 2026-11-17. **Base:** verified #113. Schema ownership of additive migration `0017_drive_scan_leases` is reserved **only to this branch**, avoiding shared Alembic collisions with #110/#114. GitHub public sources and CI use fictional folder/worker IDs only.

## Implemented test-only contract
- `drive_scan_leases` stores HMAC folder/ephemeral lease identity, lease expiry, timestamp, last accepted synthetic scan number and source snapshot HMAC, an independent keyed last-good receipt, failure count and permission-revoked flag. No raw filename, Google ID, token or original bytes in SQL.
- `drive_scan_lease.py` requires `APP_DATA_MODE=synthetic`, `DRIVE_FAKE_TRANSPORT_ONLY=1`, `P1J_FAKE_SCAN_LEASE_ONLY=1`, pinned HMAC folder; SQLite is only for isolated tests. PostgreSQL transaction advisory lock serializes first lease acquisition across workers. Expired owner loses the lease; replay/wrong token fails.
- Complete success is accepted only with the matching **committed authenticated full-folder `DriveInboxCheckpoint`**, including full-snapshot idempotent replays; crash/failed second page leaves the previous accepted success untouched. Permission denied suspends future acquisition pending explicit owner reauthorization. The status API is internal fake-only, not a public endpoint or actual heartbeat.
- Independent unit tests: two workers, restart/expired takeover, idempotent replay, missing/partial provider page, last-good tampering, denied permission, real-mode/unknown folder denial. Ephemeral PostgreSQL18 CI separately proves race+receipt+replay, full G1 backup/clone table inventory and restricted-role regressions.

## Not included / security gates
This is neither a running cron worker nor a real Google connector. The owner has not authorized a real OAuth connection, public callback, Railway schema migration or source content. Real-mode G1/G2/G3 remains BLOCKED. No owner original move/delete. Do not report a real heartbeat or finance figures in the user UI. An independent reviewed scheduler, owner identity, key lifecycle and auth is still required. Record exact-head CI and merge/rollback evidence in latest main handoff.
