# P5D — Financial ambiguity review and evidence roadmap

Status: `P5A` source-byte SHA-256 pilot, `P5B` encrypted comment custody and `P5C` Bank AL Habib layout candidate are merged. `P5D` is the reviewed, **default-disabled** owner-only UI/API bridge, not a claim of active real financial totals.

## Owner-approved behavior

- The approved Google Drive folder is **read-only**; no existing file is renamed, edited, moved, shared or deleted.
- The source reader uses the existing owner Google read-only-content grant, full single-folder inventory, version checks and bounded source bytes. Authentication uses owner MFA, CSRF, restricted private gateway, exact no-log reverse proxy and pinned source HMACs.
- Owner comments are append-only AES-GCM ciphertext and HMAC integrity-checked records in `owner_financial_review_comments` (Alembic revision `0024_review_comments`). No owner note, raw account ID, source filename, OAuth token, password or money amount is placed in public GitHub fixtures.
- For each private approved-folder document that appears in the bounded SHA preflight result, the UI can show **Your comment or clarification**, Save comment and View comments **only after secure schema/ingress acceptance**.
- Saved notes are always `PENDING_EVIDENCE_RECONCILIATION`. They do **not** modify source originals, post cashflows, clear anomalies, certify transfers, or change figures automatically. A separate reconciler must test notes against trusted evidence before proposing any classification decision.
- Current P5D interface permits **document** subjects only. Do not expose transaction-specific note endpoints until stable, authenticated and owner-bound source transaction IDs exist and have been verified.

## Deployment and release dependencies

1. Protect and independently verify an encrypted owner database backup, including owner identity, recovery and grants. Test a disposable restore and confirm the exact schema + least-privilege DDL role. Do not use automatic application-startup migrations.
2. Apply additive migration `0024_review_comments` using the approved migration role. Reattest schema, secret key continuity, single owner and recovery. Verify backup and restore remain complete with the new table.
3. Review the exact source/owner route contract, strict Origin and CSRF, append-only/owner isolation, no sensitive logs, privacy and rate limits.
4. Only then consider setting `P5B_OWNER_REVIEW_COMMENTS_ENABLED`, `P5B_G2_PRIVATE_REVIEW_ENCRYPTION_ACCEPTED`, `P5B_G3_FINANCIAL_REVIEW_SCHEMA_ACCEPTED`, `P5D_OWNER_REVIEW_HTTP_RUNTIME` and `P5D_REVIEW_PUBLIC_INGRESS_ENABLED` to 1 in the appropriate backend/frontend services. All are default off until explicit acceptance.
5. Sign in with MFA and verify GET review/status, POST comment and history on an **approved** document, wrong-owner/invalid-HMAC/CSRF denial, XSS-safe text display and secure read-only Drive. Revoke P5D flags if acceptance fails.

**Google reauthorization** is not needed simply to activate P5D when the existing read-only-content refresh grant remains valid. If the grant is absent/revoked, scope mismatched or refresh fails, show a private reconnect action rather than using the metadata scope for source bytes.

## Unfinished financial-accuracy gates (must not be described as shipped)

- P5A hashes are currently ephemeral: `source_hashes_persisted=false`. Build a versioned, encrypted, owner-bound source manifest with persisted SHA-256, incremental inventory/diff detection, complete snapshot atomicity, and safe scheduled/explicit refresh.
- P5C is a bank-specific **candidate**, not a fully accepted production PDF malware/network sandbox. Validate authentic statement layouts and other banks, original full-coverage period and arithmetic; prompt for missing PDF passwords **only in the owner private app**, never GitHub or chat logs. Protect sensitive temporary buffers.
- Store source-backed normalized economic evidence separately from owner notes. Reconcile transfers across owned accounts, credit card settlement, investments, tax withholding, duplications and opening/closing balances before labelling gross credit as income or gross debit as spending.
- Once stable verified transaction HMACs exist, introduce **transaction-level** comment queue and explicit review states (needs explanation, owner replied, checking evidence, resolved, still ambiguous) with immutable audit records. Comments must be treated as data, not instructions.
- Publish actual PKR figures only via a reviewed, authenticated evidence-backed reporting API, each with source, period, date of observation and confidence. Historical statement balances **must never** be presented as today's available balances. Accountant's TY2026 working workbook stays draft until verified with filed TY2025 return and underlying statements.
- The source-copy/organized-folder feature is separate and must use an explicitly authorized destination folder, retaining original hashes and source immutability; it is **not** enabled by the source-read grant.

## Code and acceptance

- `P5A` PR #213 and hotfix #216 — original-read proof and valid Nginx.
- `P5B` PR #214 — encrypted, append-only comments table + full backup inventory.
- `P5C` PR #215 — bank-specific statement reconciliation candidate.
- `P5D` PR #217 — exact private comments routes + owner-only PWA editor, synthetic CI.
- Existing roadmap: issues #98 (single-folder inbox), #185 (evidence-backed values), #186 (source-read/organized-copy scope), #183 (mobile/desktop owner dashboard).

No private source bytes, exact personal amounts, bank account numbers or document passwords belong in this document.
