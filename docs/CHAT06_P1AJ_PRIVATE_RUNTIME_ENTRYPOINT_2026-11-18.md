# Chat06 P1AJ — gated existing-Railway-service owner login runtime

**Scope and owner mandate (18 Nov 2026):** Advance real Personal CFO owner login and single-folder Google metadata activation without asking owner to redo encrypted backups or unnecessarily creating another paid Railway service. Source-only security implementation; **not** authorization to expose public login, apply the staged Google client secret or ingest original financial documents.

## What has changed

The existing `backend/Dockerfile.preview` now launches `app.private_runtime_entrypoint:app` with one Uvicorn worker, `--no-access-log --no-server-header --no-proxy-headers --log-level warning`. **Default mode remains exactly the pre-existing `create_preview_app()`**: only read-only synthetic `/healthz` and `/internal/preview/status`. No new Railway variables are required and the existing private service and public mobile preview stay functional.

Only an explicitly reviewed `P1AJ_OWNER_LOGIN_RUNTIME=1` combined with `P1AJ_G2_EXACT_INGRESS_REVIEWED=1`, `P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED=1`, synthetic mode, Google network disabled, and **all** previous P1AI/P1Q/P1N/P1S review, isolated DB, least-privilege SQL, existing owner escrow and TLS/recovery checks enables a combined ASGI process. It runs both the preview and owner lifespan preflights, then sends **only three exact internal paths** to the existing owner MFA app: login POST, session GET, logout POST. All else including Google callback/start, finance, recovery operator and public browser routes stays unmounted. Failed owner startup aborts the entire service, not a degraded private login.

The active frontend `nginx.railway.conf` and Dockerfile are unchanged: **no publicly callable owner route exists yet**. Public UI does not solicit password, TOTP or financial original data. Existing secret fields in Railway are untouched.

## Evidence

`backend/tests/test_private_runtime_entrypoint.py` enforces default-off shape, fail-closed mismatched/partial flags, exact three-route routing and rejected aliases/callbacks, both preview and private nested lifespan, Docker no-access-log/no-untrusted-proxy flags and no public frontend login. Full exact-head backend CI and disposable PG18 is required before merge.

## Next dependency

1. Independently review the exact frontend Nginx reverse-proxy candidate, bounded request size/rate limits, replacing (not forwarding) gateway key, Host/origin/proto/path overrides, and Railway edge/upstream logs. **Do not claim that `--no-access-log` disables Railway platform logs.**
2. Prepare explicitly approved named Railway owner-login configuration without changing `APP_DATA_MODE=synthetic`, applying unrelated Google staged changes or reintroducing true finance endpoints. Verify a reviewable rollback and authenticated operator smoke test before exposing login.
3. After G2 secure ingress and actual MFA login/session acceptance, add a real-compatible session-bound Google code exchange (distinct from P1T synthetic-only rehearsal), encrypted grant custody, exact callback and restart-safe metadata index for only the approved folder. One actual Google browser consent must be performed by the owner. Authentic file media/tax/financial uploads still require G1/G3.
4. Respect user confirmation that encrypted recovery files are copied in two places; no repetitive manual copy/restore exercise during source-only engineering. Formal real restore acceptance remains tracked separately as unverified for a later security release checkpoint.

Refer to [merged P1AH #162](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/162), [merged P1AI #163](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/163) and [Chat06 final prior handoff](CHAT06_FINAL_ENGINEERING_CHECKPOINT_2026-11-18.md).
