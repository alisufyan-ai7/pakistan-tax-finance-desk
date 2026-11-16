# G1-c phase 2 — sealed PostgreSQL candidate on verified encrypted restored clone

**Status:** Phase 2 implementation candidate, under review and independent CI. Related [G1-c issue #21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21). **Never execute against real records.**

## Behavior and trust boundaries

- New Alembic `0011_canonical_mirror` creates `canonical_source_mirrors` with only random UUID, independently HMAC-blinded source identity, an entire AES-GCM encrypted row payload and technical insertion time. **No queryable bank dates, amounts, account refs or financial link columns** are introduced to the new table.
- Existing `backend/app/g1c_preflight.py` now inventories **20 registered tables** (the 19 original source tables and the new sealed candidate table), verifies authentic encrypted values and source owner/account/year signed directions. Current PostgreSQL/schema revision checks updated accordingly.
- `create_verified_sealed_candidate(backup_file)` in `backend/app/g1c_candidate.py` is explicit/offline only, guarded by `APP_DATA_MODE=synthetic` and environment-only DSNs. It requires `PG_G1C_SOURCE_DSN` and `PG_SNAPSHOT_SOURCE_DSN` to be identical, both `synthetic_*` source names, plus a **different EMPTY Alembic-upgraded** `synthetic_restore_*` target from `PG_SNAPSHOT_RESTORE_DSN`. Separate AES backup, AES field and HMAC keys are mandatory. **No API or startup path calls it.**
- Strict ordered sequence: (1) source preflight with no anomalies, (2) independent encrypted G1-b full known-table DATA snapshot, (3) source HMAC re-check to reject source changes, (4) independent full-row-verified restore of all 20 tables to a brand-new target, (5) read-only restored HMAC parity with original, (6) **one transactional** source-row copy on the **restored target only**, sealing every row and source identifier, (7) decrypt/verify every copied row against its original source and ensure no missing, extra or duplicate source entries, (8) re-check original source unchanged.
- Includes ALL current registered source tables: accounts, source documents, bank transactions, review/audit/reversals, loans/cash and their linkages, historic filing revisions, protected event/bank source payloads and synthetic auth metadata. Source primary keys are retained inside ciphertext, external equality uses a blind HMAC. No existing legacy finance record is rewritten, classified or deleted. Ambiguous/unreviewed rows remain preserved as recorded, not converted into assumed taxable income.
- Failure injection between mirror rows and independent negative checks verify **candidate transaction rollback**; the original source is never touched. The sealed backup remains for diagnosis. Key/tamper/unknown schema rejects with no approval.
- Return only a redacted receipt: counts, encrypted snapshot digest and keyed source/direction HMAC, not personal/source amounts, dates or references.

## Not yet complete — particularly important

**This is still NOT the authoritative canonical accounting ledger.** It is a **restored candidate mirror**: the target **also contains the legacy plaintext tables** because it must retain a complete restored source for validation. No app read/write switch, old table retirement, key rotation/offsite backup, production recovery plan, bank/FBR real-format ingestion or G2 private MFA deployment has occurred. `APP_DATA_MODE=real` MUST remain prohibited. The new table cannot be used to imply G1 complete.

**Next G1-c phases:** define typed confidential canonical active model and read/write contract, make exact source/candidate account×tax-year and cash/loan/asset/FBR year-end parity acceptance and migration replay audit, then guarded authoritative cutover and safe legacy plaintext removal in a separately recoverable tested environment. Production offsite recovery and key lifecycle remain later gates.

## CI strategy

Existing optimized single-job PR CI includes: 221+ synthetic Python tests, PostgreSQL18 schema/no-drift, operational G1-a confidential bank smoke, G1-b encrypted snapshot/independent restore, G1-c preflight and a new PostgreSQL18 **backup-first restored candidate** acceptance smoke, including mid-copy injected rollback, raw SQL ciphertext inspection, full row parity and source untouched. No additional Docker installation, cloud provider or owner files.

## Explicit setup for previously authorized synthetic PostgreSQL environment only

From `backend/`, with external environment injected and a separately prepared empty migrated target:

- `APP_DATA_MODE=synthetic`
- `PG_G1C_SOURCE_DSN` — source `synthetic_*` database, same full DSN as `PG_SNAPSHOT_SOURCE_DSN`
- `PG_SNAPSHOT_SOURCE_DSN` — exact same source
- `PG_SNAPSHOT_RESTORE_DSN` — distinct independent `synthetic_restore_*` database
- `PG_SNAPSHOT_KEY` — independent 32-byte base64url AES backup key
- `PRIVATE_EVENT_HMAC_KEY` — independent 32-byte base64url source-index/parity HMAC key
- `LEDGER_FIELD_KEYS_JSON` / `LEDGER_FIELD_ACTIVE_KEY` — independent AES field keyring

```python
from app.g1c_candidate import create_verified_sealed_candidate
redacted_receipt = create_verified_sealed_candidate("/secure-synthetic-test-dir/new-backup.tfpg")
assert redacted_receipt["independent_restore_verified"]
assert not redacted_receipt["active_ledger_cutover"]
```

Do not put DSNs, encryption keys or confidential source rows in public GitHub, CI logs or this documentation. Existing [project-only context/resource boundary](PROJECT_CONTEXT_AND_INFRASTRUCTURE_ISOLATION.md) remains binding.
