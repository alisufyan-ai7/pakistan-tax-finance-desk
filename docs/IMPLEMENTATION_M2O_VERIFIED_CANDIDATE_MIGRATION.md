# M2o — Verified, backup-first migration of synthetic bank events

**Status:** Development implementation, synthetic-only. No live migration or production deployment is authorized.

## Goal and safety boundary

The M1 bank ledger still has **readable monetary amounts, dates, running balances and account relationships** in its original SQL tables. M2m added a separate authenticated-encrypted event journal, and M2n added a no-write migration preflight. M2o constructs a **verified candidate copy**, backed by an independently restorable encrypted snapshot, without modifying the source database or switching application reports to the new journal.

This is a safe *migration rehearsal* and input-validation path, **not** the final plaintext-removal cutover. The restored candidate intentionally retains the legacy tables, so it must not be treated as encrypted-at-rest compliant, and real financial-data mode remains blocked.

## Execution prerequisites

1. Use synthetic SQLite database files only; shut down active writers. PostgreSQL migration still requires a dedicated backup and coordination strategy, and this CLI intentionally does not accept a PostgreSQL URL.
2. Configure externally supplied, distinct 32-byte secrets: `LEDGER_FIELD_KEYS_JSON`, `LEDGER_FIELD_ACTIVE_KEY`, `PRIVATE_EVENT_HMAC_KEY`, `LEDGER_DEDUP_HMAC_KEY`, `BACKUP_KEY`. No secrets may enter GitHub, CI logs or audit receipts. Sample test keys are fake and must never be used for real data.
3. All existing bank source rows must be individually included, reviewed, categorized, free of unresolved overlapping imports, have individual PKR ownership, a valid signed debit or credit and a supported source date. A scan of more than 20,000 source rows fails rather than silently truncating.
4. Specify a **new** encrypted-backup path, a **new** restored-candidate directory and a **new** audit-receipt path. The source database and evidence vault must remain available and untouched.

Example, in an isolated offline test environment with synthetic keys already configured:

```sh
cd backend
python -m app.synthetic_migration \
  --sqlite-db ./data/finance.db \
  --evidence-dir ./data/evidence \
  --encrypted-backup ./data/migration-recovery.tfbk \
  --candidate-dir ./data/migration-candidate \
  --receipt ./data/migration-audit.json
```

**Never execute this against actual personal financial data or a running production database.** It has no `--promote` or `--delete-original` action.

## Migration sequence

1. Reject real-data mode, unsafe source paths, reused crypto/HMAC/backup secrets, or existing output paths.
2. Fully inventory, classify and HMAC-sign the eligible source (no unreviewed, excluded, unresolved or unsupported rows). This happens **before** a backup is written.
3. Use SQLite's consistent snapshot API to create an encrypted AES-256-GCM backup containing SQLite and any registered encrypted synthetic evidence blobs.
4. **Independently restore** the encrypted backup to a new directory, verifying the archive manifest/file hashes, SQLite integrity and a complete source-inventory HMAC match before any migration writes.
5. Within a **single transaction on the restored candidate only**, materialize each reviewed bank row into the encrypted M2m journal using a stable `legacy-m1:<UUID>` source reference, its direction and a domain-separated HMAC source index. Reject competing same-source content, foreign/orphaned mirrors and mismatched HMAC indexes. Keep old source rows unmodified.
6. Validate total event count and per-(tax-year, account) debit and credit sums against decrypted journal contents. Receipt publishes only a keyed aggregate digest, not actual amounts, dates, account IDs or counterparty names.
7. Commit, independently re-read ciphertext, rerun parity and `PRAGMA integrity_check`, verify the original source fingerprint remains unchanged, then write a mode-`0600` redacted audit receipt if requested.
8. On failure, automatically delete **only** the freshly created restored candidate. The encrypted backup and untouched source remain for rollback and investigation. An injected mid-batch failure is covered by regression tests.

## What this milestone intentionally does **not** do

- Does not overwrite, purge, rotate or rewrite the original M1 bank tables. Source SQL amounts, dates, balances and relationship metadata are **still plaintext**.
- Does not migrate loan contractual details, cash movements, nonbank asset snapshots, historic FBR filing records or actual bank documents.
- Does not propagate bank running balances into the M2m event schema. The bank source remains available for original balance verification; more detailed encrypted source provenance is future work.
- Does not switch tax, wealth, cash or income calculations to v2 or double-count mirror events. `tax_due_minor` remains `null` and no FBR filing or legal deduction is certified.
- Does not implement PostgreSQL *data-copy* migration, cross-service backups, multiworker locks, production secrets, MFA recovery or private hosting acceptance. CI runs a separate ephemeral PostgreSQL schema migration check, not the SQLite candidate-copy tool on Postgres.
- Does not permit personal documents in the temporarily public GitHub repository or synthetic-only application. `APP_DATA_MODE=real` remains fail closed.

## Verification and follow-up

`backend/tests/test_synthetic_migration.py` covers two tax years, encrypted payload and redacted receipt, byte-preserved source ledger, persisted candidate parity, existing mirror replay, conflict and unreviewed rejection, distinct key enforcement, failure injection with rollback, backup recovery and real-data refusal. GitHub Actions must pass the full regression suite and ephemeral PostgreSQL18 Alembic schema check before merge.

**Next owner-independent gate:** build an explicit, audited and tested conversion of the remaining bank/loan/cash plaintext schema with a production-approved read model, source completeness and switch-over/rollback. Then build isolated real-document converters, secure private deployment, MFA recovery, external encrypted backups and verified FBR multi-income tax-year rules. Owner's historic returns are **not a dependency for synthetic engineering**, only later secure input/acceptance.