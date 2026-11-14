# Statement import, deduplication and reconciliation

## Supported input aspiration

CSV, XLSX and text-layer PDF initially; scanned PDF through carefully controlled OCR fallback. Bank-specific adapters for Pakistani banks. Password-protected statement support via client-side/ephemeral prompt; never persist passwords. Document provenance and source format must be retained. Never claim perfect parsing.

## Import pipeline

1. Authenticated upload -> malware/type/size checks -> encrypted original object -> content SHA-256.
2. Detect bank/layout/account/currency and statement period; choose parser version; leave unsupported layouts in manual review.
3. Extract rows (posting date/value date, narrative, debit, credit, signed amount, balance, ref number, branch etc). Keep page/row pointer and raw text.
4. Validate totals, running balances, opening/closing rows, statement period, monotonicity only if layout warrants; flag warnings not false success.
5. Generate deterministic per-source row ID and candidate global transaction fingerprints using bank account, amount/currency, date, reference, description and nearby running balance; near matches require review.
6. Compare with existing transaction set across overlapping documents and corrections; store new evidence without double posting.
7. Build ledger events and cross-account transfer matches. Incomplete transfer pair stays unlinked, not invented.
8. Apply high-confidence classification rules; AI only proposes low-confidence candidate with evidence and privacy-redacted context.
9. Recompute affected ledger periods, fiscal-year tax snapshots, cash flow, loan positions, holdings and wealth statements.
10. Show an import receipt: accepted, duplicated, rejected, unresolved, reconciled balances and coverage gaps.

## Edge cases to test

- Same statement imported twice unchanged; re-export with different header/format; overlapping statement months.
- Same date and amount for two *different* purchases; do not incorrectly dedupe.
- Own transfer from A to B with fee, FX spread or T+1 lag; avoid fake income/expense.
- Reversal, chargeback, bounced payment, posted/pending duplication, credit card bill vs individual card purchases.
- Salary net deposit with employer withholding; gross salary requires separate certificate/payroll data.
- ATM withdrawal later partly spent and partly deposited; don't double count.
- Loan advance, installment split between principal/interest, interest income from borrower, charge-offs.
- Refund/donation with look-alike narration, recurring monthly deductions, cash donations without bank evidence.
- Multi-currency accounts and cross-border remittances; exchange rate original source/effective date.
- Business receipts from personally held account and incorporated-company account; require ownership tagging.
- Scanned and unreadable pages; mixed-language descriptions; statements with trailing minus signs; missing running balances.

## Human review

One actionable queue; user can confirm once to create durable rule scoped to bank/account/counterparty and dates; corrections replay the ledger and re-evaluate historical snapshots. Do not infer deductibility from classification alone.

## Bank onboarding acceptance

For each layout: synthetic samples; parser fixtures; statement-level reconciliation proof; overlap and duplicate tests; error reporting; field accuracy benchmark; sample checked by owner without exposing real details to repo.
