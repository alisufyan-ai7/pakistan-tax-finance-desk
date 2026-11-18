# P1AG — Offline owner credential recovery rehearsal, no Railway writes

**Evidence:** On 18 November 2026 the owner reported a successful **real**
`private_owner_credential_snapshot capture`: `encrypted_snapshot_created=true`,
`one_owner_and_recovery_records_included=true`, `plaintext_database_rows_saved=false`,
`google_grant_included=false`. A separate local `verify` reported
`authenticated_decryption=true` and `encrypted_file_permissions_restricted=true`.
The return values `independent_off_device_copy_verified=false` and
`restore_tested=false` must stay **open** until separately proven.
Snapshot contents, TOTP code and recovery codes must NEVER be uploaded to
ChatGPT, GitHub, a public storage service, or Railway Variables.

## 1. Independent encrypted backup first

On the owner's trusted Mac, locate these **different encrypted artifacts** in Finder
(press Command+Shift+G):

- `~/personal-cfo-owner-credentials-2026-11-18.enc` — encrypted owner-credential snapshot
- `~/personal-cfo-owner-keys.enc` — separate encrypted five-key/HMAC escrow
- `~/personal-cfo-recovery.pem` — separate encrypted Ed25519 offline signing private key (unless the owner intentionally chose another private path)

All three need independently secure off-device copies. Keep the **three
different passphrases** retrievable in a secure password manager, separately
from backup storage, and retain the eight one-time recovery codes
**separate from the authenticator phone**.

Example with the owner's own encrypted removable drive mounted as
`/Volumes/SecureBackup`; replace the name with the REAL already mounted
volume and do NOT run against any guessed path:

```sh
cp -p "$HOME/personal-cfo-owner-credentials-2026-11-18.enc" \
  "/Volumes/SecureBackup/personal-cfo-owner-credentials-2026-11-18.enc"
shasum -a 256 "$HOME/personal-cfo-owner-credentials-2026-11-18.enc" \
  "/Volumes/SecureBackup/personal-cfo-owner-credentials-2026-11-18.enc"
```

The two SHA-256 digests must be exactly equal. This is evidence of an
identical encrypted copy, **not** evidence of decryptability; additionally
run the existing `private_owner_credential_snapshot verify` on the copy.
The snapshot verifier requires the backup file mode `0600` and the same
private passphrase. If the off-device medium does not support Unix mode
0600, use a separately encrypted filesystem/archive with controlled
permissions; do not weaken the file-permission check. Retain the original.
Never paste hashes if you are unsure they may uniquely identify a private
file; a simple VERIFIED/NOT VERIFIED acknowledgement is sufficient.

## 2. Trusted Mac-only ephemeral PostgreSQL 18 restore drill

After the independently encrypted copy is verified, check Docker Desktop
is installed, started and trusted. The restore drill **must run locally on
the owner's Mac** and not on Railway, CI using real data, a shared terminal,
remote Docker context, or an untrusted computer. Confirm Docker is targeting
the owner's local Docker Desktop engine (e.g., inspect `docker context show`
and `docker info` privately) before proceeding.

From the existing local repo's `backend` folder with the private virtualenv:

```sh
git pull --ff-only
source .venv/bin/activate
python -m app.private_owner_restore_drill \
  "$HOME/personal-cfo-owner-credentials-2026-11-18.enc" \
  "$HOME/personal-cfo-owner-keys.enc"
```

The tool privately prompts for the **credential snapshot** passphrase and
then the separate **five-key escrow** passphrase. Neither is placed in
command arguments or stdout. It first authenticates the snapshot's local
AES-256-GCM file, then verifies owner row HMAC and encrypted TOTP against
the five separately escrowed keys, the recovery state ciphertext, its
authenticated audit chain, and presence of eight **hashed** (never plaintext)
recovery codes.

Then the tool creates a **one-use `postgres:18` Docker container** with
`--network none`, no published ports, and an isolated RAM-backed tmpfs
for the database files. It recreates the reviewed seven-table owner-only
schema and receipt, replays the initial three actual owner/recovery/audit
records through stdin (never process arguments or files), and validates
row counts and schema revision/signature. The raw SQL and Docker stderr
are NEVER printed; Docker container is forcibly removed at the end.
This is the **isolated owner credential** database, not the finance ledger.
No connection or mutation to Railway occurs.

The returned JSON reports only sanitized checks such as
`snapshot_owner_row_hmac_verified`,
`encrypted_totp_decryption_verified`,
`recovery_ciphertext_and_audit_verified`,
`disposable_postgresql18_schema_recreated`,
`six_owner_security_tables_restored_and_verified`,
and `disposable_container_removed`. It will still say
`independent_off_device_backup_verified=false`, because a local
application cannot attest actual physical/off-device backup, and
`offline_ed25519_private_signer_backup_verified=false`: those
are independently verified by the human owner.

**Important limitation:** This is an isolated initial owner
credential-state PostgreSQL restore and crypto verification. It is not a
full financial database disaster restore, not a full device-loss recovery
ceremony with a signed Ed25519 proof and one-time recovery code redemption,
and not a reason to activate public login or Google Drive consent.
After any future owner password, TOTP or recovery-code change, capture and
independently back up a **new versioned snapshot**; the initial-only
P1AF capture refuses evolved or Google-authorized state.

## 3. G2 and OAuth remain gated

Only one human owner identity. A successful offline local drill does not
turn on public login. The two staged `P1C_GOOGLE_CLIENT_SECRET`
Railway fields remain unapplied; do not press Apply Staged Changes,
start Google consent, ingest finance originals or set G1/G2/G3 true
from backup tests alone. The future public OAuth callback still needs its
exact-route safety acceptance.

Reference: `backend/app/private_owner_restore_drill.py` and
`backend/tests/test_private_owner_restore_drill.py`. All synthetic CI
tests use fabricated identities/keys, never real user snapshots.
