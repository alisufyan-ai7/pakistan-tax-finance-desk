# Wealth, investments, liabilities and financial planning

## End-to-end wealth ledger

Track PKR and original currency: bank deposits, cash at home/in hand, mobile wallets, PSX securities, mutual funds, fixed-income/savings/National Savings/sukuk, precious metals, real estate, vehicles, business ownership equity, crypto (if used), and other relevant assets. Maintain loans payable and receivable, credit cards, liabilities, installments, due dates, guarantees (off-balance where appropriate) and net worth snapshots.

Asset balances: `cash value`, `cost basis`, `current estimated market value`, `unrealized P/L`, `realized P/L`, `tax basis` are separate fields. A bank transfer to a broker is a contribution, not proof of a purchase or gain. Optional broker/C DC/NCCPL evidence, statement files and licensed price feeds can supply holdings and gains.

## Loan module

Track two-sided classification: `LOAN_GIVEN` (receivable) and `LOAN_TAKEN` (payable). Each obligation has counterparty, currency, contract proof, original amount, disbursement date, repayment events, principal, agreed markup/interest (if any), installments, collateral, due date, overdue state, waivers and remaining balance. Linked bank transfers reduce cash and increase/decrease balance sheet accounts; never misclassify loan principal as income or consumption. Generate reminders and dashboards with explicit user review.

## Gifts, donations, zakat

Separate categories for giving and receiving, beneficiaries, purpose, charitable-recipient eligibility, date, amount, payment channel and receipts. Zakat/personal philanthropy is a cash outflow but not automatically an income-tax deduction/credit. Gift and inheritance transactions require source and legal/tax classification before treatment.

## Cash-in-hand

A bank ATM withdrawal is not automatically *spent*, nor proof it remains cash. Allow an explicit cash wallet with opening balance, deposits/withdrawals, manually logged expenses, cash gifts and purchases. Mark any inferred cash balance `UNVERIFIED` and do not fabricate FBR cash-in-hand values.

## Planning assistant (personal release)

**Goal: useful, responsible decision support**, not an unregulated promise of fiduciary service. Provide:

- Cash runway and expense volatility; emergency reserve target based on actual recurring spending and income stability.
- Debt overview: rates/fees, maturities, late risk and whether paying down expensive debt has priority over investing surplus.
- Goal buckets by horizon (near-term needs, 1–3 years, longer-term); risk capacity vs risk tolerance vs liquidity needs.
- Portfolio concentration, currency mismatch, asset allocation, liquidity and diversification checks; known-fee and tax comparisons.
- Alternative scenario analysis: cash deposits/profit accounts, sovereign savings/sukuk, diversified funds, equities, gold, etc., only as applicable and supported, with realistic risks and no guaranteed returns.
- Investment planning in PKR with inflation sensitivity, fee assumptions, tax impacts, drawdown scenarios and uncertain returns.
- Explain assumptions, cite data inputs and official sources, invite a user correction before making personalized recommendations.

Do NOT recommend buying a particular security with a specific quantity solely from bank statements; do NOT execute trades, promise outperformance, assume religious/Shariah preferences, or use third-party feeds outside permitted terms.

## Future regulated boundary

Before offering personalized securities/investment advice to other users, obtain appropriate Pakistan legal counsel review of SECP investment/securities advisory licensing and digital advisory requirements. Consider a first commercial tier restricted to record keeping, expense analytics and tax preparation support. Selling generic software is different from representing oneself as a licensed adviser.
