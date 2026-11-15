# M2s — synthetic bank CSV/XLSX source-signature preflight

**2026-11-16; G3 document-intake groundwork; synthetic-only.** Related: [Issue #29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29), [Issue #30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30), [release gates](DELIVERY_GATES_AND_RELEASE_READINESS.md).

## Engineering change

- New pure standard-library `backend/app/document_preflight.py`: input must be <=4 MiB and actually UTF-8 CSV or an OOXML ZIP workbook matching the supplied extension. A disguised PDF/legacy OLE XLS/HTML/XML/JSON download error is rejected for CSV, and arbitrary ZIP is rejected for XLSX.
- Before `openpyxl` reads a synthetic .xlsx, ZIP entries are inspected without extraction to disk: count, individual/total inflated size, abnormal compression ratio, duplicate/case-colliding names, path traversal, symlinks, encrypted/unsupported compression, embedded objects/macros/external links and unsafe relationships. Known unrecognized content is rejected, not reinterpreted.
- `backend/app/importer.py` calls the preflight as the parser iterates the source. Failure is an `ImportErrorDetail`, so the existing statement API returns a 422 and no accepted document/transactions.
- `backend/tests/test_document_preflight.py` has fabricated valid CSV/XLSX and adversarial package cases, plus an API no-ledger-mutation check.

## Limits and security boundary

This work is **NOT** a PDF/image converter, malware scanner, sandbox, password-unlocker, real-bank adapter or a production authorization. OOXML ZIP metadata is inherently untrusted; 4 MiB compressed limits and ~32 MiB aggregate expansion are a conservative defense layer, not a proof of runtime isolation. `openpyxl` stays local to the synthetic FastAPI process. Legacy `.xls` intentionally unsupported; a downloaded HTML/error page disguised as `.xls` is not imported. Password-protected PDFs, valid bank-specific layouts and multi-sheet accountant drafts still need isolated private pipelines and evidence review.

Active M1 bank/loan/cash money/date/linkage metadata remain **plaintext in the development source DB**. This update does not solve G1 confidentiality, G2 secure private deployment, G3 real bank/FBR acceptance or G4 full statutory tax. `APP_DATA_MODE=real` MUST remain fail-closed. Never put genuine statements, accountant workbooks, identifiers or opening passwords into public GitHub/CI.

## Verification and release gate

**Verified 2026-11-16:** [PR #32 merged](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/32) at `37625adfa3fbe5b88b9ff7d012aab77db292d5c7`; exact PR-head [hosted workflow 43769169270](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43769169270) **178 pytest passed, 2 warnings, ephemeral PostgreSQL18 migrations/no-drift PASS**. Previous M2r baseline was 153 tests. Valid synthetic openpyxl OOXML imports still work, suspicious/unrecognized or disguised formats fail before synthetic ledger persistence.

Run `cd backend && python -m pytest -q` for subsequent changes; independently verify the final `main` head after merged implementation. This preflight alone **does not permit actual financial uploads**, PDF handling or real-data deployment.

Next owner-independent G1 focus is replacing plaintext active legacy finance relationships with confidential canonical storage and testing PostgreSQL source migration/rollback. G2 MFA/private deployment and G3 isolated real-document adapters may proceed as separate slices. Earlier FBR documents are not needed for synthetic development.
