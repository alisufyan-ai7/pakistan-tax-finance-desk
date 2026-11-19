# P5I — Complete original SHA source-scan planner (synthetic-only)

19 November 2026. Parent [#219](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/219), [Chat 8 release handoff](CHAT08_RECOVERY_AND_NEXT_ENGINEERING_2026-11-19.md). **This first independent implementation slice is never imported into a live HTTP controller or the existing source hash endpoint.**

## Implemented in this slice

- `backend/app/private_source_sha_scan_plan.py` consumes one **complete** fake metadata inventory plus an exactly matching set of separately generated verified-byte-hash HMAC receipts. It never accepts file IDs, names or PDF bytes through an untrusted browser. The owner-pinned folder HMAC must match the existing configured Drive pin; `APP_DATA_MODE=synthetic`, explicit fake-only feature flag and approved-fixture boolean are mandatory.
- It rejects duplicate source identities/receipts, wrong folder, stale revisions, unverified or missing receipts, extra receipts, incomplete pages and malformed prior state before returning any planned change. Existing last-good persistent state cannot be mutated because this helper has **no SQL or provider access**.
- Its proposed all-blinded state distinguishes NEW, changed actual SHA HMAC, metadata revision, rename, missing, historical still-missing, reappearance and identical replay. A provider MD5 hint cannot masquerade as a verified source SHA.
- Fake-only regression tests use deliberately fictional Drive records and content HMACs. No genuine owner statement, password, amounts or OAuth secret is in the repository.

## Deliberately NOT implemented / not released

- The planner trusts `byte_hash_verified=True` provenance supplied by a future **trusted** server-side pinned Google reader; it does not independently recalculate SHA256. The current P5A batch preflight can generate blinded receipts but is not yet a guaranteed all-files complete snapshot pipeline.
- No private PostgreSQL table, encrypted source manifest, schema migration, durable original SHA persistence, crypto key rotation, independent backup/restore acceptance, credential grant query, real Google network call, quarantine, manual refresh integration, timer, scheduler, parser, real financial posting or user-visible status is implemented here. Do **not** set any P5I or P5E/P5G/P5H/P5D runtime activation flag on account of this PR.
- Failed/password-protected/oversized original files require a later, independently reviewed quarantine and explicit retry record. Until that exists, an unreadable source makes this strict plan **fail closed** instead of pretending the folder snapshot was fully hashed. A removed file is a historical missing record, never a Drive delete command.

## Next independent acceptance

1. Build an owner-scoped encrypted `content_hmac` versioned source manifest using a reviewed additive migration and least-privilege role; atomically commit only after complete Google inventory, valid latest-revision receipts and source ownership. Preserve last-good on errors, cursor exhaustion, key/consent failure or mutation races.
2. Add a separate retry/quarantine state for files that cannot yield verified hashes, with honest coverage state; do not mark a partial scan as complete. Bind verified original Google source network reader to private MFA/CSRF endpoints, no user-supplied Drive IDs.
3. Prove full backup + independently disposable PostgreSQL restore including source manifest and owner grants; only after security review may add an owner-triggered refresh. A bounded scheduled refresh is later.
4. Use completed source generations to prevent duplicate transactions/reconcile revisions; the source SHA is **not** proof of money, spending, income, or tax. Continue independent G3 PDF isolation and bank adapter certification before genuine financial figures.

**Security policy:** original approved Google Drive folder is immutable and read-only, and tests must remain synthetic. This module is safe to merge as inert source-only preparation but is not a production activation approval.
