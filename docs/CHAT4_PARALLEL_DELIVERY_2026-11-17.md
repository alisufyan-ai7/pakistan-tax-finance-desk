# Personal CFO — Chat 04 parallel delivery map and integration checkpoint

**Date:** 17 November 2026  
**Project source:** `alisufyan-ai7/pakistan-tax-finance-desk` only. No unrelated-project infrastructure, memory, secrets or data.  
**Owner instruction:** Develop independent tasks concurrently to reduce elapsed delivery time, preserve the **whole source-safe project context** in GitHub, and never bypass G1/G2/G3 security gates or infer real finances from synthetic fixtures.

## Parallel batch 2: actual branches and exact independent acceptance

| Lane | PR | Independent result | CI | Release limitations |
|---|---|---|---|---|
| **A — P1G, G2 owner login security** | [#111](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/111), squash `db457a9d9af043fbd598401dcace5a22410c240b` | Additive migration `0016_owner_login_throttle`; single-owner HMAC identity; PostgreSQL transactional advisory lock; 5 bad attempts/10min, 15min lockout; fake scrypt+TOTP session; replay/lockout tests | [run 44084144361](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44084144361): **685 pytest + PG18 PASS** | No public login, real credentials, production MFA or G2 acceptance |
| **B — P1H, Google Drive sync readiness** | [#112](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/112), squash `3f31a68a5762d84ce80beb485d6e58026b416554` | Deterministic fake-only 24h scan cadence, 36h stale state, bounded 5/15/45/120min retry, permission-loss pause and last-good-success retention; no schema | [run 44084245982](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44084245982): **683 pytest + PG18 PASS** | No hosted background job/heartbeat, real Google listing or owner data |

Both PRs were independently tested and merged in sequence, starting from verified #109. Their reviewed code domains did not overlap. The **combined integration branch** exercises both modules in one process and confirms real-mode denial and absence of public OAuth/login routes; exact-head CI and final merge must be recorded once verified. The earlier failed initial test runs are retained as history, not acceptance evidence. [P1G detail](CHAT4_P1G_OWNER_LOGIN_THROTTLE_2026-11-17.md) · [P1H detail](CHAT4_P1H_SCAN_CADENCE_2026-11-17.md)

## Roadmap parallelism — dependency-aware execution

| Workstream | May proceed independently now? | Parallel work without private source access | First real-world dependency |
|---|---|---|---|
| **Priority 1 / Google Drive** | **Yes, partition by file and contract** | G2 owner-login/rate/CSRF/recovery; fake folder paging/cadence and index integrity; mobile review-state rendering from fictional status; strictly controlled route/logging threat model | Real Google OAuth / metadata requires independent G2 owner auth, encrypted key custody, public gateway security review and owner-scoped consent |
| **Priority 2 / Document understanding (G3)** | **Yes, synthetic fixture adapters** | Bounded bank/IRIS/PDF/XLSX parser profiles, corrupt ZIP/PDF tests, provenance and quarantine metadata; synthetic-only | Original bytes require approved encrypted vault, sandbox and real bank/FBR format certification under G2/G3 |
| **Priority 3 / Encrypted financial ledger (G1)** | **Yes, separate coordinator** | Synthetic canonical source/ledger parity, coverage, backup/restore and reversible cutover rehearsals with dedicated migration owner | Genuine authoritative cutover **must be serialized** after full data confidentiality, restore/rollback, owner/account×year provenance |
| **Priority 4 / Owner security (G2)** | **Yes for design/test; no for activation** | Independent session/login throttles, restricted-role/key rotation plans, recovery audits, trusted proxy/callback redaction tests | Private live MFA/role/key approval and recovery acceptance **cannot be waived or parallelized with real ingestion** |
| **Priority 5 / Tax/accountant reconciliation (G4)** | **Yes, pure evidence contracts** | Synthetic FY/TY rule fixture coverage, source versioning, draft-versus-filed workbook state machine, withholding/wealth unknown-evidence planning | Personalized tax/wealth conclusions require verified documents and legal rule-year review; accountant DRAFT never silently final |
| **Priority 6 / Mobile PWA financial pulse (G5)** | **Yes, synthetic UX** | Responsive review queue, empty/loading/error states, source-coverage labels, recurring bill/expense change/investment return date placeholders with explicit unknowns | Real month spend, invoices, asset balances and alerts require G1 source-authoritative reconciliation and G3 verified evidence |

**Recommended next concurrent batch, respecting feature rank and safety:** 
- **Lane A / P1G-next:** private simulated login endpoint + cross-worker lockout/rate controls, recovery audit and independent restricted-key-store/role tests; **no public deployment**.
- **Lane B / P1H-next:** fake-only scan-run receipt persistence/heartbeat/lease proofs and private review queue status contract; no genuine Google requests.
- **Lane C / G3-plus-PWA:** static synthetic document-review mobile UI and malformed file fixtures, keeping original bytes and real amounts inaccessible.
- **Lane D / accountant/G4:** pure DRAFT-vs-filed evidence-completeness checks, never a real FBR assessment.

Do not have two lanes alter `models.py`, Alembic head, `g1c_preflight.py` or backend CI simultaneously; serialize common-schema changes under an integration owner. Limit GitHub Actions usage to necessary exact-head checks plus **one combined-main acceptance run**; no new paid runners, cloud providers, credentials or Rails servers.

## Non-negotiable dependency gates

`G2 owner authentication + restricted real credential custody + reviewed public callback` → separate authorized live OAuth consent → `one-folder metadata-only scanner` → authenticated mobile review index. 

`G1 encrypted canonical authority + independent backup/restore` AND `G2 private security` AND `G3 certified original-format adapter` → original-byte parsing/reconciliation → real dashboard, tax/accountant and owner alerts.

The registered owner Google redirect is **not yet live**. Existing Railway frontend only serves synthetic status; private API still starts `app.preview_api:app` even if an automatic code-only image deployment occurs. Public repo remains synthetic only. The owner is not expected to re-create the Google Cloud project or supply private secrets for code-only development.

## Continuous GitHub handoff protocol

Each parallel lane must document base SHA, exact head/CI, PR/merge, verified behavior, negative tests, security gates and next step. Integration owner updates `AGENTS.md`, `AGENT_START_HERE.md`, `README.md`, `docs/CURRENT_HANDOFF.md`, `docs/PROJECT_STATUS.md`, `docs/PRIORITIZED_PERSONAL_CFO_ROADMAP_2026-11-17.md`, decisions/requirements/architecture/release-gates where materially changed and parent issue [#98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98). A future chat must be able to resume from current GitHub `main` **without previous chat transcripts**. Security and factual claims must always distinguish merged proof, code-only fixtures, deployed endpoints and genuine live connection.

## FINAL combined-main code acceptance — 17 November 2026

**[Parallel integration PR #113 MERGED](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/113)**, squash `b1019b0b36c1d7af216a3a9d31bbcf8b64ee775e`, exact tested head `183b307da49637fbf3d9e62ce8b26c1f54836f40`, [CI 44085169774](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44085169774): **697 backend pytest PASSED, 3 warnings, PostgreSQL18 P1G atomic lockout, P1 Drive encrypted inbox, G1 clone/restore and G2 restricted role PASS**. Independent merged [P1G #111](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/111): **685 pytest PASS**; [P1H #112](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/112): **683 pytest PASS**.

GitHub main accepted the independently green lanes #111 and #112 and cross-lane integration #113. Final regression specifically exercised both fake-only modules together and rejected real mode and accidental public routes. **No shared-schema merge conflict** occurred because only lane A touched migration 0016; lane B was pure. The private Railway API auto-deployed #111 code image and still runs `app.preview_api:app`; frontend/Nginx unchanged. **No production owner MFA, actual Google account connection, running scanner, real metadata index or personal finances are active.** Future work should parallelize source-safe tasks per the dependency table above; do not run real credential provisioning/consent/original-data operations without G2 and owner-scoped approval. [Latest verified handoff](CURRENT_HANDOFF.md), [project status](PROJECT_STATUS.md).

**New independently executable next-lane issues (2026-11-17):** [#114 P1I mobile Documents UX](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/114) (synthetic review status/unknowns, no backend schema changes) and [#115 P1J fake scan lease/heartbeat](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/115) (bounded restart/concurrency with one schema migration coordinator). These can proceed concurrently with G2 [#110](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/110) and G3 synthetic format fixtures [#29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29); all live Google access, original bytes, actual amounts, owner MFA deployment and G1/G2/G3 release acceptance remain serial and separately approved. See [parallel DAG](CHAT4_PARALLEL_DELIVERY_2026-11-17.md).
