# M2r — encrypted-only synthetic archival projection

**Status:** Implementation intended for PR validation; update this line only after CI and merge. **Do not confuse with production security or a live DB cutover.** This milestone reduces the risk of mistakenly using an older candidate database with plaintext financial columns as a supposedly encrypted database.

## Why this is necessary

The current M2m encrypted event journal covers only specific events and M2o produces an independently restored candidate, but **both its source and candidate still contain legacy plaintext amount/date/balance/linkage fields** in `transactions`, `documents`, loans, cash, and historical filing data. That violates the real-data acceptance gate.

M2r introduces a distinct **offline archive artifact**, not the active ledger: every recognized application table's records, schema and relationship identifiers are sealed into one AES-256-GCM encrypted-only SQLite archive. Its only tables are `sealed_manifest` and `sealed_records`. There are **no legacy money/date/account identifier columns** in the archive. Each row is protected by table/index-bound authenticated encryption; the row identity is a separate keyed HMAC blind index. An encrypted manifest contains schema DDL, column names, counts and a keyed whole-source HMAC. Table names and row counts are still observable side channels. All original economic values, legacy ciphertext and schema details remain inside the encrypted envelopes.

## Explicit workflow and restrictions

1. Input is a local, **synthetic-only** SQLite database migrated to the current schema, plus an optional synthetic evidence directory. No `APP_DATA_MODE=real` accepted.
2. Provide **distinct external 32-byte keys** for `CONFIDENTIAL_ARCHIVE_KEY`, `CONFIDENTIAL_ARCHIVE_INDEX_KEY`, `BACKUP_KEY`, `PRIVATE_EVENT_HMAC_KEY`, `LEDGER_DEDUP_HMAC_KEY` and every `LEDGER_FIELD_KEYS_JSON` key. Keys must not be pushed to GitHub or reused.
3. Run an explicitly invoked offline CLI. No startup job, live endpoint, change to the source, or deployment is provided.
4. Inspect the database's **entire recognized schema and all rows**; fail closed on missing/unknown tables, missing primary keys, oversized sources or SQLite integrity errors. This is a bounded local engineering tool, not a large dataset export service.
5. Create a new encrypted source/evidence backup, then restore it independently in a 0700 temporary directory. Recheck row-by-row source parity before writing anything to the sealed artifact.
6. Serialize all SQLite column values with precise type tagging, encrypt row payloads with independent AES-GCM nonces and per-row AAD and store only HMAC-keyed record IDs. Persist a separately sealed manifest; never overwrite existing archives.
7. Verify every ciphertext and HMAC, reconstruct the source schema **in memory** for row and FK checks, validate total row/content parity and check archive SQLite integrity. Publish an encrypted-only `0600` file and optional redacted `0600` receipt. No plaintext reconstruction is placed on disk by the archive verification.
8. On failure, retain the original and encrypted backup; remove any newly created candidate artifact. The owner must intentionally approve any later authoritative cutover; there is none in this implementation.

Example (synthetic file names, *no real financial records*):

```bash
cd backend
python -m app.secure_archive \
  --sqlite-db ./data/synthetic-finance.db \
  --evidence-dir ./data/synthetic-evidence \
  --encrypted-backup ./private-work/synthetic-recovery.tfbk \
  --sealed-archive ./private-work/synthetic-sealed.db \
  --receipt ./private-work/synthetic-sealed-receipt.json
```

**Do not run this on production, real statements or genuine previous tax returns.** The existing encrypted source backup remains a separate recovery mechanism; the sealed-only archive is **not** a drop-in replacement for the operational PostgreSQL schema or an FBR-certified ledger.

## Validation expectations

- Successful archive contains no `accounts`, `transactions`, `cash_holdings`, `loan_accounts`, `historical_filings` or other plaintext SQL finance tables.
- Verify all recognized financial and auth/source tables, original SQLite integrity, independent restore, typed row/foreign-key parity and row-count completeness.
- Prove that raw dates, PKR amounts, account identifiers, descriptions, cash declarations and owner secrets cannot be extracted as plaintext from the new sealed file.
- Reject changed/wrong/reused keys, tampered ciphertext, deleted rows, unknown tables, overwrite attempts, injected failures, and `APP_DATA_MODE=real`.
- Production-readiness test remains **FAIL**. Legacy source contains plaintext money/date/metadata, no secure PostgreSQL data migration or authoritative read model exists, no independent key-rotation/enterprise recovery, no private real-document ingestion, no FBR mixed-income certification.

## Next owner-independent priority after this PR

Extend the canonical encrypted read model to represent **complete** bank/document/loan/cash/asset relations with accessible indexed projections; build a parity-checked PostgreSQL data migrator and cutover/reversal plan. Then privacy-controlled original PDFs and FBR/real bank adapters, private MFA/recovery/deployment and genuine 2023+ legal tax computations and reconciliation. Preserve first-owner MVP simplicity and the modular personal CFO direction from `docs/PROJECT_DECISIONS_AND_SCOPE.md`.