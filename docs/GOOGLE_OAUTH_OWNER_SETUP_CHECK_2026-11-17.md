# Chat 04 — Owner Google Cloud screenshots + staged sealed Railway secret (17 Nov 2026)

**Owner action:** Supplied screenshots of the existing approved Personal CFO Google Cloud project and owner-approved Railway `development` environment. This file is source-safe: no owner test-user email, real client ID/secret value, Drive folder ID, access code, financial document or private source is included.

## Confirmed in owner screenshots

- **Google Drive API: ENABLED** (Google Cloud API Library).
- **Google OAuth Audience:** `External`, `Testing`; **one test user** listed (no email recorded here). The intended Drive owner account must be the listed test user; screenshot alone does not independently verify folder ownership.
- **Data Access:** exactly the `.../auth/drive.metadata.readonly` restricted scope displayed; no sensitive or non-sensitive extra rows. This grants metadata visibility at the whole-account consent layer, while the app must restrict its listing to the explicitly owner-approved one folder.
- **OAuth Client:** existing **Web application** client, masked secret status **Enabled**, no JavaScript origins shown, and an HTTPS Railway redirect listed but **visually truncated by the Google field**. Previous owner assertion and canonical `docs/PRIORITY_1D_REGISTERED_RAILWAY_GOOGLE_REDIRECT_2026-11-17.md` establish expected exact URI:
  `https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback`
  Confirm its complete trailing path by clicking inside the field; **do not add another URI**. Google client's blue `Save` button was visible; screenshot does not prove a new unsaved change, so only click Save if the intended URI is edited.
- **Railway:** owner prepared `P1C_GOOGLE_CLIENT_SECRET` on **private `personal-cfo-api-preview`** and used the UI sealed-secret icon. Owner screenshot displays `Apply 1 change` / `Deploy` — the change was **STAGED**, not applied. Do not assume a sealed variable is accessible at runtime or that a running API uses it.

## Independent Railway read-only confirmation

Queried **only** approved Railway project `personal-cfo-dev-sandbox`, environment `development`. `describe-environment` reports `STAGED` patch, changeCount **2** (the encrypted value addition plus the seal flag for the **one** variable). `describe-service` for private API shows two staged configuration diffs under `P1C_GOOGLE_CLIENT_SECRET`: `encryptedValue` added and `isSealed` added, no destructive changes. The private API has **zero public domains**, healthy/latest SUCCESS synthetic preview, and still has only `app.preview_api:app` as its deployed application. No live Google OAuth handler/proxy/sync is verified. **Never read or echo the secret value.**

## Immediate next action

1. **Do not click Railway `Deploy` yet:** the sealed client secret is staged securely in the correct **private service**, but deploying it into the current synthetic preview API adds a real credential to a service that is not the production-approved OAuth owner gateway. Keep the staged patch pending for implementation review (do not delete or retype the secret).
2. Google console configuration checks are complete except **full URI trailing path visual confirmation** and **the owner's confirmation that their folder-owning account is the listed test user**. Do not publish/verify the OAuth app to production as a shortcut.
3. Continue engineering and independent acceptance of actual owner-MFA enrollment/recovery, dedicated encrypted/recoverable credentials and token custody with DB least privilege, exactly scoped public callback without query/code access logs, session-bound single-use state/PKCE and narrow Google metadata-only one-folder query. **Synthetic test modules are not substitutes for these gates.**
4. Only after reviewed and deployed private backend, trusted proxy and backup/role acceptance: coordinate application of staged sealed backend secret and controlled browser OAuth consent. The browser owner must do interactive Google consent themselves, with no client secret, code, refresh token, OTP or recovery code pasted in chat.
5. Scope `drive.metadata.readonly` is **restricted**; the External/Testing app's refresh token typically expires in **7 days** (Google OAuth docs) outside profile-only exceptions. Plan re-consent/staleness and verify any personal-use/publishing exemption before promising unattended long-term sync.

## Must not be inferred

A visible masked secret and green Drive API check do **not** prove it is deployed or that there is a working callback. Google project published status is still `Testing`, not production. No real Google consent/account/folder validation, actual metadata scanned, background worker, documents parsed or G1 real finance authorized. G1/G2/G3 real release gates remain **BLOCKED**, although the owner explicitly approved progressing toward real Google OAuth and later metadata-only consent.

## Links

- [Owner's explicit earlier consent and private setup plan](OWNER_APPROVAL_REAL_GOOGLE_OAUTH_2026-11-17.md)
- [Approved exact callback URI](PRIORITY_1D_REGISTERED_RAILWAY_GOOGLE_REDIRECT_2026-11-17.md)
- [Current handoff](CURRENT_HANDOFF.md)
- [Owner security issue #110](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/110)
- [One-folder Google connection issue #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98)
- [Google OAuth testing refresh token expiry](https://developers.google.com/identity/protocols/oauth2)
