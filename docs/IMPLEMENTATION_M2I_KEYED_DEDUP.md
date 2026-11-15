# M2i — Keyed bank import identifiers, not full financial encryption

**Status:** synthetic-only implementation. A separate 32-byte `LEDGER_DEDUP_HMAC_KEY` protects equality indexes for *new* normalized bank documents/transaction fingerprints, using domain-separated HMAC-SHA256. This is **not** encryption of balances, amounts, dates, source row numbers, tax data, account relationships or all metadata.

## Behavior

- Raw file content is never stored by the old importer. Its `documents.sha256` legacy-named field now stores a *keyed* document HMAC, not a publicly reproducible SHA256 hash.
- A transaction's original canonical fingerprint is HMAC-wrapped with the same dedicated key and different domain, maintaining repeat-import idempotence, occurrence numbering, and strong cross-export comparison.
- Separate cryptographic domains prevent using a document digest as a transaction digest.
- Startup and requests reject missing/invalid keys. No compiled-in production key. The synthetic test key in fixtures is **public and must never be used with actual records**.
- `documents.digest_scheme` explicitly tracks `hmac_sha256_v1`; older documents receive `legacy_sha256` in the migration. Startup refuses any legacy documents instead of treating two hash schemes as equivalent. Rebuilding **synthetic fixtures only**, with an explicit backup, is required. No undocumented automatic conversion/destruction of user records.
- Changing the dedicated HMAC key changes all document and transaction IDs; **no online rotation/reindexing implemented**. Maintain a separately encrypted key backup, plan an audited offline rotation, and do not expose genuine records.

## Known privacy gaps / real-data prohibition

Even with keyed identifiers, existing transactional monetary amounts, dates, bank balances, account identifiers, tax years, and relational metadata are plaintext. Encrypted backups do not provide continuous database-at-rest protection. The prototype still has local authentication limitations and no authorized live bank/FBR document support. `APP_DATA_MODE=real` remains fail closed. Real files may **not** be uploaded until a separate private app has authenticated encryption of all sensitive sources, audited key management, MFA, offsite recoverability, parser validation and complete acceptance testing.

## Validation

- Synthetic tampering/changed HMAC key tests; no raw document SHA256 equality.
- Exact reupload and overlapping bank import scenarios continue passing.
- Legacy imported documents yield controlled startup refusal.
- Hosted CI checks all tests plus PostgreSQL 18 Alembic `0007_keyed_import_digests` and schema-drift detection.