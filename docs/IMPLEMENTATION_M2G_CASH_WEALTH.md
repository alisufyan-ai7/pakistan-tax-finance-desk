# M2g — Synthetic cash-in-hand and annual wealth movement bridge

**Scope:** Local/synthetic-only. No live banking records, FBR filings, verified cash holdings, financial advice, or certified tax savings. Current source GitHub is intentionally public by owner choice and must never contain real personal financial records or identifiers.

## New records

- `cash_holdings`: separate owner-declared PKR cash holdings, dated opening amount, encrypted label and declared evidence basis. Values may be zero **only when explicitly stated**; `missing` never defaults to zero.
- `cash_movements`: dated cash movement linked either to a reviewed bank transaction **or** a separately declared manual receipt/spend. Kinds: `bank_withdrawal` (cash increases), `bank_deposit` (cash decreases), `manual_receipt` (cash increases), `manual_spend` (cash decreases). Manual receipts and expenses remain unverified, not assumed taxable or deductible.
- `cash_movement_reversals`: append-only encrypted reasons for audited corrections; active-only uniqueness allows a bank source to be reallocated after an explicit reversal without deleting original rows.
- Immutable source references; encryption for cash-holding labels and notes via M2d AES-GCM key-ID envelope; **amounts/dates/identifiers remain plaintext** as a known security gap.

### Source validation

A bank withdrawal requires a reviewed, included, overlap-resolved **individual-owned PKR** transaction categorized `atm_cash`, exactly matching the debit amount and posting date. A bank deposit likewise requires the new reviewed credit category `cash_deposit`, matching amount and date. Cash movements may not reuse active loan/confirmed-transfer sources; those sources may not subsequently be linked to loans/transfers. Linked source classification edits are blocked until audited reversal. Bank-only and manual-only forms cannot be confused.

Cash balance is opening amount plus active dated movements; report **as-of** date. Every accepted mutation and reversal validates the full chronological end-of-day schedule to prevent impossible negative balances and silent negative backdating. Intraday cash ordering is unknown; tests assume only **end-of-day** reconciliation.

### API (all endpoints require existing synthetic local auth)

- `POST /api/finance/cash` — explicitly declare opening date/amount and evidence basis.
- `GET /api/finance/cash?as_of=YYYY-MM-DD` — list as-of cash holdings, still owner-declared.
- `GET /api/finance/cash/{cash_id}?as_of=YYYY-MM-DD` — individual dated balance and immutable movement/reversal history.
- `POST /api/finance/cash/{cash_id}/movements` — bank-linked or reasoned manual cash movement.
- `POST /api/finance/cash/{cash_id}/movements/{movement_id}/reverse` — reasoned, idempotent correction with preservation of original movement.
- `GET /api/finance/cash/annual?tax_year=2026` — July 1–June 30 opening/closing cash movement bridge. When an opening predates the represented holding's declared opening date, the total is **null** and status `MISSING_OPENING_EVIDENCE`. **Never substitute zero**.

Outputs explicitly declare `synthetic_only`, `fbr_wealth_verified=false`, `tax_treatment_verified=false`, and `tax_due=null`. The annual cash bridge is **not** full wealth reconciliation: bank balances, loan receivables/liabilities, investments, properties, gold, vehicles, gifts and unexplained opening wealth require separate evidence.

### Automated acceptance

Synthetic tests cover: bank debit→cash increase and bank credit→cash decrease; owner-declared manual spending/receipt; annual tax-year crossing; no fabricated opening balances; negative/out-of-order cash posting prevention; reviewed-source checks and exact replay; no double-assignment or silent reclassification; reversal with idempotency and safe relinking; encrypted notes on disk; no FBR eligibility/tax computation; SQLite and PostgreSQL18 Alembic schema parity. All fixtures synthetic.

## Explicit exclusions / next milestones

- Real documents and real-data mode remain prohibited. Dates, money, identifiers and source digests are not encrypted; private deployment, full MFA/recovery, key rotation drills and PostgreSQL protected backups must precede genuine personal files.
- Cash-in-hand valuations are **owner assertions** and may not be recorded as already verified wealth or allowable expenses; gifts, zakat and business cash expenses need separate eligible evidence.
- Physical cash may leave/re-enter off-ledger and cannot be reconstructed from bank PDFs alone. Missing manual sources produce an **unknown**, not a guaranteed net-worth position.
- Next priorities: broader full-sensitive-field encryption or whole-database protection and keyed dedup; synthetic FBR prior returns and bank PDF parser; historical wealth reconciliation incorporating existing loan and cash evidence without treating opening gaps as zeros; production-grade private app security; official year-effective Pakistan tax rules and legal tax-minimization cards.