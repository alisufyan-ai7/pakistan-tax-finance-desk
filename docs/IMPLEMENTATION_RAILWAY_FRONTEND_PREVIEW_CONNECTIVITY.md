# Public synthetic frontend → private Railway FastAPI/PostgreSQL (one safe read-only route)

The frontend remains a public fictional preview on Railway. This PR changes Nginx's `connect-src` only from `none` to **`self`**, and adds an exact-match `GET /api/preview/status` proxy to `personal-cfo-api-preview.railway.internal:8000/internal/preview/status`. **Every other private API, document upload and financial request remains 404/blocked**.

The frontend obtains the service-to-service `PREVIEW_INTERNAL_TOKEN` through Railway service variables. The token is substituted **inside Nginx's server configuration at container startup**, using `NGINX_ENVSUBST_FILTER=^PREVIEW_INTERNAL_TOKEN$`. It does not appear in JavaScript, HTML, HTTP response data, public GitHub, CI or browser storage. The client fetches only the same-origin fictional readiness response; it strictly checks known contract fields and displays either `Private synthetic backend + PostgreSQL connected` or `Private backend unavailable · demo remains local`. No real records, balances or FBR returns are requested.

**Deployment order:** merge/test private backend, create the private Railway backend service with Postgres reference and token, confirm backend online; set the frontend token to match and merge this PR, then verify Nginx health/static UI, status-only path, and deny private finance API paths. Railway's existing frontend service remains the same ID and branch. No other Railway project, public backend domain, additional vendor, secrets in GitHub or autonomous financial write action.

This is **synthetic infrastructure connectivity only**. G1–G5 private owner production readiness remains blocked; `APP_DATA_MODE=real` stays disabled.
