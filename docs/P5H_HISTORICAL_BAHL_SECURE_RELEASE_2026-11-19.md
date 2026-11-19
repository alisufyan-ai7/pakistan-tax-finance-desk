# P5H — Historical Bank AL Habib report: private release acceptance

Date 2026-11-19. Scope: one owner, existing Google Drive read-only folder, historical bank statements only.
Tracking: issue #222, source-byte preflight PR #213, source reconciler #215 and #220, private strict controller #223, mobile/desktop integration PR #224, encrypted document comments #214/#217.

## What is implemented
- On-demand, server-selected pinned-folder original bytes, with SHA-256 and revision/filename HMAC checks; never edit the source or search beyond the approved folder.
- PDF and password processed in a bounded, separately invoked worker, password provided only through private HTTPS POST JSON to the MFA/CSRF owner controller. No passwords in URL, GitHub, logs, SQL, or browser storage.
- Private Documents screen lets the owner analyze eligible previously hashed BAHL statements; Accounts screen shows opening/closing historical balances, statement period, gross bank debits/credits and transaction count. In-memory browser view resets when sources are rechecked or owner session ends. Figures are not stored in static public assets.
- Claims remain explicit: historical_only is true; financial_values_verified is false; income, expenses, current available balance remain null; transfers excluded is false and complete account coverage is not established. No transfer or expense classification and no live ledger mutation.

## Independent activation gates, not yet approved
1. Backend: keep existing exact MFA and Google content OAuth review flags and source-verification pilot. Require P5E_OWNER_HISTORICAL_REPORT_PILOT, P5E_G3_ISOLATED_BANK_READER_REVIEWED, P5G_OWNER_HISTORICAL_HTTP_RUNTIME, P5G_G2_HISTORICAL_EXACT_INGRESS_REVIEWED, P5G_G3_PASSWORD_AND_SOURCE_ISOLATION_ACCEPTED, P5H_OWNER_HISTORICAL_BAHL_RUNTIME each set to 1 ONLY after independent signoff.
2. Frontend: P5H_BAHL_PUBLIC_INGRESS_ENABLED must remain 0 until exact proxy route, rate limits, zero-sensitive request logging, trusted host/headers, no-query POST, no-cache handling, origin, CSRF and MFA have been accepted. No wildcard finance route.
3. Important: the BAHL subprocess is a resource-bounded PDF parser, not an independently audited OS-level no-network/malware sandbox. Validate containment, authentic layouts, password-failure paths, parser timeouts and safe memory/log handling before G3 signoff.
4. Verify exact-head GitHub synthetic Python + frontend CI and Railway frontend/backend terminal SUCCESS; then perform authorized owner-only smoke tests against known originals without uploading any actual values into GitHub.
5. Fail-closed rollback is to disable the P5H runtime and edge flags; preserve existing source/original/grant data. Never make a bank current-balance claim from a historical statement.

## Parallel work still needed
- The append-only encrypted document-comment schema 0024 requires independent off-device encrypted backup, disposable restore and migration-role/least-privilege acceptance before P5B/P5D activation. Local key/snapshot verification alone does not meet this.
- Transaction-level comment targets require stable source-backed transaction identities and separate reconciliation states; current P5D UI supports document comments only and never automatically resolves a financial ambiguity.
- P5A source hashes are currently ephemeral. Implement versioned encrypted durable source manifest, new/changed/removed-file detection, safe full-inventory refresh and owner-review queue.
- Multi-bank transfers, monthly living costs, recurrent bills, investments, net-worth, tax-year-2026 accountant draft and filed-tax proof need additional adapters and source-independent finance validation. Gross credits are NOT automatically income and debits are NOT automatically expenses.
- Google reauthorization is not a routine blocker if the saved content scope grant is valid; if revoked or expired, use the private existing Google consent UI.
- A separate organized COPY folder is out of scope and needs future distinct write permission; original approved Drive folder stays immutable.

No account numbers, personal values, owner passwords, real source text or tokens are stored in this document.
