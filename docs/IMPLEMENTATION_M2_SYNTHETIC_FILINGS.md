# M2a — Synthetic historical filing and evidence foundation (2026-11-15)

**Implemented in feature branch; local tests only until merged.** Public GitHub is approved for source-code development. No genuine bank statements, FBR returns, real identifiers or taxpayer figures belong in this repository or CI.

## What works now

- Local *synthetic-only*, owner-authenticated API accepts **normalized numeric fixture records** labelled `synthetic_fixture: true`, with income-return or wealth-statement kind, tax year >= 2023, permitted field names, individual legal entity, and version history.
- Original and revised test filings are immutable; exact replay returns an already-imported result, changing original requires a linked revision, and revisions cannot branch or mix years/types.
- Uploaded **synthetic JSON fixture** is encrypted with AES-256-GCM, a unique random nonce and metadata-bound authenticated additional data; file uses exclusive create (no overwrite) and restrictive POSIX permissions, key provided only via environment.
- Recorded numerical fixture fields are also stored in **unencrypted SQLite** for local prototype queries; **this is NOT a safe real-data storage path**. Later security gate must protect both structured data and original evidence, replace local Basic auth with proper MFA/TLS, and prove encrypted backups and restore.
- Wealth-statement continuity checks previous tax-year closing wealth against next tax-year opening wealth, returning `MATCH`, `DISCREPANCY` or `MISSING_EVIDENCE` (missing never treated as zero).
- Read-only tax opportunity hints flag reviewed transaction categories `donation`, `zakat`, `business_expense` and `tax_paid` as **EVIDENCE_REQUIRED** with no statutory eligibility verdict, calculated tax or claimed savings (`potential_tax_savings: null`). These are candidates, not legal advice.

## What is intentionally not built

No PDF parsing or private-tax-document upload; no production sessions/MFA; no PostgreSQL/Alembic migration; no encrypted structured DB/backups/restore; no rule-verified FBR tax calculation; no legally verified tax relief. No automatic filing or revision. The synthetic fixture endpoint is not a general upload feature. Do not use a real FBR document or authentic filed figures to construct its payload.

## Local synthetic test flow

Configure backend `OWNER_PASSWORD` with >= 16 characters. For the local encrypted synthetic-fixture API, also set `DOCUMENT_VAULT_KEY` to a fresh URL-safe base64-encoded 32-byte random key and `DOCUMENT_VAULT_DIR` to a private location under `backend/data/evidence`. Never commit this key or store it in GitHub Actions. The API remains local-loopback-only and requires existing owner Basic auth. From `backend`:

```bash
python -m pip install -e '.[dev]'
pytest -q
```

Example **made-up test only** JSON:

```json
{
  "synthetic_fixture": true,
  "tax_year": 2024,
  "kind": "wealth_statement",
  "filing_status": "filed_original",
  "fields": {"opening_wealth_minor": 1000000, "closing_wealth_minor": 1500000}
}
```

Methods (all loopback-authenticated):

- `POST /api/historical/synthetic-filings` accepts only normalized JSON synthetic-fixture records and returns a source hash and immutable revision metadata.
- `GET /api/historical/filings?tax_year=2024` displays normalized synthetic records, ordered by kind/revision.
- `GET /api/historical/wealth-continuity?tax_year=2025` checks previous TY closing vs current TY opening.
- `GET /api/tax/opportunities?tax_year=2025` lists nonbinding *evidence-required* category candidates, no savings.

## Tests and risks

Regression tests cover authenticated upload, file idempotency, cross-year continuity and explicit zero, revision lineage, invalid fields/types, missing keys, key-independent tamper detection, authenticated-data binding, protected paths, and conservative opportunity hints. Synthetic records only. **Code in this stage is not certified for financial-data use.**

## Next priority (M2b)

1. Replace `Base.metadata.create_all` with explicit Alembic migrations and PostgreSQL integration tests, migrate safely from local prototype; protect structured financial fields at rest.
2. Implement private access with MFA and TLS, encrypted file/document storage lifecycle, secret rotation, full audit logs, and encrypted backup/restore drills. Keep public repo strictly synthetic.
3. Add real PDF adapters against synthetic bank/FBR layout fixtures, with parser provenance, tamper, sandbox and failure-closed checks.
4. When security and import format gates pass, ingest owner's 3–4 previously filed returns *through the application* and reconcile with bank/wealth history; do not rely on uploads into GitHub.
5. Verify TY2023+ applicable tax provisions, and independently test every deduction/credit/withholding treatment before calculating actual tax savings.
