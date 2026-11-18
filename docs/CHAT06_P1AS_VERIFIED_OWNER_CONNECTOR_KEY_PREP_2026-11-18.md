# Chat06 P1AS: owner connector key preparation VERIFIED (18 Nov 2026)

## Proven new checkpoint — latest handoff over previous Chat06 milestones

**Source of truth:** `main` at `51d73c0c14824eaa0ad4cc3a2fc3b62780afbad4` after [P1AR #176](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/176) and [P1AR #177](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/177). The exact-head [GitHub CI #44341748398](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44341748398) **SUCCESS: 1,126 synthetic pytest, disposable PostgreSQL18 and owner-role checks PASS**. Existing Railway development frontend and backend report deployment SUCCESS at this source SHA. The public/demo app remains synthetic only.

**Real owner operation actually completed:** The owner pulled `main`, ran `python -m app.private_owner_google_keys_prepare_cli` from the existing Mac backend virtualenv and typed the displayed exact local approval phrase. The owner supplied only the sanitized terminal result, containing:
```json
{
  "approved_existing_railway_services_only": true,
  "approved_folder_hmac_prepared_without_printing_id": true,
  "gateway_proof_prepared_for_both_services": true,
  "google_client_secret_staged_patch_applied": false,
  "new_private_key_domains_prepared": 6,
  "original_document_bytes_accessed": false,
  "owner_identity_and_recovery_keys_unchanged": true,
  "private_secret_values_printed": false,
  "public_owner_or_google_routes_activated": false,
  "railway_deployments_triggered": false,
  "real_financial_mode_enabled": false,
  "real_google_grant_created": false
}
```

**Independent Railway name-only verification:** all required names are present on existing `personal-cfo-api-preview`:
- Owner: `P1N_OWNER_ENCRYPTION_KEY`, `P1N_OWNER_IDENTITY_HMAC_KEY`, `P1N_OWNER_SESSION_HMAC_KEY`; original P1P recovery encrypted/HMAC keys, original P1W owner ref, operator public key and the separately configured owner credential DB DSN name.
- New P1R: `P1R_OAUTH_STATE_ENCRYPTION_KEY`, `P1R_OAUTH_STATE_HMAC_KEY`.
- New P1M: `P1M_METADATA_ENCRYPTION_KEYS_JSON`, `P1M_METADATA_ACTIVE_KEY_ID`, `P1M_METADATA_ROW_HMAC_KEY`.
- Drive one-folder: `DRIVE_INDEX_HMAC_KEY`, `DRIVE_ALLOWED_FOLDER_HMAC`, `P1B_GOOGLE_CLIENT_ID`, `P1B_GOOGLE_REDIRECT_URI`, `P1B_GOOGLE_FOLDER_ID` and two private contract-only switch names.
- Distinct `P1Q_PRIVATE_GATEWAY_SHARED_TOKEN` name exists in **both** `personal-cfo-api-preview` and `personal-cfo-frontend-preview`.

Railway variables were checked **by name only**, without retrieving, echoing or committing values. The owner's successful on-device command is the evidence for matching gateway values, not the name-only check. **None of the G2 activation flag names is currently set on the inspected Railway services.** The Google client secret continues as a sealed staged `P1C_GOOGLE_CLIENT_SECRET` change **not applied for consent**; no grant exists. `--skip-deploys` explicitly means the freshly prepared variable values are not attested active in old container processes; future controlled redeployment needs its own G2 review. Do not claim current live app has a real authenticated owner or a Google Drive grant merely from variables.

## What is implemented and what is still blocked

- **Completed source-only and deployed default-off:** exact owner MFA/session/logout ingress/mobile, exact Google metadata OAuth start/callback/status, encrypted session-bound single-use PKCE and approved-folder grant custody, on-demand owner Documents metadata page, no file content. PRs [#166](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/166), [#167](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/167), [#170](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/170), [#171](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/171), [#172](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/172), [#174](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/174).
- **G2 RELEASE BLOCKED:** Need independent live Railway edge/private API TLS+trusted proxy Host, cookie/CSRF/Origin/same-site behavior, bounded rate protection and request-target/code/state/cookie logging suppression across *all* platform and application layers, and a rehearsed rollback. Previous fake callback path probes showed public 404 and did not surface the **fake** marker in examined Railway HTTP/deploy fields; this **does not certify** unexamined platform logs.
- **Owner database G2 verification remaining:** read-only live attestation of exactly one owner and recovery state under `personal_cfo_owner_credentials` on private TLS PostgreSQL, effective least-privilege role, correct owner credential DSN (separate from financial `DATABASE_URL`), and safe isolated owner lifespan readiness. Names alone are insufficient.
- **New connector key continuity:** New P1R/P1M keys are not part of the *previously copied* original owner credential archive. Reviewed key escrow/rotation/rollbacks are required before depending on a real Google refresh grant. Do not ask the owner to repeat existing three-file backup-copy work; that occurred and is owner-reported in two places. An independently tested real restore remains separately unverified and cannot be silently labeled accepted.
- **OAuth connection still requires owner browser:** after G2 independent acceptance, release owner login first in a controlled operation, validate actual MFA/session, then narrow Google OAuth callback/code log safety, apply **only** the reviewed staged secret with explicit approval/rollback, and only the owner may click Google consent. App must verify owned/unshared pinned folder and store encrypted token before claiming connected. No original bytes and no full-Drive scan.
- **G1/G3/G4/G5 not complete:** Only an on-demand metadata snapshot source path is implemented; no persistent real synchronized heartbeat, original source import, authoritative encrypted actual finance ledger, reconciled owner financial claims or certified FBR results. Do not set `APP_DATA_MODE=real`.

## Nonrepetition / immediate next direction

**Do not rerun** `python -m app.private_owner_google_keys_prepare_cli`. Rerunning can replace already prepared independent keys. Do not request screenshots or raw Railway variables, OAuth code, TOTP, private folder identifiers, password, or owner recovery passphrases. No new service or paid cloud is approved.

Next *engineer-owned* action: perform independent read-only G2 checks from existing GitHub/Railway evidence, identify precise remaining accept/reject criteria and prepare a rollback-safe scoped activation protocol without turning flags on prematurely. A private owner-terminal/Google browser step is permitted only when genuinely required and should be as short as possible. Track [G2 #126](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/126), [edge/log #132](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/132), [key/role #133](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/133), [Drive #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98). [New verified G2 evidence](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/126#issuecomment-6984759000).
