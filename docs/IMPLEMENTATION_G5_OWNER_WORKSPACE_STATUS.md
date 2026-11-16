# G5 owner-workspace authenticated status read-model, synthetic only

**Scope:** New `backend/app/owner_workspace_status.py` and `GET /api/owner/workspace/status?tax_year=2027`; [owner MVP blueprint](OWNER_MVP_COMPLETION_BLUEPRINT_2026-11-16.md), [frontend free Vercel preview plan](FRONTEND_OWNER_UI_VERCEL_FREE_PLAN.md) and [project isolation](PROJECT_CONTEXT_AND_INFRASTRUCTURE_ISOLATION.md).

This is the first carefully bounded **owner dashboard backend contract**, not a financial-dashboard API or public frontend integration. Existing local owner-authentication middleware/dependencies protect the endpoint, and it returns `Cache-Control: no-store`/nosniff. It **never queries legacy plaintext SQL** and does not depend on a real bank statement or FBR file.

The default response is deliberately honest: missing owner evidence means `coverage.state=UNAVAILABLE`, case/review counts **null rather than zero**, and all money fields (bank, cash, assets, liabilities, net worth, income, spending and tax due) **null**. A tax-year coverage matrix reports how many category rules are unavailable, not statutory tax due. An optional offline synthetic domain projection may ingest B2 month-coverage receipts plus C2 immutable cases and DRAFT workbooks, aggregate *structural counts only* and reject mixed-legal-owner records, unverified amount inserts, missing inputs and contradictory case state. This optional composition does **not** make an official FBR filing verified.

`required_gates` explicitly signals G1–G5 incomplete; `actions` refuses real-file upload, autonomous filing, payments, trading or production readiness. Real mode is rejected even if a caller bypasses the API; no real data/credentials in fixtures/CI. The static Vercel frontend remains **independent, public synthetic-only** with `connect-src 'none'` until a protected G1/G2/G3 owner data source and approval allow coupling. Do NOT expose actual source rows in status or attach this to genuine personal financial files.

Tests validate authorization, bounds, wrong years, source-owner separation, missing-not-zero, no financial value leaks, no FBR false claims and real-mode denial. CI uses existing backend single PostgreSQL18 job; no cloud/Vercel database/project provisioned.

**Later**: once full encrypted authoritative ledger, private MFA/TLS host, supported bank/IRIS evidence and independent backup/restore are verified, define versioned authenticated source-linked overview queries and connect the UI through same-origin HTTPS/CSRF. No frontend access to legacy plaintext finance tables.
