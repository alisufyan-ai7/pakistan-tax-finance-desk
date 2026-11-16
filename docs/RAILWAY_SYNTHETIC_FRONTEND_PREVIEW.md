# Railway Hobby — owner-visible synthetic Personal CFO preview

Owner explicitly approved using the connected Railway account on 2026-11-16 and requested an initial deployment **so the frontend can be viewed**. The existing `personal-cfo-dev-sandbox` project has an empty `development` environment. **Do not touch other Railway projects.**

## Deployment scope

- **Service:** `personal-cfo-frontend-preview` in existing `personal-cfo-dev-sandbox` project, `development` environment
- **GitHub:** `alisufyan-ai7/pakistan-tax-finance-desk`, verified merged branch `main`
- **Root directory:** `/frontend`; Dockerfile uses **unprivileged Nginx**, fixed internal HTTP port 8080
- **Public domain:** Railway-generated `*.up.railway.app` (HTTPS); no custom-domain charge
- **Included files:** `index.html`, `ui.css`, `ui.mjs`, `demo-data.mjs` — explicit four-file allowlist. Earlier `legacy-import.html`, backend sources, tests, financial documents and developer files are intentionally excluded from the built image
- **Security:** no environment secrets, connected bank, real PostgreSQL, file volume, S3 bucket, active financial upload, background worker, third-party analytics, API or email. Explicit `connect-src 'none'`/no form submissions, restrictive framing/indexing and HTTP health endpoint `/healthz`.
- **Costs:** Railway Hobby resources are metered; the user's existing Hobby plan is not automatically $0 additional usage. This is one small static container. No separate database/queue/provider is created.
- **Acceptance:** `frontend-static-ci` must pass Node contract/syntax tests on PR head before merge. After merge, check Railway build/deployment health and public root/CSS/module HTTP responses. Only then share live URL. A broken deployment is not declared launched.
- **Non-goals:** no private Personal CFO production service. G1 active canonical economic database cutover, G2 private MFA/TLS/recovery, G3 real bank/FBR adapters, G4 complete statutory tax and G5 secure owner journey are **not complete**. The public preview uses only entirely synthetic financial data.
- **Operational caution:** do not store genuine user records on this preview, nor connect the preview to existing Railway database services from unrelated projects. Production use requires separately approved architecture, encrypted persistence/offsite recovery and security acceptance. Never silently expand the deployment scope.

[Frontend usage details](FRONTEND_OWNER_UI_VERCEL_FREE_PLAN.md) were written before the owner's Railway-only preference. This deployment is the approved replacement preview hosting approach; Vercel is not necessary.
