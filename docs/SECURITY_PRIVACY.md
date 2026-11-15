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
