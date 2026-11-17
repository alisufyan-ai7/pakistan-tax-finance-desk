# Chat 04 / Issue #110 — isolated fake-only owner login HTTP candidate

**Date:** 2026-11-17. **Base:** verified #113 (697 synthetic tests + PostgreSQL18 PASS). This branch changes only a new unmounted backend ASGI module/tests and this focused documentation; no tables, migrations, frontend Nginx, public endpoints, or Railway settings.

## What is included
- Standalone `create_fake_owner_login_http` app, intentionally **not imported by** `app.preview_api`. Narrow private HTTPS Railway Host path contract: POST `/internal/drive/auth/login`, GET `/internal/drive/auth/session`, POST `/internal/drive/auth/rotate` and POST `/internal/drive/auth/logout`.
- No token or password appears in a response or URL. Only fictional `synthetic-owner` credentials are accepted by the existing durable PostgreSQL multiworker five-failure throttle with scrypt and one-time TOTP; response sets host-only `__Host-` Secure/HttpOnly/SameSite=Lax 15-minute cookie. Exact Origin on mutations, session-specific CSRF on rotate/logout, short JSON body limit, no API docs, no wildcard host/proxy or real Google.
- Explicit feature flag `P1G_FAKE_LOGIN_HTTP_CONTRACT_ONLY=1`; all existing `P1G/P1F/P1E` fake gates and `APP_DATA_MODE=synthetic` must also pass. Standalone test-client verifies lockout, malformed body, spoofed Host/proxy, HTTP, CSRF replay, session rotation/revocation, no public preview route and real-mode denial.
- No real session is ever provisioned in Railway; this is a **contract rehearsal**, not production owner identity.

## Pending acceptance and release blockers
- No genuine owner enrollment, separate credential encryption/rotation/restore, device revocation registry, recovery, distributed abuse/DoS mitigation, audit/logging/CSRF infrastructure or trusted Railway reverse-proxy review. Session rotation and fake lockout are NOT full G2 production security.
- No actual public callback route, Google consent, scheduled Drive scanner, original files or financial reconciliation. G1/G2/G3 remain BLOCKED. New provider/cost or live Railway secret/network changes require separate owner-scoped approval.
- Exact-head full backend pytest and disposable PostgreSQL18 workflow are required, followed by independently validated parallel merge/integration. GitHub `main` and latest handoff supersede historical notes.
