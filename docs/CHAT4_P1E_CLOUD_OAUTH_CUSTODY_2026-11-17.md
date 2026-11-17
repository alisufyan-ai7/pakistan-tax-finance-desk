# Chat 04 / Priority 1E — guarded cloud Google OAuth custody rehearsal

**Date:** 17 November 2026  
**Owner instruction:** Continue from merged PR #107; keep the **entire current project context, decisions, status, security limitations, tests and handoff** durable in GitHub at every meaningful milestone. GitHub `main` and the latest `docs/CURRENT_HANDOFF.md` remain the authoritative current checkpoint. Historical milestone documents remain historical, not misleadingly rewritten as if their test counts were current.

## Source of truth and owner-approved direction

- Repository: `alisufyan-ai7/pakistan-tax-finance-desk`, temporarily **PUBLIC for synthetic source only**.
- Existing authorized Railway resource: `personal-cfo-dev-sandbox` / `development`, frontend preview, private preview API, private PostgreSQL. **No additional provider, new paid resource, live secret/role/network change or real financial upload is approved by this milestone.**
- Existing dedicated Google Cloud OAuth client and metadata-only permission `drive.metadata.readonly`; owner already registered **only** exact frontend HTTPS `/api/drive/oauth/callback` and removed localhost. Never copy client secret, client ID, private folder ID or filenames into source, issues, logs, CI or synthetic Railway.
- Owner puts unsorted past/future originals in **one private Google Drive folder**; app must do virtual classification/duplicate/version/follow-up work. No original moves or deletes. Backblaze B2 deferred.
- Priority list, ordered: (1) Drive folder intake; (2) actual bank/FBR/accountant document certification; (3) encrypted canonical financial authority; (4) cross-cutting owner MFA/private recovery; (5) tax/accountant reconciliation; (6) mobile PWA with real source-backed financial pulse. G1/G2/G3 cannot be bypassed in rank order.
- The owner expects a PWA with clear, source-backed account coverage, current-month spending changes, recurring bills, investments/return timing, outstanding follow-ups, wealth, FY tax and distinction between an accountant DRAFT and an official filed return. Missing evidence remains UNKNOWN, not zero.

## P1E implementation scope

This tranche adds **only a synthetic/test-only PostgreSQL custody rehearsal**, behind `P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY=1`, `P1D_RAILWAY_CALLBACK_CONTRACT_ONLY=1`, existing OAuth-contract and synthetic-mode guards. It refuses authentic Google OAuth client IDs, real folder IDs and refresh tokens even when enabled.

1. Migration `0015_drive_cloud_oauth_custody` adds dedicated `drive_cloud_oauth_attempts` and `drive_cloud_oauth_grants` tables, separated from the legacy financial ledger and existing synthetic Drive inbox.
2. AES-256-GCM stores PKCE-verifier and fake refresh grant inside domain-separated authenticated envelopes with an **independent vault encryption key**; SQL-visible state identity is HMAC-blinded with a **distinct HMAC key**. No raw state, verifier, fake token, original folder ID or client registration in SQL columns.
3. One-time consent attempts expire after 10 minutes; an atomic transaction/row lock and PostgreSQL advisory lock serialize simultaneous claims; consumed attempts replace the verifier with a tombstone. Replay, expiry, ciphertext tampering, wrong key, wrong folder/client, absent flags and genuine token formats are denied.
4. Fake-only scope-bound grants can be stored/recovered and revoked in tests; no real access token, OAuth consent or Google API request is sent. SQLite access exists **only for isolated unit tests**, not the Railway runtime.
5. The GitHub Actions backend job performs actual *ephemeral* PostgreSQL 18 migration + fake two-worker concurrency and encrypted-row checks; no live Railway database, original Drive item, public callback, deployed cloud keys, persistent live token or finance import is touched.
6. The public preview remains restricted to the existing fictional status route; `APP_DATA_MODE=real` remains prohibited.

## Explicitly not done / next tasks

- **NOT** an actual cloud OAuth handler, owner sign-in, Google refresh-token vault, real API permission, owner consent, scheduled metadata sync or real Documents queue.
- **NOT** independently accepted MFA/recovery/rate/device/CSRF TLS/cookie controls, least-privilege private runtime credentials or offsite encrypted restore.
- **NOT** authorization for private original bank/FBR/PDF/Excel contents, genuine format certification, effective FBR tax conclusions, verified wealth or actual owner finances.
- **Next P1E secure implementation:** design the separately isolated *real* vault key lifecycle/roles and authentic owner MFA/session binding; build a strictly exact-route callback gateway on existing Railway frontend with anti-replay and privacy-safe logging; add a scheduled one-folder metadata worker and mobile private review status only after owner-scoped live approval and independent G2 review. Keep disabled by default until this is verified.

## Evidence and continuity procedure

This milestone is not complete until the exact-head backend CI run (including PostgreSQL 18 and new race test) is successful and its PR is squash-merged; then record the **actual** PR number, head SHA, run URL, pass count, merge SHA, risks and next task in `docs/CURRENT_HANDOFF.md`, `docs/PROJECT_STATUS.md`, `AGENT_START_HERE.md`, the ordered roadmap and Issue #98. Each future chat must review current `main` and current handoff before changing code, and commit source-safe status after every implementation milestone. Never substitute an old conversation transcript for the committed handoff.

## FINAL VERIFIED implementation and integration acceptance — 17 November 2026

**[PR #108 MERGED](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/108)**, squash `59aadc02297a5615f717abffd9bdb30722058147`, exact tested head `5ad97b5e2aee8bd26e45e924d5ea1b6d6bfc3939`, [GitHub Actions 44073123421](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44073123421): **659 pytest passed, 3 warnings; PostgreSQL18 migration/schema, fake OAuth atomic two-worker claim, AES-GCM ciphertext custody, backup + independently restored parity, G1 A8 clone rollback, G2 recovery and restricted-role acceptance all PASS**.

GitHub Actions verified all **659** synthetic Python tests and real disposable PostgreSQL18 migrations/operations, including `POSTGRES_18_P1E_FAKE_CLOUD_OAUTH_ATOMIC_CUSTODY=PASS`, encryption, real two-session same-state race, G1 source/inventory key parity, restored-clone SQL TEMP rollback, independent encrypted backup restore, recovery-code race and restricted synthetic preview role. Initial CI heads failed closed because hardcoded legacy schema inventories, an intentionally strict candidate parity guard and an outdated candidate-table count needed explicit review. These were brought into the reviewed census without relaxing financial authority. The final PR head passed; prior failed runs are superseded, not hidden.

**Current state:** synthetic fake vault only; no live Google OAuth start/callback/status, no genuine token stored, no real Drive file access, no financial source bytes, no owner MFA deployment and no Railway changes. New migration `0015` is source-code accepted in public GitHub and ephemeral CI only; it is **not** approval to apply it to the existing Railway production/private real-owner PostgreSQL outside separately authorized activation. Work may continue safely with synthetic tests. Next milestone requires independently G2-reviewed authenticated cloud handler and dedicated isolated real token lifecycle before touching Google consent or Railway service settings.
