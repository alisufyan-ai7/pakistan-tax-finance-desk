# P1AA — Read-only runtime verification before attended owner MFA enrollment

**Date:** 18 November 2026. Source-safe, default-off. This does not activate a public login or Google consent.

The owner completed the `P1Z` encrypted local key escrow and private Railway CLI upload with `--confirmed-independent-backup`. Railway independently confirmed seven variable **names** on `personal-cfo-dev-sandbox/development/personal-cfo-api-preview` (five unique runtime encryption/HMAC keys, one opaque owner reference, one TLS restricted-role URL), and the existing offline signer *public* key. No values should be printed, copied to chat or committed to GitHub. The two staged fields for the sealed Google client secret are still **not applied**.

## Read-only preflight scope

A new separately invoked CLI `python -m app.private_owner_runtime_preflight` checks:

- exact development Railway project/service and `APP_DATA_MODE=synthetic`;
- five distinct, correctly sized secret keys, valid opaque one-owner reference and off-device signing *public* key;
- exact dedicated `personal_cfo_owner_auth` database and `personal_cfo_owner_credentials` technical role with a **TCP/TLS** SQL connection;
- full effective least-privilege `P1S` audit: no finance/admin/version-table grants, row deletion, table/sequence privileges, temp/schema creation or inherited authority;
- read-only SQL transaction and each of six approved owner/recovery/OAuth tables **empty**, so the first-account operation cannot overwrite an existing enrollment.

It returns only booleans/count of key *domains* and no credentials, key values, identity records, database rows or source contents. Run no migrations, administrative SQL, Google token exchange or financial ingestion in this step. The SQL role may be active while actual owner password/TOTP enrollment remains absent.

## Operator procedure

1. Independently verify that the previously staged `P1C_GOOGLE_CLIENT_SECRET` remains **STAGED and UNAPPLIED**. Verify the public preview still serves only synthetic data. Do not use Railway **Apply Staged Changes**.
2. Choose a narrowly controlled private API deployment that includes the five live keys and restricted DSN, without committing staged changes. A normal code build/redeploy is NOT the same as `accept-deploy`; confirm Railway behavior and review deployment metadata before proceeding. If there is any doubt that the staged Google secret would be committed, stop.
3. Through an authenticated Railway CLI SSH session, execute only:

```sh
railway ssh \
  --project 7021b227-f704-43d6-bcff-debdb7255b81 \
  --environment development \
  --service personal-cfo-api-preview \
  -- env P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1 \
  python -m app.private_owner_runtime_preflight
```

4. Share **only sanitized JSON**, never the DSN or any key. A successful result is a prerequisite to, but never sufficient approval for, actual MFA enrollment.
5. Before claiming that the database password is server-enforced, verify a deliberately **incorrect** password is denied by the same restricted TCP path; the previous `psql -W` password prompt by itself does not prove the server's authentication method. Avoid placing the real password in chat, command args or logs.
6. Once all above passes, configure the one-time private operator G2 flags through a separately reviewed process (not public preview), then the owner runs an authenticated **private attended** `python -m app.private_owner_setup_cli enroll` to set their new Personal CFO password, confirm an authenticator code and receive eight recovery codes exactly once. Save them away from the authenticator device; keep the offline signing private key separate.
7. Secure and verify the minimal encrypted credential database snapshot and the independent recovery keys needed to restore the one-owner account. A full financial DB backup rollout may remain deferred.

**Release truth:** this preflight and all prior source merges do **not** certify full G2, active real user authentication, production OAuth callback, Google consent or actual bank/FBR processing. Existing Google test user, OAuth client and exact HTTPS callback need no recreation.
