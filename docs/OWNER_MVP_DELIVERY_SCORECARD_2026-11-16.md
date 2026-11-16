# Personal CFO owner-MVP delivery scorecard and next parallel queue — 2026-11-16

**Canonical plan:** [Owner MVP Completion Blueprint](OWNER_MVP_COMPLETION_BLUEPRINT_2026-11-16.md). This is **synthetic engineering progress**, NOT private production/readiness certification. Scope-bound to this Personal CFO repository and project-only knowledge. GitHub remains temporarily public; no private user bank/FBR/accountant records or keys.

## Definition of completed product

The owner can log into a privately protected app, securely onboard 2023+ bank/FBR evidence, upload irregular statements, verify balances and source gaps, resolve review cases, reconcile owner/cash/loans/assets/wealth/tax, examine draft vs officially acknowledged filed work, export accountant pack, use cashflow/goals/recurring expense analytics, and restore encrypted records after a failure. This requires **all G1–G5 independent acceptance, including actual approved private host/evidence/legal owner signoff**. No family/accountant multiuser SaaS or automated filing/trading is required.

## Verified engineering milestones before this batch

- PR #34 encrypted synthetic operational bank source; #35 bounded encrypted independent PostgreSQL backup/restore; #37 read-only PostgreSQL census; #40 backup-first restored sealed candidate mirror; #41 combined 253-test PostgreSQL18 integration. **G1 blocked**: legacy live and restored SQL plaintext amounts/dates still present.
- PR #38 six explicitly synthetic bank/IRIS adapter contracts (not real format certification); #39 read-only DRAFT XLSX diagnostics; #41 cross-lane compatibility. Actual owner evidence cannot enter public GitHub.
- Current baseline confirmed PR #42: [detailed definition, graph, DoD and parallel plan](OWNER_MVP_COMPLETION_BLUEPRINT_2026-11-16.md).

## Batch 1 — separately implemented and PR-head verified

| Work package | PR | Technical deliverable | Limited acceptance |
| --- | --- | --- | --- |
| **B2 account-month coverage** | [#43](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/43) | Complete month/account/legal-owner/currency matrix with missing/partial/conflicting/unsupported flags, exact source replay, no missing=zero | 263 synthetic pytest + PG18 PASS ([CI 43855346382](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43855346382)); code **synthetic-only**, no authentic source |
| **C2/C3 accountant review states** | [#44](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/44) | Immutable event/evidence references and owner review + DRAFT status revision, no FILED claim from workbook, unauthorized accountant rejected | 259 pytest + PG18 PASS ([CI 43855354706](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43855354706)); pure **in-memory domain**, not access control or persistence |
| **E1 recurring expense** | [#45](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/45) | Monthly/quarterly source-verified/cadence/complete-coverage-gated candidates; excludes unverified, transfer, principal, tax and investment money | 261 pytest + PG18 PASS ([CI 43855362121](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43855362121)); estimated annual spend ≠ actual savings or tax benefit |
| **A5a authenticated G1-c candidate reads** | [#46](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/46) | Read only AES-GCM restored source mirror, verify keyed source identity and independent whole-graph HMAC parity; reject key/tamper/missing/extra | 259 pytest + PG18 encrypted candidate read-side PASS ([CI 43855370234](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43855370234)); NOT typed active canonical ledger or cutover |

**Integration check:** PR from this branch must test all above together on merged `main`, using one optimized PostgreSQL18 backend CI check, including synthetic coverage→recurring→review and `APP_DATA_MODE=real` denial. Record actual merged SHA/CI only after verified. **No G1/G2/G3 private acceptance yet.**

## Next highest-throughput parallel queue

| Priority/lane | Work | Owner-independent now | Dependencies and done proof |
| --- | --- | --- | --- |
| **P0 A5b/A6** | Protected typed operational canonical economic graph + year/account cash/loan/asset/FBR parity | Yes, synthetic test graph | Need independently verified active read/write source adapter, key continuity, no-double-count; no real source switch |
| **P0 A7/A8/A9** | Reversible protected authority cutover, plaintext retirement and offsite recovery | Synthetic clone dry runs yes; production later | True G1 only once raw SQL live leak test, replay/rollback and external key/offsite backup pass |
| **P0 B3–B5** | Source registry, account-period overlap, typed balance replay and constrained conversion worker | Yes synthetic | G3 accepted only with G1/G2 private host and real supported format validation |
| **P1 C4/C5** | Persist encrypted evidence-case history, source-cell financial diff and accountant export | Schema/code synthetic yes | Do not allow draft to mutate original filed records; owner-authorized accountant role later |
| **P0 F1/F2** | MFA/CSRF/rate-limit attack tests, private file-conversion contract | Synthetic no new infra yes | Actual G2 requires approved private deployment/secrets/restoration |
| **P1 D1–D3** | TY2023+ rule coverage audit + independent sourced versioned vectors/mixed income/WHT | Pure code and official source verification yes | Human legal review before a tax due/savings estimate is marked verified |
| **P2 E2/E4/E5** | Coverage-aware cashflow, reserves/goals, source-linked dashboard API and UI | Synthetic contract and component tests yes | Actual owner UI requires private G1/G2/G3 and E2E restore |

**Critical release blockers / owner dependencies later:** explicit approval of a private host/secrets/provider (no default Vercel/Railway/Neon fallback), supported genuine bank/FBR sample verification privately (never public GitHub), external independent tax-law review and owner personal-history acceptance. No owner task for the currently available synthetic engineering queue.

**Operating procedure:** parallel separate branches, one PR-head CI each when ready, one combined integration PR, no redundant main push CI, cancellation of superseded runs, no new Docker/cloud, no background work implied. At every handoff record exact SHA, passing test evidence, open issue and first dependent next step.

## Batch 1 & additional G4/D4 checks — actual verified checkpoint

- [PR #47 combined MERGED](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/47), squash `5f78374f643d9972eceb9b76a310f746a27e1bcf`; [CI 43856233389](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43856233389) **285 pytest PASS + PG18 all security/candidate/read-side operations PASS**. Confirms B2+C2/C3+E1+A5a interoperate and real-mode denied.
- [PR #48 D4 versioned wealth CONTINUITY MERGED](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/48), squash `067c195a976d1bf6b5df31d3570be125e3c09ee2`; exact-head [CI 43857422279](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43857422279) **294 pytest PASS (2 warnings) + PostgreSQL18 Alembic, encrypted source, encrypted restore/candidate/read parity PASS**. Current combined tested tree includes Batch 1 modules. D4 remains fixture-acknowledged, not genuine IRIS verification. See [D4 guide](IMPLEMENTATION_D4_VERSIONED_WEALTH_CONTINUITY.md).
- Owner-MVP **NOT COMPLETE**. G1 full encrypted *active* authoritative financial model+cutover/key/offsite recovery, G2 private owner runtime, G3 actual document format acceptance, independent G4 statutory tax/wealth and G5 owner application/E2E are **not accepted**. The only verified status is **synthetic engineering**.
- **Critical next integration owner:** A5b/A6 typed confidential canonical operational graph, year/account/cash/loan/asset/FBR provenance and full parity. **Parallel:** B3 bank-source registry/duplicate coverage, C4 source-linked accountant review/export, F1 MFA/API/worker threat tests, D1/D2 legal-rule coverage and verified law vectors, E2/E4 CFO budgeting/API. Same repo synthetic-only, optimized Actions, no new providers.

