# Domain and conceptual data model

## Accounting model

A **source-first, double-entry-capable ledger** (at least balanced classified money movements) is the authoritative financial record. Separate raw imports from normalized events, interpretations and derived reporting. Prefer append-only corrections/adjustments with audit history.

## Entities (suggested)

| Entity | Key fields / notes |
|---|---|
| User, TaxProfile | residence status, tax year, tax identifiers encrypted and only where needed; salary/business/entity links |
| LegalEntity | individual, sole proprietor, partnership/AOP, company; ownership and consolidation policy; **never confuse entities** |
| FinancialAccount | bank, wallet, brokerage, cash, credit, loan; masked identifier, institution, currency, owner |
| SourceDocument | content hash, encrypted object URI, date coverage, bank/layout/version, upload timestamp, immutable provenance |
| ImportBatch / ParsedLine | source row/page reference, raw text, amount, date, balance, parser confidence and exception state |
| Transaction | normalized posting date, value date, amount/currency, account, counterparty, transfer group, source pointer, current classification |
| LedgerEntry | dated balanced debit/credit lines, type, status, linked transaction, correction chain |
| Category / Classification | user-confirmed vs inferred, confidence, rule id/version, financial purpose, tax treatment tags |
| Counterparty | beneficiary, employer, borrower, lender, charity, supplier, broker; identity minimized and access-controlled |
| TransferMatch | linked sides, FX/spread/fees, time offset, match evidence, confirmation status |
| LoanContract / LoanEvent | receivable or payable, lender/borrower, opening principal, disbursement, scheduled/actual repayment, markup, fees, collateral, documentation, outstanding |
| Gift / DonationEvent | received/given, recipient, purpose, bank/cash, eligibility evidence, zakat/sadaqah category, deductible/credit status unresolved until verified |
| Asset / Holding / Lot | cash, bank, PSX, fund, gold, property, vehicle, crypto etc; cost basis, acquisition, disposition, quantity, fees, verified value |
| PriceObservation / FXRate | price, source, timestamp, currency, stale/reliability flag, licensing metadata |
| TaxRuleVersion | jurisdiction, tax year, date-effective interval, law/source URL, reviewed status, calculation tests |
| TaxEstimate / TaxEvidence | income heads, tax components, adjustable/final/minimum withholding status, assumptions, result and source references |
| WealthStatementSnapshot | start/end balance sheet, adjustments, personal expenditures, reconciliation difference, confidence |
| FilingRecord | filed/under review, user-supplied evidence, date, notice info, frozen original vs prospective revision |
| FinancialGoal / AdviceScenario | horizon, liquidity needs, risk capacity/tolerance, assumptions, options, disclosure and user acknowledgement |
| AuditLog | actor/action/time, before/after, reason, source, no plaintext secrets |

## Type/semantic rules

- **Loan received**: increases bank cash and liability; loan principal receipt is not automatically taxable income.
- **Loan given**: decreases cash, increases loan receivable; not ordinary consumption expense. Principal return decreases receivable; any explicit return/markup treated separately after review.
- **Own-account transfer**: net-worth-neutral and not taxable income; may cross institutions/currencies.
- **Bank withdrawal/ATM**: movement to presumed cash or uncertain use; cannot both count as expense and remain cash indefinitely. Cash spending requires confirmation or basis for inference.
- **Gift received / family support**: may affect wealth and applicable disclosure; not automatically tax-free or salary. Capture source, relationship, evidence and applicable tax-year treatment.
- **Donation / zakat / sadaqah**: separate personal spending from any tax-credit eligibility. Recipient and formal evidence matter; never apply blanket tax deductions.
- **Investment buy/sell**: funding transfers are not gains. Gains require acquisition/disposal details, permitted cost methodology, fees and current-year legal treatment.
- **Refund**: reverse underlying expense/revenue when established, not new earned income by default.
- **Capital expenditure**: acquisition of asset, not automatically deductible business expense.
- **Business vs individual**: revenue and costs linked to legal entity; avoid double counting transfers to owner.
- **Cash and bank balances**: accounting balance estimates distinct from independently statement-verified balances.

## Invariants

One real-world transaction can have multiple evidence records but must have one canonical ledger effect. All manual overrides retain previous version and reason. Reports must carry coverage dates, entity ownership, sources and confidence. Store original currency and decimal precision; derived PKR conversion documents FX basis. Database schema should allow many tenants in future, but enforce single user now (isolation first, not premature multi-tenant billing).
