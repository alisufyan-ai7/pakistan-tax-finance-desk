# P5H Linux PDF OS-jail hardening — candidate, not acceptance

20 November 2026. Parallel critical-path work for [#222](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/222). The original `private_bahl_pdf_worker.py` child used resource limits but no Linux no-network namespace.

## Implemented and intentionally default-off

- New `private_bahl_os_sandbox.py` constructs a fixed, no-shell Linux bubblewrap profile with `--unshare-all` (including network and PID), no capabilities, `--clearenv`, a fresh temporary root, read-only Python runtime and app code only, isolated `/tmp`, fresh `/proc` and `/dev`. Nothing in host `/etc`, Railway secrets or original PDF paths is bound into the child; PDF/password still travel only through bounded private stdin and stderr remains suppressed.
- Dockerfile candidate installs bubblewrap; actual Railway kernel namespace support is **not yet attested**. The entrypoint does not invoke the reader until the existing P5H historical flags and the new `P5C_BAHL_OS_JAIL_ENFORCED` review switch are separately enabled.
- When owner historical report mode is set, the PDF parser **must** construct this jailed command and fails closed if the reviewed profile, binary, trusted executable/app path or kernel sandbox is unavailable. The old unjailed child remains allowed ONLY for local isolated synthetic fixture tests without P5E report runtime.
- New synthetic negative tests assert the plan uses no network or host root, cannot silently fall back, and rejects missing jail/profile/binary/wrong paths. They **do not** execute an actual jailed process or prove hostile PDF security.

## What still must happen before the bank endpoint can be switched on

1. Run inside the exact existing Railway image/container as the deployed low-privilege runtime owner and prove user+PID+network namespaces, no outbound connections (including DNS/TCP), no access to credentials or host/mounted files, fresh read-only root, no writes outside scratch, process-tree termination and per-request cleanup. If `bubblewrap` cannot create namespaces in Railway's environment, **do not disable sandboxing to make the test pass**. Choose a separately reviewed isolated worker architecture with appropriate container security instead.
2. Independently test adversarial PDF samples, malformed/oversized/page-bomb cases, pypdf security/dependencies, correct password absence/rejection and exception/timeout memory/log redaction. Confirm no dangerous interpolation of secrets into command line, shell or environment.
3. Revisit current live `APP_DATA_MODE=synthetic` and exact owner MFA/CSRF/Origin/route/no-sensitive-access-log browser ingress before approving flags; perform genuine supported Bank AL Habib layout review in owner-private storage only, with no real statements in GitHub/CI.
4. A signed G3/G2 release acceptance is still mandatory. Only once it passes may the separate P5E/P5G/P5H service flags be considered, and historical values must remain clearly dated and gross movements (NOT current cash, income/expenses, tax or full ledger).

**Warning:** Installing or testing bubblewrap is engineering progress, NOT independent certification; default-off behavior is the safety property. Original approved Drive folder remains immutable. All tests in public repo are fictional.
