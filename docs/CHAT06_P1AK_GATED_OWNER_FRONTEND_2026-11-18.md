# P1AK — Default-off owner login ingress and mobile sign-in (Chat06, 18 Nov 2026)

## What actually changed (no owner login or Google consent activated by code merge)

The existing **public synthetic frontend** Nginx gained exactly three method-constrained, separately guarded owner MFA routes:

| Browser HTTPS route | Private Railway-only route | Method |
| --- | --- | --- |
| `/api/owner/login` | `/internal/drive/auth/login` | POST |
| `/api/owner/session` | `/internal/drive/auth/session` | GET |
| `/api/owner/logout` | `/internal/drive/auth/logout` | POST |

Each exact location returns HTTP **404** unless the operator separately sets `P1AK_OWNER_INGRESS_ENABLED=1`; even then it fails closed with **503** absent the 48+ character `P1Q_PRIVATE_GATEWAY_SHARED_TOKEN`, and backend P1AJ/P1AI/P1N/P1Q/P1S independent default-off G2 gates remain mandatory. Nothing is wildcard-mapped from `/api/*` to the private API. **Google OAuth start, callback, status, redirect/consent, original file media, finance and recovery operator endpoints are NOT added.**

The existing frontend server already sets `Cache-Control: no-store`, secure CSP, robots/noindex, anti-framing and Referrer-Policy. These new locations inherit those security headers rather than overriding them with partial local `add_header`. Sensitive routes disable local Nginx access logs and suppress request-target Nginx error logs at critical level; actual Railway edge/platform access/error logs remain **NOT independently accepted**, so this is NOT G2 public release authorization.

Per-request security: hardcoded expected HTTPS host and fixed private Railway service host, exact method, **no query strings** (the browser never forwards a Google code here), bounded 4 KiB request, 3-second connect/8-second read/5-second send, controlled proxy/request buffering, hardcoded `X-Forwarded-Proto=https`, all incoming Forwarded/original-URI/path override/IP headers stripped, incoming preview service token removed, and backend gateway proof replaced with the separately configured server-side secret. Never read/reuse browser-provided gateway header. Shared `http{}` rate zones limit login per gateway IP and impose a global owner-route ceiling (not a substitute for platform abuse controls).

Public `/owner-login` is also 404 until `P1AK_OWNER_INGRESS_ENABLED=1`; direct `/owner-login.html` is always denied. A mobile-first static owner page can then POST same-origin password+6-digit TOTP and sign out with in-memory CSRF, without username/multiple accounts, browser storage, third-party scripts, telemetry, URL tokens, Google sign-in or financial upload. It does NOT claim Google is connected.

The frontend Dockerfile allowlists only three new owner-login static assets and the reviewed Nginx rate-zone config, and extends `NGINX_ENVSUBST_FILTER` to precisely `PREVIEW_INTERNAL_TOKEN`, `P1AK_OWNER_INGRESS_ENABLED`, `P1Q_PRIVATE_GATEWAY_SHARED_TOKEN`. No secret literals or `ENV ...=1` enabling flags are committed. The existing backend `app.private_runtime_entrypoint` from P1AJ defaults to preview-only and requires separate reviewed live flags to mount just three owner handlers. No additional Railway services, Postgres databases or public original-file endpoints.

## Acceptance evidence and remaining work

- Frontend Node static suite plus new `frontend/tests/owner-login-gate.test.mjs`: exact route shape, default-off owner and direct filename, no Google public callback, dynamic gateway replacement, rate limits, all forwarded headers removed, CSS/CSP, no browser credential persistence.
- Full backend synthetic + disposable PostgreSQL18 integration CI (including updated live-frontend contract tests).
- **Before operator sets live ingress flag:** independently verify Railway public edge TLS/Host/Origin/CSRF/session/cookie/logging and actual Nginx rendered template/runtime config; establish tested rollback; produce a separate operator-controlled shared gateway key without exposing its value to ChatGPT/GitHub. Require backend P1AJ/P1AI environment and owner-auth TLS/role G2 review. Public login via real owner's browser and MFA requires an attended owner step, not raw password/TOTP here.
- Stage-only `P1C_GOOGLE_CLIENT_SECRET` must not be blindly applied through Railway's existing two pending changes. Actual Google OAuth code exchange/grant custody + one-folder metadata sync are **not** completed here; real file content/financial totals remain G1/G3 gated.

**User direction:** all three encrypted owner recovery artifacts are already copied to two locations; stop repeated owner backup/download/restore exercises during independent source development. A real offline owner credential restore remains a separately tracked, currently unverified security release acceptance item.

Next code milestone: minimum real-compatible session-bound Google callback/code exchange and encrypted metadata-only grant on private P1R/P1M, then verified exact ingress/public OAuth callback, then owner-directed Google consent. Avoid repeatedly setting up an existing Google Cloud client.
