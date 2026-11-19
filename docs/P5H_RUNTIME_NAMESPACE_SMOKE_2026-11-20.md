# P5H no-network OS-jail smoke — operator-attended, synthetic only

20 November 2026. This module is an **independent smoke input**, not independent G3 approval. Current backend image includes bubblewrap after Dockerfile hotfix #231; real kernel/runtime sandbox execution has not been confirmed.

After GitHub CI and exact-head Railway deployment succeed, a trusted authorized operator may use Railway's existing backend SSH entrypoint for a *single safe synthetic test*, without opening originals or typing any passwords. This command sets three **process-local** switches for the test only; it does not change Railway service variables:

```sh
P5H_OPERATOR_SANDBOX_PROBE_ONLY=1 \
P5C_BAHL_OS_JAIL_ENFORCED=1 \
P5C_BAHL_SANDBOX_PROFILE=bubblewrap-v1 \
python -m app.private_bahl_sandbox_probe
```

Run this command **in the deployed `/srv/backend` directory inside the existing Personal CFO API container**, not in the frontend service, public shell, production bank reader or source Drive folder. The probe invokes only a constant-synthetic subprocess: confirms no TCP egress, no host `/etc/passwd` or home exposure, read-only app code and the availability of Python/pypdf within the same namespace profile. It does not query Railway variables, PostgreSQL, Drive, Google, source filenames, OAuth grants or owner's files. Stdout is redacted booleans only; stderr discarded. It fails closed if bubblewrap cannot create the namespace.

**Required acceptance:** `sandbox_synthetic_smoke_passed=true`; if false, keep *every* P5E/P5G/P5H activation flag OFF and review runtime capabilities in approved infrastructure. Even if true, independently review malware/PDF failure cases, process tree cleanup, resource/cgroup confinement, exact no-log ingress and genuine bank layout acceptance before any bank figures become live. Do not self-approve G3 from a single smoke.

## Live operator observation — 20 November 2026

The owner successfully executed the SSH command in the existing Railway `personal-cfo-api-preview` container using CLI version 5.74.1. The probe returned `sandbox_synthetic_smoke_passed: false`, `g3_independent_review_complete: false`, `historical_bank_runtime_activated: false`. This is a **real runtime failure**, not a CLI/login failure. The original probe intentionally hid the underlying reason; do not claim an inferred root cause (such as blocked user namespaces) without new evidence. No financial file, PDF password or account information was used.

P5H follow-up delivers a minimal **allowlisted reason code**, with no raw child stderr, exception contents, paths, Railway environment, Google token, owner document, file names or amounts. Re-run the **same original** operator command only after exact-head backend CI and Railway deployment succeed; the JSON then contains a `safe_failure_reason` when false:

| Code | Safe interpretation | Direction |
|---|---|---|
| `PROBE_NOT_ENABLED` | Process-local probe authority missing | Verify original command syntax |
| `JAIL_COMMAND_UNAVAILABLE` | Reviewed bubblewrap launch command cannot be constructed (binary/path/profile prerequisite) | Check image/profile; do **not** bypass jail |
| `JAIL_CANNOT_START` | Same jailed Python cannot boot a fixed minimal synthetic test | Investigate actual Railway namespace/mount permissions; no document access |
| `ISOLATED_CHILD_FAILED` | Minimal Python boots in jail, but the full synthetic pypdf/isolation child did not complete | Review jailed interpreter imports/runtime and child script |
| `CHILD_TIMED_OUT` | Synthetic launch exceeded fixed time budget | Examine available runtime limits; leave off |
| `CHILD_RESULT_INVALID` | Bounded synthetic child result is missing/malformed | Review fixed probe/result contract |
| `ISOLATION_POLICY_FAILED` | A required denial check returned false | Treat as containment failure; leave off |
| `JAIL_LAUNCH_ERROR` | Controlled launch failed unexpectedly | Verify base runtime, without logging sensitive state |

None of these codes automatically enables owner financial data or approves G3. No repeat OAuth, original Drive changes, paid database or bank password is needed for this diagnostic.
