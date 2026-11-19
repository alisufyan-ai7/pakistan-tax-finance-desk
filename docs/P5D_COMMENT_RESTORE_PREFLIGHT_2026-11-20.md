# P5D — owner comment migration preflight and controlled release

20 November 2026. Independent code-only branch under issues #218/#222.

## Implemented

`backend/app/private_comment_schema_release_probe.py` is a *read-only* synthetic operator diagnostic. It checks for the exact encrypted comments table columns and an accepted Alembic revision; it does not query, return, decrypt or write any comment value or owner credentials. It never calls Google or touches originals. It intentionally returns `release_authorized=false` even when the SQL schema matches, because a developer cannot attest an independent external encrypted backup, disposable full restore, least-privilege migration authorization or actual owner authenticated browser smoke simply from table inspection.

## Unfinished real owner activation

1. Independently verify that a **recent full** encrypted PostgreSQL backup contains owner identity, recovery state, metadata/content grants, original-source hashes and owner-comment changes where present, rather than only the initial credential-only snapshot. Store encrypted copies in two independent owner-approved locations with separate recovery keys; never put backups or passphrases in GitHub or ChatGPT.
2. Restore to a disposable database on an isolated approved resource. Validate row counts, decryption/key continuity, grants, source manifest and authorized owner account, then destroy the disposable database. Do not test restore over the running Personal CFO database.
3. Confirm the reviewed restricted SQL migration role, current Alembic version, production-compatible additive **0024** comment migration and (after review) **0025** SHA-source manifest migration. These must be run exactly once in a controlled maintenance window, never at application startup. If failure, restore from the *verified* independent backup.
4. Validate strict owner MFA, CSRF, Origin, exact reverse-proxy allowlist, no sensitive request/access log, encrypted append-only note writes and comment history retrieval, source/owner HMAC isolation, wrong-owner/invalid-source rejection and no automatic finance reclassification.
5. Activate only the approved P5B/P5D runtime/ingress flags after all independent signed evidence. Do not turn on bank PDF analysis at the same time unless its separate sandbox G3 review passes.

## No immediate user password/request

The already confirmed Google read-only document permission and MFA enrollment do not need to be repeated. When operator acceptance requires the owner, provide a short exact checklist for secure encrypted database backup/restore, without transferring secret values into chat. This code change is **not** permission to claim saved document comments are now live.
