# Security and privacy requirements

## Sensitive data rule

**Never commit genuine bank statements, financial transactions, account identifiers, NTN/CNIC, IRIS credentials/PIN, income/wealth declarations, tax certificates, bank passwords, customer identity details, personal contacts, secrets, access tokens or unredacted screenshots to GitHub.** Do not put sensitive source data in GitHub issues, PRs, CI logs, prompts or analytics. Use `samples/` for synthetic data only.

## Baseline for real data ingestion

- Dedicated private app and database; owner MFA, secure session and minimum privilege service roles.
- TLS in transit; server-side encryption at rest with restricted keys; encrypted originals and backups; segregated staging/prod.
- File encryption key separation and rotation; avoid sending raw documents to third-party models by default; AI opt-in with redaction; disable provider training where contractually available.
- Virus scanning/type validation; deny active content; enforce upload sizes; PDF parser sandbox/resource limits; audit import exceptions.
- Audit trail of financial changes, classified/verified sources and data exports; redact logs and errors.
- Access requests and deletion/export controls; clear retention plan referencing relevant tax records retention and any active legal hold.
- Tested recovery: encrypted backups, least-privilege restore, RPO/RTO target before production, periodic disaster recovery tests.
- No bank credentials scraping; user uploads statements. External integrations only with explicit user authorization and supported terms.
- No public app or search-engine indexing for private financial pages; CSRF/CSP/cookie hardening, secure cookies and rate limits.

## Threats to design against

Malicious PDFs and OCR injection; prompt injection in statement descriptions; account impersonation; IDOR/broken access controls; secrets in logs; double-counting or silently dropped imports; malicious AI-generated tax outputs; forged donation/loan data; compromised backup; broker API misuse; third-party price rights.

## Safety before any real documents

Do not process actual statements or tax docs until key management, access control, deletion and disaster restore basics are verified. For development, use anonymized samples after explicit owner approval and preserve a clear source boundary.

## Data retention

FBR publishes six-year retention of tax return records for relevant taxpayers; exact exceptions, pending proceedings and other duties need current legal verification. Store document retention policy per applicable data and purpose, not indiscriminately forever; preserve exported user copies and deletion capability subject to legal obligations.

## Source repository is temporarily PUBLIC (explicit owner instruction, 2026-11-15)

The public status is intentional to facilitate development, with a later planned move to private. It is **not** permission to publish actual financial data. Public repo may contain code, reviewed documentation, synthetic statements and synthetic tax fixtures only. Do not allow personal tax returns/wealth statements into Git, GitHub issues, CI caches/artifacts, workflow logs, PR comments, sample PDFs or screenshots. Use fake identifiers in tests and fixtures; verify no committed secrets. Keep real files in restricted application storage with encryption, MFA, access auditing, backup/restore verification and private networking as appropriate. Changing visibility to private at a later date does **not** erase any past public exposure.

Owner may provide 3–4 years' filed returns separately as conversational inputs to discuss, but full confidential versions should be processed by the secure application when ready. If supplied through chat for early analysis, minimize or redact personal identifiers and bank details; never upload, copy, paraphrase sensitive numbers into public GitHub. Application ingestion is **not yet implemented**; M1 SQLite prototype remains synthetic only.

## Current security implementation inventory (2026-11-15, synthetic only)

- M2b implemented authenticated AES-GCM encryption for *synthetic* historic filed-return structured values, plus encrypted synthetic SQLite/evidence archive recovery tests. **M1 transaction descriptions and audit notes remain plaintext in the development database**; a single encrypted column is NOT blanket financial data-at-rest protection.
- M2c introduced optional local HTTPS/synthetic owner MFA: scrypt credentials, RFC6238 one-time codes with persisted replay counter, secure hashed-token sessions, strict same-site cookies, CSRF validation and logout revocation. Default Basic auth remains only for local synthetic demo, and **no production account enrollment/recovery or multiworker rate limiting has been certified**.
- Until secured deployment, all-sensitive-field encryption, bank/FBR parser acceptance, off-site backup/restore, MFA recovery and independent security QA are demonstrated, `APP_DATA_MODE=real` MUST remain disabled/fail closed. No actual personal bank statements, filed returns or identity documents may be ingested or published.

## M2e data classification (2026-11-15)

Loan counterparty labels, opening-balance basis text and allocation/transfer evidence notes are encrypted using existing versioned AES-GCM keys; the synthetic key-rotation utility now traverses these tables. **Loan amounts, markup, dates, transaction IDs, account linkage, file hashes and other metadata remain plaintext** in the current prototype. Agreement existence/identity and FBR tax treatment are not independently verified. No actual taxpayer, lender, bank, or personal financial information is permitted in temporarily public GitHub, CI or the synthetic-only app. The real-mode startup prohibition remains active. Audited corrections and private secured storage are mandatory before onboarding real records.

## M2f audited reversal data (2026-11-15)

Each synthetic loan-allocation reversal or transfer revocation has an encrypted reason in a dedicated append-only audit row, with a separate active flag controlling derived principal and transfer linkage. The app does not delete original bank transactions or original confirmation records. This is still **not a tamper-proof external audit journal**, and bank amounts, dates, identity/linkage and metadata remain plaintext pending broader redesign. No real financial-data intake or production deployment authorized; `APP_DATA_MODE=real` remains blocked. GitHub remains temporarily public for synthetic engineering only.

## M2g synthetic cash privacy boundary (2026-11-15)

Cash holding labels, opening basis, cash movement evidence notes and append-only reversal reasons are encrypted with the existing AES-GCM key-ID envelope; source notes never enter GitHub. **Cash amounts, event dates, transaction IDs, and bank account linkages remain plaintext in the development database**. All cash figures are owner assertions or reviewed synthetic source relationships. No verified bank/FBR import, tax treatment or public-service access exists. `APP_DATA_MODE=real` remains fail-closed. Never upload personal cash ledgers, bank statements or previous returns to public GitHub/CI.

## M2i–M2l actual security boundary (2026-11-15)

- **M2i**: HMAC-SHA256 keyed bank import dedup IDs limit dictionary/guessing attacks against old raw hashes; does **NOT** encrypt original bank amounts/dates/metadata, and dedicated key changes require a controlled rebuild. `documents.digest_scheme` marks legacy records; no silent mixing.
- **M2j**: `pypdf` PDF extractor with strict synthetic marker/preflight/size and form constraints is not a production sandbox. Actual hostile PDF conversion must be an isolated resource-limited worker with malware and unsupported format controls, no network, and private encrypted source vault.
- **M2k**: new asset valuation snapshots are encrypted as a whole JSON envelope, including date, asset identity, quantity, cost basis, valuation and evidence. Existing legacy SQL bank/loan/cash monetary fields and relational IDs are **not encrypted**; no claim of full database protection.
- **M2l**: statutory rule metadata, synthetic salary bracket values and candidate references contain **no actual owner tax data**; all inferred eligibility/savings remain false/null. Prior filed returns cannot be ingested yet.
- The owner intentionally operates this GitHub repository PUBLIC temporarily for development; no real statements, tax forms, personal identities, secrets, unredacted screenshots or confidential records in source/CI. `APP_DATA_MODE=real` explicitly denies startup. Do not disable this gate without complete security QA and owner approval.

## M2m privacy boundary — 2026-11-16

New `private_financial_events` records store financial amounts, dates, source/account references and all accompanying information under authenticated AES-GCM. Queryable fields reveal random row IDs, ingestion timestamps and equality patterns via separate HMAC owner/year/source indices; confidential index HMAC key must remain independent of AES and original bank dedup HMAC. **Legacy bank/loan/cash tables still store plaintext financial numeric and date fields**, and actual file originals/production backups have not been certified. Privacy parity is NOT complete; do not upload real data. The public GitHub repository still contains only source/docs/synthetic fixtures. Key rotation and protected source migration require explicit backup, no-plaintext, rollback and audit review.

## M2o backed-up synthetic migration rehearsal — 2026-11-16

The new `synthetic_migration.py` CLI fails closed without separate AES/HMAC/backup secrets and an entire reviewed source scan, creates an encrypted and independently restored SQLite/evidence backup, then transactionally writes authenticated-encrypted private bank event mirrors ONLY inside a restored **new candidate**. It verifies source/count/debit-credit parity, rejects tampering/conflicts, and has test-injected rollback. Redacted receipt uses purpose-separated HMAC aggregates; the source remains untouched. **No real-data or production cutover is authorized.** Source and candidate still contain existing bank/loan/cash plaintext amounts, dates and relationship metadata; older fields are not encrypted just because a second v2 copy exists. Do not import actual tax returns, bank statements or user financial secrets. GitHub remains temporarily public by owner choice for synthetic source code only.
