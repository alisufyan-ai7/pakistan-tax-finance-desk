# Chat 04 / P1M — First real-compatible private Google metadata grant custody slice

**Date:** 17 November 2026 · **Owner authorization:** already granted for preparation toward actual Google OAuth in the approved existing Personal CFO project; owner has validated one exact registered Railway callback and test-user/folder ownership and securely STAGED, not deployed, `P1C_GOOGLE_CLIENT_SECRET` on the private API.

## Why this is different from prior fictional-only vaults

Earlier `cloud_drive_oauth_vault`, `fake_credential_keyring` and `private_drive_google_http` deliberately accept only synthetic fixtures/loopback. This P1M milestone begins a **separate real-compatible server-only custody implementation**. It allows opaque refresh-token-shaped bytes under strict dedicated config, while **all GitHub and CI tests use invented tokens and key material only**. It does not depend on the actual Google client secret, does not call Google and is not imported by `app.preview_api`. It is not an already-deployed/release-accepted owner OAuth service.

**New files:** `backend/app/private_metadata_grant_custody.py`, `backend/migrations/versions/0018_owner_google_grants.py`, `backend/tests/test_private_metadata_grant_custody.py`. Only one migration owner. Existing G1 source census, backup/recovery schema revision and disposable PostgreSQL18 CI acceptance updated to include the new table exactly.

## Actual implementation (code-only)

- PostgreSQL transaction-level advisory lock serializes first owner row insert, re-consent, key rotation and local revocation across workers, including when no row exists. SQLite is available only under an explicit **isolated fake-test** guard.
- The new table persists **only HMAC-blinded owner/folder/client identity**, AES-256-GCM ciphertext, independent row HMAC, active key ID, row revision, revoked flag, and coarse epoch. **No plaintext Google refresh token, client ID, owner account or folder ID** in SQL or GitHub. AAD binds ciphertext to owner+folder+client+single immutable `drive.metadata.readonly` scope+key version, preventing cross-owner/folder transfer and scope substitution.
- Dedicated version-labeled 256-bit encryption keys and independent row HMAC key come from private environment only; rejects key reuse between encryption and index domains, wrong active key, damaged/corrupt ciphertext, missing keys, revoked rows, malformed owner/folder/client or refresh tokens. Rewrap to a new active generation requires both old+new keys and increments revision. An operator must separately back up keys and validate independent encrypted restore before removing old generation.
- Local revoke **blanks the ciphertext** and prevents reads; explicit result shows Google **provider revocation is NOT complete**. A future private endpoint needs explicit Google revocation for complete disconnect.
- **No public route and no OAuth state/PKCE handler.** A future caller must independently authenticate the owner with production MFA and bind single-use OAuth state/session/folder **before** invoking this vault; private unmounted library cannot assert this.
- The stage has no new Railway env/config/network mutations and never reads the owner's already-staged `P1C_GOOGLE_CLIENT_SECRET`. Real financial `APP_DATA_MODE=real` remains prohibited; private metadata grant code requires `APP_DATA_MODE=synthetic` plus **two default-off, independently reviewed release flags** and keys: `P1M_PRIVATE_METADATA_CUSTODY_ONLY`, `P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED`, `P1M_METADATA_ENCRYPTION_KEYS_JSON`, `P1M_METADATA_ACTIVE_KEY_ID`, `P1M_METADATA_ROW_HMAC_KEY`. No live environment contains these flags at this checkpoint.
- Only within disposable CI tests are these flags and **public fabricated CI keys** set. Do not flip them on Railway as an authorization shortcut.

## Required negative proofs and acceptance

Tests cover roundtrip ciphertext storage and absence of plaintext SQL, wrong owner/folder/client, independently keyed HMAC, nonce uniqueness, corrupt/tampered row fields, invalid token, dual-worker first insert, active key rotation+retirement, revocation/reconnect, G1 recovery/census, PG18 precise schema version, and no public OAuth/login route. **No real Google account, financial document or credential is touched**.

For genuine G2 acceptance and actual owner browser consent still needed: (1) independently vetted real owner enrollment/recovery, throttling, CSRF+session revocation; (2) dedicated private least-privilege DB role, audited key backup/restore/rotation and key-loss drill; (3) trusted Railway exact-route TLS proxy that suppresses access log callback code/state, single-use PKCE and SameSite=Lax session bound to owner; (4) verified existing exact Google client and one private folder, and restricted-scope policy assessment; (5) controlled owner consent / staged secret deployment only **after** those tests. Then metadata-only scanning and authenticated owner review UI; originals/G1 ledger/G3 parsers remain independently blocked.

## Verified facts at authoring

GitHub client-side docs and owner evidence: [owner config checks](GOOGLE_OAUTH_OWNER_SETUP_CHECK_2026-11-17.md), [owner OAuth approval](OWNER_APPROVAL_REAL_GOOGLE_OAUTH_2026-11-17.md), [latest handoff](CURRENT_HANDOFF.md), [G2 issue #110](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/110), [P1 Drive #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98). **CI and merge acceptance are PENDING** until exact PR head runs green; do not describe test implementation as accepted deployment.

No real bytes, account identity, folder ID, OAuth code/secret or refresh token are in this public document.
