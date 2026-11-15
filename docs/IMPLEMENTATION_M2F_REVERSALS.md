# M2f — Audited corrections to loan allocations and owner-confirmed transfers

**Status:** Synthetic-only development milestone. No actual bank statements or filed returns may enter this application or the public source repository. No tax figures or legal conclusions are certified.

## Why this is needed

M2e linked reviewed bank transactions to a loan principal/markup schedule or to the opposite bank account's own-transfer record. Those initial links were immutable, meaning a mistaken pairing could not be corrected without a database edit. M2f adds a controlled correction API with **permanent, encrypted, append-only reversal evidence**; original bank transactions and original link records remain present.

## Correction semantics

- Loan allocation reversal requires an authenticated request with a meaningful reason (12–500 characters), verified allocation ID and matching loan ID. An identical replay is idempotent. For a disbursement reversal, the remaining dated loan posting schedule is recalculated first; a reversal that would cause a negative outstanding balance is rejected. Reverse dependent repayments first, then the advance.
- Confirmed transfer reversal requires an authenticated reason and exact confirmation ID. Original confirmation remains in the database with an inactive flag and independent, encrypted revocation record.
- Reversal changes only the **active** flag and appends an immutable audit row; it does **not** delete the original bank transaction, classification audit or supporting description. It does not imply an FBR return amendment.
- Unique partial database indexes prevent one bank transaction from being assigned to two **active** loans, or one transfer side from being used by two **active** confirmations. After a reversal, a corrected transaction link can be created. Cross-entity, currency, posted-date and category checks still apply.
- Reversed loan allocations remain visible in loan history with `status=REVERSED` and their reason, but stop affecting current and historical as-of principal/markup totals. Active confirmed transfers appear in `/api/finance/transfers/confirmed`; revoked confirmations remain accessible through the audit API.
- Neither loan opening amounts, transaction categories nor tax effects are now independently verified. Existing `tax_due` and projected tax fields remain `null`.

## API routes

All routes are local-authenticated and inherit existing MFA/CSRF checks when MFA session mode is enabled:

- `POST /api/finance/loans/{loan_id}/allocations/{allocation_id}/reverse` with `{ "reason": "meaningful correction evidence" }`. Returns created reversal (HTTP 201), or same prior reversal (HTTP 200) for idempotent repeat.
- `POST /api/finance/transfers/{transfer_id}/reverse` with a similarly meaningful `reason`.
- `GET /api/finance/links/audit` returns reversal IDs, original allocation/confirmation IDs, encrypted-at-rest reasons (decrypted for the authenticated owner) and timestamped history.
- Existing loan and transfer read/create endpoints remain backward-compatible; confirmed/reconciled views exclude inactive allocations.

## Database and tests

New Alembic revision `0005_link_reversals` adds `active` flags to loan allocations and transfer confirmations, replaces strict unique constraints with **active-only partial unique indexes**, and introduces `loan_allocation_reversals` and `transfer_revocations` audit tables. Their reason text fields are encrypted using AES-GCM key-ID-bound envelopes and included in the existing offline synthetic key-rotation inventory.

CI must pass the entire synthetic test suite, ephemeral PostgreSQL 18 `alembic upgrade head`, and no-drift `alembic check`; SQLite migration tests must also pass. Specific checks: disbursement reversal with dependent repayments rejects; repayment-first correction succeeds; exact replay idempotent; corrected reassignment works; owner transfer can be revoked/reconfirmed; source lock follows **active** links only; correction reasons stored encrypted; tax figures remain unverified/null.

## Security and product limitations

These corrections are user-directed, not independently evidenced. Financial numbers, dates, bank transaction IDs and other metadata still remain unencrypted in the prototype. The reversal audit is append-only at the API level, but no complete forensic database logging, immutable external archive, production multiworker controls, disaster-recovery certification or legal-accountant review exists yet. Current code still fails closed on `APP_DATA_MODE=real`. Keep genuine personal records out of temporary public GitHub, CI and the synthetic application.
