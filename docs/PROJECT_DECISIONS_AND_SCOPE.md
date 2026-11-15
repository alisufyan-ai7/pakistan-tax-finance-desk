# Owner decisions, project direction and non-negotiable scope

**Updated:** 2026-11-16. **Purpose:** an independently readable, durable record of decisions discussed across the project and current chat, so future agents can resume without requesting history from the owner. Historical implementation evidence is in [PROJECT_STATUS.md](PROJECT_STATUS.md) and [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md). Requirements and acceptance are in [REQUIREMENTS_COVERAGE_MATRIX.md](REQUIREMENTS_COVERAGE_MATRIX.md).

## Product purpose and priority

- **Personal-first:** a secure, private Pakistan tax, finance, wealth and personal CFO/adviser desk for **one owner** now. Future paid product for others is an optional exploration, **not** a reason to delay private owner release.
- **Expandable, not artificially narrow:** use a modular monolith with versioned contracts, entity/owner boundaries, pluggable adapters and strict audit/evidence provenance; do not prematurely add microservices, multi-tenant runtime, expensive hosting or payment dependencies. Business/legal-person bookkeeping stays separate from individual FBR returns until appropriate treatment is verified.
- **Historical coverage:** include opening investment/cash/loan/asset history starting in **2023 or earlier where evidence exists**, and financial/tax history **2024 onward at minimum**. Annual Pakistan tax years span **1 July–30 June**; support historic versions and future tax years without code assumptions hardwired to TY2027.
- **Routine experience:** owner uploads PDF/CSV/XLSX bank statements when available—annual bulk or irregular/monthly increments—for multiple banks. Deduplicate overlaps; normalize cashflows; produce cumulative year-to-date and projected annual outcomes; prompt only for exceptions and missing supporting evidence. Later secure onboarding can take **3–4 years of historical IRIS income tax returns and wealth statements** once genuine files are supported.
- **Complete financial picture:** salary, business/freelance income, rental/property, interest/profit, investments, realized gains, other income; expenses, bank transfers, loans borrowed/lent, installments and markup, cash-in-hand, fixed deposits, donations/Zakat/gifts, withholding/advance tax, gold, vehicles, property, stocks/funds/crypto, liabilities, insurance, household obligations, savings, goals and historical changes. Missing evidence is **unknown**, not zero.
- **CFO and financial advice:** interactive briefings, recurring bills/subscription leakage, budget and cash runway, spending trend/variance and anomaly checks, debt priority, appropriate emergency reserve, insurance/goal planning, liquidity forecasts, tax readiness, compliant tax opportunities, investment diversification and researched cash-allocation options with suitability and source caveats. User remains the decision-maker. Never present specific investment picks, live yields or automated trades without evidence, consent and relevant compliance checks.
- **Tax policy:** help the owner **minimize taxes legally** via accurate classification, timing, allowable deductions/credits and compliant investment/filing planning. No illegal evasion, concealment, false deduction, disguised transfer or fabricated proof. Deterministic year-effective official FBR rules with audit trail and human review. Filing/IRIS submissions require explicit confirmation.
- **Operating priorities:** owner-independent development first. Do not block synthetic code for owner financial evidence expected later. Favor minimal cost, efficient green CI, few iterations, clear short owner action items only when unavoidable. Keep project docs up to date **after each meaningful step** and continuously merge reviewed/validated PRs.
- **Data protection:** GitHub source is temporarily PUBLIC only because of GitHub Actions. Never put actual personal financial/tax records, identifiers, secrets or private bank files there; switch private when suitable. The prototype remains synthetic-only and fails closed for real-data mode until private deployment/keys, encrypted legacy finance fields, source vault, secure parsers, MFA/backup/restore and law/evidence gates pass.

## User-requested capabilities in priority order

1. Reliable source capture, historical accounts and secure bank/FBR/broker ingestion with no duplicate/missing records.
2. Deterministic personal income and expenses + tax-year computation and legal tax optimization; full IRIS income + wealth reconciliation.
3. Complete cash/loan/gift/donation/investment/wealth provenance across years.
4. Personal CFO dashboard, budgeting, recurring payments, subscription and bill checks, reserve, scenario advice and investment planning.
5. Optionally household conveniences (shopping-list/meal-cost planning), financial coaching and business administrative automation **after core finance and security**.
6. Future accounts for families/advisers/businesses/SaaS only after owner version is dependable and privacy, permission, commercial/legal requirements are addressed.

## Decision-recording rule

Any later discussion that modifies this order, scope, tax/legal posture, security assumptions, sources, productization intent or owner approval must be incorporated into this file or a linked focused decision record, and reflected in `PROJECT_STATUS.md` and `CURRENT_HANDOFF.md` before the chat ends. Unresolved questions remain openly labeled. **GitHub is the source of truth for successor chats**: see [CHAT_CONTINUITY_PROTOCOL.md](CHAT_CONTINUITY_PROTOCOL.md) and root [AGENTS.md](../AGENTS.md).

## Article-driven decision (2026-11-16)

The owner shared a [Daily Mail Australia article](RESEARCH_AI_HOUSEHOLD_BUDGETING_2026-11-16.md) about AI-powered household budgeting. **Agreed product-relevant direction:** evidence-backed expense patterns, recurring subscriptions and savings opportunities, understandable bill explanations and optional household tasks. Treat the reported Australian AI coaching earnings and market-demand claims as unverified journalistic/interview anecdotes, **not** a proof of future product revenue or a reason to change the private-first plan. Financial recommendations require human oversight and owner confirmation.

## Delivery priority and timing discussion — 2026-11-16

Owner requested continued owner-independent implementation of financial-data confidentiality, secure private deployment and genuine Pakistan bank/FBR support, plus a realistic answer about completion after approximately 5–6 hours of initial agent development. Decision: use [release gates](DELIVERY_GATES_AND_RELEASE_READINESS.md) (G0 synthetic foundations; G1 operational encryption; G2 private MFA; G3 genuine docs; G4 FBR law/wealth; G5 usable private CFO; optional G6 SaaS) and transparent verified status. The previous hours produced synthetic prototypes, **not** a launch-ready private tax adviser. Do not invent a delivery date or declare total completion without real source, deployment and tax acceptance. Continue synthetic engineering independent of owner; require real records, infrastructure authorization and specific legal judgments only once secure integration genuinely needs them.
