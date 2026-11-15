# G1-b — encrypted, independently verified PostgreSQL data recovery (synthetic-only)

**Date:** 2026-11-16. **Engineering status:** proposal until exact PR-head CI is verified. **Source of truth:** [Issue #21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21), [release gates](DELIVERY_GATES_AND_RELEASE_READINESS.md), [G1-a](IMPLEMENTATION_G1A_CONFIDENTIAL_BANK_SOURCE.md) and [accountant-ready product scope](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md).

## Why

G1-a added a genuinely readable/writable protected bank-source path, but active legacy finance data stays plaintext. Real owner onboarding needs **independently tested recoverability** before attempting a multi-table encryption migration or changing which ledger is authoritative. The earlier synthetic backup program protects SQLite only. G1-b introduces a bounded **PostgreSQL 18 data snapshot + independent restore** to test that prerequisite using no real data.

## New code and safety contract

- `backend/app/pg_recovery.py`: **explicit offline functions** `create_pg_snapshot(output_file)` and `restore_pg_snapshot(file, inject_failure_after_tables=None)`. They are **not API routes**, not automatic startup hooks, and not a real-data backup service.
- Source and target are supplied through *external environment* `PG_SNAPSHOT_SOURCE_DSN` and `PG_SNAPSHOT_RESTORE_DSN` and **must** be named `synthetic_...` and `synthetic_restore_...` respectively. The target cannot have the source database name. `APP_DATA_MODE=real` is rejected.
- Backup requires distinct external random 32-byte `PG_SNAPSHOT_KEY`; fail if reused from active ledger field encryption. No credentials or key bytes are placed in GitHub, backup receipts or command line. CI uses deliberately public fictional credentials.
- Read-only **REPEATABLE READ** PostgreSQL transaction enumerates *every* recognized SQLAlchemy application table, validates exact expected table set + Alembic revision `0010_confidential_bank`, exports each table in deterministic primary-key order (CSV) with bounded in-memory size and row counts/digests. Unknown/missing tables, incomplete source, oversized data or drift **fail closed**.
- A single AES-256-GCM authenticated envelope stores source DB identity, schema revision, every table's CSV **inside ciphertext**, SHA256 digest and row count. The output is an exclusive-new mode 0600 file; no plaintext dump is created on disk. Row data is necessarily momentarily present in application memory; this is not hardware-backed encryption or memory zeroization.
- A restore can operate **only** against an existing **independent, empty and already Alembic-migrated** synthetic PostgreSQL target. It verifies every expected table is empty, blocks conflicting concurrent access while copying in FK dependency order, and checks full exported bytes/digest + counts *inside a single SQL transaction* before commit. A wrong key, altered backup, unknown table, truncated import, explicit failure injection or mismatched parity aborts without a partial committed restore.
- A separate CI PostgreSQL 18 service creates independent synthetic restore databases and tests successful equality, wrong key, deliberate mid-restore rollback, backup ciphertext/no plaintext, refusal to overwrite restored records and source data preservation. Regular pytest validates fail-closed key/manifest/DSN boundaries.

## Operational semantics and exact limits

This utility is a **small, fully inventoried synthetic snapshot** program. It is deliberately limited (24 MiB decrypted data, 26 MiB encrypted backup, a fixed known Alembic revision) and supports no live, real-data workloads. Database **schema is not stored** in backup: destination must have separately installed and verified Alembic `0010_confidential_bank`. It is not off-site, scheduled, continuous WAL backup/PITR, replica recovery or tested regional disaster recovery. **No full arbitrary PostgreSQL dump is claimed**; only registered application table data is covered. PostgreSQL roles/grants, extensions, object storage and infrastructure configuration are outside this format. A source DB containing unfamiliar tables is rejected (not silently dropped).

**Critical ongoing G1 limitation:** The older active M1 bank/loan/cash tables contain **plaintext** money/dates/links; this encrypted backup protects the *backup artifact*, not those original SQL values or the materialized restored DB. The new encrypted bank-source G1-a table is still separate from historical ledger. **G1 remains BLOCKED** until all active financial data has been migrated into an encrypted canonical model with independent parity, rollback and safe plaintext retirement. G2 private MFA/recovery/deployment, G3 authentic source intake, G4 FBR/wealth legal correctness and G5 owner UI also remain incomplete. `APP_DATA_MODE=real` stays disabled.

## Tests and failure cases

- Valid synthetic fixture: compare per-table exact primary-key-ordered CSV source/target, table count and digest after independent restoration; source DB remains untouched.
- Failure injection after first table: restoration transaction rolls back; target remains empty; original file and source unchanged.
- Wrong key / altered encrypted file: reject before querying/modifying destination.
- Source schema revision drift or unknown/missing application tables: refuse snapshot; restore refuses non-empty target or source-target equality.
- 0600 encryption output; no plaintext account/statement identifiers in file bytes. Fixed key IDs/secret values are never committed.
- Regular tests protect real-mode refusal, key independence, malformed manifests and unsafe synthetic database names.

## Next G1 engineering step

Full **legacy PostgreSQL DATA MIGRATION** is a *different* milestone: from active M1 original financial accounts/documents/transactions/loans/cash/assets/FBR into normalized, encrypted canonical economic events and source/evidence graph; preserve all original source IDs, amendments and audit history. Require backup-first, backed-up independent restore, per-account/financial-year income/outflows and loan/cash/asset parity, corrupt/partial migration failure injection, no-double-count; then a reversible app-read switch and controlled plaintext retirement only after approval. Do **not** automatically migrate or delete a real source. Continue owner-independent synthetic implementations without asking the owner for historic FBR returns or additional credentials.

## Verification record

Before CI: **pending exact-head hosted pytest, PostgreSQL18 schema and data-backup/independent-restore test.** Do not claim this tool implements full G1 or supports real finance until separate acceptance is proven.
