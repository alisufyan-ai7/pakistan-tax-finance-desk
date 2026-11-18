# P1AR — Single private one-owner Google connector key preparation

**Goal:** eliminate manual multi-key Railway setup while retaining strict one-owner/G2 security and existing two Railway services. A successful preparation **does not activate public owner login, Google network, consent, files, or actual finance**.

The owner has already configured the actual Google Cloud OAuth Client ID, registered exact HTTPS callback and an existing private Drive folder in the Railway API variable names, and has copied the original **owner credential recovery** artifacts to two places. Do not ask to repeat those tasks.

The attached Mac-only `backend/app/private_owner_google_keys_prepare_cli.py` performs one attended owner decision:
- Requires a trusted macOS Terminal attached to an authenticated Railway CLI in `personal-cfo-dev-sandbox` / `development` and explicit approval typed on-device. Never send password/TOTP, passphrase or terminal variable output to ChatGPT.
- Reads **privately captured Railway variable listings** for the two known services. Aborts if login/Google runtime is already active, or if the existing client/callback/folder are missing/mismatched.
- Generates six mutually independent 256-bit secrets locally: P1R one-use OAuth state AES-GCM/HMAC, P1M two versioned Google metadata refresh-grant AES-GCM keys + row HMAC, and HMAC-based Drive metadata-index key. Computes the pinned-folder HMAC locally from the existing private Railway folder ID. It also sets the two non-network Google client/callback contract switches.
- Reuses the existing strong matching gateway token if already prepared by P1AM; otherwise generates one independent strong token and installs it in **both** existing Railway frontend/backend services.
- Every secret enters Railway **only on standard input** of `railway variable set <KEY> --stdin --skip-deploys`. Values are never placed in shell argv, stdout/stderr, GitHub, ChatGPT or a new file. No additional Railway services, DB/schema migrations, raw financial data or new provider consent. The staged sealed `P1C_GOOGLE_CLIENT_SECRET` remains unapplied.
- Fails closed before key generation if client/callback/folder or CLI wrong, refuses any already active G2 runtime, and on partial provider writes reports **incomplete** with no release enabled. A partial operation can be rerun only while **all** login and Google ingress/runtime flags remain OFF. Do not rotate real token-custody keys after actual consent: use a separately reviewed rotation process.

Once this source tool has merged, the **one necessary private owner command** from the existing updated `backend` directory/venv is:

```sh
python -m app.private_owner_google_keys_prepare_cli
```

It will request the exact approval phrase displayed on-screen; the only shareable result is its sanitized JSON booleans. Do **not** send screenshots of private Railway variables or keys.

**Important honest boundary:** six newly generated connector keys are not in the previously copied original owner credential snapshot. Loss of Google metadata keys may require fresh consent. Long-term independent key recovery/rotation remains a separately accepted release-hardening task—not an excuse to repeat the old owner backup exercise right now.

Next operator-owned step after private key prep: independent actual Railway TLS/Host/edge request-target/access log/CSRF/cookie/rate audit, restricted Postgres real MFA acceptance and safe rollback, before setting G2 activation flags. The provider's metadata-readonly permission is Google-account-wide; Personal CFO limits operations to the one pinned owner folder by exact verified query. G1/G3 still prohibit original data and real finance mode.
