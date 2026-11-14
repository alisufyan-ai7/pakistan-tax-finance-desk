# Technical architecture and implementation standards

## Minimal deployable architecture

- **Web**: Next.js + TypeScript, mobile-first, single-user access and audit UI.
- **Backend**: FastAPI Python, domain modules (import, ledger, classifications, assets, loans, tax, wealth, advice) in one deployable service.
- **Database**: PostgreSQL with explicit migrations; strong account/entity references and transaction invariants.
- **Documents**: private encrypted blob store; content-addressed immutable originals; only encrypted object references in DB.
- **Workers**: small transactional queue for statement parsing and recalculation; avoid distributed infrastructure prematurely.
- **Model gateway**: optional AI classification limited to sanitized transaction text, consent/configurable provider; deterministic rules prioritized.
- **Tax**: independent pure-function versioned rules library, `Decimal`, well-sourced configurations, calculation audit traces, strict test coverage.
- **Pricing/market data**: optional future adapters, terms-of-use reviewed, timestamped and flagged stale.

## Bounded modules

Auth/Profile; Accounts; Documents; Import/Parse; Canonical Ledger; Classification/Transfers; Income & Expenses; Loans & Counterparties; Investments/Holdings; Net Worth; Tax Rules; FBR Reconciliation; Planning/Scenarios; Export; Audit.

## APIs (suggested)

- `POST /statements` and `GET /imports/{id}` (status plus reconciliation receipt)
- `GET /accounts`, `GET /transactions`, `PATCH /transactions/{id}/classification` (audited)
- `GET /coverage?tax_year=2027`
- `GET /cashflow?period=...`, `/loans`, `/assets`, `/holdings`, `/net-worth`
- `GET /tax/estimate?tax_year=2027`, `/tax/rules/versions`, `/fbr/readiness`, `/fbr/export`
- `POST /financial-planning/scenarios` (no execution)

## Recalculation contract

One import or correction creates a durable event. Derivations are versioned by ledger revision and tax ruleset; recompute only affected account/date/FY while tracking dependencies (e.g. investment costs from historic lots). Re-running same import is idempotent. Raw evidence never edited; audited corrections change active interpretation, not source.

## Testing and deployment

pytest unit/integration; parsing fixture regressions; Postgres migration tests; property tests for balance invariants and currency; deterministic tax vectors; security tests; Playwright browser E2E. Use synthetic fixtures only in CI. GitHub actions should be cost-conscious; separate staging from production if live deployment. No credentials in Git, artifacts, PR or CI logs. Implement export/import & backup restore test before storing real statements.

## Multiuser-ready without premature SaaS

Keep `owner_id`/`tenant_id` concept at domain boundaries (safe key constraints, defense in depth), but serve one private owner in v1. If public productization happens, design an audited migration to strong per-tenant isolation, authorization and deletion workflows; do not expose a multi-tenant endpoint in personal v1.
