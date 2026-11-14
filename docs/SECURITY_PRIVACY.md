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
