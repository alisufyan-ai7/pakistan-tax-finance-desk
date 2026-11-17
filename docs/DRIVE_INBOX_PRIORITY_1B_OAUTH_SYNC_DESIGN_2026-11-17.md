# Priority 1B — Personal CFO application Google OAuth + reliable one-folder synchronization

**Owner directive:** the existing dedicated, private Google Drive folder is the **only** source inbox, and the owner will not rename, organize or move documents. Backblaze B2 remains deferred. Do not put the actual folder ID, private original filenames, OAuth tokens or account numbers in GitHub or CI.

## Verified implementation in this branch

1. `drive_google_oauth.py` builds an owner-consented Google web-server OAuth authorization URL using fresh state and SHA256 PKCE. It requests only `https://www.googleapis.com/auth/drive.metadata.readonly`, offline consent and an exact **loopback HTTPS** callback. Public Railway or another host cannot be configured as a callback in this development contract. The approved folder is pinned by a private HMAC and is never placed in the OAuth URL.
2. It validates callback state, a fresh authorization code shape, exactly the approved metadata-read scope and an offline refresh grant, **but deliberately does not exchange/persist real tokens or mark the PWA connected**. A true implementation must atomically consume a persisted OAuth state, exchange codes through Google's token endpoint, verify Google's user identity, encrypt/store/rotate refresh tokens, add owner MFA and an audited revoke/disconnect path. This must not be improvised on the public preview.
3. `drive_private_sync.py` orchestrates complete, bounded one-folder `files.list` **synthetic fake** metadata pages, retries 429/5xx failures with a maximum 3 attempts/page, never saves a partial page sequence, then calls the **existing encrypted transactional Drive inbox** from Priority 1A. A redacted internal review queue is available; it never returns raw names/IDs or file content and cannot claim verified finance.
4. External public preview remains read-only and synthetic; no new public API, OAuth callback, token vault, persistent scheduler, real file import or Railway deployment. This PR is **application-side protocol and worker preparation**, **not a completed connection to the owner's Google account**.

## Google's real access restrictions

- `drive.file` grants file-specific access and a Picker-selected folder does NOT guarantee the app automatically sees new files independently uploaded under that folder. Since the owner insists on a **single passive drop folder**, Google's broader `drive.metadata.readonly` scope may be needed to list its direct children reliably. This scope is **restricted at the Google permission layer** even if our application queries only the approved folder. It can require Google consent-screen verification/security review depending on deployment category.
- A dedicated new Google account helps bound the account-wide authorization risk, but account-level read access is **not** equivalent to a technically enforced Drive-native folder-only grant. The app imposes an additional pinned-folder query and independently checks each returned item's parent. Non-owner Drive folders must never be scanned.
- Web server OAuth requires a Google Cloud OAuth client ID, exact redirect URI, registered consent screen and an actual user authorization. The existing ChatGPT Google Drive connection cannot be transferred into the Personal CFO app.
- External Google OAuth apps in **Testing** mode may issue refresh tokens expiring after seven days (unless only basic OpenID scopes), so it cannot be described as a fully reliable indefinitely scheduled production sync. Google Restricted Scope Verification (or applicable personal-use exception) and G2 credentials/privacy acceptance are needed before live owner operation.

Official references: https://developers.google.com/identity/protocols/oauth2/web-server , https://developers.google.com/workspace/drive/api/guides/api-specific-auth , https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list , https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification .

## Release prerequisites before genuine Google Drive app connection

- Owner approves the exact private resource used for Google OAuth/token storage, secure MFA flow and callback host; an OAuth client is created/registered specifically for Personal CFO **without** committing its secrets or redirecting to the public demo.
- Build encrypted persistent OAuth state/refresh token vault, audit, expiry/replay/CSRF protection and least-privilege network access. Owner authorizes using their dedicated account.
- Complete genuine-data G1/G2/G3 checks before downloading/processing original bytes; metadata-only inventory is not financial import or official FBR filing proof.
- Implement a supervised scheduled scanner with durable cursor/heartbeat, retry/backoff and owner-visible stale/error states; only successful complete snapshots advance it. No empty snapshot on a provider error.
- Connect the **authenticated private owner app** review queue to the phone-first Documents tab; never expose source metadata/tokens through the current public synthetic Railway preview.

## Tests

The Python regression suite validates PKCE/state generation and strict redirect/scope/folder config, rejects forged/expanded callback scopes and real mode, and proves complete two-page scan, 429 retry, failure on page 2 preserving the last committed index, outside-folder denial and no public token/financial assertion. CI uses only fictional metadata and no Google network requests.

**Priority 1 stays OPEN** until the app truly connects and syncs the approved Google account and source verification passes. The owner retains a one-folder, no-sorting workflow.
