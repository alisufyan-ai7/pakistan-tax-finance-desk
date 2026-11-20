# P5H: Railway container bubblewrap failure — narrow isolation architecture decision

**Observed 20 November 2026. Owner-attested actual existing deployment, no user documents processed.**

## Evidence; no inference promoted to proof

Existing `personal-cfo-api-preview` Railway service in environment `development` is healthy as an API. Owner used authenticated Railway CLI 5.74.1 to execute two **synthetic-only** runs of `python -m app.private_bahl_sandbox_probe` with temporary process-local `P5H_OPERATOR_SANDBOX_PROBE_ONLY=1 P5C_BAHL_OS_JAIL_ENFORCED=1 P5C_BAHL_SANDBOX_PROFILE=bubblewrap-v1`:

1. First: `sandbox_synthetic_smoke_passed=false` (unclassified).
2. Second after PR #237 deployed: `sandbox_synthetic_smoke_passed=false`, **`safe_failure_reason=JAIL_CANNOT_START`**, `g3_independent_review_complete=false` and `historical_bank_runtime_activated=false`.

The fixed minimal jailed Python child cannot start under the **full existing command profile**, even without PDF parsing, owner files, passwords or Google/database access. This proves an OS-jail **launch blocker in the current deployed service**. It does **not** identify whether denial happened at user, mount, network, PID, cgroup namespaces, root-mount setup, or another launch step; never claim the exact kernel syscall was proven. Do not attempt repeated unsupported flag combinations or drop `--unshare-net`, mounts, `--clearenv` or root isolation to make this security boundary silently pass.

Railway public user reports describe bwrap namespace denial in standard containers; Railway **Sandboxes are separate isolated Linux VMs**, not the standard service container. A Railway staff response says a previous Sandbox VM user-namespace bug was fixed. Neither report establishes that our specific image, code or private data pipeline already works. References: [Railway Sandboxes](https://docs.railway.com/sandboxes), [Railway VM namespace issue & employee response](https://station.railway.com/questions/codex-sandbox-fails-bubblewrap-cannot-c-71a2988d), [standard container user report](https://station.railway.com/questions/hobby-supported-sandbox-for-image-decod-e68509ef).

## Product decision: stop attempting in-container bwrap; maintain minimal P6

- **Keep live P5E, P5G and P5H reader flags OFF.** Continue existing owner MFA, approved read-only Google OAuth, original source preflight, manual metadata refresh and the newly deployed historical evidence UI in read-only state. Original owner Drive folder remains unmodified; no broad imports, current cash guesses or leaked sensitive debug output.
- For untrusted, password-protected bank PDFs, test *one disposable Railway Sandbox VM* with isolated private networking (`networkIsolation=ISOLATED`), **no user source bytes, no Google/DB credentials, no network/persistence permissions supplied**, short idle TTL and hard destroy. Boot an OS-isolated Python process with the **same bwrap-style `--unshare-all`/no-network and readonly-root** policy. Use fixed synthetic code to confirm child cannot reach network, host files or credentials. Reject on any missing denial; do not use the VM's outer network mode as a substitute for child network denial.
- Railway's `ISOLATED` mode still has **outbound internet**, it merely denies access to Railway services on the project's private network. Thus it is **not equivalent to no network**. PDF bytes may enter only after bwrap (or equally restrictive validated VM in-guest enforcement) passes in the real VM. Never put PDFs/passwords in CLI arguments, GitHub, process environment or logs. Prefer bounded SDK `exec` stdin/file API; enforce source SHA + version pinning at download and result, password transient stdin, no persist/caching, child limits, fixed JSON and encrypted result custody.
- Once VM synthetic test succeeds, implement the **smallest** app handoff: existing authenticated API retrieves pinned Drive source, sends only file bytes and transient password to an ephemeral isolated VM with **no OAuth/DB credentials**, receives only bounded reconciled historical statement JSON, validates arithmetic/source identity, and destroys VM in a `finally` path. No long-running paid worker, extra database, background poller or second public ingress. Original source remains read-only.
- If VM cannot enforce the child sandbox, stop PDF ingestion and consider a compatible minimal isolated execution provider rather than running adversarial PDFs in the original API container.

## Cost / permission: one explicit owner approval only

A new Railway Sandbox is metered at VM rates, **$50/GB RAM-month + $50/vCPU-month + $0.05/GB outbound**, charged by actual use while running; Railway's official example is ~**$0.03 compute for a 20-minute task** at 1 GB memory, 30% vCPU, excluding egress. No fixed cost claim is made for this one test. Sandboxes share the plan's included usage. Always destroy afterwards. See [Railway official pricing](https://docs.railway.com/sandboxes#pricing).

**Do not instantiate even the disposable VM before explicit user authorization for a metered resource.** No other new permission is needed merely to keep developing non-billable code, documentation or synthetic CI tests. Ask only this decision: *May Personal CFO create and automatically destroy one short-lived metered Railway Sandbox VM to prove safe, no-network PDF isolation?* Approval for this test is **not** approval for unrestricted recurring sandbox expenditure or live ingestion.

## Acceptance gates after approval (not a new ceremonial roadmap)

1. One no-data VM synthetic probe: VM created with zero project secrets, `ISOLATED` private network, limited resources/TTL; exact code SHA and runtime recorded, no raw log dumps.
2. Same approved child isolation policy verifies no TCP/UDP egress, host file/cookie/secret exposure, writable trusted code, or host process visibility; sandbox always destroyed even on error. A green result is **not** self-approval for any actual private document.
3. Developer CI exercises synthetic realistic BAHL cases and hostile layout negatives; real file must pass pinned SHA/version, supported format, transaction/running balance reconciliation and owner review labeling. Once done, enable first historical statement results, not unsupported current cash/spending.
4. One encrypted *full* DB backup + disposable restore, then existing approved review comment migration `0024` and on-demand source hash migration `0025` when their corresponding live features require them. Avoid introducing new cost-dependent database resources without approval.

## Ownership

Track operational outcome in [GitHub issue #222](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/222) and [lean P6 release plan](P6_PRIVATE_OWNER_MVP_MINIMUM_RELEASE_2026-11-20.md). Do not ask the owner to repeat the failed standard-container probe. Bank reader is **not live** until later explicit acceptance.

## First approved metered VM — executed and deleted; result is a script preflight failure

**20 November 2026, operator-provided authenticated Railway CLI output.** Under explicit approval for exactly one metered test VM, a local Mac operator ran `personal_cfo_railway_sandbox_once.sh` against Personal CFO `development`. A VM was actually created with ID `4bd59b74-8849-4c65-b8ab-cf90ba5d78f1` (ID is not a secret). The tool reported:

```json
{"contract":"personal_cfo_one_time_railway_vm_isolation_v1","sandbox_synthetic_smoke_passed":false,"reason":"UNSUPPORTED_PYTHON_PATH"}
{"sandbox_destroyed_verified":true}
```

**Precise finding:** The v1 shell checked `PYTHON_BIN="$(command -v python3)"` and unconditionally rejected a Python executable that does not begin with `/usr/` or `/bin/`. Railway's isolated VM **did provide** a `python3` executable (otherwise it would emit `PYTHON_UNAVAILABLE`), but its chosen executable path did not satisfy that v1 allowlist. The test **stopped before bubblewrap ran**, so it is **not evidence** that VM kernel user/network namespaces are unavailable. The actual executable location and symlink target were neither captured nor required. No owner PDFs, bank passwords, Drive credentials, database credentials or source files were processed. Destruction was explicitly requested by the script and its absence from the active VM list was verified. No VM is running as part of this attempt.

**Corrected v2**: The test is now interpreter-path-independent for the **OS-jail kernel smoke**. It uses a fixed trusted `/usr/bin/bash` ELF (or a `/bin/bash` symlink resolving into `/usr`) and runs fixed synthetic Bash-only checks within the **unchanged, fully enforced** `bwrap --unshare-all` jail; `/usr` and libraries mounted read-only, ephemeral root and procfs, **no** `/etc`, `/home`, `/root`, `/var`, `/opt` or project secret mount, `--clearenv`. Checks in the child include failed `/dev/tcp` connection, only loopback interfaces in the fresh `/proc/net/dev`, host-path concealment, attempted `/usr` write denial **plus** read-only `/proc/self/mountinfo` record, and absence of known sensitive environment names. All six constant booleans must be true. `python3` runs **outside** the jailed subprocess only to validate fixed JSON, so an arbitrary VM Python alias cannot block testing Linux sandbox compatibility. This **does not yet prove the PDF worker Python environment or pypdf import**; those remain separate gates. When unsupported, fail closed with `TRUSTED_SHELL_UNAVAILABLE` or `JAIL_CANNOT_START`, not an unjailed fallback.

Verified offline (NO VM created): `bash -n` for both shell files, plus a synthetic mocked `railway` CLI and `bwrap` running the full one-VM cleanup script: both success and intentional jailed-launch failure returned the expected **fixed JSON**, called exact-ID destroy and verified deletion. These are **mock tests**, not a live guest kernel security attestation. SHA256 of the distributed v2 shell is `a2cba2783e2c5c6ec648431f7aa5e71c51c7aa70b10269307e62d3bd5a27167f` and its output contract is `personal_cfo_one_time_railway_vm_isolation_v2`.

**Authorization boundary:** The owner's first authorization was for **exactly one** metered VM, now consumed. Do not run v2, create/retry/fork a VM or incur another charge until the owner separately authorizes **one additional** short-lived metered synthetic-only VM. A new successful OS-jail smoke does **not** authorize real PDF import or change production flags. Keep read-only Drive originals unchanged and all live historical bank processing OFF.
