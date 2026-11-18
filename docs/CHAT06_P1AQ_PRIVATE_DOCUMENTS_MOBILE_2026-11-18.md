# P1AQ — Owner MFA Documents metadata review in mobile login (default-off)

Connects merged [P1AP #172](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/172) to the existing private one-owner Google controller, public exact-route ingress and mobile owner login. **No live owner financial files or Google provider calls occurred; code is disabled in Railway by default.**

### Complete source-only path

1. P1AN private ASGI only mounts a new exact `GET /internal/drive/documents/queue` if BOTH `P1AP_OWNER_FOLDER_METADATA_REVIEW_ONLY=1` and `P1AP_G2_AUTHENTICATED_METADATA_UI_REVIEWED=1` **plus** the existing P1AN/P1AL/P1M/P1C one-owner G2 gates. The private P1Q gateway validates server-provided shared proof, Host/HTTPS and exact allowlisted path; the real owner session must be active.
2. The private HTTP handler obtains a **verified owner-only session** from the isolated credential DB, uses P1M encrypted Google refresh grant, refreshes one short-lived Google token, checks exact owner/unshared folder, and collects only complete bounded `files.list` metadata pages through P1AP. No file download, content extraction, write, unrestricted Drive search or financial ledger.
3. New exact public `GET /api/drive/documents/queue` is **independently 404** unless `P1AP_DOCUMENTS_INGRESS_ENABLED=1`, `P1AO_GOOGLE_INGRESS_ENABLED=1`, `P1AK_OWNER_INGRESS_ENABLED=1` and the trusted shared gateway proof is configured. Hardcoded host/upstream, no query, rate limits (IP+global), no local sensitive request logs, proxy header override stripping, no wildcard `/api`.
4. Frontend Dockerfile explicitly defaults the new substitution variable to `0` (prevents the previous unset-variable Nginx boot failure). Mobile `/owner-login` Documents section becomes visible only after authenticated metadata grant status, and requires a user click to check files. It renders a maximum 150 items via `textContent`, never innerHTML, avoiding filename injection. Nothing enters localStorage/sessionStorage or unprotected public dashboard, and no provider ID/token/folder ID is returned.
5. **Not claimed:** automatic scan, durable last-good heartbeat, background scheduling, persistent encrypted source inventory, file content evidence, G1/G3 financial authority. The snapshot is ephemeral and refuses partial Google pages.

### Release dependencies and owner direction

Only after actual G2 edge/TLS/Host/CSRF/cookie/logging acceptance and private P1R/P1M key custody, safe deployment/rate rollback, and owner-attended MFA+Google consent may the frontend/backend/runtime switches be enabled. Google's Drive permission remains metadata-readonly at account OAuth level; the application restricts its actual query to the one owner-selected folder. The approved folder must be independently verified through Google OAuth, not assumed from ChatGPT's Drive plugin. Previously reported two copies of the owner credential recovery files remain acknowledged; no repeated backup-copy exercise.

Adversarial tests verify routes default off and exact, no file bytes, OAuth controller inactive by default, owner MFA required, and safe mobile DOM rendering. **No new Railway resource or unreviewed flags are set in this PR.**
