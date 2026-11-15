# M2d-1 — Synthetic ledger text encryption, key rotation & fail-closed migration

**Status:** Implementation milestone (2026-11-15). Code and tests are synthetic-only. This is NOT authorization to upload actual Pakistani bank statements or FBR returns.

## Scope delivered

- Authenticated AES-256-GCM encryption at rest for account display name and institution, transaction description/reference/category, and classification audit old/new category and note.
- Each value has a random 96-bit nonce, an envelope version and a key id (`TFLE1:<id>:...`). Authenticated associated data binds it to a fixed table/column domain.
- Strict keyring configured with `LEDGER_FIELD_KEYS_JSON` and `LEDGER_FIELD_ACTIVE_KEY`; no default key for the application and no silent plaintext fallback. Key material stays outside GitHub. Key rotation can read old and new keys and re-encrypt ciphertext atomically in a maintenance window.
- Explicit database migration `0003_ledger_text` widens encrypted SQL text columns and is non-destructive. The app checks for old plaintext in migrated columns and **refuses to start** rather than silently accepting or rewriting legacy synthetic records. For current synthetic-only data, take encrypted backups if applicable and reimport synthetic fixtures after migration. Never apply this as an unattended real-data migration.
- The SQL query for uncertain duplicate descriptions now compares decrypted candidates in Python, because randomized ciphertext cannot be compared using SQL equality. Account sorting is also performed after decryption.
- Regression tests cover confidentiality of synthetic strings in SQLite, idempotent import, repeated transactions, audited classification, key mismatch/tampering, dry-run and atomic key rotation, and legacy refusal.

## Generate separate local keys

Generate 32 random bytes for each ledger-key identifier, storing outside source/CI artifacts. Example for a local test shell:

```bash
python -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'
```

Set `LEDGER_FIELD_KEYS_JSON` to a JSON mapping, for example `{"local_v1":"<base64url-random-32-bytes>"}` and `LEDGER_FIELD_ACTIVE_KEY=local_v1` in your **local environment only**. The keyring must not be committed. `DOCUMENT_VAULT_KEY` (historical-file encryption) and `BACKUP_KEY` (synthetic encrypted backup archive) remain separate keys. In tests, fixture keys are explicitly synthetic and public by design.

## Key rotation (synthetic-only, service OFF)

1. Create and verify an encrypted backup; verify the restore and that old key remains available.
2. Add new random key `local_v2` alongside old key in `LEDGER_FIELD_KEYS_JSON`, but keep both through the rotation; set `LEDGER_FIELD_ACTIVE_KEY=local_v2`.
3. In the backend directory, run `python -m app.rotate_ledger_keys --db-url sqlite:///./data/finance.db --new-key-id local_v2` for a dry-run count.
4. With no running app, execute the same command with `--apply`. Changes are in one DB transaction; any invalid legacy plaintext or invalid ciphertext aborts without partial key rotation.
5. Verify real backups and post-rotation UI/tests. Only then remove old key from your private secret storage. Do not delete an old key while encrypted backup versions still require it.

## Important limitations

**Do not treat this as complete financial-data encryption.** Transaction dates, amounts, balances, category-derived totals, file/content digests, account IDs, audit timestamps, and metadata remain plaintext. Also, the transaction fingerprint currently uses SHA-256 rather than a secret-keyed lookup digest. Prior synthetic historical filing data is encrypted with a separate vault key. FBR/loan and investment algorithms are not certified. The local development app still has test-only auth modes; owner recovery/rate limiting and private TLS deployment remain unfinished. `APP_DATA_MODE=real` MUST fail closed.

Existing prototype databases containing plaintext synthetic records must be explicitly retired/rebuilt; do not attempt to upload real records into the synthetic importer. Next milestones: (1) more complete sensitive monetary-data protection and dedup keyed indexes, (2) robust loan/cash/transfer reconciliation, (3) authenticated document adapters and secure private deployment + recovery, (4) tax-year-specific verified statutory calculation and legal tax optimization.