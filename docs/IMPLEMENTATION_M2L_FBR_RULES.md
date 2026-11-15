# M2l — Year-effective FBR registry and narrow salary / optimization preview

## Scope — not a complete FBR calculator

The public, synthetic-only app now indexes the **official FBR source versions for Tax Years 2023–2027** and encodes a **narrow salary-slab component for Tax Years 2026 and 2027 only**. Actual mixed-income tax, investment/dividend/interest taxes, rental/property rules, final/minimum taxes, exemptions, withheld adjustments, credits, foreign income, refunds and FBR filing are NOT implemented. TY2023–2025 numerical slabs are deliberately disabled until verified instead of guessed.

### Official sources checked 2026-11-15

- [FBR consolidated Income Tax Ordinance 2001, amended to 30 June 2026, First Schedule Part I Division I clause (2), PDF pages 526–527](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf). The TY2026 rates are visible in the historical table replaced by Finance Act 2026. TY2027 uses the Finance Act 2026 eight-bracket schedule.
- [FBR historical ordinances amended through 2022–2026](https://fbr.gov.pk/Categ/Income-Tax--Income-Tax-Ordinance/326)
- [FBR Finance Act index, 2022–2026](https://www.fbr.gov.pk/Categ/Finance-Acts/620)
- [FBR withholding rate cards for TY2023–TY2027](https://www.fbr.gov.pk/withholding-tax-rate-card/174298/174301)
- [FBR IRIS income tax and wealth reconciliation guidance](https://fbr.gov.pk/categ/file-income-tax-return/51147/80860/71160)

## Routes and safety

`GET /api/tax/rules?tax_year=YYYY` returns current indexed legal version, whether salary slabs are source-checked, and missing rule coverage. `POST /api/tax/salary-slab-preview` requires an explicitly synthetic annual taxable-income scenario with salary **strictly exceeding 75% of taxable income**, no other separately taxed sources or adjustments, and taxable income **<= PKR 10m**. For unsupported scenarios, return 422 rather than a plausible-but-inaccurate tax quote. Rates are computed with Decimal/paisa precision, and source/legal bracket is displayed.

The existing authenticated `GET /api/tax/opportunities` also gives year-specific *statutory entry points* and evidence requirements for charitable donation section 61, Zakat section 60, business sections 20/21, advance/withholding review and investment tax regimes. All suggestions remain `EVIDENCE_REQUIRED`: **no legal eligibility, credits, refunds or potential savings are asserted**.

The narrow calculation returns `salary_slab_component_minor` ONLY. Always returns `tax_due_minor=null`, `net_tax_payable_minor=null`, `refund_minor=null`, `potential_tax_savings_minor=null`, `fbr_ready=false`. It does not read bank credits as taxable income, auto-amend historical returns, or connect to IRIS.

## More independent work required

Verify TY2023–2025 statutory schedules and year-specific salaries/non-salaries, 2027 non-salary rules, sections 60/61 caps/eligibility and amendments, full taxable-income assembly, investment gains/losses cost basis, final-vs-adjustable withholding, surcharge/super-tax, foreign income and legal entity boundaries, evidence and prior return reconciliation, independent finance/tax practitioner review, supported real documents, and production security. `APP_DATA_MODE=real` stays disabled; public GitHub contains code and synthetic tests only.