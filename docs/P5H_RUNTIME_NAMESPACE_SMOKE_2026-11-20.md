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
