# Priority 1A — Durable encrypted Google Drive document-review queue (synthetic)

**Master ordered roadmap:** [Six-priority Personal CFO roadmap](PRIORITIZED_PERSONAL_CFO_ROADMAP_2026-11-17.md). **Issue:** [#98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98). **Status:** code/test slice in development; not deployed or reading real owner documents.

## What this implementation does

- Adds **two additive database tables** (`0014_drive_inbox`) with HMAC-only SQL-visible identity and authenticated AES-256-GCM per-file review metadata. The owner-approved folder is pinned by a separately supplied HMAC; no raw owner folder ID, provider file ID or filename is stored in plaintext SQL.
- Accepts a **complete bounded synthetic one-folder metadata snapshot**, with no network calls or OAuth credentials. It atomically upserts the inventory and its keyed current-state checkpoint in **one transaction**. Replay of unchanged metadata is no-op and must not create duplicate items or scan counters.
- Tracks **new**, **changed**, **no longer visible**, **returned after gap**, **quarantined unsafe format** and **weak possible-duplicate** stages. A source that disappears or becomes inaccessible is **retained for owner review**, not deleted. Only the user uploads to the one Drive folder; the application never moves, deletes or renames originals.
- Provides a bounded, HMAC-only **review queue** and privacy-safe aggregate counters, not unverified money/tax facts. The queue deliberately has no owner name, statement filename, account number, original URL, tax return figures or credential.
- Cross-checks integrity of *every persisted row* and a keyed complete-state receipt before trusting a saved scan; fails closed for missing/deleted/tampered rows, wrong folder HMAC, incomplete provider pagination, duplicate file IDs, unsupported data or `APP_DATA_MODE=real`.
- New schema is included in Alembic, the full source inventory, PostgreSQL 18 encrypted backup/restore and ledger key-rotation contract. Existing financial SQL and the Google Drive account are unchanged.

## What this implementation does NOT do

It does **not** connect the owner's actual Google Drive to the Personal CFO PWA, install the optional Apps Script, poll the real folder, read/download actual PDF/Excel/source bytes, unlock source passwords, parse tax/financial records, infer income/expenses, store real bank data, or enable `APP_DATA_MODE=real`. The connected **ChatGPT** Google Drive plugin and daily metadata watch are separate. G2/G3 private original processing and G1 real data authority remain blocked, as documented in the master roadmap. No new Railway resource, billable service or Backblaze B2 setup is authorized.

## Verification required

- All new synthetic first/unchanged/changed/returned/missing/duplicate/quarantine cases in SQLite pass.
- Two separate synthetic clients scanning the same folder are serialized.
- SQL raw values are `TFLE1:` ciphertext for all source-specific review payloads, and only HMAC values are indexable.
- Deleted or altered encrypted rows cause the complete-state integrity check to deny review; a failed partial scan cannot commit a cursor or erase earlier evidence.
- **Real ephemeral PostgreSQL18 CI** confirms first scan, idempotent replay, changed/missing source and ciphertext while existing full G1/G2/G3 PostgreSQL recovery/role/parity checks remain green.
- Source schema migration and recovery revision verified; existing live Railway configuration and original Drive files untouched.

**Next Priority 1B:** behind separately authorized owner MFA/private credentials, build the actual Personal CFO app-side Drive OAuth and durable sync service constrained to the already owner-approved private folder, and a mobile review UI. Existing ChatGPT Google Drive connection does not grant those backend credentials. Do not start real-document content processing until genuine G2/G3 acceptance.

## Priority 1A verified completion — 17 Nov 2026

Owner-approved six-item roadmap [#100](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/100) was merged before beginning the next work. Priority 1 [#98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98) then advanced in [PR #101 MERGED](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/101) at `3869922c22b01761091c520527ba59b82cab37b6`. **Exact tested PR head** `1e76035e79acfeb16491bb68e93b02b3818c1cda`; [GitHub Actions 44047777376](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44047777376) **596 pytest PASS, 3 warnings** and actual ephemeral PostgreSQL18 `POSTGRES_18_P1_DRIVE_ATOMIC_ENCRYPTED_INBOX=PASS`, with G1 encrypted canonical journal, G1c original/source/candidate parity, G1 A8 rollback, G2 atomic recovery/two-worker replay/independent restore/restricted-role, and encrypted backup recovery all PASS.

Additive **Alembic `0014_drive_inbox`**: two tables `drive_inbox_items` and `drive_inbox_checkpoints`; SQL-exposed source/folder/revision identities are HMAC-only, per-source review metadata is AES-GCM encrypted, and a keyed complete-state checkpoint detects missing/deleted/tampered inventory rows. Synthetic-only bounded single-folder metadata snapshots are atomically committed, identical replay is a no-op, changed/missing/returned/unsupported/weak-duplicate items remain retained for review (never deleted), and a bounded privacy-safe review queue is available to internal synthetic tests only. No real owner file bytes downloaded or imported; no Google OAuth integration, real app polling, external endpoint, PWA review UI, financial figures or official FBR filing verification. Previous #96/#97 fake planner/optional not-installed Apps Script and the separate ChatGPT daily metadata watch remain distinct.

**P1 NEXT:** #98 B — approved restricted app-side Google Drive OAuth/credential custody and reliable one-folder incremental sync, review-queue phone UI, then G2/G3-cleared private original source verification and G1 ledger reconciliation. Do not use the public GitHub/CI or synthetic Railway environment for genuine originals and do not infer authority from the ChatGPT connector. Keep the owner's one upload folder unchanged, Backblaze B2 deferred and all G1/G2/G3 real release gates BLOCKED. More detail: [P1A design and tests](DRIVE_INBOX_PRIORITY_1A_ENCRYPTED_REVIEW_2026-11-17.md).
