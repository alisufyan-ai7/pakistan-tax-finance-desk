# Personal CFO platform — extensible product architecture and scope contract

**Decision 2026-11-16.** The product is a private, personal Pakistan Tax & Wealth Desk **now**, designed as a modular personal CFO and adviser platform that may later serve others. The core is NOT a narrow bank-statement parser nor solely an FBR calculator. Security and truthful decision support take priority over feature count.

## Desired experience

**Owner's default workflow:** provide a one-time profile, upload multiple years of historical evidence (2023/2024 onward) and then upload bank statements occasionally or in bulk. Each accepted new statement is deduplicated, linked to prior periods and recalculates a historical ledger; genuine evidence gaps prompt rare targeted questions. The advisor may recommend what to *review or consider*, but NEVER assumes cash withdrawals are expenses, transfers are income, loans are earnings, or a donation is legally deductible without evidence. The system shows both *observed* and *unknown*, not invented tax or net worth.

The owner may elect to use it for personal income/expense/net worth, freelance/sole-proprietor cash flow, investments, debts, insurance, donations, taxes and wealth statements. Later: budget/goal planning, reminders, risk/liquidity and portfolio health, evidence-backed legal tax planning, retirement, estate/document readiness, business dashboards, household shared views and independent accounting/adviser access. No automatic trades, transfers, tax filing or paid market-feed usage without separately approved integration, rights and user permissions.

## Engineering decision: modular monolith first

FastAPI + SQLAlchemy + PostgreSQL remain ONE deployable backend, with explicit internal bounded modules; static/local synthetic prototype evolves toward a mobile-first Next.js experience. No microservice split or separate data pipeline until justified by observed load. Keep an auditable append-only economic event as an immutable input, distinct from classified interpretation, approved advice, tax-law rules and generated projections.

| Bounded context | Long-lived capability | Inputs and boundaries |
| --- | --- | --- |
| Identity / Security | Private owner, later explicit tenant, entity and role boundaries | MFA, session, RBAC, encrypted secrets, revocation, export/delete |
| Evidence & Import | Bank/broker/payroll/FBR document format adapters and immutable original vault | Adapter version, timezone, source confidence, duplicate matching, reconciliation receipt; manual only for exceptions |
| Finance Ledger | Canonical source movement, transfers, loans, gifts, zakat, donations, tax withheld | Money in integer minor units, currency and FX provenance; entity/legal ownership; corrections as append-only interpretations |
| Wealth & Positions | Cash, banks, securities, gold, property, vehicles, holdings, liabilities | Cost lot vs valuation vs cash contributions; timestamp and independently verifiable source; missing != zero |
| Obligations | Debt schedules, future commitments, expenses, insurance, goals | Contract/evidence, due date, outstanding, interest vs principal, overdue/future flags |
| Pakistan Tax & Filing | Versioned effective tax rules, withheld/final/adjustable, evidence-led eligibility and IRIS package | TY2023+, legal basis + Finance Act version, exact independent golden vectors; no automatic filing |
| Planning / CFO | Budget, scenario planning, cash flow, liquidity, risk, savings targets, financial goals | Pure deterministic projections, explicit assumptions, confidence/provenance; no trading or real tax claims |
| Recommendations | Rule + evidence + confidence + consequence + owner action and decision history | Explainable, non-intrusive, jurisdiction-aware, no guarantees or autonomous execution |
| Exports/Integrations | Owner-controlled open financial packages and optional connectors | Explicit consent, data minimization, audit and reversible sync, API contracts |

### Domain contracts to preserve scalability

1. **Source != interpretation != advice.** Immutable source evidence and financial event identity; multiple versioned interpretations; advisor insight references exact evidence and the ruleset used. Reclassification never overwrites the original and must invalidate dependent derived views.
2. **Money != valuation != tax.** Record currency, amount_minor, FX quote/source/date where needed, acquisition cost lots, unrealized vs realized gains and withheld tax separately. Conversion has traceability; never assume all amounts are PKR when extending to foreign accounts.
3. **Entity, party and access scope.** The local prototype is individual + PKR only. Future owner/tenant_id, legal_entity_id, bank_account_id, counterparty and family-member access need enforced storage partition, scoped blind indexes and row-level authorization. No public multi-tenancy before adversarial isolation tests.
4. **Version and confidence.** Every parser, legal rule, valuation and recommendation version is immutable and timestamped. Output states include `OBSERVED_UNVERIFIED`, `OWNER_DECLARED`, `EVIDENCE_REQUIRED`, `COMPLETE_SOURCE_RECONCILED` and `NOT_AVAILABLE`; unknown numeric values remain `null`.
5. **Derived views.** Read models for tax years, calendar cash flow, investments, debt, obligations, future goals and full net worth have explicit source lineage, currencies and missingness. Avoid double counting cross-account transfers, principal, cash-to-asset movements and candidate private mirrors.
6. **Privacy first.** Private encrypted financial source and event payloads plus indexed minimum metadata; separate encryption/HMAC/backup keys, rotation and replay. Legacy plaintext columns and insecure actual-document parsing remain blockers. Production deployment requires private TLS/MFA, backup restore rehearsal and limits.
7. **AI supports, never certifies.** Optional model can suggest memo/category or ask for missing evidence, but deterministic money math and law rules own final computations. Personal financial strategy is informational and may require a licensed professional for regulated advice. No financial or tax execution without user approval.

## Financial advisor design

Every advice item should specify: `id/domain/priority/status`, time horizon, evidence source IDs, currency, *facts*, assumptions, calculation version, missing evidence, downside/risk, action for owner, last verified timestamp, human review state, and optional FBR section/Finance Act citation. Scenarios are pure functions and **never** silently read from unreviewed statements. If data is missing, the advisor recommends obtaining evidence, not buying a product or estimating guaranteed savings.

**Proposed advice modules:** cash-buffer/runway, income stability, recurring/spending leak detection, bills/debt obligations, emergency reserve, retirement/education/property goals, investment concentration/asset allocation, scenario comparison, income volatility, tax reserve (when legally verified), lawful deductions/credits, foreign income/FX risk, asset insurance adequacy, cash-vs-invest decision, conflict/related-party loan evidence and wealth statement reconciliation. Family/business/estate views are future separate entities/permissions.

## Productization (optional, not a prerequisite)

Potential audiences: Pakistani salaried professionals; freelancers and consultants with mixed income; sole proprietors; investors; expatriates with Pakistan reporting; households managing loans/assets; accountants and tax practitioners with client consent. Start with *one* private owner and a no-cost-friendly modular monolith. Later isolate each tenant's encryption, access scopes, retention, billing and legal-entity/tax-residency rules. Commercial tax/advice services, market feeds and IRIS integration need legal, privacy, licensing and data-rights review before a public launch.

## Present vs planned

**Implemented and tested (synthetic only):** source-ledger imports/review, reviewed transfer/loan/cash relationships, encrypted evidence/text and new event journal, HMAC indexes, backup-first offline rehearsal, historical source and cash/asset snapshots, partial recorded wealth and narrow FBR salary brackets. M2p adds a pure hypothetical scenario engine and encrypted-event *observation-only* CFO briefing.

**NOT IMPLEMENTED / blocking real use:** final migration of plaintext bank/loan/cash amount/date/linkages; authoritative secure query projection/switch; private deployed app with product-grade MFA/recovery, key rotation, offsite backups and tested disaster recovery; real PDF/bank/broker/IRIS adapters; full multihead Pakistan tax rules for TY2023 onward; source-complete wealth statement; comprehensive cost-lot/investment P&L; business P&L/payables; evidenced recommendation/suitability and adviser approval; lawful IRIS submission; user experience and mobile E2E.

## Acceptance principle

An expanding feature cannot bypass the real-data safety gates. Add modules with stable domain contracts and tests, not new hard-coded assumptions that one market, bank, income source, year or tax law applies globally. A feature is NOT done solely because a type exists: require data ingestion, cross-source reconciliation, tests, audit, security and useful end-user flow.
## M2q expansion — investment domain primitive (2026-11-16)

The portfolio domain now has a **pure** FIFO accounting-cost-lot calculator (`app/investment_lots.py`) for fictional opening lots and broker-style buy/sell events. It is kept separate from immutable source imports, bank cashflows, encrypted asset valuations and legal tax calculation. When broker/NCCPL evidence becomes available, preserve source identity and acquisition lots, add corporate actions and FX provenance, reconcile bank cash contributions before computing trusted positions, and route tax consequences to the correct versioned FBR engine. No independent broker/market-data microservice is necessary for the current owner-only stage.

## Article-driven addition: everyday spending intelligence (research 2026-11-16)

Source assessment: [AI-assisted household budgeting article, checked 2026-11-16](RESEARCH_AI_HOUSEHOLD_BUDGETING_2026-11-16.md). The core design lesson is to give the owner *daily practical financial value*, not merely annual tax totals: expense trends, forgotten subscriptions, bill explanations, repeat payments and explainable budget changes. This is **proposed**, not shipped.

Within the existing modular monolith, add a **Spend Intelligence / Recurring Obligations** domain whose inputs are *reviewed* ledger event IDs, account/entity ownership, merchant aliases and statement-coverage intervals; outputs are non-authoritative `RecurringCostCandidate`, `BillDueEstimate`, `PriceIncreaseInsight`, `SavingsHypothesis` and owner action records. Facts stay in the encrypted canonical finance store; derived suggestions carry ruleset version, supporting source references, missing coverage markers and confirmation/reversal lineage. Prefer deterministic sequence/cadence and math, with privacy-gated AI explanation or classification. **Do not infer a canceled expense, tax deduction or savings from unobserved months**. User confirms subscription cancellation or any action; no payment/trade/filing autopilot.

Add later optional **Bills & Household Productivity** domain: invoice/utility/telecom explanation, cost-aware shopping/meal lists, everyday admin with explicit preferences and local verified prices. Do not infer personal health details, use foreign-Australian prices as Pakistani market facts or prioritize this over security and real-bank/FBR integration. All advice runs through suitability/evidence/human-approval controls. [Issue #25](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/25) tracks the first spend-intelligence engineering slice.

This scope is also committed as an owner direction in [PROJECT_DECISIONS_AND_SCOPE.md](PROJECT_DECISIONS_AND_SCOPE.md) and governed across new chats by [CHAT_CONTINUITY_PROTOCOL.md](CHAT_CONTINUITY_PROTOCOL.md).
