# G3 real Pakistani bank/IRIS format certification — private acceptance boundary

**Status (2026-11-17): NOT CERTIFIED / G3 BLOCKED.** This source-control document contains no owner originals, account numbers, passwords, private PDF text, workbook cells, fingerprints of owner files or tax return amounts.

## Why engineering alone is not certification

The existing Docker synthetic parser can reject active PDF objects and hostile OOXML structures, but a successful disposable CI run cannot authenticate *genuine* export layouts, identify all bank-specific statement variants, prove opening/running/closing balance continuity across owner source documents, or verify a filed FBR/IRIS tax return. Real-file processing needs an **explicitly approved private environment**, restricted owner MFA, encrypted immutable originals and independent recovery. The current public GitHub, its GitHub Actions, and the public Railway synthetic preview are not that environment. Do not copy user-provided files into any of them. Do not enable `APP_DATA_MODE=real` in the existing application.

## Acceptance requirements by source kind

| Source | Mandatory private evidence | Unsupported / quarantine rules |
|---|---|---|
| Bank statements: PDF, CSV, XLSX | Reviewed exact institution/layout/version, account and legal owner binding, declared date range, opening and closing balance, every row's debit/credit direction and running-balance equality, page/row provenance, overlapping imports/dedup and reversals, source reference to canonical encrypted posting | Any guessed institution, unknown file variant, unbalanced row, duplicate/overlapping period, truncated PDF text, missing opening balance, password stored in logs, worksheet formula result used without review |
| IRIS income return PDF | Reviewed year-effective identity, tax year, return metadata, source-wise salary/business/investment/withholding claims, source-page provenance, clear separation of accountant **DRAFT** from *filed claimed* and independent official FBR filing acknowledgment | Treating a DRAFT as filed, deriving tax due from an unverified screenshot, mixing tax years, owner IDs or return revisions |
| IRIS wealth statement PDF | Reviewed original owner/tax year, source page provenance, asset/liability/loan/cash and capital movement schedules, opening-to-closing wealth roll-forward and consistent linked banking/loan/asset evidence, official FBR acknowledgment where claiming filed status | Implied net worth from unlabeled bank movements, double-counted inter-account transfers, missing source or fiscal period |
| Accountant Excel working paper | Read-only, macro-disabled parsing, external link/formula quarantine, exact cell/formula provenance, draft/final distinction, tax-year rule evidence, independent accountant confirmation | Executing VBA, refreshing external links, trusting cached formula output as official FBR evidence, importing an unfinished tax workbook as final |

## Private approval and evidence package, in order

1. Owner explicitly approves **the exact Personal CFO private resource and scope** for processing originals; confirm encryption keys, tenant isolation, access roles, TLS, MFA, risk acceptance and restore target. Existing deployment/public CI do not inherit approval. No new provider or paid resource without owner consent.
2. Independent security review confirms pinned worker image, dependencies/security advisory fixes, network denial, OS isolation, cgroup limits, malware scanning, MIME and PDF/OXML content type quarantine, no public backend route or raw stderr. Current synthetic Docker checks are necessary but not sufficient.
3. Encrypt original bytes before persistence; store only in an owner-approved immutable private vault; keep PDF password only transiently and never in the repo, application logs, PR discussions or GitHub Actions. Back up/restore with separately verified recovery keys and test deletion of scratch.
4. Two independent private reviewers validate each exact bank and FBR document-layout version with multiple positive AND negative originals (different dates, page counts, reversals, missing balance, password/scan and malformed files). Keep page/row/cell provenance and deterministic source identity inside the private vault, not public code.
5. The import candidate remains **pending owner review** until all bank account×year funds, loan/cash/asset/withholding/FBR claims reconcile without double count and corrections have an immutable audit trail.
6. A signed private acceptance record stores layout revision, source evidence identifiers (HMAC only inside private vault), reviewer proof, parser/image digests, scanner results, validated range, filed/DRAFT status and rollback drill. No self-declared checkbox may produce a public *certified real source* result.
7. The actual application may be promoted from `APP_DATA_MODE=synthetic` only through a separately designed and independently accepted G1 authority cutover, G2 owner MFA/least-privilege/recovery, and G3 certification. A developer PR or successful CI alone never authorizes that switch.

## Verified parser dependency note (2026-11-17)

The public Python `pypdf` dependency previously permitted older vulnerable versions via `>=5.9,<7`. The new requirement is **`>=6.18.1,<7`**, above the fix for malformed `/FlateDecode` decompression denial of service, [CVE-2026-102997](https://nvd.nist.gov/vuln/detail/CVE-2026-102997), with a regression test. This does **not** certify the image is free of other vulnerabilities. Review images and complete vulnerability scans in the private environment before any real original is permitted.

## Current unblockers

- G1 encrypted full financial authority + backup-first independent rollback/plaintext retirement acceptance still BLOCKED.
- G2 actual owner-scoped MFA, private restricted role, monitoring/rate limiting and offsite/PITR restore still BLOCKED.
- G3 independent private sandbox + immutable vault + authorized real bank/FBR/Excel originals and complete source-version certification still BLOCKED.

**Accept only fictional synthetic input in existing CI.** `backend/app/private_format_release_gate.py` reports missing independent controls but intentionally cannot grant real certification, even if every checkbox is claimed complete.
