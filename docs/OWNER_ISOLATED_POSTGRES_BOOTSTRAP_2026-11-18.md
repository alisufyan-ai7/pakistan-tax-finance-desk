# P1Y — One-owner database bootstrap without touching financial tables

**Checkpoint:** 18 November 2026, after user's authenticated Railway read-only preflight.  
**Status:** SOURCE/CANDIDATE only until exact-head PostgreSQL18 CI, human-reviewed SQL and private administrator deployment.  
**Human accounts:** one owner. `personal_cfo_owner_credentials` is a technical database role, not another human account.

## Observed (read-only; not an administrator inventory)

The owner's Railway SSH preflight returned: `credential_tables_present=0` of 6, `alembic_table_present=false`, `role_present=false`, `offline_public_recovery_key_configured=true`, `enforced_read_only=true`. The live preview credential cannot attest whether unrelated financial tables exist. It **does not** establish that the entire database is empty, and must not justify `alembic upgrade head` on that connection.

## Chosen safe path

Keep the existing Postgres Railway service, network and synthetic finance preview unchanged. Provision **one additional logical PostgreSQL database inside that same existing service**, named exactly `personal_cfo_owner_auth`. No new Railway service, public TCP proxy, Google OAuth client, paid provider or extra human login is created. It is a credential boundary, not a financial-data source.

The source-reviewed schema is generated only from the six existing SQLAlchemy owner models:

- `owner_private_identities` (single owner + encrypted TOTP and salted password hash)
- `owner_private_sessions` (hashed short-lived session/CSRF)
- `owner_private_recovery_states` (encrypted one-time recovery kit)
- `owner_private_recovery_audit` (audited hold/re-enrollment)
- `owner_google_metadata_grants` (encrypted restricted metadata grant)
- `owner_private_oauth_attempts` (one-time encrypted PKCE attempt)

An **administrator-only** `owner_auth_schema_version` receipt records `p1y_owner_auth_v1` and the model signature. It must remain unreadable by the runtime credential role. This is not an Alembic migration of the 36 financial tables; no existing Alembic revision is fabricated. Subsequent changes to the separate owner database require a separate versioned migration.

The reviewed schema SQL fails if executed on any database not named `personal_cfo_owner_auth`, or if that database already has any public user tables, views, or sequences. All initial six-table DDL is in one transaction and automatically rolls back on failure. Generate the SQL **without connecting to any database**:

```sh
cd ~/projects/pakistan-tax-finance-desk/backend
git pull --ff-only
source .venv/bin/activate
python -m app.private_owner_auth_schema > "$HOME/personal-cfo-owner-auth-v1.review.sql"
```

The output is nonsecret SQL, but **do not execute it until** the separate, empty database has been positively identified in an authenticated private administrator session and the exact-head CI/PG18 test is successful. Use an administrator-owned connection through Railway private SSH; never expose the existing PostgreSQL service on a public TCP proxy to run this.

The role plan `ops/owner_auth_isolated_role.review.sql` must be executed only **after** the schema receipt passes on that isolated logical database. It creates `personal_cfo_owner_credentials` as **NOLOGIN**, NOINHERIT, no role/database creation, no replication/BYPASSRLS, grants connection and usage only on the isolated database/public schema, grants SELECT/INSERT/UPDATE to exactly those six tables, and leaves version-receipt, DELETE/TRUNCATE, schema CREATE, database CREATE/TEMP and unrelated table rights denied. It removes `PUBLIC` database CONNECT/TEMP only in the *new isolated database*, not the existing synthetic/finance database.

Only after an independently verified P1S effective-role audit does an administrator set a randomly generated credential using **interactive** `psql \password personal_cfo_owner_credentials`, activate LOGIN in the reviewed database, and configure `P1W_OWNER_CREDENTIAL_DATABASE_URL` privately on the approved administrative runtime. The password/URL must not be pasted into ChatGPT, SQL files or GitHub. All user-facing finance and OAuth routes remain disabled.

## Required readiness before MFA activation

1. Exact-head PostgreSQL18 tests successfully create the isolated owner schema and validate the role, including no access to the version receipt.
2. The owner already has an encrypted Ed25519 offline recovery signing key; its public half is in Railway `P1Q_OPERATOR_PUBLIC_KEY`. Private file, passphrase and backups stay on the owner's devices.
3. A separately escrowed minimal encrypted copy of **owner credential database state plus versioned encryption/HMAC keys** must be restorable. This is significantly smaller than the deferred full *financial* database disaster-recovery rollout.
4. A verified attended private terminal / credential role must run `python -m app.private_owner_setup_cli enroll`; the user creates the password, confirms the TOTP code, and stores eight one-time recovery codes off-device. No authentication detail is entered into chat, GitHub or the public preview.
5. Minimum public TLS/Host/Origin/CSRF/log redaction and approved callback must be accepted before applying the existing staged Google client secret or starting **actual** Google consent. The comprehensive later Railway audit does not excuse basic callback protection.

**Do not equate code merge, a role's existence, or this plan with completed owner enrollment, live Google connection or G2 acceptance.** The current preview's report may continue to show zero owner tables because the isolated database is separate; run a separate credential-role attestation against `personal_cfo_owner_auth` to verify the new store.
