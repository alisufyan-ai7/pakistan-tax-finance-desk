# M2e — Owner-reviewed loans, principal/markup, and account transfers

**Status:** Synthetic-only implementation; not available for genuine financial records. No verified tax treatment or FBR output.

## What this adds

The system now supports a non-destructive financial event layer over the previously imported, **reviewed** bank ledger. A loan agreement has a direction (`borrowed` = liability; `lent` = receivable), explicitly stated opening date and balance, encrypted counterparty label, and an encrypted opening-basis note. **Opening balances are owner declarations, not independent proof.**

A bank transaction can be allocated only once, and only when it is reviewed, included, resolved for overlap, in an individual-owned PKR account, on or after the loan opening date. Each immutable loan allocation records the exact principal and markup split. The entire amount must reconcile to the bank transaction in PKR minor units; there is no rounding, guessed markup, or default deduction. Chronological end-of-day principal may never become negative or exceed the supported cap. Interest/markup does not reduce principal. Source transactions linked to a loan are protected from reclassification/exclusion.

Allowed reviewed categories:

| Direction | Loan advance | Principal-only repayment | Principal + markup installment |
|---|---|---|---|
| Borrowed | `loan_received` (credit) | `debt_principal_paid` (debit) | `loan_installment_paid` (debit) |
| Lent | `loan_given` (debit) | `loan_repayment_received` (credit) | `loan_installment_received` (credit) |

For an installment the user states `principal_minor` and `markup_minor`, and they must **sum exactly** to its source debit/credit amount. Interest-only payments are permitted if explicitly described in the installment category. For disbursements and principal-only repayments, markup must be zero.

The owner may also explicitly confirm two **reviewed** `own_transfer` transactions: a debit and matching credit of the same PKR amount, from two distinct accounts owned by the same individual, within two days. The confirmation must include a meaningful encrypted evidence note. An exact confirmation replay is idempotent; different pairing reuses are rejected. The confirmation does **not** mutate the bank ledger, record revenue/expense, certify beneficial ownership or create a tax conclusion. Cross-June/July tax-year joins appear in both years' linked-transfer results.

## API routes

All API routes use the existing local synthetic authentication and (when configured) MFA/CSRF protections:

- `POST /api/finance/loans`: create `direction`, `counterparty_label`, `opening_as_of`, `opening_principal_minor`, `opening_basis`.
- `POST /api/finance/loans/{id}/allocations`: link reviewed `transaction_id`, `principal_minor`, `markup_minor`, `evidence_note`. Exact amount replay returns `already_linked=true`.
- `GET /api/finance/loans?as_of=YYYY-MM-DD`: outstanding debt/receivable at selected date, original opening note, principal advances, principal repayments, observed markup and event history.
- `GET /api/finance/loans/{id}?as_of=YYYY-MM-DD`: individual loan.
- `POST /api/finance/transfers/confirm`: `debit_transaction_id`, `credit_transaction_id`, `evidence_note`.
- `GET /api/finance/transfers/confirmed?tax_year=YYYY`: owner-confirmed transfer pairs for a given FBR July–June year.

Rows are append-only in this stage; corrections/reversal interfaces, authenticated evidence documents and transaction reassignment are planned separately. A manual database edit is not an approved correction workflow. The app does not assume that a borrowed-loan receipt is taxable income, that an interest payment is deductible, or that a repayment is a sale/purchase.

## Migration and regression acceptance

- Alembic `0004_finance_links` adds `loan_accounts`, `loan_allocations`, `transfer_confirmations`; no destructive downgrade; new encrypted text domains included in the existing explicit keyring/rotation scope.
- CI must pass the entire synthetic Python test suite, then apply migrations through `0004_finance_links` to ephemeral PostgreSQL 18 and confirm `alembic check` yields no schema drift.
- Test borrowing/lending and interest split; a backdated repayment that would generate negative outstanding; exact replay; double-link rejection; rejected inappropriate classification; cross-year transfer confirmation; mismatched accounts and amounts; source editing lock; encrypted synthetic counterparty and evidence notes; `APP_DATA_MODE=real` remains rejected.

## Security and accounting limitations

**Not production safe.** Loan principal, markup, balances, dates, source IDs and linkage still reside as unencrypted database metadata. Names/basis/evidence notes use AES-GCM encrypted columns with external keys, but no tested real-data key management, automatic audited reversal, secured off-site backup, production MFA recovery, or complete numerical-field encryption exists. There is no supporting document upload/verification, entity/company support, bank authentication, FBR tax computation, capital-gain treatment, zakat eligibility certification, or IRIS filing. No bank statements or previous tax returns are necessary to build/test this milestone.

GitHub stays temporarily public by the owner's decision; **never commit genuine taxpayer data, bank statements, credentials or source-identifying personal figures**. Keep `APP_DATA_MODE=real` fail closed.

> **M2f update (2026-11-15):** The original M2e restriction on link corrections is superseded by the audited reversal and reassignment workflow in [M2f](IMPLEMENTATION_M2F_REVERSALS.md). All underlying data remains synthetic-only and not FBR-verified.
