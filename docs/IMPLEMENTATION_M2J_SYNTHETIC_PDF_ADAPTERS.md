# M2j — Synthetic bank and FBR IRIS PDF text adapters (strict preview only)

**Scope:** Code paths exercised with *made-up* text-first PDF fixtures. **No genuine bank-specific or current IRIS production layout is recognized or certified.** Real Pakistani banks differ by institution, export version, scanning, columns, headers, posting dates, reversals and statement balances. FBR forms differ by tax year and filing status; a PDF alone does not verify that a return was actually filed.

## Features
- PDF preflight: `<=512 KiB`, 1–3 pages, strict `%PDF-` header, rejects encrypted/interactive/JavaScript/attachment-style records, 24k extracted text cap.
- Explicit `TAXFIN SYNTHETIC BANK STATEMENT V1` marker and exact headers; strict dates, money formatting and running-balance verification using existing normalized statement parser.
- Explicit `TAXFIN SYNTHETIC FBR IRIS V1` marker and strict income-return/wealth-statement test fields, preserving NULL instead of zero, year >=2023.
- Authenticated **preview-only** endpoint `POST /api/documents/synthetic-pdf/preview` with `file` and `document_type=bank|income_return|wealth_statement`. It does not store or import the PDF, create ledger transactions, mark tax as paid, revise FBR returns or certify returns.
- Unit/API tests generate their own synthetic text PDFs. Unsafe/unsupported documents return controlled errors; **never guess an undocumented bank format**.

## Security gate before any real document
`pypdf` text extraction in the API process is **not** a sandbox. For actual uploaded PDFs, isolate conversion in a constrained process or container with CPU/memory/time limits, malicious-content scanning and no outbound network; add bank-specific parsers validated on the owner's redacted actual exports, FBR IRIS official return/wealth statement line item cross-checks, encrypted original document vault, MFA, full financial data encryption and tested recovery. Keep production upload disabled until those checks pass. No real files in GitHub or CI.

## Validation
Host CI (Python pytest + PostgreSQL18) and malformed/blank/encrypted/JavaScript fixture coverage required prior to merge. The parser is a foundation, not a complete real-document importer.