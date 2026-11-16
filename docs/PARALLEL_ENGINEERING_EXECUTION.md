# Owner-approved parallel engineering execution — Personal CFO

**Decision:** 2026-11-16. The owner wants the maximum **independent** progress without unnecessarily serializing every roadmap item. Prioritize concurrent code/design/testing that cannot compromise G1–G3 financial security gates.

## Parallel workstreams and shared boundary

| Lane | Priority / issue | Independently deliverable | Does not authorize |
| --- | --- | --- | --- |
| **A / G1-c security** | P0 [#21](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21) | Protected bank source, encrypted DB backups, source census, backup-first independently restored sealed candidate, rollback/parity, later guarded cutover | Real-data mode, active cutover or plaintext retirement before separate verified safety acceptance |
| **B / G3 adapters** | P0 [#29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29) | Synthetic format manifests, typed records, bank/FBR parser contracts, bad-format/ZIP/PDF defenses | Certified real Pakistani bank/IRIS parsing or access to personal files before G1/G2/G3 private acceptance |
| **C / Accountant evidence** | P1 [#30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30) | Read-only DRAFT spreadsheet diagnostics, filed-vs-draft state machine, review queue/contracts, source-gap planning | Treat provisional accountant workbook as a final filed return or silently calculate tax |
| **D / CFO/tax** | Later G4/G5 [#5](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/5), [#25](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/25) | Pure hypothetical scenario/investment/withholding or FY-specific verified reference-rule tests, no live inputs | FBR liability, personalized investment recommendation or automatic filing |

**Integration DAG:** Lanes B, C, and pure D can develop while A is underway. **Live owner data, app cutover and releases remain serialized** behind G1 full confidentiality + recovery, G2 private MFA/TLS/hosting, G3 genuine adapters and G4 statutory/legal independent review. Moving other lanes forward **does not make G1–G3 pass**.

## GitHub work partitioning

- Confirm the latest same-repository `main` plus project [context/provider isolation policy](PROJECT_CONTEXT_AND_INFRASTRUCTURE_ISOLATION.md) before any work; never use ChatGPT account-wide memory or unrelated account projects.
- Create **one short-lived branch/PR per independently reviewable code lane**, each with its own new files, tests and focused owner-visible acceptance. Independent modules reduce collision. Use only this repository, no other provider, no Docker workspace required.
- When changing common models, encryption, Alembic or CI, coordinate by **one integration owner**; avoid concurrent edits to the same file. Record security flags and contract changes before dependent lanes adopt them.
- Run **at most one PR-head GitHub Actions workflow per finished iteration** when possible, plus necessary reruns only after fixing real failures; keep the existing single PostgreSQL18 service/job, pip cache, path filters and cancel-in-progress. Do not incur a separate database/runner for each test group.
- Exact PR-head CI must pass before merge; verify merge SHA after squash. For multiple independently tested feature branches, run **one consolidated integration PR** after merges to confirm the combined `main` tree rather than relying on separate green PRs.
- Keep G1-c complex candidate/cutover failures **fail-closed**; no automated cleanup/deletion of source, no plaintext owner records or real-data mode even if synthetic tests pass.
- No background or autonomous scheduled work is implied: a future agent must be explicitly invoked to execute the next work slice. Each chat commits honest merged changes, pending dependencies and verified CI/risks to GitHub.
- End each cycle by updating `docs/PROJECT_STATUS.md`, `docs/CURRENT_HANDOFF.md`, `AGENT_START_HERE.md`, relevant issue/roadmap and link the exact PR-head checks. Any unfinished branch and CI blocker must be explicit.

## First parallel delivery batch (2026-11-16)

- [PR #38](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/38): G3 synthetic bank/IRIS adapter capability manifest; PR-head [CI 43849382462](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43849382462) **235 pytest + PG18 PASS**; squash `6df1b3124dde04643675386cd53f5278660d15ac`.
- [PR #39](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/39): synthetic DRAFT XLSX formula/cache diagnostics; first CI found fixture serialization mismatch, corrected; exact validated [CI 43850290572](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43850290572) **232 pytest + PG18 PASS**; squash `c08edbcf923594f6ac3325d183a2322e00abc669`.
- [PR #40](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/40): backup-first independently restored AES-GCM candidate mirror of full synthetic PG registered source graph, with source HMAC/row parity and injected transaction rollback; earlier stale migration assertion corrected; exact [CI 43850977371](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43850977371) **251 pytest + PG18 + candidate restore/rollback PASS**; squash `5e9b1dc620a97e3c9e4b279ab0448095f67782fd`.
- **Integration VERIFIED:** [PR #41 MERGED](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/41), squash `2ee17e0e3fb576a8a0207ad25e8fbd4686680d68`, exact validated PR-head [CI 43851527422](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/43851527422): **253 pytest PASS, PostgreSQL 18 Alembic, G1-a/G1-b/G1-c encrypted candidate + rollback PASS**, with combined synthetic-only and `APP_DATA_MODE=real` denial tests. The integrated branch includes all three earlier merged PRs. No production/real-source gate passed.

**Security status unchanged:** all three are synthetic foundations. G1-c complete live canonical finance cutover/legacy plaintext retirement/offsite recovery and G2 private MFA and G3 authentic source certification **remain blocked**. Only owner-approved providers may host anything; no added cloud project, VPS, Docker installation or real financial data was used for this batch.
