# P5H Chat 9 — default-off on-demand Railway VM PDF reader

This is a narrow continuation of issues #222 and #185. It does not activate bank-PDF processing, investment balances, source persistence or recurring paid compute. Read the current Chat 9 handoff and canonical lessons LL-01–LL-11.

## Secure app-to-VM chain

- The existing owner MFA/CSRF HTTP controller resolves ONLY an approved Drive folder file HMAC and independently pins revision plus exact source-byte SHA before invoking a PDF reader. Never change the original.
- A separately reviewed remote-mode flag makes the parent invoke Node 22 and the pinned Railway Sandbox SDK; the ordinary API container's known-failing Bubblewrap remains fail-closed and is NEVER bypassed.
- The remote SDK creates one ISOLATED five-minute-idle VM, without parent secrets in the guest. Its environment-scoped project token exists only in the parent process as RAILWAY_TOKEN. The VM installs Python/pypdf and Bubblewrap before touching any owner source.
- The VM receives only approved static code files. It runs Python and pypdf INSIDE the exact Bubblewrap no-network, read-only-root child, with a fixed synthetic probe proving loopback-only, denied TCP, hidden host paths/secret env and read-only code. Any failure blocks PDF bytes.
- Only after successful guest proof, the PDF and transient password reach the jailed child over ephemeral SDK stdin, in 16 KiB chunks, never argv/env, temporary files, GitHub or logs. Bounded JSON stdout is validated again by existing strict Python bank arithmetic/unknown-value rules.
- The VM is destroyed in a finally block and destruction is checked against the active Sandbox list BEFORE any result is accepted. SDK stdin or destruction incompatibility fails closed.

## Acceptance and cost

The owner's current approval covers ONE short-lived SYNTHETIC Python/pypdf VM review with auto-destroy, not an ongoing stream of billable on-demand invocations. All actual historical-report/VM/G3 flags stay OFF on Railway. The previous Bash-only guest smoke did not prove Python/pypdf or genuine BAHL parsing, so neither is claimed.

The connected Railway tools expose no sandbox create/exec/destroy or service shell operation. The owner must privately create an environment-scoped Railway project token and set it as RAILWAY_TOKEN on the existing API service (never send its value into chat). Only after the code has green CI and is deployed, the owner can invoke one process-local synthetic probe through their existing Railway CLI shell using the reviewed Node entrypoint; no owner originals or passwords should be passed. A successful synthetic probe must be independently observed before any source-specific test or live flag change.

The project plan and issue #222 track genuine source layout reconciliation, historical UI verification, and future per-document cost approval separately. No owner MFA/Google reauthorization or additional database/service was required for this source implementation. This PR uses only fictional and fake-transport tests; successful CI does not mean a real VM passed.
