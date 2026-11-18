# P1AF — One-owner private MFA enrollment and credential-only recovery snapshot

**Date:** 18 November 2026. Scope: the **single** human Personal CFO owner; existing
private `development/personal-cfo-api-preview` only. No public MFA route,
Google consent, new human accounts or real financial-data access.

## Verified prerequisites

The owner independently ran the approved read-only live checks:
- P1AC `result=PASS,stage=complete`: corrected Railway private DNS/TCP and
  restricted PostgreSQL auth.
- P1AA `authenticated_tls_tcp_connection=true`,
  `least_privilege_attestation_passed=true`,
  `owner_security_tables_empty=true`, five distinct runtime 256-bit key domains
  and offline signing *public* key available.
- P1AE `result=PASS,stage=complete`,
  `server_rejects_intentionally_wrong_password=true`, same private TCP path.
- Private Railway SSH reports stdin/stdout `True True` TTY.

The five-key encrypted escrow is on the owner Mac and an independent encrypted
backup was acknowledged. The encrypted private Ed25519 offline signer also
needs an **independent off-server backup** and separately retained passphrase
before any one-shot enrollment. Its public key alone cannot restore the account.
Never send any password, TOTP URI, recovery code, encrypted key file or snapshot
to ChatGPT, GitHub, Railway Variables or email.

## One-shot *private* operator enrollment (only after key/signer backup acceptance)

This step requires separate owner authorization in their authenticated
Railway account and a private attended Terminal session, with all terminal
recording/sharing disabled. The nine default-off review switches are supplied
to the **one command only**, not configured permanently in Railway. These
indicate explicit acceptance of this isolated operational ceremony, **not**
production G2, public login, bank ingestion or Google OAuth approval.

```sh
railway ssh \
  --project 7021b227-f704-43d6-bcff-debdb7255b81 \
  --environment development \
  --service personal-cfo-api-preview \
  -- env \
  P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1 \
  P1N_PRIVATE_OWNER_AUTH_ONLY=1 \
  P1N_G2_OWNER_IDENTITY_REVIEWED=1 \
  P1P_PRIVATE_RECOVERY_ONLY=1 \
  P1P_G2_RECOVERY_REVIEWED=1 \
  P1Q_PRIVATE_OFFLINE_REENROLL_ONLY=1 \
  P1Q_G2_OFFLINE_PROOF_REVIEWED=1 \
  P1W_ATOMIC_OWNER_BOOTSTRAP_ONLY=1 \
  P1W_G2_TERMINAL_CUSTODY_REVIEWED=1 \
  python -m app.private_owner_setup_cli enroll
```

You personally type `ENROLL MY ONE OWNER ACCOUNT`, choose a strong **NEW**
Personal CFO app password (different from restricted Postgres password,
local encrypted escrow passphrase and offline signer passphrase), and type
it twice through `getpass`. The private terminal shows an `otpauth://totp`
URI containing a SECRET. Privately register it in an authenticator app:
if QR import is unavailable, add a time-based 6-digit TOTP account manually
using the URI's `secret=` value; don't paste it into any conversation.
Enter the current six-digit code when asked. Only after TOTP proof passes
does P1W atomically insert one HMAC owner identity, encrypted TOTP and
encrypted/HMAC recovery state and return **exactly eight one-time codes**.
Write them directly to an offline safe place separate from your phone.
Never screenshot, send, paste or publicly display the setup URI/codes.
The CLI refuses to overwrite an existing owner; do not repeat `enroll`.

**Atomic recovery kit is not the same as independently restorable SQL data.**
If the owner DB vanishes, the eight recovery codes alone cannot reconstruct
the HMAC state. The next step must be taken promptly using the new credential
snapshot helper and verified independently. In the meantime do NOT use the
public app or start Google OAuth.

## Credential-only backup: encryption before transmission to Mac

`backend/app/private_owner_credential_snapshot.py` has separate
remote `export`, Mac `capture`, and Mac `verify` modes. Only `capture`
should be run by the owner; it invokes the SSH-only `export` with a fresh
one-use X25519 **public key**. The six whitelisted SQL security tables
are read in a read-only transaction using the existing least-privilege
role and checked to include exactly one owner and recovery record, a recovery
audit record and **zero** session, Google metadata grant and pending OAuth
attempts. This snapshot is only for the initial account setup before Google
OAuth activation. No financial data, role password, raw recovery codes or
encryption/HMAC keys are exported; encrypted credential ciphertext and
password-scrypt verifier **are** included and must be treated as sensitive.

The private API encrypts this data to the one-use public key (X25519+HKDF+
AES-256-GCM) before emitting the tagged ciphertext over authenticated
Railway SSH. The Mac captures it in process memory without terminal display,
decrypts in memory, and immediately writes a second passphrase-encrypted
scrypt+AES-256-GCM file with mode `0600`, never plaintext on disk.

On the owner's Mac (inside `backend` and `.venv`), **after enrollment**:

```sh
git pull --ff-only
python -m app.private_owner_credential_snapshot capture \
  "$HOME/personal-cfo-owner-credentials-2026-11-18.enc"
python -m app.private_owner_credential_snapshot verify \
  "$HOME/personal-cfo-owner-credentials-2026-11-18.enc"
```

The capture command asks for a **new local snapshot passphrase** twice.
The verify command asks for the same passphrase and confirms authenticated
decryption, one-owner recovery records and restricted filesystem permissions.
Both print sanitized booleans only; they NEVER print SQL owner rows or
encryption keys. The file must be independently copied to a physically/offline
separate encrypted storage device and verified by decrypting that copy.
Never overwrite a prior snapshot; issue new files with unique dates after
future credential/recovery state changes. Keep the earlier **five-key escrow**
and separate **offline Ed25519 private signer** backups safe too.

**Limit:** this validates encrypted capture/decryption, not restore to a
disposable database. A source-reviewed, nonproduction restore rehearsal
using exactly the schema receipt and versioned five-key escrow remains
a distinct hard recovery acceptance milestone. Do **not** claim fully
restorable G2 until that succeeds. Full *financial* database backup rollout
may still remain later.

## Unchanged release boundaries

- Only one human account, technical SQL role not another user.
- Two sealed `P1C_GOOGLE_CLIENT_SECRET` Railway changes remain STAGED,
  NEVER Apply Staged Changes or Connect until OAuth callback route safety
  passes TLS/Host/Origin/CSRF/log-redaction checks.
- Real finance originals remain G1/G3 blocked; preview synthetic only.
- The owner credentials are not yet a public login and the mobile PWA's
  synthetic setup screen must not collect real passwords.
