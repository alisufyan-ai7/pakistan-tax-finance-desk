# Pakistan primary-source reference registry

**Verification date:** 2026-11-15. Links are reference entry points, not a certified list of current rates. Before coding or filing any FY calculation, select the applicable statute/finance act/rate schedule and review its exact effective dates, exceptions, and later amendments.

1. FBR — tax-year period (July to June): https://www.fbr.gov.pk/income-tax/81145/81149
2. FBR — income-tax basics and five heads of income: https://www.fbr.gov.pk/income-tax-basics/51147/61148
3. FBR — filing income-tax returns, income and wealth statements / wealth reconciliation: https://fbr.gov.pk/categ/file-income-tax-return/51147/80860/71160
4. FBR — Income Tax Ordinance archive (includes amendment versions for 2023–2026): https://fbr.gov.pk/Categ/Income-Tax--Income-Tax-Ordinance/326
5. FBR — current and historic withholding tax rate cards incl. TY2023–TY2027: https://www.fbr.gov.pk/withholding-taxes-rate-card/174298/174301
6. FBR — tax return records retained for six years: https://fbr.gov.pk/categ/file-income-tax-return/51147/80860/71163
7. FBR — past-return revision guidance: https://www.fbr.gov.pk/categ/file-income-tax-return/51147/80860/%2071161
8. FBR IRIS: https://iris.fbr.gov.pk/
9. SECP — securities/futures advisers licensing (future public tailored advice boundary): https://www.secp.gov.pk/licensing/capital-markets/securities-advisors-and-futures-advisor/
10. SECP — investment advisory services licensing: https://www.secp.gov.pk/licensing/nbfcs/investment-advisory-services/
11. SBP — customer information confidentiality example guidance: https://www.sbp.org.pk/circulars/bprd-circular-no-08-of-2018

## Implementation protocol

For each rule, record: tax_year, legal jurisdiction, rule id, section/regulation, source URL, publication/commencement date, effective date, taxpayer residency/entity applicability, reviewed_by, test case IDs and confidence. Charitable donation eligibility (including relevant section 61 terms), gift/loan treatment and wealth disclosure are not blanket assumed. Use professional/tax expert review before declaring FBR-ready. For financial-market productization, obtain an up-to-date legal/regulatory opinion.

12. FBR — Income Tax Rules, 2002, including 2026 updated version: https://fbr.gov.pk/categ/income-tax-rules-2002/335
13. FBR — official guidance on correcting/revising previously filed return and wealth statement: https://www.fbr.gov.pk/categ/file-income-tax-return/51147/80860/%2071161
14. FBR — income return and wealth statement filing/reconciliation: https://www.fbr.gov.pk/categ/file-income-tax-return/51147/80860/71160

**Source-gating note:** All provisions and their historic applicability must be checked against the version effective for the relevant tax year (and amendments/notifications). A general statement on an FBR help page is not automatically legal authorization for retrospective filings or a specific tax credit.

## M2l authoritative year-specific legal source index (reviewed 2026-11-15)

- [FBR Income Tax Ordinance 2001 amended through 30 June 2026](https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf) — First Schedule Part I Division I clause (2), PDF pages 526–527: salary rate table for TY2027 and historic TY2026 table it replaced; legal schedule applies to salaried individual when salary **exceeds 75%** of taxable income.
- [FBR Income Tax Ordinance historical versions](https://fbr.gov.pk/Categ/Income-Tax--Income-Tax-Ordinance/326) — amendments covering 2022–2026; TY2023–TY2027 registry versions indexed.
- [Finance Acts](https://www.fbr.gov.pk/Categ/Finance-Acts/620) — relevant historical source acts.
- [FBR withholding-tax year card index](https://www.fbr.gov.pk/withholding-tax-rate-card/174298/174301) — withholding treatment requires source-specific verification, not assumptions from bank narratives.
- [FBR IRIS income and wealth reconciliation](https://fbr.gov.pk/categ/file-income-tax-return/51147/80860/71160) — wealth reconciliation requirement.
- Prototype computes a **hypothetical salary-bracket component** in TY2026/TY2027 for explicitly bounded scenarios; it is not full mixed-income tax due. TY2023–TY2025 numerical statutory rules, statutory tax credits and actual eligibility remain unimplemented/not independently verified. See `docs/IMPLEMENTATION_M2L_FBR_RULES.md`.
