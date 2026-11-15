# G1-a — confidential *operational* bank-source foundation (synthetic-only)

**Date:** 2026-11-16. **G1 remains BLOCKED**, this PR is a narrowly scoped first step, not a full secure personal finance application. Follow [G0–G6 acceptance](DELIVERY_GATES_AND_RELEASE_READINESS.md), [owner-approved product plan](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md) and [Issue #21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21).

## Problem and tested implementation

Prior M2m/M2r created a separately encrypted event journal and an encrypted offline archive, **but the active M1 bank/loan/cash database still stores monetary values, posting dates, amounts, balances and relationships in plaintext**. An encrypted *copy* alone is not an operational confidential ledger.

G1-a introduces a separately readable/writable, **active** encrypted source subset:

- `backend/app/confidential_bank.py`: typed `ConfidentialBankInput` and `ConfidentialBankRow` validate fabricated PKR bank source batches. Explicit statement start/end, opening/closing amounts, increasing source row numbers/post dates, exactly one debit or credit and **running-balance parity for each row** are mandatory. Unknown or missing balances and unsupported company/FX data fail closed; do not assume a full month's coverage from a few rows.
- `confidential_bank_batches`: randomized UUID, three **domain-separated keyed HMAC indexes** (owner/account/source) plus a single AES-256-GCM encrypted `payload_json` containing **all** economic fields, dates, bank name, account/source references, descriptions, amounts, individual row references and balances. The payload is decrypted and revalidated before every read. It is not joined to M1 legacy relations.
- `confidential_bank_key_state`: fixed-domain HMAC verifier and an encrypted keyring sentinel; protects against wrong/missing HMAC key being treated as empty account history. The index key MUST be different from bank dedup, event HMAC and all field encryption keys. No automatic key rotation/re-index.
- `backend/migrations/versions/0010_confidential_operational_bank.py`: explicit versioned **SQLite/PostgreSQL 18 schema**, with restrictive non-destructive downgrade, no plaintext finance columns. PostgreSQL app boot checks Alembic revision `0010_confidential_bank`; migration is **schema only**, no live source data is copied.
- `POST /api/finance/confidential-bank/statements`: authenticated synthetic-only atomic insertion. Exact same canonical `source_ref` replay is idempotent; changed content conflicts 409. Source facts persist to the operational DB and can be queried; no data is written to legacy M1 tables.
- `GET /api/finance/confidential-bank/statements?account_ref=...&tax_year=YYYY`: authenticated bounded, source-verified retrieval. A statement spanning July/June appears in both applicable years with **no income/tax/net-worth aggregation, no annual completeness certification and no double counting into the legacy ledger**.
- Synthetic tests check SQLite raw schema/ciphertext, no plaintext sensitive values, replays, conflicts, strict balances/periods, malformed data, missing/reused/rotated keys, tampered source index, lost anchor, auth+real-mode refusal and **encrypted SQLite backup plus independently restored read**. Hosted CI must additionally verify PostgreSQL18 Alembic upgrade and `alembic check`.

## Developer usage and secrets (names only)

Configure *separately* for synthetic local development: `LEDGER_FIELD_KEYS_JSON`, `LEDGER_FIELD_ACTIVE_KEY`, `LEDGER_DEDUP_HMAC_KEY`, `PRIVATE_EVENT_HMAC_KEY` and an independent random 32-byte `CONFIDENTIAL_BANK_HMAC_KEY`. Synthetic-only encrypted local SQLite backup/restore uses separate `BACKUP_KEY`. **Do not use published test fixture key bytes or store actual keys/files in GitHub.**

Existing `APP_DATA_MODE=real` startup prohibition remains in force. The new API requires the same protected local-only app authentication; it is **not** a public/private production host or certified real-bank adapter. Source rows are accepted only when the request contains `synthetic_fixture=true`. All older unprotected M1 APIs remain developer demonstrations.

## What was intentionally NOT completed

- No source-to-v2 migration from legacy bank/loan/cash/asset/filing data, and no cutover. Legacy financial numeric/date/link fields **remain exposed** in the original development DB. No deletion/retirement of original source or canonical no-double-count reconciliation between models.
- No PostgreSQL **data** backup/restore/point-in-time recovery, no offsite storage, key/rotation/reindex audit, availability/restore drill or row-level tenant access review. G1 operational privacy is **partial**, not accepted.
- No immutable original bank PDF vault, real bank/FBR conversion, secure external TLS/MFA runtime or professional security review. G2/G3 still blocked. No verified tax computation or IRIS filing; G4/G5 incomplete.
- This batch model is an atomic protected **source record** (a bounded array), **NOT** a comprehensive ledger transaction graph or a durable ledger for million-row imports. Source row conflicts across different statements are not deduplicated in this new store. A future verified migration and canonical event projection are needed.
- Confidential encrypted payloads have at-rest secrecy, but record counts/timestamps and keyed equality patterns are observable; a compromised API, stolen key or missing backup remains a serious threat. Source deletion is not currently detected by an append-only hash chain. Do not claim threat model completion.

## Next owner-independent G1 development

1. Design/prove an **offline, backup-first PostgreSQL source data migration** from legacy account/document/transaction/loan/cash/asset/FBR tables into fully typed encrypted canonical v2 events and source graph, including full scan, source version, event identity, owner/account/financial-year debit/credit/asset parity and preserved immutable corrections.
2. Run an *independent* encrypted PostgreSQL backup and restore on a new database/branch; test wrong keys, tamper, schema drift, redacted receipts, reversible cutover and no double count. Do not delete the plaintext source until the protected operational read path is independently verified, approved and recoverable.
3. Only after G1 acceptance progress G2 private MFA/isolated owner deployment and G3 genuine bank/FBR adapters, enabling real mode with explicit owner approval. The owner's previously uploaded financial documents remain private **design context only**, not synthetic fixtures or public GitHub content.

## Verification record

[PR #34](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/34) merged to `main` at `2c7bf08f784abc17c544ac13f2d584eabcf2ec3b`. Exact PR-head [GitHub Actions run 43775409962](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43775409962) **SUCCESS**: **205 pytest passed, 2 warnings**; ephemeral **PostgreSQL18** `0010_confidential_bank` migration + `alembic check` no drift **PASS**, and actual protected DB API write/exact replay/read/no-legacy-totals SQL smoke **PASS**. First PR CI attempt had an outdated CI revision assertion (0009), which was corrected before the independently successful re-run. No genuine bank or FBR documents, secrets or source identifiers were used.

**NOT FULL G1:** source M1 tables and non-bank legacy relationships remain plaintext; no real PostgreSQL data migration or independent PostgreSQL backup/restore has been executed. `APP_DATA_MODE=real` remains disabled. G1-b next: encrypted PG backup/restore and a verified migration from legacy graph to encrypted canonical form with no double count and auditable reversible cutover.
