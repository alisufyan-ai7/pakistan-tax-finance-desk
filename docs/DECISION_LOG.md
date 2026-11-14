# Decision log / ADR summary (established 2026-11-15)

| ID | Decision | Status / rationale |
|---|---|---|
| D-001 | Personal private single-user first | APPROVED by user, future commercialization optional |
| D-002 | GitHub source of truth for engineering/docs | APPROVED; TEMPORARILY PUBLIC by express owner choice to facilitate development, intended PRIVATE later; code/docs/synthetic fixtures only; never real records |
| D-003 | Historic records from 2023-01-01, extend earlier if needed | APPROVED interpretation of '2024 or 2023'; partial TY2023 marked as partial |
| D-004 | Statement-only normal input, exceptions allowed for truth | APPROVED goal; opening balances, actual holdings, salary slips, proof may be necessary |
| D-005 | Tax engine multi-year, year-effective and deterministic | REQUIRED for legal accuracy |
| D-006 | Loan given and taken; gifts, donations, zakat, cash and other assets in one financial graph | APPROVED scope |
| D-007 | Financial planning assistant built on evidence; never unlicensed execution | APPROVED high-level intent; legal boundary required before commercial advice |
| D-008 | Initial IRIS-ready human-reviewed package, no unsupported auto-file | IMPLEMENTATION DEFAULT / safety |
| D-009 | Next.js + FastAPI + PostgreSQL modular monolith | PROPOSAL, reversible by evidence |
| D-010 | Distinct legal entities cannot be merged into personal tax income | REQUIRED correctness |
| D-011 | Cost-conscious architecture and documentation synchronized to main | PROPOSAL matching owner workflow |
| D-012 | Historical filed returns are immutable evidence until deliberate review/revision | REQUIRED correctness |

| D-013 | Proactively identify ways to **legally minimize** personal tax while complying fully with FBR | APPROVED 2026-11-15; evidence-based statutory rules, attributable benefit, eligibility and human review; never evasion |
| D-014 | Import owner's 3–4 years of filed tax returns and wealth statements as historic evidence | APPROVED 2026-11-15; ONLY after secure private document ingestion; immutable source and discrepancy review |
| D-015 | GitHub source repo intentionally PUBLIC during development, intended PRIVATE afterward | OWNER OVERRIDE 2026-11-15; do not hold sensitive data or secrets in public repo; app production privacy remains mandatory |

## User intent, unresolved rather than invented

- Owner's preferred hosting/provider, application name/brand, bank list, tax residency, source of salary, ownership of companies and investment types are not yet confirmed. Not blockers to create design and synthetic MVP.
- Do not assume all bank statements are sufficient for a legally accurate return, portfolio return, or wealth statement.
- Product audience hypotheses are **not** authorization to launch.
