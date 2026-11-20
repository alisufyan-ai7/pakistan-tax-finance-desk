# Personal CFO — Lessons learned (living project memory)

**Status:** Active, required reading for every new engineering chat or agent session.  
**Established:** 20 November 2026.  
**Owner:** Personal CFO project; maintained in GitHub with normal pull requests.  
**Primary references:** [Startup instructions](../AGENT_START_HERE.md), [agent rules](../AGENTS.md), [current handoff](CURRENT_HANDOFF.md), [evidence-first MVP](P6_PRIVATE_OWNER_MVP_MINIMUM_RELEASE_2026-11-20.md).

> **Goal:** Stop making the same mistakes. This is a *short, actionable operating policy*, not a second roadmap, a progress diary, or a replacement for security/privacy rules. Consult it **before deciding how to work**, not only after a failure.

## Every-session and every-change rule

1. **At the beginning of a new chat/task:** read this file, `AGENTS.md`, the top/latest section of `AGENT_START_HERE.md`, and relevant current handoff/feature docs **before** proposing commands, new resources or implementation. GitHub's latest main is authoritative; conversation summaries may be stale. Check for newer entries.
2. **Before execution:** ask internally: *Can I do this directly with the connected tools? Is this already done? Is a real owner action actually indispensable? Does it create recurring cost? Am I solving the smallest problem that delivers visible financial value? What is the exact security and data boundary?* Make the result of those checks clear when relevant; never claim capabilities a connector lacks.
3. **After a substantive mistake, user correction, failed real-run assumption or unexpected environment behavior:** append one concise entry here in the same engineering PR (or the next docs-only PR if no code changes). Include evidence link, **observed vs inferred** cause, impact, the precise prevention rule, and what evidence would verify the fix. Do not copy long logs or private details into GitHub.
4. **Before merging any PR:** explicitly assess whether it revealed a new reusable lesson. If yes, update this document and any startup rule it changes; if no, note "No new lesson" in the PR description or checklist. Do not add entries just to fill the checklist.
5. **After verifying a fix:** update that lesson's status or verification reference in place; don't prepend a contradictory "latest" paragraph to multiple 100-KB documents. Link to the one canonical entry. Never erase what happened.
6. **Priority:** protect original source files, encryption, owner login, least privilege, and financial truth. Learning from overengineering never grants permission to bypass these safeguards.

## Non-negotiable working rules, derived from actual incidents

| ID | Rule to apply *before* work | Failure it prevents |
|---|---|---|
| LL-01 | **Optimize for the first real owner-visible, source-backed result**; distinguish genuinely required safety checks from unrelated future features. | Shipping many foundations while the dashboard still has no verified finance amounts |
| LL-02 | **Inspect tool permissions and runtime capabilities before promising to act or delegating to the owner.** If a capability is unavailable, say so once and use the shortest supported alternative. | Repeated Mac Terminal requests for Railway operations the assistant said it would perform |
| LL-03 | **Make a single operator step cover the necessary diagnosis and cleanup.** Validate script syntax, prerequisites and success/failure branches before using a billable runtime. Don't loop on the same failed command. | Multiple probes and v1's avoidable guest-Python-path failure |
| LL-04 | **Use exact, single-use, cost-scoped authorization.** Count each created metered resource, destroy it in a `finally`/trap path and verify deletion. No automatic retries or extra VM on old approval. | Unplanned Railway VM charges or forgotten sandbox resources |
| LL-05 | **Report only the verified acceptance level.** Source merged, CI green, Railway deployed, OS sandbox smoke passed, Python reader passed, real source reconciled, and financial figures live are all different milestones. | Presenting synthetic success as actual bank document analysis |
| LL-06 | **Do not replace a safety boundary with a convenient but weaker one.** Fail closed, use an appropriate runtime, and preserve no-network/untrusted-PDF controls; minimize only bureaucracy unrelated to the risk. | Temptation to remove Bubblewrap restrictions when the standard container cannot start |
| LL-07 | **Don't hardcode assumptions about a guest platform.** Prefer tested capability checks and documented fallback behavior; one sandbox test should be capable of reporting which stage failed. | Rejecting a valid sandbox VM solely because Python lived outside `/usr` or `/bin` |
| LL-08 | **Keep original Google Drive folder immutable and financial labels honest.** Gross bank credits/debits are not income/expenses; a statement closing balance is historical, not today's available cash. Source SHA, date, completeness and review required. | Incorrect financial dashboard numbers or inadvertent source modification |
| LL-09 | **One canonical lesson and one canonical current fact; link rather than duplicate.** The startup docs should contain short instructions and links; older checkpoints must be treated as historical, not as current active blockers. | Massive repetitive handoffs, contradictory "latest" notes and rediscovering past outcomes |
| LL-11 | **Inspect the approved real source with the connected read-only provider before designing another generic data adapter.** Analyze actual file signatures, headers and reconciliation privately; never copy private contents into GitHub. | Building a series of synthetic-only adapters while genuine original layouts were already accessible through the connected Drive account |
| LL-10 | **Investigate test failures before changing unrelated code.** Separate a real regression from transient CI infrastructure, retry the *same head* once where appropriate, and only merge after green evidence. | Treating a disposable PostgreSQL CI failure as a change in PDF security behavior |

## Incident evidence and the resulting change in practice

### LL-01 — Infrastructure effort displaced a useful financial MVP
- **Observed:** Multiple security/adapters/preview PRs shipped while the owner still couldn't see genuine statement-backed balances. The Home historical statement view was added in [PR #236](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/236), but its real bank-reader source remained off.
- **Lesson:** A deployed shell of a CFO app is not a working financial dashboard; show clearly dated, individually verified source facts first, then add broader investment, recurring bills and automated sync *after their data exists*.
- **Prevention:** Every new priority must state its **first owner-visible result**, the smallest real source prerequisite, and the items deliberately deferred. Separate required security from optional architecture.
- **Status:** **Practice adopted; real source-backed bank numbers still pending.** [Lean release plan](P6_PRIVATE_OWNER_MVP_MINIMUM_RELEASE_2026-11-20.md).

### LL-02 / LL-03 — Repeated owner Terminal work and poor initial diagnostic coverage
- **Observed:** Owner ran the same Railway service sandbox smoke more than once. First attempt returned only `false`; [PR #237](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/237) added allowlisted diagnostics; the next output was `JAIL_CANNOT_START`. The assistant's connected Railway integration did **not** expose Sandbox create/exec/destroy, despite earlier promises to manage it directly.
- **Lesson:** Before promising "I'll do it," discover exact connector capability. Ask the owner to run a CLI command only if truly necessary, explain why first, and make the **first** diagnostic useful and safe.
- **Prevention:** Inventory tool contract and environment constraints before requesting action; build bounded, no-secrets reason codes; record owner action count. Do not ask to repeat a known-to-fail probe without a changed hypothesis.
- **20 Nov Chat 9 update (same LL-03/04, not a new lesson):** A subsequent operator-run VM Python probe emitted only the fixed code P5H_REMOTE_SANDBOX_UNAVAILABLE. The Railway project-token variable was present when checked, but this generic error hid whether failure preceded VM creation, occurred during setup, or completed cleanup. **VM creation, single-use consent consumption, and destruction are UNKNOWN**. The source bridge also omitted explicit guest directory creation before file uploads: a missing precondition but **not a proven cause** of the reported error. Before any additional paid run, add zero-create inventory inspection, fixed stage-only diagnostics and tested cleanup reporting. Never ask to rerun the same blind metered test.
- **Status:** **Practice reinforced; real Python VM outcome unverified.** Historical context in [P5H runtime evidence](P5H_RAILWAY_SANDBOX_VM_PIVOT_2026-11-20.md).

### LL-04 / LL-07 — A metered VM was wasted by a script portability assumption
- **Observed:** First explicitly approved disposable Railway Sandbox VM exited with `UNSUPPORTED_PYTHON_PATH` **before** Bubblewrap ran; the script assumed Python must reside under `/usr` or `/bin`. The VM was verified destroyed. Owner then separately approved a second single-use VM; a corrected interpreter-independent synthetic shell probe passed.
- **Lesson:** "Unsupported path" was a **script preflight false negative**, not proof that the VM kernel blocked isolation. A green mocked CLI is also not a real VM test.
- **Prevention:** Review guest interpreter/symlink/runtime assumptions and mock the CLI's success/failure/deletion paths before starting metered compute; preserve an exact maximum of one VM per consent; verify deletion by readback. Keep separate phases for Bash OS isolation and Python/pypdf compatibility.
- **Status:** **VM OS isolation verified in second real guest; Python PDF worker not verified.** VM v2 returned `sandbox_synthetic_smoke_passed=true`, `python_pdf_worker_verified=false`, `bank_runtime_activated=false`, `sandbox_destroyed_verified=true`. [PR #239](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/239), [PR #240](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/240).

- **20 Nov later result (LL-03/04/05 applied, no distinct new rule):** Owner's second separately approved on-demand VM attempt returned `stage=GUEST_PROBE`, `vm_creation_confirmed=true`, `vm_destruction_verified=true`; read-only follow-up inventory showed `active_sandbox_count=0`. Setup and trusted-file upload were reached, but the original guest launcher hid whether Bubblewrap started or the in-jail Python/pypdf process failed. **The one-use metered consent was consumed.** Prevent further blind VM expenditure by testing fixed jailed Bash launch and in-jail Python/pypdf import as separate phases under the **same** unchanged no-network/readonly policy before the full guest security probe. No change to live financial flags. [Scoped real-VM evidence](P5H_CHAT09_EPHEMERAL_PYTHON_VM_BRIDGE_2026-11-20.md).

### LL-05 / LL-06 — Security acceptance and functionality were conflated
- **Observed:** The **standard API container** returned `JAIL_CANNOT_START`; the isolated **Railway VM** later passed the Bash-only OS containment test. Neither result proves the real in-VM `pypdf` interpreter, original BAHL layout reconciliation or owner-visible bank figures.
- **Lesson:** The actual boundaries are separate: authenticated Google source, safe untrusted PDF execution, supported reconciler, source identity/sha, truthful display. Fix a blocked link instead of calling unrelated infrastructure milestones completed.
- **Prevention:** Each status report has **Passed**, **Not yet tested** and **Not enabled** fields; route real PDFs only after verified parser containment. No owner bank data in public GitHub logs, PRs or artifacts.
- **Status:** **OS smoke passed on VM; live bank pipeline remains off.** [Issue #222](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/222).

### LL-08 — Data semantics and privacy are harder requirements than UI polish
- **Observed:** Verified historical statement UI can exist without a source reader; a ledger built from gross credits/debits alone would falsely imply current spend or income.
- **Lesson:** An unknown number must remain unknown. Original Google Drive remains read-only; make organization/copies in separate approved storage only.
- **Prevention:** Label historical as-of dates and source coverage; never sum duplicate/overlapping statement periods, reinterpret transfers as earnings, or rewrite original files.
- **Status:** **Binding rule; keep verifying with genuine source fixtures.** [P6 plan](P6_PRIVATE_OWNER_MVP_MINIMUM_RELEASE_2026-11-20.md).

### LL-09 — Too much duplicated "latest" documentation undermined continuity
- **Observed:** `AGENTS.md`, `AGENT_START_HERE.md`, `docs/CURRENT_HANDOFF.md` and `docs/PROJECT_STATUS.md` accumulated long chronological prefixes; historical "next actions" remained visible after being superseded.
- **Lesson:** Longer notes can make a new chat *less* informed. The assistant must consult the concise current rules and latest verified main/runtime state, not just the first stale sentence.
- **Prevention:** Maintain **this file once** for learned practices, the P6 plan for scope, and the current handoff for latest actual state. Startup docs link here instead of copying the full lesson list. Preserve old incident detail via stable links and only append when truly necessary.
- **Status:** **Process established by this change.** Existing large historical docs remain archival; do not bulk-rewrite or erase evidence in this PR.

### LL-10 — One unrelated CI infrastructure failure is not a product regression
- **Observed:** [PR #237](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/237) initially failed after 1,446 passing tests because a disposable PostgreSQL restore rehearsal did not complete in GitHub Actions. Rerunning failed jobs on the same head passed; new sandbox-specific tests did not fail.
- **Lesson:** Read failing test names/logs first. Never change safety code or relax tests to treat an unrelated environmental hiccup as solved.
- **Prevention:** Investigate failure by name and stage, preserve full CI evidence, allow one justified same-head rerun, and do not merge while required checks are red.
- **Status:** **Adopted; that PR subsequently merged with green CI.**

### LL-11 — Source-first adapter design, not synthetic-first assumptions
- **When/evidence:** 20 November 2026, Personal CFO owner request to consolidate actual Google Drive documents into the CFO dashboard; [P6 read-only CSV source pipeline PR #244](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/244).
- **Observed:** The already connected approved Personal CFO Drive folder was directly accessible with the live read-only Drive connector. It held actual bank CSVs, encrypted PDFs, tax returns and an inventory workbook. Real-source inspection immediately established a supported 7-column CSV bank layout and revealed that the previously assumed PDF layout might differ from a genuine owner bank file. No documents needed to be reuploaded.
- **Root cause confidence / impact:** Repeated assumptions about source inaccessibility led to excessive infrastructure design and owner-visible empty dashboards. Direct connector access was tested; whether the existing app has all PDF execution gates remains separately unverified.
- **Prevention:** In each new financial feature, first verify exact approved source inventory through authorized read-only tools, inspect representative real format privately, then implement only source-compatible bounded validators. Never put private amount/identifiers/filenames, source bytes, passwords or connector responses in public GitHub or CI. Keep bank debits/credits distinct from classified income/spend.
- **Verification/status:** **Adopted** with one privately reconciled genuine bank CSV and a source-backed route candidate; production source ingestion must still be proven separately from a successful code merge.

## How to record the next lesson (copy this compact template)

```md
### LL-XX — Short behavioral rule
- **When/evidence:** YYYY-MM-DD, link to issue/PR/verified test (no private data).
- **Observed:** What actually happened, distinct from an assumption.
- **Impact/root cause confidence:** User cost and known vs still unproven cause.
- **Prevention:** What we will do differently *before* next similar task.
- **Verification/status:** Evidence the preventive measure works; open / adopted / verified.
```

**Keep this file actionable:** update an existing LL entry for repeated symptoms; add a new ID only for a genuinely distinct failure mode. Do not store passwords, account numbers, financial amounts, original document names, authentication material, private file hashes or raw diagnostic logs. A future chat should be able to review this file in minutes and change its behavior immediately.
