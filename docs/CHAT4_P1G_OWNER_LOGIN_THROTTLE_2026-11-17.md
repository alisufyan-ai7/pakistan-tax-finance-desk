# P1G — Owner MFA login lockout rehearsal, separate parallel lane A

**Project:** Personal CFO · 17 Nov 2026 · after verified PR #109.

This is a **synthetic-only, unmounted** owner MFA authentication primitive. The public Railway Nginx, private `app.preview_api:app`, original Google OAuth client, exact registered callback and genuine records are untouched. No UI login route, real password, real folder or token is accepted. G1/G2/G3 remain BLOCKED.

## Independent deliverables
- Additive migration `0016_owner_login_throttle` and model keyed solely by distinct HMAC of **fixed fictional** owner identity.
- PostgreSQL advisory transaction lock + row lock serialize first insert, concurrent failures and lockout across workers; SQLite-only isolated tests use `BEGIN IMMEDIATE`.
- Five failed password/OTP/username attempts within 10 minutes cause 15-minute lockout, checked **before** expensive password hashing; successful scrypt+one-use TOTP returns a hashed 15-minute session and resets count. Failure counters are committed and preserved on rejection; no financial records or original data.
- Final exact-head CI must exercise adversarial replay, expiry, invalid flags, missing HMAC key, two-worker race and disposable PostgreSQL18 lockout, plus the existing full G1 source-schema and encrypted backup/restore parity.

## Remaining hard gates
No actual owner MFA enrollment/login/rate-limited HTTP endpoint, trusted reverse-proxy/CSRF audit, recovery, device/session management, distributed abuse prevention, separate production credential custody/rotation/restore or G2 security signoff. Lockouts can be weaponized as denial-of-service and real deployment must add audited rate policy and owner recovery; this is not production authorization.

This is independent of the **parallel P1H Drive cadence planner**, which creates no tables, sessions or grants. The two PR heads need independent CI, merge validation and a final combined-main regression. Main handoff and roadmap must distinguish code acceptance from real Google/finance access.

## Final CI acceptance — 17 November 2026

[PR #111](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/111) squash `db457a9d9af043fbd598401dcace5a22410c240b`, tested head `1c46cdf4bb9c677bc754274c5cde56b165898464`, [CI 44084144361](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44084144361): **685 backend pytest passed, 3 warnings; disposable PostgreSQL18 migration 0016, two-worker failed login lockout, complete G1 provenance/restore and G2 restricted roles PASS**. [Combined integration #113](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/113) **697 tests + PostgreSQL18 PASS**. Original test-fixture isolation failure was corrected before final acceptance. **No actual owner account or production MFA, real token, public login route or private Railway DB migration approval.** The private API code image was auto-redeployed at #111 merge and still starts `app.preview_api:app`; all real-data gates remain BLOCKED. [Full handoff](CURRENT_HANDOFF.md).
