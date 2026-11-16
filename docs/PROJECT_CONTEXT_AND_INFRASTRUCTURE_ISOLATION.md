# Mandatory Personal CFO project-only context and infrastructure boundary

**Effective:** 2026-11-16. **Decision:** explicitly requested by the owner. **Applies to:** every ChatGPT conversation in this project, all coding/research agents and successor chats working on this repository. Read immediately after [root AGENTS.md](../AGENTS.md). **Priority:** overrides any older, broader suggestion to use connected tools freely or to infer project facts from account-wide history.

## 1. Strict context isolation

**Permitted context, and only these sources for project-specific facts:**

1. **This ChatGPT Personal CFO project only:** messages in this project, explicitly included project files/knowledge, and project-only memory *if enabled and verifiably scoped to this project*. A new instruction from the owner in this same project is valid immediately but must be recorded in GitHub for persistence.
2. **This project's GitHub repository only:** `alisufyan-ai7/pakistan-tax-finance-desk`, current `main`, its own docs/AGENTS/decisions/handoff, issues, branches, PRs, CI/Actions and owned synthetic fixtures. Engineering implementation state is established by actual current GitHub evidence, not memory.
3. **Public external references when necessary:** official software documentation, legal/FBR sources and published third-party material can be consulted for *general technical or legal facts*, clearly cited and not treated as the owner's personal context. Public research cannot authorize interacting with any user account or uploading private information.
4. **External accounts/services only when individually allowlisted:** a service-specific approval by the owner for **this project**, naming provider, project/resource, purpose, and permitted action. Consent to use GitHub does NOT authorize Vercel, Railway, Neon, email, other repositories, other projects, billing, remote hosting or private credentials.

**Explicitly prohibited as a Personal CFO source:**

- ChatGPT **account-wide Memory** or saved information gathered from conversations outside this Personal CFO project, even if available to an agent.
- Prior chats, project knowledge, connected drives/files, discussions, identities, preferences, infrastructure, accounts or personal details belonging to **other ChatGPT projects**.
- Other repositories or issues, other deployed apps or databases, and provider-wide cloud inventories as a way to choose environments for Personal CFO.
- Access to unrelated accounts, live databases, emails, calendars or third-party applications merely because a connector is installed or authorized at the account level.
- Guessing/borrowing budgets, domain names, environments, cloud projects, credentials or product requirements from another project.

**No crossover rule:** Do not import knowledge or data from other projects, or export this project's financial facts, code secrets, files or agent memory into another project. When the requested fact cannot be verified from the allowlist, say it is unknown. Do not silently fill it using account-level Memory.

## 2. Provider / resource approval firewall

1. First check **the in-repository owner-approved resource register** and the specific authorization in the current Personal CFO conversation. No provider is approved solely by existing account access, an installed plugin, or a previous project's deployment.
2. Before any external project/service/database/paid sandbox or persistent resource is **created, modified, deployed, connected, billed, deleted or exposed**, require this project's owner authorization naming the provider/resource type and scope. General instruction to "set up a development environment" permits preparation, code, synthetic local tooling and researching providers, **not an automatic switch between paid cloud vendors or reuse of an unrelated existing provider project**.
3. If an authorized provider returns 403, is unavailable or cannot offer the needed runtime, **stop**, disclose the limitation and request authorization for a specifically named alternative. Do not provision another vendor or select a different existing cloud project to route around permission checks.
4. For an approved infrastructure resource, use **new explicitly named Personal CFO-only isolated resources**, least-privilege access, private networks, bounded cost, synthetic-only data and `APP_DATA_MODE=real` fail-closed. Never target or introspect unrelated resources as a fallback.
5. Docker and PostgreSQL can run in a permitted local/container environment without involving unrelated account projects. GitHub CI is an optional independent test checkpoint when necessary, not proof that a cross-provider workspace can be used.
6. Track any approved development resources by provider, authorized project, nonsecret resource identifier, cost/lifecycle, owner consent and deletion policy **in a private approved resource inventory**, never publish credentials, private DSNs, payment details or other sensitive external account information into this currently public repository.
7. For errors or accidental out-of-scope provisioning: stop further activity; disclose which **new project-specific** resource was created and its running/cost status; request authorization before deleting persistent data or using the resource for anything else. Never touch other projects to clean up a mistake.

## 3. Verification and handoff workflow

- At each new chat, **read this policy first**, then the current GitHub `main`, [AGENT_START_HERE](../AGENT_START_HERE.md), [continuity protocol](CHAT_CONTINUITY_PROTOCOL.md), owner [decisions](PROJECT_DECISIONS_AND_SCOPE.md), [project status](PROJECT_STATUS.md), and newest [handoff](CURRENT_HANDOFF.md). Use project-visible context only.
- Do not assume account-level ChatGPT Memory or global saved context is disabled just because these repository instructions exist. **Repository policy directs agent behavior; it cannot alter ChatGPT product-level Memory settings.** Project-only Memory configuration, when available, is a separate owner-controlled UI setting. If its state is unknown, abstain from using non-project memory.
- Distinguish public GitHub facts, project conversation decisions and official external research. The current owner's instruction may supersede GitHub docs until recorded; older GitHub docs cannot authorize ignoring the current explicit owner boundary.
- After any substantial project work, commit sanitized decisions/requirements/status to this repo, so future chats **do not need any account-wide or cross-project context**. Current verified technical source remains the repo, not remembered account facts.
- Maintain the existing privacy gates: real personal financial documents, identities, passwords, tax figures and correspondence stay outside public GitHub; the prototype cannot handle real records until G1–G3 independently pass.

## 4. 2026-11-16 incident and resolution

During a request for a self-managed development environment with Docker/PostgreSQL, the assistant attempted a separate Vercel Sandbox project, received a **403 permission denial**, then provisioned a distinct Railway development project and PostgreSQL service without first asking whether Railway was an acceptable provider for Personal CFO. **This was an unapproved provider substitution**, not an authorization to access other projects.

- The Railway resources were separately named for Personal CFO; the assistant did not intentionally import other projects' data or deploy this finance application there. However, **creating provider resources in the same account without explicit Personal CFO provider authorization was inappropriate**.
- The existence of this environment **does not approve Railway**. Do not use it for development or copy financial data into it until the owner specifically authorizes continued use, or separately authorizes deletion. This document records no sensitive resource IDs or cloud credentials.
- Continue project-specific GitHub/code work in the meantime. When an independently permitted development runtime is available, use it for Python/Docker/PostgreSQL tests, without crossing projects.
- No change to software security status: G1-c full encrypted canonical PostgreSQL migration remains incomplete; real data mode stays disabled.

## 5. Project instructions snippet (for owner-controlled ChatGPT Project settings)

The following can be copied into this ChatGPT project's own instructions. GitHub agents follow the policy above even if the UI does not permit changing Project Memory settings:

> **Personal CFO isolation rule:** Use only conversations, files and project-only memory belonging to THIS Personal CFO ChatGPT project, plus GitHub `alisufyan-ai7/pakistan-tax-finance-desk` as the canonical engineering/decision source. Never use ChatGPT account-wide Memory, other chats/projects, their files, repositories, credentials, cloud resources, or assumptions. Public official documents may support general research but never add personal context. Do not access or create infrastructure in Vercel, Railway, Neon or any other provider without my specific Personal CFO authorization for that provider and resource. If an approved service denies permission, stop and ask rather than switching providers. Store durable project decisions in this repo, synthetic/public-safe only; keep real financial data private and `APP_DATA_MODE=real` disabled until release gates pass.
