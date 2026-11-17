# Chat 05 — parallel G2 recovery, owner Google OAuth, and credential-role continuation

**Checkpoint:** 18 November 2026 (Pakistan local date).  
**Canonical repository:** `alisufyan-ai7/pakistan-tax-finance-desk`, default `main`.  
**Scope:** owner-approved Personal CFO project only; this is NOT a production release, Google consent or financial import.

## Why this checkpoint exists

The owner directed immediate parallel implementation and offered to act on any genuine owner-side blocker. We are **continuing Chat 04** rather than recreating context. The previous GitHub `CURRENT_HANDOFF.md`, approved six-priority roadmap and original owner decisions remain binding. The complete earlier conversation is not necessary for engineering when GitHub has verified handoff and evidence.

The owner already completed Google's Web OAuth setup, exact Railway HTTPS redirect, the folder-owning account as external test user and metadata-read-only scope. The single sealed `P1C_GOOGLE_CLIENT_SECRET` was previously staged on the approved private Railway API, **not applied**, and must not be pasted to chat. No new Google project, callback, additional Drive folder or account is needed.

## Independent source-safe PR tracks

| Priority | Engineering lane | Evidence and release distinction |
| --- | --- | --- |
| #133 P1S | [PR #135](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/135) strict credential PostgreSQL role attestation | **MERGED** squash `2ca8f90ebef2a9839e0b1a142e6345a289f0cad1`; exact-head [CI 44156140867](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44156140867) **SUCCESS**. Read-only default-off audit denies financial/column/sequence access, role inheritance, CREATE/TEMP and unapproved destructive privileges. **Not** a live Railway role grant, key-backup or complete G2 acceptance |
| #131 P1Q | [PR #134](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/134) independent signed offline MFA re-enrollment | **MERGED** squash `ff1f9a593df66aa87126c2dd0ca16553e9a41d3c`; [CI 44157530578](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44157530578) **SUCCESS**.  one-time recovery hold-release tied to signed Ed25519 operator proof, new TOTP, current encrypted/audited recovery revision, prior-code invalidation and all-session revocation. Additive migration `0021_private_reenrollment`. **Validated in disposable PG18, not live identity activation**. Not a public login, UI, live MFA enrollment or Google network action |
| #132 P1R | [PR #137](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/137) real-compatible encrypted session-bound OAuth state | Clean rebase on merged #134; supersedes closed-unmerged #136. Separate 10-minute AES-GCM/HMAC OAuth state with a persistent owner session binding, strict scope/folder/client, mutation CSRF and transactional single-use callback claim. Additive migration `0022_private_oauth_attempts`, linearly after merged #134's 0021. **Subject to exact-head CI/merge**, unmounted; no Google token exchange or live callback |

A failed test run is not accepted as success. Initial #134 CI runs disclosed SQLite CHECK-alter incompatibility, then two old tests with hard-coded schema revisions; changes to use Alembic batch mode and update revision assertions were committed for re-test. This is ordinary source-compatibility work and **not** a reason to bypass or weaken security tests.

## Mandatory next serialization after source-side parallel work

1. #134 exact-head CI/PG18 **passed and merged**. Verify no live owner recovery was activated.
2. Finish clean-main #137 exact-head regression/PG18, including full-source encrypted backup census and one-time PKCE race, and merge only when green. #136 is closed without merge as superseded. Keep shared schema revisions linear.
3. Implement and accept a **private** owner HTTP login/session/recovery interface, independently verifiable operator MFA signing/key custody, and correctly trusted Railway edge/forwarded TLS/Origin/CSRF/Host/rate/log boundary. Do not expose public wildcard `/api/*`.
4. Provision a **dedicated real restricted PostgreSQL credential role** and separately versioned strong keys only after a recorded migration/backup-first plan, independent encrypted restore/key-loss recovery and owner-scoped live authorization.
5. Independently audit actual Railway/Nginx/private upstream/edge handling of OAuth query/code/state/cookies, no sensitive logging; separately apply the existing staged sealed client secret and perform an interactive owner Google consent only after G2 acceptance. Keep `APP_DATA_MODE=synthetic`.
6. Verify the existing one private folder via Google metadata-only API; implement bounded complete pagination/cursor heartbeat, scheduled app sync and authenticated mobile Documents review. Real original contents still wait for G1/G3 certification.
7. Continue independent safe financial canonical authority, actual format adapter and accountant/evidence work, without claiming real figures before verified source intake.

## User action policy

**No immediate Google Cloud action or secret disclosure needed.** The development agent performs source/test/CI work without waiting on the owner. At the narrowly scoped live gate, the owner may need to approve private deployment/migrations/key restore, enroll password and authenticator through a secure private interface (never send password/seed/code to chat), and personally complete Google consent. Provider changes, new paid resources or public financial-data exposure are not preapproved.

## Production truth and unchanged boundaries

- Source code may be merged and the existing Railway preview image deployed, but **neither CI nor a code-image build means production G2 approval**.
- Public GitHub contains only synthetic fixtures and general engineering code/docs. Existing private real financial records, identity details, folder ID, exact filenames, client secret, TOTP seeds and recovery codes do not belong here.
- G1 full confidential authoritative financial cutover, G2 operational private identity/key/recovery/callback and G3 certified owner bank/FBR original parsing all **remain BLOCKED**.
- One unsorted owner-private upload folder, mobile-first installable PWA financial pulse, source-backed accountant/tax continuity, lawful year-specific savings, and no additional paid provider remain fixed goals.

**Continuity:** update this checkpoint and `docs/CURRENT_HANDOFF.md`, `docs/PROJECT_STATUS.md`, root `AGENT_START_HERE.md` after each actual verified merge. Open issues #98, #126, #131–#133 remain authoritative for unfinished production work.

## Additional independent owner login gateway slice

[PR #138](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/138) adds a separately instantiated, nondeployed, default-off private owner-login/session/logout FastAPI gateway. It uses P1N scrypt/TOTP with 15-minute Secure HttpOnly SameSite=Lax cookie, CSRF/Origin, shared internal-gateway proof and strict proxy/request bound; no financial or OAuth routes. **Merged** via [PR #138](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/138), squash `e9f274656657526768ca49680a824c50b562c7f3`, [CI 44159992853](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44159992853) **893 tests + disposable PG18 PASS**. The real Railway ingress and actual owner authenticator enrollment remain explicitly unapproved. The public preview still does not mount this gateway.
