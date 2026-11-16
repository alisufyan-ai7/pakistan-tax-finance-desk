# Railway private Nginx upstream stale DNS incident — 2026-11-16

**Affected only** the owner-approved Personal CFO `personal-cfo-dev-sandbox` / `development` **synthetic preview**. Public website and PWA static assets loaded, but the one safe status endpoint `GET /api/preview/status?tax_year=2027` started returning 502/504 after the private FastAPI backend redeployed. No genuine financial data was involved.

## Root cause and evidence

- Railway reported all three services **online / SUCCESS**: public Nginx frontend, private synthetic-only FastAPI and private PostgreSQL18.
- Independent live HTTPS request to `/api/preview/status?tax_year=2027` returned **502**, while `/healthz` returned `ok` and PWA manifest was available.
- Railways frontend deployment logs at `66f7723d-0aa3-4339-acb4-f7b51cd9952a` showed a successful **200** status request at `15:52:05 UTC` while the earlier backend generation was still available, followed by `upstream timed out ... while connecting to upstream` at `15:53:17 UTC` using a stale private IPv4 address after the backend deployment `22a523fc-a39c-47ed-875e-19e6f14beb87` replaced the API instance.
- The Nginx directive `proxy_pass http://personal-cfo-api-preview.railway.internal:8000/...` resolved the private hostname at **Nginx startup** and held that address despite Railway replacing the private address during an independent backend deploy. Backend health was not evidence of proxy reachability.
- Railway employees document this exact deployment class of Nginx private-DNS stale-IP failure: [Railway Central Station](https://station.railway.com/questions/service-times-out-on-outbound-api-calls-ffd53b56). Their internal DNS resolver is `fd12::10`; explicit frequent re-resolution is recommended.

## Correction

- Inside the **existing exact public GET-only** Nginx location, use `resolver [fd12::10] valid=5s ipv6=off` plus `resolver_timeout 2s`.
- Assign **hardcoded** project-private host:port to `$private_preview_upstream`, then use variable-based `proxy_pass http://$private_preview_upstream/internal/preview/status$is_args$args`. This enables dynamic DNS resolution, retains a single bounded path and forwards the optional synthetic tax-year query. The backend remains private: never point proxy to an external/public domain or move the token into browser JavaScript.
- Keep all original `PREVIEW_INTERNAL_TOKEN` Nginx template substitution rules, no POST, no extra API paths, no external scripts and no genuine data.
- Frontend regression test asserts resolver, hardcoded private backend, preserved query string, GET-only and absence of static hostname `proxy_pass`. Validate actual Nginx syntax, exact-head green Node CI, merge, then verify Railway frontend deployment and live HTTPS status. A service marked `SUCCESS` is insufficient; an **actual 200 with the synthetic-only readiness contract** is the acceptance criterion.

## Prevention / next gates

Run a real HTTP probe after **each backend redeploy**, since Nginx health `/healthz` only reflects static-container health. Do not enable any real owner uploads, caching, bill payments or private financial APIs. Separate unresolved production gates (G1 full active encrypted canonical data, G2 owner MFA/least-privilege/recovery, G3 actual verified source adapters, G4 tax and G5 authenticated end-to-end) remain blocked.
