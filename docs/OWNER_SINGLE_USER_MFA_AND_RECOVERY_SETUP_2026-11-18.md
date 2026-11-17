# Personal CFO — single-owner MFA and recovery setup

**Date:** 18 November 2026  
**State:** operational runbook and source-safe executable; live owner enrollment still requires a private attended session. **Never collect the real password/TOTP/recovery codes in chat or public GitHub.**  
**Owner decision:** one human user now; keep the financial database's full disaster-recovery rollout and final exhaustive Railway edge audit as later milestones. This does **not** authorize public OAuth before minimum real ingress safety.

## What is already built

The one human `owner` principal is enforced by `owner_private_identities.singleton_id=1`. There is no team-members, support-admin or invitation workflow. Explicit `private_owner_roles.py` limits session/recovery/Drive metadata/doc review capabilities and refuses financial mutations from the auth role alone. A separate PostgreSQL `personal_cfo_owner_credentials` **technical service role** is not another human user: it grants only SELECT/INSERT/UPDATE on exactly six identity/recovery/OAuth tables. Its non-deployed, initial `NOLOGIN` review plan is `ops/one_owner_credential_role.review.sql`.

The real-compatible backend has encrypted TOTP, scrypt password, 15-minute CSRF-bound sessions, durable lockout, eight one-time recovery codes, account hold, independently signed offline replacement device enrollment and session revocation. The new P1W atomic bootstrap only writes the owner identity and recovery/audit kit together after a genuine authenticator code and privileged operator check. All sensitive values are never written to public GitHub or ordinary web requests.

## Essential recovery minimum, even when full backups are postponed

Before enrolling, retain **independent off-server copies** of (a) the encrypted Ed25519 private recovery signing key and its passphrase, (b) the eight recovery codes stored separately from the authenticator phone, and (c) the independently versioned identity/recovery encryption/HMAC keys. A working backup of current credential DB state is still required for recovery from database loss; without one, recovery codes cannot reconstruct deleted SQL rows. The full **financial ledger backup / disaster restore pipeline** may be scheduled separately, but do not falsely certify recovery from complete credential DB loss without a tested minimal encrypted credential snapshot.

The encrypted offline signer is **not a second application user**. It is your separate lost-phone identity-proof key, stored on another trusted device.

## What you must do on a trusted device at the owner-activation stage

1. On your own trusted computer, check out the approved repo at the verified release commit. Within `backend/`, install the package and the cryptography dependency using your existing Python 3.11+ environment, then generate the off-server recovery signing key:

   ```sh
   python -m pip install -e .
   python -m app.private_owner_setup_cli keygen /absolute/private/path/personal-cfo-recovery.pem
   ```

   The private PEM is encrypted and saved locally with restrictive file permissions. The command prompts for a separate long passphrase and prints **only the public signing key**. Put the public value into private Railway `P1Q_OPERATOR_PUBLIC_KEY`; do **not** upload the private file into Railway/Google/GitHub/this chat. Store two separate encrypted backups of the file and passphrase safely.

2. A verified administrator must first bring the existing private Personal CFO PostgreSQL schema to the accepted Alembic head `0022_private_oauth_attempts` and configure the technical credentials. `ops/one_owner_credential_role.review.sql` is a review-only plan. It deliberately creates `NOLOGIN` until the operator separately sets an interactive password and audits the effective PostgreSQL `PUBLIC` / TEMP / sequence / schema privileges. Do not reuse the financial `DATABASE_URL`. Exact P1S restricted role attestation must pass.
3. In Railway **development**, configure separate, randomly generated 32-byte URL-safe base64 keys `P1N_OWNER_ENCRYPTION_KEY`, `P1N_OWNER_IDENTITY_HMAC_KEY`, `P1N_OWNER_SESSION_HMAC_KEY`, `P1P_OWNER_RECOVERY_ENCRYPTION_KEY`, `P1P_OWNER_RECOVERY_HMAC_KEY`, the separately retained public signing key, and `P1W_OWNER_CREDENTIAL_DATABASE_URL` for the restricted technical role. Keep them outside chat and record their versions/off-server restore plan. Other required reviewed default-off flags are `P1N_PRIVATE_OWNER_AUTH_ONLY`, `P1N_G2_OWNER_IDENTITY_REVIEWED`, `P1P_PRIVATE_RECOVERY_ONLY`, `P1P_G2_RECOVERY_REVIEWED`, `P1Q_PRIVATE_OFFLINE_REENROLL_ONLY`, `P1Q_G2_OFFLINE_PROOF_REVIEWED`, `P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT`, `P1W_ATOMIC_OWNER_BOOTSTRAP_ONLY`, and `P1W_G2_TERMINAL_CUSTODY_REVIEWED`. They must be set only after their actual operator reviews, **not** toggled just to bypass blockers. Keep `APP_DATA_MODE=synthetic` until genuine financial data clearance.
4. When the private runtime and restricted role are independently verified, enter a **private interactive Railway administrative service shell** under your own Railway account. Run `python -m app.private_owner_setup_cli enroll`. The CLI refuses a noninteractive shell, a missing reviewed gate or an unrestricted credential DB role. It prompts for one-owner approval, the password twice and the live authenticator code; it displays the one-time TOTP enrollment URI and eight recovery codes in the attended terminal. Make sure the shell output is not recorded or shared; complete the setup entirely yourself. **No password, seed or code should be given to the assistant.**
5. Verify fresh login after the first TOTP time step; test the one-time recovery-code validity in a controlled accepted environment without using your only real device, verify independent signer availability, and preserve the minimal encrypted state/key recovery evidence. Only then may the owner account be recorded as *enrolled*. Never run the bootstrap a second time.
6. To recover a lost phone, use password + one unused recovery code through the privately administered recovery ceremony. It invalidates all sessions and places the account on hold. Re-enrollment of a different TOTP device requires your separately held Ed25519 authorization bound to the precise recovery-state revision and new device secret, with no active Google grant. This must not turn into a generic public reset URL.

## Frontend and Google consent

The new **Owner setup** mobile PWA page is merged and deployed in PR #143. It shows your personal setup journey and clear status, but deliberately cannot accept credentials in the synthetic public preview. The owner login/session source backend is merged, but the public frontend has no approved private forwarding yet.

The owner's exact Google Cloud HTTPS callback/test user and sealed Railway Google client secret were already configured. The secret remains **staged but unapplied**, and no app Google grant was established. When minimal real exact-route TLS, Host, cookie, Origin, CSRF, authorization-code logging and rate controls are accepted, the existing Google consent page may be opened by you in the browser, using metadata-only scope and exactly one approved folder. The final extensive threat audit may be later, but basic public OAuth protection **cannot** be deferred. Do not apply the sealed client secret or click a public Connect button until the private route is actually secured.

## Verification rules

- Never claim full production, real login or Google connection solely because code CI and Railway preview deployments succeed.
- A staged secret or nondeployed SQL file is not live credential configuration.
- No additional human users or paid providers are created. Future multi-user authorization needs a separate reviewed data model.
- G1 real financial-ledger cutover, G2 runtime identity/ingress and G3 real Pakistani bank/FBR parser acceptance remain separate gates.
