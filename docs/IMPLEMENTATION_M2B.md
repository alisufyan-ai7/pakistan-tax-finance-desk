# M2b — Synthetic Security and Database Foundations (2026-11-15)

**Status: implemented, synthetic-only.** This is not an FBR tax engine, an IRIS filing implementation, or production-ready personal financial-data storage. The repository is temporarily PUBLIC at the owner's explicit direction; **commit only source, docs and synthetic fixtures**. This milestone has no dependency on the owner's filed returns or statements.

## Code delivered

1. **Reproducible Alembic schema baseline** (`backend/migrations/versions/0001_initial_synthetic_ledger.py`, `alembic.ini`, `migrations/env.py`). Creates five financial-domain tables from a fixed explicit migration, with indexes, constraints and a revision ID. For PostgreSQL runtime, migrations must exist at precisely the expected version; app no longer auto-creates PostgreSQL tables. Synthetic SQLite local demo still auto-creates its schema to preserve earlier tests. Destructive Alembic downgrade is disabled. Existing pre-migration SQLite demo data is not automatically upgraded; recreate from synthetic fixtures or carefully handle separately.
2. **Encrypted structured synthetic filing fields** (`app/field_crypto.py`). `HistoricalFiling.fields_json` contains authenticated ciphertext rather than human-readable numerical filing fields for new M2b records. Uses the same 32-byte vault key but **separate authenticated associated-data namespace** bound to document ID, TY and type; incorrect key, tampering or wrong context fails closed. Previously stored plaintext *synthetic* rows must be discarded/re-ingested; there is no unsafe plaintext fallback. **Other M1 financial fields and audit notes remain unencrypted in SQLite**—never use with real personal data.
3. **Encrypted synthetic-only backup and verified restore** (`app/synthetic_backup.py`): SQLite's `backup()` snapshot, encrypted AES-256-GCM archive of SQLite + encrypted evidence vault files, SHA-256 manifest, strict bounded file count/sizes, refusal of symlinks and unexpected paths, restore to a **new empty directory only** and SQLite `PRAGMA integrity_check`. No cloud backup, rotation, scheduling or disaster-recovery certification yet. Do not reuse `DOCUMENT_VAULT_KEY` as `BACKUP_KEY`.
4. **Two strict synthetic bank-like CSV profiles** (`app/bank_profiles.py`): `synthetic_split` (withdrawals/deposits) and `synthetic_direction` (DR/CR); visible in local UI. Both map to the canonical parser and must pass the same exact minor-unit arithmetic, posting-date order, duplicate detection, provenance and running-balance checks. These are **NOT certified HBL/Meezan/any actual bank formats**. Explicit fixture layouts under `samples/m2b/` contain no financial identifiers or user data.
5. **Real-mode startup denial**: `APP_DATA_MODE=real` refuses initialization, so this prototype cannot accidentally be relabeled as secure for personal use.
6. **CI coverage**: backend synthetic pytest suite plus PostgreSQL 18 ephemeral service migration upgrade/check and application schema preflight. No credentials for genuine systems; CI password is a deliberately fake test string.

## Local repeatable checks

```bash
cd backend
python -m pip install -e '.[dev]'
pytest -q
python -m compileall -q app
# Versioned migration on a NEW disposable database, not an existing personal DB:
python -m alembic -x db_url=sqlite:////tmp/taxfin-synthetic-m2b.db upgrade head
python -m alembic -x db_url=sqlite:////tmp/taxfin-synthetic-m2b.db check
```

For a PostgreSQL *synthetic disposable* database, first install `.[dev,postgres]`, set a synthetic `DATABASE_URL=postgresql+psycopg://...`, and run `python -m alembic upgrade head`. **Never use a personal/production database for smoke testing.** CI independently creates ephemeral PostgreSQL 18 and runs migrations.

### Local synthetic encrypted backup example

```bash
# Generate two separate 32-byte keys locally and export them as DOCUMENT_VAULT_KEY and BACKUP_KEY.
# Keep them outside Git, terminal history, CI output and application logs.
python -m app.synthetic_backup create --db ./data/finance.db --evidence-dir ./data/evidence --output ./backups/synthetic-001.tfbk
python -m app.synthetic_backup restore --backup ./backups/synthetic-001.tfbk --target ./data/synthetic-restored-001
```

Restore deliberately refuses pre-existing targets. All source and restored content is **synthetic only**. Tests check file mode, wrong-key and ciphertext tampering, no-overwrite behavior, unsafe filenames, mandatory mode guard and an actual SQL query against the recovered database.

## Acceptance / verification

- Existing M1 + M2a tests remain passing.
- M2b tests cover fresh Alembic SQLite baseline and re-run, real-mode startup refusal, both synthetic profiles, unknown/wrong profile rejection, authenticated structured field encryption, encrypted backup/restore with SQLite query, wrong key, tampering and symlink/unexpected-file defenses.
- PostgreSQL 18 schema/`alembic check` must pass in **real hosted Actions** before merge. Do not claim PostgreSQL compatibility solely from SQLite migration tests.
- No real FBR amounts, bank statements, taxpayer IDs or filings are introduced.

## Remaining M2c prerequisites for real documents

- Strong owner authentication with **MFA** and protected browser sessions, TLS/CSRF/session rate-limits; basic local HTTP authentication is NOT sufficient.
- PostgreSQL/production key lifecycle, encrypted *all* sensitive structured transaction text/notes and private document storage; safe handling of old database representations.
- Key rotation and encrypted **off-site** backup scheduling, controlled disaster restore evidence; test concurrency, database roles and least privilege.
- Real Pakistani bank and FBR PDF/Excel format adapters validated against carefully redacted or securely supplied source layouts. Restrict PDF/office parsers and extract only data with provenance.
- Original records and adjustment audit; transfers, loan principal vs interest, donations, investments, wealth reconciliation and trustworthy year-specific FBR rules.
- Private application environment separate from temporarily public code repo; no real financial data in GitHub, logs, CI or chat-generated fixtures.

## Handoff

Read `AGENT_START_HERE.md` and `docs/CURRENT_HANDOFF.md` first. Next coding task can proceed immediately **without owner data**: MFA/session infrastructure, encrypted structured ledger fields, PostgreSQL integration tests, and synthetic Pakistani-document adapter tests. Request no passwords, returns, bank statements, subscriptions or deployment approvals until owner action is truly necessary. Preserve conservative `tax_due=null` while statutory rules remain unverified.
