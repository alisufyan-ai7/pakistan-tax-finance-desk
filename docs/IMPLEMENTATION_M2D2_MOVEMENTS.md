# M2d-2 — Conservative own-transfer candidates and non-earnings cash movements

**Stage:** Synthetic-only read-only accounting assistance, no real bank statements or confirmed legal tax treatment.

## Delivered

- Read-only `GET /api/finance/movement-review?tax_year=2026` identifies **UNVERIFIED_TRANSFER_CANDIDATE** pairs when a user-reviewed `own_transfer` debit on one individual account has exactly one corresponding `own_transfer` credit on another individual account with equal amount and posting date within two days. The reciprocal match must also be unique.
- Ambiguous same-amount cross-account matches are **not** auto-paired; they appear as IDs requiring manual review. Single-sided entries are flagged unmatched. Category review/overlap resolution must be complete before matching.
- Performs boundary lookups two days beyond the selected tax year so June 30 ↔ July 1 movements can be considered, while in-year summary totals include only actual in-year transaction dates.
- Distinguishes reviewed bank movements classified as loans, loan repayments, own transfers, cash withdrawals, donations/zakat, tax payments, investment purchases and gifts. Totals are **movement observations**, not income tax figures, verified loan receivables or net-worth calculations.
- No automatic deletion, category reassignment, tax calculation, investment gain inference or confirmed loan balance. The ledger and audit trail remain immutable.

## Acceptance and limitations

Unit tests require unique matching, ambiguous failure closed, legal-entity separation, unreviewed item rejection, FY boundary behavior and no tax/loan claims. Integration test imports synthetic bank rows in two distinct accounts and confirms read-only pair detection and unchanged existing category totals.

This does not track counterparties, loan principal schedules, accrued markup, proof of own-account ownership or original loan contracts. Those require a separate loan/entity registry with provenance and audit controls. The current application remains synthetic-only with incomplete numeric/date encryption and no actual FBR tax engine. See `docs/CURRENT_HANDOFF.md`.