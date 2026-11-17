# P1C — Owner's Google Cloud OAuth client → private local callback and sealed grant

**Owner confirmed 17 November 2026:** dedicated Google Cloud project created, OAuth **Web application** client ID registered, `https://www.googleapis.com/auth/drive.metadata.readonly` configured, and **exact** loopback `https://localhost:8443/api/drive/oauth/callback` registered. The actual Client ID and Google Cloud Project ID are held in the owner's private conversation/configuration, **not hard-coded into this public GitHub repo**. The **client secret was NOT disclosed** to this assistant and must not be pasted into chat, commits or Railway. One already approved owner-private Google Drive folder remains the single unsorted upload inbox. Backblaze B2 deferred.

## What this PR implements

- `backend/app/private_drive_oauth_vault.py`: **separate private local SQLite** credential vault with exact owner-only directory/file permissions and dedicated AES-GCM key injected outside GitHub. Random state HMAC lookup, encrypted PKCE verifier, 10-minute expiry and **atomic one-time claim before token exchange**, including independent worker replay/race denial. Refresh token sealed to exact registered client + approved one-folder HMAC; local disconnect erases token, but Google-side revocation remains separate. Never writes credentials into the legacy finance database or synthetic Railway.
- `backend/app/private_drive_google_http.py`: narrowly restricted Google TLS token exchange/refresh and **metadata-only** Drive folder verification. Uses fixed Google HTTPS endpoints, no redirects and bounded JSON bodies; requires specific opt-in flags. It checks exact granted scope, token expiry and the source folder ID, MIME type, not trashed, not shared, and `owners(me)=true` before sealing the refresh grant. A Google `files.list` builder is pinned to direct children of **one** owner-approved folder; never calls `alt=media`, file export or a Drive write operation.
- `backend/app/main.py`: adds four routes **only to the existing local, authenticated, HTTPS-only synthetic application**: POST `/api/drive/oauth/start`, GET `/api/drive/oauth/callback`, GET `/api/drive/oauth/status`, POST `/api/drive/oauth/disconnect`. All default to **disabled**. Starting, checking or removing a grant requires local owner MFA session, including CSRF protection for POST; Google's callback cannot reuse a state and is restricted to loopback HTTPS. The public Railway `preview_api.py` remains untouched, with **no** public OAuth or financial route.
- Adversarial tests in `backend/tests/test_private_drive_oauth_vault.py` and `backend/tests/test_private_drive_google_http.py`, including synthetic two-worker replay races, ciphertext tamper, file permissions, expired state, broad scope and wrong folder denial. **No real OAuth secrets, source content or Google API calls occur in GitHub Actions.**

## Activation is not automatic

**These controls alone do not activate a real Personal CFO Google connection.** The owner still needs their computer running a separately approved **private** Personal CFO service with correctly provisioned TLS for registered localhost callback, actual independently accepted MFA, G2 credential-vault/key recovery, and explicit consent. The public Railway PWA has **no** callback or private metadata API. Google Testing-mode refresh grants can expire after seven days; renewal/re-consent and formal production verification/personal-use scope conditions must be assessed. The owner should NOT run a live callback or enter client secrets into an unreviewed host.

Local-only environment variable names (values are owner-private and **must never** be committed, printed or provided in chat):
- `P1B_GOOGLE_CLIENT_ID`: owner-registered Client ID
- `P1B_GOOGLE_REDIRECT_URI`: exact `https://localhost:8443/api/drive/oauth/callback`
- `P1B_GOOGLE_FOLDER_ID`: only owner-approved private Drive folder ID
- `DRIVE_ALLOWED_FOLDER_HMAC`: keyed HMAC of the approved Drive folder ID; `DRIVE_INDEX_HMAC_KEY` is secret and distinct from the encryption key
- `P1C_GOOGLE_CLIENT_SECRET`: private OAuth Web client secret, **never** stored in the source repository
- `P1C_OAUTH_VAULT_PATH`: absolute path to local `*.sqlite3` in a pre-created private user-owned 0700 directory **outside** the repository
- `P1C_OAUTH_VAULT_KEY`: independently generated 32-byte URL-safe base64 AES-GCM key, stored separately from vault and source control
- `P1B_PRIVATE_OAUTH_CONTRACT_ONLY=1`, `P1C_LOCAL_OAUTH_VAULT_ENABLED=1`, `P1C_GOOGLE_NETWORK_ENABLED=1`, `P1C_PRIVATE_OWNER_MFA_ACCEPTED=1`: **all default disabled**; these are gates, not substitutes for actual private MFA/security certification
- `OWNER_AUTH_MODE=totp_session`: the local service enforces a private MFA session for this flow, HTTPS and CSRF. `APP_DATA_MODE=synthetic` remains mandatory.

## What remains blocked

- No owner setup actions have been executed on the owner's computer, no TLS listener on port 8443 has been launched, no Google Cloud resource or secret modified, no actual OAuth code exchanged, no real refresh token stored, no live Drive API queried, no original contents accessed.
- This is a local credential/metadata *development path*, not a production deployment. The user's previous ChatGPT Google Drive connection is separate and cannot be repurposed as Personal CFO's OAuth grant.
- Completing the private authenticated PWA/mobile review API and *scheduled*, heartbeat-tracked Google Drive one-folder sync still requires G2 independent security acceptance and approved hosting. No genuine bank/FBR/Excel source file processing until G1/G2/G3 separately release.
- **G1 real owner financial ledger cutover, G2 actual owner MFA/independent offsite recovery, and G3 genuine-source certification remain BLOCKED**. Neither Client ID registration nor a synthetic test permits real financial-data import or `APP_DATA_MODE=real`.

Official Google docs: [Web-server OAuth and PKCE](https://developers.google.com/identity/protocols/oauth2/web-server), [Drive metadata permission](https://developers.google.com/workspace/drive/api/guides/api-specific-auth), [Drive v3 files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list), [Google OAuth consent and token lifetimes](https://developers.google.com/identity/protocols/oauth2).
