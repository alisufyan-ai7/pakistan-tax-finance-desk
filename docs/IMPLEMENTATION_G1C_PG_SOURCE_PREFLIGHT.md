# G1-c phase 1 — safe PostgreSQL legacy source census (synthetic only)

**Status:** implemented on a review branch; do not treat this document as proof of CI or G1 completion. See [Issue #21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21). **Effective 2026-11-16.**

## Objective

Inventory the entire *current* source relational graph **before any encrypted canonical migration**, preserving every row, original ID, status and source relationship. Detect unknown tables/columns, incomplete scans, broken parent links, transaction direction and declared statement-period mismatches, transfer/cash/loan inconsistencies, still-active reversed records, incompatible ownership/currencies and filing revisions. Produce **redacted keyed receipts**, no raw account IDs, dates, monetary aggregates or financial values.

This is a deliberately conservative *first slice*, not the encryption migration itself, no candidate creation or authority cutover. Existing legacy finance SQL is still plaintext. No real owner data, production PostgreSQL DB, cloud provider or other repository was used.

## Implementation

- `backend/app/g1c_preflight.py`: explicitly invoked `preflight_postgres_source()` reads environment-only `PG_G1C_SOURCE_DSN` for a PostgreSQL database named `synthetic_*`. It rejects `APP_DATA_MODE=real`. PostgreSQL uses **REPEATABLE READ, READ ONLY**; no INSERT/UPDATE/DELETE/DDL, no API/startup hook, no automatic migration or copy.
- Strict reviewable `SOURCE_COLUMNS` lists **every known mapped column in all 19 financial/evidence/auth/sealed tables**; cross-check both the registered ORM and exact `public` SQL columns, plus expected Alembic `0010_confidential_bank` revision. Any schema drift blocks the census. Hard limits: **20,000 total rows / 24 MiB canonical in-memory scan**; excess is a failed scan, never silently truncated.
- Verify each existing EncryptedText token's AES-GCM authentication, rejecting plaintext and mismatched keys; check ORM-declared foreign keys against complete table data. Check selected economic link invariants; preserve (and count) unreviewed/ambiguous rows rather than pretend to classify them. No tax classifications/figures are inferred.
- Response includes a schema revision, total and per-table counts, generic issue codes+counts, review-needed count, account/legal-owner/tax-year direction parity **HMAC** and all-table source integrity **HMAC** using an independently supplied `PRIVATE_EVENT_HMAC_KEY` with new G1-c domain separators. No unkeyed economic hashes or unredacted source rows. Using a known, fabricated key in public CI is only for synthetic tests.
- `backend/tests/test_g1c_preflight.py` exercises strict manifest, keyed redaction, source row change detection, broken refs, invalid money direction, source period, ownership restrictions, overflow and authentic AES-GCM field verification.
- Existing PostgreSQL 18 CI job exercises an **actual PG18 read-only G1-c census** after inserting fabricated account/document/transaction rows; verifies the old plaintext data is unchanged and that no account reference, date, amount or narrative appears in the receipt.

## Action boundaries and remaining G1-c work

1. This preflight **does not take, verify or restore a backup**, and returns `backup_verified=false`, `migration_performed=false`, `cutover_authorized=false`, `actual_private_canonical_ledger_ready=false`. An error-free inventory is **not** permission to copy or destroy original data.
2. Current graph checks are a **partial set of economic invariants**, not comprehensive wealth/account balance parity. A future release must include full immutable source detail and audit provenance in the protected canonical graph, with explicit migration code and complete covered field mapping. Additional tables/columns must be reviewed, not accepted automatically.
3. The next coding slice is an explicitly invoked, backup-first **PostgreSQL candidate migration into encrypted canonical active-schema tables**, conditioned on independent full-row encrypted snapshot restoration (existing G1-b foundation) and source inventory/hash equality; verify exact source- and fiscal-year parity. Do not call a mirror or snapshot alone the canonical ledger.
4. Then test rollback, replay/key failures, active single-source read/write switch, decommissioning/retiring plaintext legacy safely and independent retention/offsite key rotation. G2 MFA/private runtime and G3 genuine evidence adapters remain separately blocked.

## Optimized GitHub Actions

`.github/workflows/backend-ci.yml` continues using **one** PostgreSQL 18 service and **one** backend job with Python pip cache, existing G1-a/G1-b smoke plus new G1-c check. PRs touching backend or workflow trigger CI, docs-only PRs do not. **Superseded PR heads cancel**, avoiding wasted re-runs; removed redundant `push` trigger on `main`. `workflow_dispatch` preserves explicit manual final verification. Tradeoff: no automatic post-squash main CI; proof is from the exact validated PR head. If future branch protection requires a main CI or merge queue, revise strategy with evidence.

## Running when an authorized PostgreSQL environment is already available

From `backend/`, with externally provided **synthetic** PostgreSQL source DSN and the appropriate synthetic field/HMAC keys:

```python
from app.g1c_preflight import preflight_postgres_source
receipt = preflight_postgres_source()
assert receipt["synthetic_only"] and receipt["read_only"]
assert receipt["migration_performed"] is False
```

Do not print raw sources, store real credentials in Git, or connect genuine financial databases. No Docker, VPS, Vercel, Railway or external development provision is part of this implementation.

**Project isolation:** [mandatory project-only context and external-provider boundary](PROJECT_CONTEXT_AND_INFRASTRUCTURE_ISOLATION.md) applies to every code/change/testing decision.
