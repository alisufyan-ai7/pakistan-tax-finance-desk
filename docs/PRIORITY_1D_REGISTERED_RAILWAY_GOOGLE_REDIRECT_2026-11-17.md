# Priority 1D — Google accepted Railway redirect; callback still private-security gated

**Date:** 17 November 2026  
**User confirmed:** In Google Auth Platform → Clients → **existing** Personal CFO Web OAuth client, the owner added the proposed Railway HTTPS callback and Google accepted it; the old localhost URI was removed. The console screenshot displayed the Railway URI in the authorized redirect field (the visible field truncates horizontally, so the owner's textual confirmation of the complete value is used). The owner's already-created Google Cloud project, Client ID, metadata-only Drive permission, Test-user entry and private client secret remain unchanged. Do **not** reproduce the Client ID or Google Drive folder ID in GitHub, CI, code or public demo.

## Approved full callback value — REGISTERED BY OWNER, NOT LIVE

`https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback`

Google's acceptance verifies the URI *may be listed* for the existing client, **not** that the site has a working callback or owner-authenticated Google consent. Google requires the runtime `redirect_uri` exactly match the registered URI. Never paste the OAuth client secret into chat or public repository, and do not complete Google consent or bypass an unverified warning until the deployed private handler is verified.

## What the code in this PR does

1. `backend/app/drive_google_oauth.py` now recognizes **exactly** this Railway callback only when `P1D_RAILWAY_CALLBACK_CONTRACT_ONLY=1` and the previous `APP_DATA_MODE=synthetic`, private OAuth-contract and owner-pinned-folder HMAC checks all pass. This is an **opt-in configuration validation, not live deployment**. It denies arbitrary Railway hostnames, lookalike domains, HTTP, extra paths, ports, query strings and mismatched callback URI. The old localhost callback no longer needs to be configured in Google Cloud, although a localhost-only dev mode remains in repository code until retired in a reviewed migration.
2. The public Railway frontend's `frontend/Dockerfile` now explicitly packages `document-inbox.mjs`, which was imported by `ui.mjs` but accidentally omitted in the copied static allowlist. The Railway Node regression test asserts that the fictional phone-first Documents UI module is present in the image allowlist. No real owner metadata is embedded into the public PWA.
3. Tests assert that the public `app.preview_api` exposes **no** Google OAuth callback/start/status/disconnect and the Nginx public proxy still permits **only** the harmless synthetic status endpoint. The public callback therefore remains **absent (not activated)**. No Railway service, secret, database role, domain or network setting has been modified.

## Existing Railway topology (verified read-only via Railway app)

- Project `personal-cfo-dev-sandbox`, environment `development`, source repo `alisufyan-ai7/pakistan-tax-finance-desk`.
- `personal-cfo-frontend-preview`: single public web entrypoint, Nginx + synthetic installable PWA. Only public proxy route `GET /api/preview/status`.
- `personal-cfo-api-preview`: **private**, no public domain; Docker starts `app.preview_api:app`, not local `app.main:app`. It currently has **no** OAuth service endpoint, no persistent volume and no owner-MFA session.
- `Postgres`: private PostgreSQL18 with its own persistent volume. Its existence is not permission to store real owner tokens or metadata in the synthetic preview database.

## Next engineering/security prerequisites to activate a real cloud callback

- Provide an **owner-MFA-authenticated private OAuth handler** reachable only through *exact*, deliberately exposed paths on the public frontend domain (start, callback, status, disconnect). Add strict session, origin/CSRF, PKCE/state one-time expiry, browser cookie hardening, account identity and dedicated-folder verification, rate limits and audit. Don't expose a generic `/api/*` or the legacy finance API.
- Replace P1C's local path-based SQLite AES-GCM vault with **durable encrypted cloud credential/state custody**, using separately accepted key custody, database isolation/roles, backup and independently verified recovery. No refresh token in public browser JavaScript, Nginx logs, Railway frontend variables or GitHub. Owner consent to using the existing Railway private resources for metadata only must be scoped and verified before doing live operations.
- Choose/verify a **private, scheduled metadata worker** with bounded retry/backoff, complete-folder atomic index and heartbeat. New manually uploaded files in the one owner-private folder should be discovered automatically without physical sorting. The app's `drive.metadata.readonly` scope allows file metadata only, not PDF/XLSX download or tax/bank reconciliation.
- Formal G1/G2/G3 private financial production release gates **remain blocked**; no `APP_DATA_MODE=real`, document content processing, offsite backup provider or new billable resource is authorized.
- Google External/Testing Drive-scoped refresh tokens normally expire after seven days; handle fresh re-consent and Google's production/verification or personal-use rules before claiming indefinite background operation.

**Owner's next manual Google Cloud action:** **none**. Do not remove/recreate the client, alter scope or reveal the client secret. The cloud callback must be built, reviewed and tested before clicking a live Connect button.

**Tracking:** [Priority 1 issue #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98), [master roadmap](PRIORITIZED_PERSONAL_CFO_ROADMAP_2026-11-17.md), [earlier cloud design](PRIORITY_1_RAILWAY_CLOUD_GOOGLE_OAUTH_OWNER_SETUP_2026-11-17.md). No Backblaze B2.
