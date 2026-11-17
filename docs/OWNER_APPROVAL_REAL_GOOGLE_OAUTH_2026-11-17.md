# Personal CFO — Owner approval to prepare real Google OAuth

**Date:** 17 November 2026, Chat 04. **Source:** explicit owner instruction in this conversation: “I give you approval for the next critical path and approval for the real Google Auth. Let me know what you need from me to configure the real Google Auth. And I give you consent for that.”

## Decision, scope, and authorization boundary

The owner approves moving from test-only design toward **actual Personal CFO → existing Google Cloud Web OAuth client → existing one private, unsorted Google Drive folder** on the approved Railway project (`personal-cfo-dev-sandbox`, `development`). The owner has already created the existing Google Cloud project, client, metadata-only Drive scope, test-user entry and exact HTTPS redirect URI. **Do not recreate any client, change the OAuth scope, purchase a provider or ask the owner to sort original files.** User consent in chat authorizes engineering/setup preparation; it is **not a Google OAuth access token, an executed Google consent click, a production G2 security approval, or blanket authority to ingest original bank/FBR/Excel bytes**.

**Permitted initial live access after independently accepted G2:** OAuth for `https://www.googleapis.com/auth/drive.metadata.readonly`, verify the account/folder (one private folder), persist state and refresh tokens encrypted in **restricted private backend storage**, and read a bounded one-folder metadata index for authenticated mobile review. Google's OAuth permission covers broad Drive metadata at the consent layer even though the app enforces the one-folder boundary. File original content download, bank/FBR ingestion, ledger cutover, real financial conclusions, further scopes, public unrestricted APIs and G1/G3 activation remain unapproved.

The registered exact callback must stay:
`https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback`

No additional public backend domain. Current frontend `frontend/nginx.railway.conf` exposes **only** synthetic `GET /api/preview/status`. Current private backend starts `app.preview_api:app` and is not an authenticated production OAuth server. Existing PostgreSQL 18 volume is attached to database service; private API has no volume. The isolated `private_drive_google_http` is loopback-only, and `cloud_drive_oauth_vault` / `fake_credential_keyring` accept only synthetic fixtures. G2 live release prerequisites must be implemented/reviewed instead of overriding their guards.

## What the owner must do (only safe actions at the correct stage)

**Now, non-secret checks in Google Cloud (do not click actual Connect yet):**
1. Open [Google Cloud Console](https://console.cloud.google.com/) and select existing `personal-cfo-drive-connector` project.
2. APIs & Services → Enabled APIs & services: verify **Google Drive API** is enabled. If absent, enable only that API.
3. Google Auth Platform → **Clients** → existing **Web application** client: confirm the exact HTTPS callback above appears under **Authorized redirect URIs**, no localhost required; do not recreate or rotate client.
4. Google Auth Platform → **Data Access**: confirm the single intended Drive scope `https://www.googleapis.com/auth/drive.metadata.readonly`. No `drive`, `drive.readonly`, file downloads or write scopes.
5. Google Auth Platform → **Audience**: report only whether **External/Testing** or **In production**, and whether the intended Drive-owning Google account is already listed as an allowed test user if Testing. Do not post the account email here. External Testing+Drive refresh tokens typically expire after seven days. Restricted scope verification/personal-use exemption and owner-controlled domain may require separate review before durable production operation. Do not change publishing status as a shortcut.

**Later, after the private auth handler and storage pass G2 security tests:**
6. Railway → `personal-cfo-dev-sandbox` → `development` → **`personal-cfo-api-preview` (private service) → Variables**: privately enter the *existing Google OAuth Web client secret*, using **sealed** private variable when supported, with exact name `P1C_GOOGLE_CLIENT_SECRET` (the currently named private Google token-exchange adapter variable). It must not go to ChatGPT, GitHub, GitHub Actions, public `personal-cfo-frontend-preview`, JS or Nginx config. The private API is currently only preview runtime; setting a secret alone does not enable OAuth and is **not needed yet**. Other required private owner account/folder configurations and per-purpose encryption/HMAC keys must be provisioned with separately validated private backend credential lifecycle, never by enabling existing fake or loopback guards in production.
7. Through Personal CFO's **newly reviewed and deployed** Connect Google Drive UI, sign in interactively as the owner of the approved folder and verify the Google consent screen before allowing metadata-only access. Do not paste the Google authorization code, access token, refresh token, MFA recovery code, password or OTP into chat. The app must verify one-folder ownership, encrypted grant and no scope escalation; then private metadata scan may be enabled.
8. Owner MFA enrollment/recovery happens through an approved private interface, not chat, with independently tested rotation/revocation/backups. Do not reuse Google credentials as an app password.

## Implementation / security gate in dependency order

1. New owner-private authentication and recovery: real MFA enrollment, password rate-limit, session-device revocation, CSRF/Origin and audit; deployment cannot reuse fake synthetic owner identity.
2. Separate *durable, encrypted* OAuth state/refresh-token custody on existing private Railway/Postgres with dedicated roles, distinct encryption and index keys, isolated encrypted backup/restore, rotation/rollback, no token in logs/frontend.
3. Authenticated exact-route public Nginx proxy review: only approved start/callback/status/disconnect, no wildcard `/api/*`, actual external TLS/trusted proxy sanitization and no access/request-target logs containing Google code/state/query/cookies. Google top-level GET callback must bind one-time state+PKCE to owner session (SameSite=Lax) and redirect to a clean URL.
4. Standalone private Google token exchange and owner-folder-only metadata client, no file download, no real financial mode; direct narrow/private network transport with retries, token expiry/re-consent, safe disconnect/revoke.
5. End-to-end live consent only with the owner present; verify Google account/folder metadata only and persist encrypted grant, then bounded complete pagination & scan receipt/heartbeat and owner-authenticated mobile Documents review queue.
6. Independently test rollback, backups, recovery, least privilege, DoS/lockout, exact-route logging and restricted-scope Google policy, then record accepted deployment and evidence in GitHub. G1 confidential real ledger and G3 original document certification **remain blocked separately**.

## Live state as inspected 17 Nov 2026

Railway project `personal-cfo-dev-sandbox`, environment `development`: the frontend has the public registered Railway domain; the private API has **no** public domain and variable names only `APP_DATA_MODE`, `DATABASE_URL`, `PERSONAL_CFO_PRIVATE_PREVIEW`, `PORT`, `PREVIEW_DB_TLS`, `PREVIEW_INTERNAL_TOKEN`. There is presently **no Google OAuth client secret or client/folder variable** set there. PostgreSQL has its persistent volume. Services show **no running cron schedule**, and no pending Railway patch. No real Google connection. Do not change `APP_DATA_MODE=synthetic` to real, do not activate fake flags or expose private API.

## References and tracking

- [Owner-confirmed registered URI](PRIORITY_1D_REGISTERED_RAILWAY_GOOGLE_REDIRECT_2026-11-17.md)
- [Prior Railway OAuth architecture](PRIORITY_1_RAILWAY_CLOUD_GOOGLE_OAUTH_OWNER_SETUP_2026-11-17.md)
- [Latest project handoff](CURRENT_HANDOFF.md), [Priority 1 issue #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98), [G2 owner-security #110](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/110)
- [Google OAuth web-server docs](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Drive restricted scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- [Google Testing refresh-token expiration](https://developers.google.com/identity/protocols/oauth2)
- [Google restricted-scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification)
