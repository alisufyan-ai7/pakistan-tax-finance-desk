# P1AT — Read-only enrolled-owner G2 SQL + Google connector key acceptance (18 Nov 2026)

**Status:** Source-only private shell diagnostic, default-off and not run against the owner's Railway database by CI/ChatGPT. Requires an operator-controlled authenticated Railway SSH command after accepting the reviewed runtime environment. **Not public login, Google consent, credential rotation, owner re-enrollment, document import or G2 release.**

## Why this separate diagnostic exists

Earlier `P1AA` and `P1AB` preflights correctly require **empty owner identity/recovery tables** before first enrollment. The owner has already enrolled one owner, completed a private encrypted credential capture and copied the three original encrypted recovery files to two locations. Reusing the **first-enrollment** diagnostic after enrollment would correctly fail, so it must not be misinterpreted as a new need to reset or repeat backups.

The owner has now successfully prepared six new OAuth/Google metadata keys and a single backend/frontend gateway key using merged P1AR #176/#177. Independent Railway variable-**name** readback confirms their presence, but does not independently test values, live process inheritance, TLS role, or original Google consent. `P1C_GOOGLE_CLIENT_SECRET` remains staged/unapplied; all owner/Google route activation flags remain absent.

## Exact P1AT check

The new `backend/app/private_owner_post_enrollment_readiness.py`:
- Refuses any active P1AJ/P1AK/P1AO/P1AN/P1AP or P1C network mode; requires the reviewed `personal-cfo-dev-sandbox` / `development` / `personal-cfo-api-preview` identity and an **ephemeral** `P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1` shell flag. No flag is written to Railway.
- Validates existing five owner/recovery encryption+HMAC keys, independent offline operator key, new P1R state encryption/HMAC, two-version P1M encrypted metadata grant keyring+row HMAC, Drive index HMAC and trusted gateway token **without revealing values**. Rejects reused/invalid key domains.
- Checks actual pinned private folder ID HMAC and exact approved Google client/callback using existing no-network contract function. It never sends any Google request or uses the staged client secret.
- Uses the existing isolated credential DSN validator, PostgreSQL TLS/least-privilege role attestor and `P1AI._attest_enrolled_owner`: **one** enrolled identity, **one** recovery state and nonempty recovery audit with a read-only SQL transaction. It does not read or return password hashes, recovery codes, identity details, monetary rows or exact counts.
- Prints fixed sanitized `PASS/BLOCKED` JSON and one safe stage; returns nonzero on failure. **Even PASS explicitly reports G2 release authorization = false** and unverified platform logs/gateway cross-service equality/new key independent restore.

Synthetic CI uses entirely fabricated keys and fake SQL connection with no actual Railway access; adversarial tests cover inactive required flags, duplicate key domains, corrupted folder, wrong origin, privileged/failed SQL and safe error scrubbing. Full existing backend CI and isolated PG18 check required.

## When the owner action becomes necessary

The existing `--skip-deploys` key preparation did not prove these freshly set variables are inherited by the currently running backend process. **Do not ask the owner to run this read-only probe until a separately reviewed deployment/variable-activation stage is ready.** Once the approved existing service has been redeployed with keys and no login/OAuth flags, this one read-only SSH command can provide the missing actual role+one-owner acceptance without any backup copy, re-enrollment or Google login:

```sh
railway ssh \
  --project 7021b227-f704-43d6-bcff-debdb7255b81 \
  --environment development \
  --service personal-cfo-api-preview -- \
  env P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1 \
  python -m app.private_owner_post_enrollment_readiness
```

Share only sanitized final JSON, never raw Railway variables/DSN, private folder/client identifiers or any private credential output. Do not run the separate generator again.

**Still after P1AT PASS:** independent full Railway edge HTTPS/Host/cookie/CSRF/Origin/access+error logging acceptance including OAuth query code/state and provider callback; one-owner successful live MFA after controlled G2, staged client secret release scope, key loss rotation/recovery risk and rollback; only then owner-attended Google consent. G1/G3 real finance/document bytes remain blocked.
