# P1P · Private one-time MFA recovery and owner-session lockdown

**17 November 2026 · Issue #126, parent #110, follows merged P1N #127.**

The owner's existing Google Cloud Web OAuth redirect, Google test-user/folder ownership and restricted metadata scope have been verified. The owner's existing sealed Railway `P1C_GOOGLE_CLIENT_SECRET` is **STAGED, NOT APPLIED**. This is source-safe implementation with invented test credentials only.

## Delivered code (isolated, not mounted)

- `backend/app/private_owner_recovery.py` provides a **real-compatible** one-time MFA recovery bundle under **separate default-OFF** G2 flags and independently keyed 32-byte AES-256-GCM recovery encryption and HMAC keys (distinct from P1N MFA/session keys and P1M OAuth keys).
- Additive `0020_private_recovery` PostgreSQL migration adds two audit-census tables: `owner_private_recovery_states` (AES-GCM encrypted 8 high-entropy one-time recovery-code digests, pending hold, revision, expiry, row HMAC) and `owner_private_recovery_audit` (append-only revision, action, prior HMAC and authenticated event hash). No raw owner ID, password, code or TOTP seed in the database. G1 source census, encrypted backup/restore and exact schema test update from 33 to 35 ORM tables.
- Issue codes ONLY to an already valid P1N owner MFA session with valid CSRF token **and** a reverified password; replace prior codes atomically, display plaintext codes to a trusted private UI only ONCE. Existing synthetic recovery APIs are not reused or enabled.
- Redeem one code only after password re-verification, a separately documented **offline owner identity verification step** and atomic PostgreSQL row lock. On successful redemption, revokes **all** authenticated owner sessions and marks the account as `recovery_pending`. All P1N owner login and session verification now fail closed on pending/tampered recovery records, including when recovery keys are missing. The code is one-time, with complete authenticated audit/replay checks and no login/TOTP reset.
- Plaintext recovery codes, owner identity and passwords exist only transiently inside the private function and **fictional tests**. This code does not contact Google, load the owner's staged secret or expose a browser endpoint.

## Still NOT production approved

This stops **before** activating a recovered owner. A real lost-authenticator owner must complete an independently verified, operator-controlled **new TOTP enrollment and release from hold**; simply presenting the code+password does NOT mint a session, lift the hold or reset the authenticator. The caller's `independently_verified_offline_owner` boolean is only a caller contract: **not an independent proof of owner identity by itself**. G2 cannot be accepted until a secure owner recovery channel, TOTP re-provisioning, role separation, key backup/restore, web abuse throttling and live Railway TLS/log privacy are tested. In particular, do not directly mount or enable a public redemption endpoint or rely on the fictional SQL tests as user-device recovery proof.

The current public/frontend `frontend/nginx.railway.conf` remains synthetic preview only. The candidate P1O exact-route OAuth config is separately reviewed, not deployed. No real OAuth state/PKCE private callback or Google consent is active; G1 encrypted finance ledger and G3 original format certification remain BLOCKED. [Full handoff](CURRENT_HANDOFF.md), [P1N owner identity](CHAT4_P1N_OWNER_IDENTITY_MFA_2026-11-17.md), [G2 issue #126](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/126).

## Verification

CI and merge status are **PENDING at author time**. Exact-head full backend pytest, disposable PG18 one-time replay/hold and G1 backup/role parity must pass before any merge. Public GitHub contains no real password, Google secret, folder ID, owner email or financial data.

## FINAL independently accepted P1P code-only proof

[PR #129 merged](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/129), squash `d91f2f52f5eadd4b8b4a6a1448df94f7dcbbdd25`; [GitHub Actions 44147806594](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44147806594) **853 backend pytest (3 warnings) + disposable PostgreSQL18 one-time recovery/lockout, G1 backup and G2 restricted-role PASS**. No public reset. Redemption revokes all owner sessions and **holds** account: it cannot log in, silently reset TOTP or release the hold. Independent private verified device enrollment/real operator review remains required. [Combined #130](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/130) tests recovery hold with OAuth custody still disabled; genuine G2/finance G1/G3 gates remain BLOCKED.
