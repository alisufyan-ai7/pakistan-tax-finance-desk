# M2n — Read-only review of legacy transactions before encrypted migration

**Synthetic only. No monetary migration has been performed.** This milestone removes the temptation to silently backfill the existing M1 bank ledger into the M2m encrypted event journal without accounting controls.

## Behavior

- Authenticated `GET /api/finance/private-events/migration-preview?tax_year=2024` performs a **read-only**, bounded scan of the existing account/transaction schema. It groups results by source evidence state: reviewed and eligible for a *future* explicitly authorized synthetic migration; excluded; unresolved overlap; not reviewed; unsupported owner/currency/category; invalid debit/credit direction; existing exact encrypted mirror; or conflicting encrypted source identity.
- Source identity for a candidate is the stable, synthetic-only `legacy-m1:<transaction UUID>`, HMAC indexed in the protected journal; account ID, date, amount and debit/credit direction would be stored inside the authenticated encrypted event payload when an independently approved migration occurs. This endpoint **does not write any record**.
- Both sides of tax-year boundary July 1/June 30 are evaluated independently. `limit` maximum 500; if more exist, `truncated=true`, `complete_scan=false`. No claim of readiness on truncated coverage or missing records.
- The categorization mapping is an **engineering placeholder**, not a ruling on tax deductibility, final/adjustable withholding, or an FBR return. Source labels `tax_paid` and `refund` map to `other` (no automatic tax credit), and transfers do not count as income. `tax_due_minor=null`, `fbr_ready=false`, `migration_performed=false` always.
- The M2m journal gains an encrypted `direction` attribute (`debit`, `credit`, or `none`) to preserve signed cashflow intent; its absence defaults to `none` to avoid retroactively changing already-created synthetic records. Neither event schema is approved for genuine user financial records.
- Hosted tests must pass on SQLite and ephemeral PostgreSQL 18; verify original ledger summary unchanged when mirrored records exist and user-facing identities never become public indexed fields.

## Remaining before real migration

1. Back up the original synthetic source and key stores, independently verify restore, calculate per-year source counts and checked digest lineage.
2. Produce authenticated sealed records in an explicit, separately permissioned migration process, not by a GET request or during application startup.
3. Verify complete row parity, no double-counting, identical bank receipt/cashflow totals, stable tax-year boundaries, all conflicts resolved and rollback evidence. Do not delete the source until a verified cutover/retention policy is approved.
4. Ensure the final private financial data schema provides adequate encrypted indexing of balances and reconciliation fields. The old financial amounts/dates and bank relationships remain plaintext until such cutover.
5. Keep `APP_DATA_MODE=real` disabled until full private authentication, key management, secure ingestion, offsite backups and statutory tax certification gates.