# M2m — Encrypted synthetic financial events (privacy-forward ledger foundation)

**Scope: owner-independent, synthetic-only engineering.** This does not authorize genuine personal financial uploads, tax-return processing, or production deployment. The GitHub repository is temporarily public by owner choice; it must contain only synthetic fixtures and engineering documentation.

## Motivation

The preexisting M1–M2l bank ledger retains plaintext dates, amounts, balances, account/document relationships and other economic metadata, even after M2i switched document and transaction fingerprints to HMAC. Keyed identifiers are **not** encryption. Historical financial data must never enter this legacy schema until an explicitly reviewed redesign/backfill, backup and private-app security acceptance.

## Implemented synthetic v2 event journal

- New append-only `private_financial_events` table. The only plaintext fields are a random event UUID, HMAC-derived equality indexes (`owner_hmac`, `year_hmac`, `source_hmac`), and ingestion timestamp. Sensitive event type, original posting date, amount in paisa, source ID, account reference, counterparty and evidence notes are **inside authenticated AES-256-GCM encrypted JSON** using the external versioned `LEDGER_FIELD_KEYS_JSON` keyring.
- Independent `PRIVATE_EVENT_HMAC_KEY` key (32 random bytes, base64/base64url) is used with purpose-separated HMAC-SHA256 labels for owner, fiscal year, and immutable source identity. This is distinct from both the ledger-field AES key and `LEDGER_DEDUP_HMAC_KEY`.
- A source identity can be replayed idempotently **only if the entire validated event is identical**; conflicting same-source input is rejected. Identical value/date entries with different stable source references are distinct events. No silent aggregation or false deduplication.
- Synthetic-only `POST /api/finance/private-events` and `GET /api/finance/private-events?tax_year=2024`. Only PKR individual ownership and explicitly marked synthetic records; no account credentials, external files, user returns, or bank provider connections. The source reference and all financial fields remain encrypted at rest.
- Fiscal tax years use July 1 to June 30. Historical TY2023 onward; no live FBR deductions, tax calculations, opening/closing wealth assertions or verified withholding. All tax due values remain `null`.
- PostgreSQL 18/Alembic revision `0009_private_events`, no destructive downgrade. Tests cover encrypted storage, source uniqueness, fiscal boundary, incomplete data, key absence and unchanged legacy calculations.

## Precise limitations

1. **Old financial tables remain as-is.** This is a separate protected-schema foundation, not a completed migration of M1–M2l, and does not make existing financial balances/private records secure.
2. The new table still leaks row count and ingestion timestamps, plus equality relationships through blind indexes. The HMAC key is essential; changing it requires a controlled, backed-up offline reindex of source, owner and year identifiers. An absent/malformed key must fail closed.
3. Encryption uses the existing authenticated ledger-field keyring. Real key rotation requires secure key management, backup snapshots and dual-key read until rotation is verified; synthetic key rotation can be tested but does not constitute production readiness.
4. The current app remains localhost-only with development authentication. Multiworker rate limiting, MFA recovery, key management, encrypted offsite backup/restore and independent security assessment are pending.
5. Event journal records are **not** used to update existing asset/loan/cash/tax screens automatically; their source ownership, account linkage, reconciliation, and auditable corrections require later integration. Data may not be counted twice across the two stores.
6. No real financial data, previous tax returns, or customer documents may be committed to public GitHub, CI, or uploaded into this synthetic-only API. `APP_DATA_MODE=real` stays disabled.

## Next owner-independent steps

1. Build a controlled synthetic-only two-ledger migration/reconciliation tool: decrypt existing rows with verified keys, write new encrypted payloads, record source lineage, run delta/equality checks, and verify rollback snapshots. **Never silently drop original data.**
2. Define blind-index query strategy for year/account/owner, daily balances and full statements without exposing date or amount distributions; distinguish duplicate-reference keys from occurrences.
3. Independently test PostgreSQL transaction atomicity, concurrency and backup/restore, plus encrypted document storage and isolated PDF extraction.
4. Only after real-data security prerequisites are met, review owner-supplied tax-year returns and authentic bank layouts through a secured private ingestion path.