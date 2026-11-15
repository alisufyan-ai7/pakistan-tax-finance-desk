# Mandatory GitHub continuity and handoff protocol

**Status:** Owner-approved standing project rule (2026-11-16). Applies to ChatGPT, Claude, coding agents and any successor conversation in this project. This file, root `AGENTS.md`, `AGENT_START_HERE.md` and the latest project status are the canonical orientation material.

## Rule: no knowledge should depend on a single chat window

**GitHub is the source of truth for the entire project and all future direction.** Every new chat must be able to independently reconstruct *verified implementation state, owner decisions, ideas, constraints, unmerged work, blockers and next steps* from this repository alone. Conversations, screenshots and assistant claims are not authoritative when they conflict with latest `main`, issues and CI.

It is neither necessary nor desirable to commit private full chats or credentials. Preserve their **material decisions, requirements, reasoning/alternatives where consequential, approvals, tradeoffs and follow-up work** in well-maintained committed Markdown. New details from current discussions MUST be added before work is considered done.

### Mandatory order at the START of any new session

1. Confirm the **exact repository** `alisufyan-ai7/pakistan-tax-finance-desk` and current `main` HEAD. Never mix this financial project with unrelated trading projects/repositories.
2. Read root `AGENTS.md`, `AGENT_START_HERE.md`, `docs/PROJECT_STATUS.md`, `docs/PROJECT_DECISIONS_AND_SCOPE.md`, `docs/CFO_PLATFORM_ARCHITECTURE.md`, `docs/REQUIREMENTS_COVERAGE_MATRIX.md`, `docs/ROADMAP_AND_ACCEPTANCE.md`, `docs/SECURITY_PRIVACY.md` and **last/latest** `docs/CURRENT_HANDOFF.md` entries. Follow relevant implementation guides and source/legal indexes if the task needs them.
3. Inspect open GitHub issues, unmerged PRs, current CI runs, latest successful *exact-head* CI, branch versions and any active deployment; read latest evidence rather than trusting old statuses.
4. Build a brief factual state: done/tested/merged, in-progress, P0 blockers, latest owner policy, dependencies, next owner-independent action. Continue without repetitive clarification if information is recorded.
5. Preserve actual work: minimal reviewable branch → tests + quality/security acceptance → PR → merge when validated → confirm `main` and docs. Never silently enable real financial data.

### Mandatory DURING each session

- Record important new user requirements and research conclusions in `PROJECT_DECISIONS_AND_SCOPE.md` or focused research/decision docs, and reflect status in requirements matrix/roadmap.
- After meaningful progress, update corresponding implementation guide, tracked issue, `PROJECT_STATUS.md`, `CURRENT_HANDOFF.md` and `AGENT_START_HERE.md`. A code PR must not depend on ephemeral chat context.
- Keep verified facts separate from unverified claims, prototypes, guesses, wish lists, and feature ideas. Include evidence refs and scope limits, particularly money/tax/advice/security.
- Record substantive changes in priorities and reasons, and revise superseded documentation links instead of creating contradictory `latest` instructions.
- When possible, keep a single active substantive engineering focus and merge continuously; minimize owner steps and fees.

### Mandatory BEFORE ending or approaching the conversation cap

Commit a self-contained handoff with:
- date, main SHA, PRs merged/open and exact CI links/results;
- completed features versus **not** completed security/tax/user-facing features;
- owner decisions, fixed operating constraints and broad future vision;
- known failure/recovery/rollback steps, secrets needed **by name only**, never their values;
- next owner-independent task with acceptance tests and blockers/approval boundaries;
- current source document locations, open issues, and any remaining in-progress branches;
- what evidence still needs to be obtained later from the owner, *without blocking coding*.

**Handoff acceptance:** a successor agent can take the next action by reading GitHub **without asking the owner to re-explain this chat**, while understanding exactly which facts remain unknown. If docs cannot be pushed, report that limitation clearly and do not claim continuity is ensured.

### Reusable new-chat instruction

> Continue the Pakistan Tax & Wealth Desk / Personal CFO project from GitHub `alisufyan-ai7/pakistan-tax-finance-desk` current `main`. GitHub—not earlier chats—is the source of truth. Read root `AGENTS.md`, `AGENT_START_HERE.md`, `docs/CHAT_CONTINUITY_PROTOCOL.md`, `docs/PROJECT_STATUS.md`, `docs/PROJECT_DECISIONS_AND_SCOPE.md`, `docs/CFO_PLATFORM_ARCHITECTURE.md`, `docs/REQUIREMENTS_COVERAGE_MATRIX.md` and the **latest** `docs/CURRENT_HANDOFF.md`; inspect issues, PRs and exact CI runs. Work on the highest owner-independent priority with synthetic data only, preserve all privacy/legal gates, test, merge and update the complete GitHub handoff before ending. Do not ask me to repeat decisions already documented. This is a private personal CFO first, extensible later.

## Public code / private finance boundary

Current GitHub intentionally PUBLIC for code/docs/synthetic fixtures only. Actual bank/FBR/broker statements, legal ID, financial amounts, user credentials and unredacted AI outputs must never enter the public repository or CI. A real-data release requires private deployment, encryption of legacy columns or secure replacement, key lifecycle, MFA/recovery, encrypted original vault, independently tested restore, PDF sandbox and audited tax rules. A docs update alone does not satisfy these gates.
