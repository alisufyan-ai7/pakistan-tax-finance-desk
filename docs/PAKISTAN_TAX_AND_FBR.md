# Pakistan tax engine and FBR filing strategy

**This is engineering design, not legal/tax advice or a verified rate table.** Applicable rules must be verified against authoritative tax-year primary law, notifications, court positions and professional review before use for actual filing.

## Tax periods and law versioning

Pakistan's normal tax year is July 1–June 30; named for ending June 30 year. Maintain rules for TY2023, TY2024, TY2025, TY2026 and TY2027 as available, with source citation, effective dates, status `DRAFT/REVIEWED/RELEASED`, test vectors and maker-checker audit trail. Never use a current-year rate for an old tax year.

## Heads and treatments

Salary; property income; business income; capital gains; other sources. Consider applicable exemptions, credits, special regimes, final taxes, minimum taxes, turnover tests, nonresident/resident distinctions, foreign-source income, employer withheld amounts, adjustable taxes, taxes already paid and arrears/penalties as distinct. A bank credit is neither proof of gross salary nor of taxable income; business net income requires authorized expenditure and sometimes accrual records.

## Three separate UI estimates

- **Recognized YTD**: tax computations based on verified classified income and known legal periods; display missing information and the fact annual tax thresholds may make attribution non-linear.
- **Projected full-year**: annualized/planned remaining salary, business income and estimated taxable gains, with selectable `conservative/base/upside` assumptions and transparent bands.
- **Estimated balance due/refund**: estimated annual tax minus eligible, classified, verified adjustable payments/credits; final-tax withholding is not automatically a credit against general tax.

Do not label `annual estimated liability * months / 12` as actual YTD statutory tax; may be shown **only** as explicitly illustrative budget allocation. Show an estimate range when income is volatile.

## Donations and gifts

Capture every donation/zakat/sadaqah/gift and charitable recipient. Eligibility for relief under relevant provisions (including section 61 where applicable) must be determined per tax year and recipient/evidence; not every donation qualifies. Distinguish gift vs loan vs income; support corroboration, wealth disclosure and anomaly detection. Do not suggest artificial revisions of prior declarations.

## Loans

Record borrowing and lending principal in wealth/assets/liabilities, while distinguishing financing cost/profit and their tax characterization. Loan proceeds are not default taxable income; repayment of principal is not default income/expense. Tax-specific treatment must be reviewed for waivers, related-party transfers, financing costs and source-of-funds requirements.

## FBR readiness

Build a reproducible evidence-backed report with: tax year, taxpayer/entity, income head schedules, allowable expenses evidence, withholding records and distinction between statuses, credits, asset/liability summary, opening/closing wealth, income less personal expenses reconciliation, unresolved variance, and item-by-item IRIS entry reference. Track separate actual historical filed returns; do not silently amend.

**Submit via IRIS manually at first.** A fully automated submit mechanism is outside scope absent official supported integration and owner approval. No scraping passwords, OTPs or PINs.

## Quality gates

- Every tax result shows tax year, statute/source version, provenance and assumption flags.
- Each prior-year rate regime has automated tests with legal examples and boundary checks, including partial FY, lumpy income and cross-year changes.
- No filing marked READY while bank statements, withholding evidence, capital gains or wealth reconciliation materially unresolved.
- Professional review before depending on outputs for actual filing, including unusual tax profiles.

See `REGULATORY_SOURCES.md` for official sources. Update versions as tax law changes.
