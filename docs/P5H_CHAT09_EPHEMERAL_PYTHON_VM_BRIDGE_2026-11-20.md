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

The connected Railway tools expose no Sandbox create/exec/destroy or service shell operation. The environment-scoped project variable RAILWAY_TOKEN has been privately configured on the existing API (only its name was inspected, not its value). The owner's first authorized process-local Python VM probe returned a generic failure; its resource state was not recorded. No source files or passwords should be passed, and a distinct real guest approval is still required before any source-specific test or live flag change.

The project plan and issue #222 track genuine source layout reconciliation, historical UI verification, and future per-document cost approval separately. No owner MFA/Google reauthorization or additional database/service was required for this source implementation. This PR uses only fictional and fake-transport tests; successful CI does not mean a real VM passed.

## 20 November: reported operator error and zero-cost diagnostic correction

The owner executed the approved process-local synthetic probe once and received only the constant P5H_REMOTE_SANDBOX_UNAVAILABLE. Independent Railway configuration inspection showed an environment-scoped project variable named RAILWAY_TOKEN now present on the API; its private value was not read. The API remains healthy. The generic message cannot establish whether the SDK created a VM, whether it was destroyed, or why Python did not report successful isolation. Treat **all three as unverified**; do not claim acceptance or ask for another paid creation on the already-consumed/uncertain permission.

The focused follow-up repairs the guest setup's missing mkdir precondition for /srv/backend/app, validates the SDK's official Sandbox.create/list APIs, and adds a strictly read-only --status-only command (lists active count only, never creates/destroys VMs). The metered path now preflights that inventory, refuses to create a second VM if another is active, and reports constant failure stages (SDK, creation, setup, file upload, guest probe, parser, cleanup) together with confirmed creation/cleanup booleans. No raw SDK exception, guest stderr, token, original file or password is printed. Synthetic tests cover these stages without billable resources.

**Stop point:** Check the new read-only inventory and actual status of any existing Sandbox before requesting fresh cost-scoped authorization for another VM. No owner source is needed for the read-only check. Do not set persistent activation flags and do not use the earlier failed command unchanged.

## 20 November: owner-performed zero-create inventory result

The owner ran the deployed read-only `--status-only` command through their authenticated Railway SSH session and returned the exact status contract `personal_cfo_p5h_sandbox_readonly_inventory_v1`: `active_sandbox_count=0`, `new_sandbox_created=false`, `original_document_read=false`, `bank_runtime_activated=false`. This confirms the SDK import, token-backed inventory access and no **currently active** Sandbox in that environment at check time. It **does not** establish whether the earlier failed probe briefly created/destroyed a VM, consumed billable compute, passed an isolated Python reader, or produced a reliable bank result. The previously authorized one-time guest attempt remains consumed/uncertain. No original PDF was supplied to the read-only operation. Keep owner-facing PDF processing OFF. The next actual Python isolation invocation is a **new metered test** and requires distinct cost-scoped owner approval; do not treat a zero active count as renewal of the original consent.

## 20 November: second approved real VM result — blocked guest probe, confirmed cleanup

The owner ran **one** newly approved, metered, synthetic-only VM probe followed by the read-only inventory command. The bounded result was:
- Failure contract `personal_cfo_p5h_sandbox_safe_failure_v1`; `status=BLOCKED`; `stage=GUEST_PROBE`; `vm_create_attempted=true`; `vm_creation_confirmed=true`; `vm_destruction_verified=true`; `original_document_read=false`; `bank_runtime_activated=false`.
- Follow-up inventory `personal_cfo_p5h_sandbox_readonly_inventory_v1`: `active_sandbox_count=0`; `new_sandbox_created=false`; `original_document_read=false`; `bank_runtime_activated=false`.

**Verified:** VM creation, guest setup and trusted-code transfer occurred before the probe, and that particular VM was destroyed and absent from the active inventory. **Not verified:** that the in-guest Bubblewrap command started, Python/pypdf ran inside the jail, or all guest security checks passed. No original statement or password was supplied. The second one-time VM authorization is **consumed**. Do not make a third VM or rerun the command without new explicit scoped approval.

The `GUEST_PROBE` code was one opaque subprocess acceptance step: nonzero exit, timeout or inaccessible output all mapped to the same stage. This PR adds **only synthetic-only, same-jail** launch markers for (a) a fixed jailed Bash, (b) a fixed jailed Python/pypdf import, before the full Python isolation probe. The guest's full `bwrap --unshare-all --clearenv` policy, zero PDF/password use and mandatory cleanup remain unchanged. Each phase is separately identifiable on the **next independently authorized real execution**. CI mocks are not genuine guest evidence; there is no promise that the static change itself fixes the runtime blocker.

**Owner-visible checkpoint:** no real historical BAHL PDF amounts yet. Continue to use only already verified historical CSV investment bank movements with honest candidate/unverified labels, preserving original Drive files and all existing owner MFA/finance gates.
