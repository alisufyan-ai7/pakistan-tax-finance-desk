# Lawful Tax Optimization and Historical Filed-Return Intake

**Status:** Engineering specification and owner-approved direction (2026-11-15). No real tax documents received through the application, no tax law eligibility certified, no live tax computation implemented. GitHub is TEMPORARILY PUBLIC by explicit owner instruction; **no personal financial data in Git**.

## Mission

Produce the lowest **legally supportable** tax liability for the owner's actual circumstances by identifying evidence-backed planning opportunities, preventing missed credits/withholding, and comparing compliant alternatives. Do not equate lower tax with lower reported income. The assistant must NOT endorse hiding income/assets, fake costs or donations, sham loans, artificial residency/status changes, manipulating dates, unsupported retroactive amendments, or misrepresenting identities.

User has mixed salary, business, investments and other sources; historical ledger from January 2023 onward, potentially earlier cost basis. User expects to provide 3–4 previously filed annual FBR income tax returns; request corresponding wealth statements and supporting schedules when available. No need to upload any genuine data to GitHub.

## A. Prior filed-return intake contract (private application, after security gate)

### Accepted evidence kinds
- **Return of Income** (filed/acknowledged IRIS export with relevant TY, taxpayer/legal entity, submission/amendment status).
- **Wealth Statement**, preferably with opening and closing assets, liabilities, expenditure and reconciliation.
- Supporting withholding/advance tax certificates, payment challans/CPRs, salary certificates, dividend/capital gains statements, bank/broker/tax schedules, prior amendments.
- **Secure app only**; no bank/tax passwords or raw unredacted documents in public GitHub, issues, PRs, CI, logs or test fixtures.

### Provenance and indexing
Each file has an immutable encrypted original, content checksum, upload source, taxpayer/legal entity, year, tax-form type, filing/submission/acknowledgment date, version/amendment lineage, extractor version, extraction confidence per field, human verification and audit history. Redact display-identifying fields; preserve protected original separately. Never overwrite the actual filed figures with recalculated figures.

### Structured annual extracted snapshot
Use optional fields (unknown != zero): income heads and receipts; declared expense adjustments; taxable income; calculated tax; adjustable taxes; final tax; refunds/carryovers; tax paid; opening and closing wealth; cash-in-hand; real estate; securities; vehicles; loans given/taken; gifts and donations; capital introduced/withdrawn; personal expenditures; reconciliation differences; schedules and source page pointers. Different forms and tax years may expose different fields. Legal-entity identity is mandatory for meaningful alignment.

### Reconciliation behavior
1. Determine tax year and exact filed document version; identify whether this is original, revised, draft or acknowledged.
2. Extract and verify high-confidence line items; mark low-confidence/ambiguous fields for review.
3. Compare filed historical values to bank/broker financial ledger **without automatically correcting either**.
4. Tie prior-year closing assets/liabilities to next-year opening where legally appropriate; distinguish historical statement gaps and unsupported cash/wealth assumptions.
5. Surface discrepancy cards: previous filed amount; reconstructed amount; reason hypotheses; evidence missing; review status.
6. Preserve filed-original even if a permitted correction is later reviewed. Any proposed revision needs explicit human/legal review, applicable deadlines, and audit record; **never submit or revise silently**.

## B. Opportunity engine: distinct from final tax liability

### Sources of potential opportunities (examples; NOT presumed entitlements)
- Eligible statutory **tax credits** (e.g., qualifying donations, subject to tax-year conditions and evidence).
- Legitimate deductible business expenditures with business-purpose evidence and entity ownership separated from personal spending.
- Verified allowable exemptions, preferential/special tax regimes and correct treatment of salaried vs business vs property vs investment sources.
- Adjustable withholding or advance payments not yet considered; distinguish final/minimum/adjustable treatments and an actual tax reduction from a refund/recovery.
- Review of investments, gains/losses, dividend/interest taxation and factual year-specific loss treatment where law permits.
- Filing-readiness suggestions, missed evidence, year-specific legal elections or refund/revision timeframes with professional review.
- Cash planning: paying due tax on time and tracking required payments; no unsupported tax-deferral advice.

### Opportunity record schema (non-PII design)
```json
{
  "tax_year": 2026,
  "legal_entity_ref": "owner_taxpayer",
  "opportunity_type": "withholding_review",
  "status": "EVIDENCE_REQUIRED",
  "law_source_url": "https://fbr.gov.pk/Categ/Income-Tax--Income-Tax-Ordinance/326",
  "law_section": null,
  "law_version": null,
  "effective_start": null,
  "effective_end": null,
  "evidence_refs": [],
  "missing_evidence": ["supported withholding certificate"],
  "base_case_tax_pkr": null,
  "scenario_tax_pkr": null,
  "potential_saving_pkr": null,
  "limitations": "Illustrative until reviewed; withholding may be final, minimum, or adjustable.",
  "requires_human_review": true
}
```

### Mandatory rule states
`DRAFT` -> `LEGAL_SOURCE_CHECKED` -> `TESTS_VERIFIED` -> `REVIEWED_FOR_USE` for tax rule versions. Opportunity `CANDIDATE` -> `EVIDENCE_REQUIRED` -> `VERIFIED_ELIGIBLE` / `INELIGIBLE` / `NOT_APPLICABLE` -> `USER_ACCEPTED` only after checks. AI may find an opportunity candidate or explain it, never silently elevate eligibility or fabricate numerical savings.

### UI: Tax Optimization Advisor
- Show **Potential opportunities**, **Needs evidence**, **Verified eligible**, **Not eligible**, **Applied to calculation**, and **Consider with a qualified tax practitioner**.
- Card fields: tax year, taxpayer/entity, why flagged, statutory source/section/version, prerequisite tests, proof missing, lawful savings estimate (or **unavailable**), timing/revision caveats, user action, audit record.
- Scenario comparison must separate liability decrease, payment/refund adjustment, and timing-only cash-flow shifts.
- Never list tax savings as certain from bank statement narrative alone; never present a tax-credit amount before verified legal prerequisites and documents.

## C. Security and deployment gates

**Current M1 prototype is SQLite + local Basic auth without encrypted document storage or MFA; synthetic data ONLY.** Before real statements/returns: secure owner MFA + TLS private app, encrypted original storage with key management, audit trail, file upload validation, PII-safe extraction, segregation from public GitHub/CI, encrypted backup and tested restore, corrections and deletion/export controls.

User may choose to share redacted historic returns through a conversation for preliminary understanding, but the permanent application importer remains unavailable until security work is complete. Never send tax documents to a third-party model by default or store raw extracts in public source control.

## D. First development slices

1. Synthetic filed-income-return + wealth-statement field schemas and example fixtures for two different tax years. Tests reject unknown tax years/document types and preserve revision lineage.
2. Private encrypted upload+MFA and versioned evidence records; robust protected extraction with user verification and file hashes.
3. Prior-return-to-ledger reconciliation with missing-vs-zero guards, discrepancy queue and cross-year wealth tie-out.
4. Statutory rule source registry 2023 onward, legal review and independent test vectors.
5. Candidate opportunity detection and human review UI, with explicit `null` savings until eligibility verified.
6. Advisory features and reports, no automatic FBR filing.

## E. Official source entry points, verified 2026-11-15

- FBR Income Tax Ordinance historical versions (2023, 2024, 2025, 2026): https://fbr.gov.pk/Categ/Income-Tax--Income-Tax-Ordinance/326
- FBR Income Tax Rules historical/current: https://fbr.gov.pk/categ/income-tax-rules-2002/335
- FBR completing return and wealth reconciliation: https://www.fbr.gov.pk/categ/file-income-tax-return/51147/80860/71160
- FBR revising filed return and wealth statement: https://www.fbr.gov.pk/categ/file-income-tax-return/51147/80860/%2071161

Sources are general entry points. The rule engine must verify precise text, commencement, amendments and applicability for the specific tax year; these links alone do not validate an individual deduction, credit or refund.
