# P1Z — Owner-controlled encryption key escrow and private Railway setup

**Context:** One human Personal CFO owner; separate restricted PostgreSQL technical login authenticated against `personal_cfo_owner_auth` using actual TCP, with current permissions `t|t|f|f|f`. This is **not** a public login, active Google grant or real-data release.

## Why this small local tool exists

Owner MFA bootstrap requires **five distinct** 256-bit random encryption/HMAC keys and one opaque owner reference. These must be independently recoverable if a device or Railway deployment is lost. The owner already stores the separate encrypted Ed25519 offline recovery signing key; do **not** regenerate it. Never ask the owner to send the five values, database password, encrypted escrow passphrase, recovery codes, or private signing file to ChatGPT.

P1Z's `private_owner_key_custody.py` runs on the owner's trusted Mac and generates a new **encrypted local file** using scrypt (N=32768, r=8, p=1) and AES-256-GCM. It rejects overwrites, creates mode 0600 and never prints the generated values by default. It contains the five runtime keys and opaque owner reference, **not** the PostgreSQL password or offline Ed25519 private key.

## Step A — Create and independently back up the encrypted escrow

In your existing Mac Terminal, inside the already-cloned `backend` folder and virtual environment, pull the approved merged revision first:

```sh
cd ~/projects/pakistan-tax-finance-desk/backend
git pull --ff-only
source .venv/bin/activate
python -m app.private_owner_key_custody create "$HOME/personal-cfo-owner-keys.enc"
python -m app.private_owner_key_custody verify "$HOME/personal-cfo-owner-keys.enc"
```

The `create` command asks for a **new, separate local escrow passphrase**, entered twice through the attended terminal. It must not match the database password or offline signer passphrase. The `verify` command asks for the escrow passphrase once and prints only verification booleans. Never rerun `create` if the file already exists.

Create **an independent encrypted backup** of the escrow file and store it separately from the Mac and the authenticator phone. Verify you can decrypt that copy; keep the escrow passphrase in a trusted password manager or other separate safe place. The owner must also preserve their existing offline signing key, which is independent from this bundle. Full financial database backup rollout may remain postponed; real owner identity key loss must not.

## Step B — Privately configure only the existing Railway API, without a deploy

Only after two copies are safely retained, use:

```sh
python -m app.private_owner_key_custody configure-private-railway \
  "$HOME/personal-cfo-owner-keys.enc" --confirmed-independent-backup
```

This attended command requests:
1. The local escrow passphrase, which is never sent to Railway.
2. The **already-created restricted PostgreSQL role password**, hidden by `getpass`. This password is used only to construct an appropriately URL-encoded, TLS-required **`postgres-ade30e25.railway.internal:5432/personal_cfo_owner_auth`** credential URL.
3. The exact acknowledgement `CONFIGURE PRIVATE API WITHOUT DEPLOY`.

It then uses the Railway CLI's documented `railway variable set NAME --stdin --skip-deploys` command to set exactly these **seven** variables on `personal-cfo-dev-sandbox/development/personal-cfo-api-preview`:

- `P1N_OWNER_ENCRYPTION_KEY`
- `P1N_OWNER_IDENTITY_HMAC_KEY`
- `P1N_OWNER_SESSION_HMAC_KEY`
- `P1P_OWNER_RECOVERY_ENCRYPTION_KEY`
- `P1P_OWNER_RECOVERY_HMAC_KEY`
- `P1W_OWNER_REF`
- `P1W_OWNER_CREDENTIAL_DATABASE_URL`

Passwords and keys are sent through **stdin**, not process argument lists, shell history, source code, workflow logs or the ChatGPT conversation. Subprocess output is suppressed and errors sanitized. If interrupted, re-run **with the same encrypted escrow**, not a newly generated one; review variable names before retrying.

**Do not press Deploy / Apply Staged Changes / Google Connect.** The previously sealed `P1C_GOOGLE_CLIENT_SECRET` remains separately staged, and this action must not apply it. The new key values do **not** appear in an already-running container until an independently approved redeployment. This command does not set G2 review flags, approve operational recovery, or authorize live Google.

If the app's private PostgreSQL host differs from `postgres.railway.internal`, stop and inspect the Railway private DNS. Do not rewrite the URL to a public TCP proxy or copy the superuser DSN.

## Step C — Verification and actual MFA enrollment (separate milestone)

After the variable names are present, an operator checks the still-staged Google secret and creates a reviewed private-only redeployment, **without applying unrelated staged changes**. The existing P1S auditor must pass against the restricted role on the isolated database, and the P1N/P1P/P1Q/P1W gates must be explicitly reviewed and configured. Only then the owner executes an attended `python -m app.private_owner_setup_cli enroll` in the authenticated private API container to set a new app password, scan the authenticator URI and save eight one-time recovery codes off-device. An initial independent encrypted credential DB snapshot must be stored and restorable before claiming recovery readiness.

Finally, the app's real Google browser redirect/callback and error/access logging must have the minimum approved TLS, Host, Origin, CSRF, rate and token-redaction controls before the staged client secret may be applied and Google consent attempted. This workflow does **not** activate owner login or Google Drive sync.

## Source references

- `backend/app/private_owner_key_custody.py`
- `backend/app/private_owner_setup_cli.py`
- `backend/app/private_owner_bootstrap.py`
- `backend/app/private_credential_role_policy.py`
- `docs/OWNER_ISOLATED_POSTGRES_BOOTSTRAP_2026-11-18.md`


## P1AD verified private endpoint correction (18 Nov 2026)

The owner ran private connectivity probe P1AC from `personal-cfo-api-preview` and received `stage=private_dns_resolution`. Railway's LIVE Postgres service configuration returned private-network endpoint label **`postgres-ade30e25`**, not `postgres`. The previous P1Z key-custody helper generated a DB URL pointing at `postgres.railway.internal`, which is not the currently assigned internal endpoint. This is not evidence of password failure, encryption-key loss or a missing database.

Use the **new merged** helper to change only `P1W_OWNER_CREDENTIAL_DATABASE_URL` in the approved PRIVATE API environment (after `git pull --ff-only`):

```sh
cd ~/projects/pakistan-tax-finance-desk/backend
git pull --ff-only
source .venv/bin/activate
python -m app.private_owner_key_custody repair-private-owner-db-host
```

The tool prompts **privately** for the *existing restricted PostgreSQL technical role password*, and then requires the exact phrase `REPAIR PRIVATE OWNER DATABASE HOST ONLY`. It uses `railway variable set P1W_OWNER_CREDENTIAL_DATABASE_URL --stdin --skip-deploys` with the checked `postgres-ade30e25.railway.internal` endpoint and TLS `sslmode=require`. It does **not** ask for your owner MFA password, escrow passphrase or signing private key; it does not rewrite any of the five keys, modify SQL roles/databases, accept the staged Google secret, or deploy the API.

A successful variable update alone does **not** cause an already-running container to adopt the new URL. Separately verify Railway staged Google changes remain **unapplied** and arrange a controlled restart/redeploy of only the private API. Then rerun the existing private P1AC connectivity probe and complete P1AA full read-only role/empty-table preflight. If the DNS stage persists, inspect the current Railway private endpoint label again; do not disable TLS, enable public PostgreSQL or retry the whole key setup.
