# P1AP — One-folder Google metadata review snapshot (source-only)

New `backend/app/private_owner_drive_metadata_preview.py` takes a previously encrypted, verified one-owner P1M metadata grant. Under distinct P1AP release flags it refreshes an access token using the fixed TLS Google token endpoint, verifies the exact owned private unshared folder again, scans only direct file children through bounded `files.list` requests, validates every item and each pagination cursor, and returns **one complete** redacted/owner-only review snapshot.

The response includes document display names, suggested virtual collections and review status, modified timestamp and size, but **not** provider file IDs, folder ID, OAuth code/refresh/access token, raw content, checksums or financial claims. Files cannot be downloaded, moved, deleted, opened or marked accounted/taxable. Errors discard the entire snapshot and suppress provider data; no partial result or irreversible database write. There is no persistent last-good scan, cron, background sync or browser route yet; those require separate authenticated review and persistent encrypted index.

Gates are independent `P1AP_OWNER_FOLDER_METADATA_REVIEW_ONLY=1`, `P1AP_G2_AUTHENTICATED_METADATA_UI_REVIEWED=1`, `P1AN_GOOGLE_METADATA_RUNTIME=1` and the existing owner/metadata P1AL, P1M, P1C gates; the owner reference must match the established `P1W_OWNER_REF`. This function may be called **only after private owner session/CSRF and rate acceptance** by an exact private HTTP route. It does not activate or weaken P1AO. Strict CI fake provider covers two-page snapshots, unauthorised parents, duplicate IDs, invalid metadata, incomplete search/cursor loop, unowned folder, missing flags, no source bytes and no SQL mutations.

Remaining: independent exact-route owner-authenticated queue endpoint, private-only Nginx exposure and mobile Documents UI, followed by private encrypted durable inventory+lease/heartbeat, scheduled metadata refresh and actual one-owner Google consent. Original-content financial authority G1/G3 stays blocked.

No user backup tasks, extra Railway services, live flags, real files or Google tokens.
