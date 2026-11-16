# Manual live synthetic-PWA deployment smoke (recovery guard)

**Purpose:** Detect the exact incident where Railway container health is green but public `GET /api/preview/status` returns 502/504 because Nginx has stale private DNS. This is a **public, synthetic-only** check and is NOT authorization for real data.

Run after deployments on the approved Personal CFO Railway sandbox:
```sh
node frontend/preview-smoke.mjs
```
Or manually trigger GitHub Actions **Personal CFO public synthetic deployment smoke** with `workflow_dispatch`. No secrets, Node dependencies, PostgreSQL job, owner files, cache or provider deployment required; the existing frontend unit CI additionally tests the probe with mocks.

Checks only the **hardcoded, approved public synthetic preview HTTPS origin**:
1. `/healthz` HTTP 200 and plain `ok`
2. `/manifest.webmanifest` mobile standalone and expected PNG icon metadata
3. `/sw.js` exists but has **no fetch handler or financial cache**
4. `/api/preview/status?tax_year=2027` HTTP 200, synthetic connected backend+PostgreSQL, canonical finance **NOT CERTIFIED**, real-data flag false, economic fields null and gates false
5. `/api/accounts` HTTP **404** — no legacy financial API exposed

Any missing endpoint, unexpected economic response, 502/504, or network error exits nonzero without exposing body/headers/secrets. The probe will never call a private Railway domain nor send a customer record.

Monitoring is **not continuous**; this workflow runs only when manually dispatched. Railway deployment success alone is not an end-to-end acceptance. Investigate public failure before claiming restored service. See [incident postmortem](INCIDENT_RAILWAY_NGINX_STALE_PRIVATE_DNS_2026-11-16.md).

**Security boundary:** this smoke check cannot validate future private owner MFA, encrypted canonical financial tables, bank or IRIS adapters, offsite backup, tax-law accuracy, mobile device installation or payments. G1–G5 remain blocked for real data.
