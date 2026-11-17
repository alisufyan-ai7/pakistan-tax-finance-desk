# P1O · Railway exact-route OAuth edge candidate (NOT deployed)

**17 November 2026 · Issue #126 / parent #98 · independent of P1N owner identity schema.**

The owner has already registered the exact HTTPS callback:
`https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback`.
The Google Drive API, External/Testing one authorized Drive-owning account and restricted `drive.metadata.readonly` scope were checked. The real client secret is securely **staged but not deployed** on private `personal-cfo-api-preview`.

This independent lane adds only `ops/nginx.personal-cfo-oauth.candidate.conf` and `backend/tests/test_private_oauth_edge_candidate.py`: an explicit, **unmounted** copy of the current Nginx server configuration with a narrow allowlist for three owner login/session/logout endpoints and four OAuth start/callback/status/disconnect paths. The current live `frontend/nginx.railway.conf` is **untouched** and still proxies only fictional GET `/api/preview/status`.

The candidate routes each exact path to a fixed **private Railway service**, rejects wrong Host/method, clears user-injected forwarded host/client IP/preview key headers, prevents generic `/api/*` proxy, and sets `access_log off` and `error_log /dev/null crit` for sensitive OAuth requests. The same-origin Google top-level GET callback is the sole allowed route to pass its code/state query to a future trusted **private** backend; it is not redirected or logged by candidate Nginx. POST routes will additionally require authenticated owner session and Origin+CSRF in the backend.

**Security limits—do NOT copy this candidate to live Nginx as-is:** Merely setting `access_log off` and `error_log` in Nginx does NOT prove Railway edge or private upstream access logs suppress authorization code/state/cookies. Those are mandatory separate live reviews. A trusted proxy/TLS config, rate-limited login and OAuth start, complete session-bound single-use PKCE state, backend clean redirect and token storage, actual browser SameSite=Lax/CSRF behavior, callback replay/DoS defense, site CSP/CSRF and error handling are still unaccepted. The candidate deliberately does not claim live response semantics or independent owner consent. Nginx configuration syntax and actual Railway TLS/log behavior require deployment-safe isolated acceptance, distinct from source-pattern tests.

No new service, public API domain, external provider, OAuth grant, secret, bank/FBR content, or real finance mode is enabled. G1/G2/G3 real-data gates remain **BLOCKED**. Keep `P1C_GOOGLE_CLIENT_SECRET` sealed and staged. Further G2 release under [Issue #126](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/126) and [complete handoff](CURRENT_HANDOFF.md); owner has already finished Google Cloud setup, so no new client is needed. Exact branch CI and merge evidence should be appended only when verified.
