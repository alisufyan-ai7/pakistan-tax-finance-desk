> **19 NOV 2026 OWNER OVERRIDE:** The 18 Nov table below says keep public `/` synthetic preview separate; that part is **SUPERSEDED** by Chat07. Retire synthetic root UI/manifest, redirect `/` into the single authenticated `/app` PWA and fix verified mobile login 403 without weakening security. See [Chat07 source-backed handoff](CHAT07_RECOVERY_MOBILE_OWNER_APP_2026-11-19.md) and [#193](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/193). All original Drive / G1-G3 finance constraints in this P2 design still stand.

# P2 — Personal CFO REAL owner workspace, source evidence and safe Drive organization
**Approved direction:** 18 November 2026. **Audience:** one owner, mobile and desktop, not a SaaS product.
**GitHub source of truth:** [P2A #183](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/183), [P2B #184](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/184), [P2C #185](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/185), [P2D #186](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/186). Existing Google integration [#98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98) is DONE for *one-folder metadata only*.

## Verified starting point (do NOT repeat the old setup)
- Real one-owner MFA browser login, consent-bound Google OAuth and private metadata-only grant are working. Owner verified live **27 document names** from exactly the approved private folder. No original bytes downloaded, no ledger figures imported. No additional login or Google metadata consent required for P2A/P2B source work.
- A connected Google Drive folder currently contains **11 PDFs, 11 PNGs, 2 XLSX, 1 CSV, 1 legacy Excel MIME type and 1 generic octet-stream**, about 26 MiB in Google metadata. This is a bounded source inventory, **not a financial analysis**. No real account/balance/income/tax claim is supported by file names.
- Public `/` desktop/mobile site is a fictional synthetic demo; authenticated `/owner-login` is a technical session/metadata page, not a complete owner dashboard.
- Existing secure infrastructure (Railway frontend + private API, TLS isolated owner credential PostgreSQL, one-owner MFA/CSRF, metadata OAuth) is enough for an owner-only app. Avoid creating more services/databases/queues as a prerequisite.
- Original folder currently remains read-only via `drive.metadata.readonly`; **this permission cannot retrieve source file bytes**, therefore no reliable financial amounts or source-content SHA-256 yet. Explicit new user consent and provider-scope/privacy review needed before read-only originals download. This is a real dependency, not a prompt to recreate the OAuth client.

## Parallel tracks and deliverables
| Track | Work now / independent | Release acceptance | Depends on |
| --- | --- | --- | --- |
| **P2A owner workspace** | New private `/app` mobile/desktop shell, real connected-folder summary, categorized document view, one-click refresh, session validation, explicit unknown financial cards, owner login -> app, logout | No unauthenticated private metadata, no mocked account figures, no source bytes, no session token persisted; safe signed-out link; mobile and desktop smoke | Existing one-owner session and metadata routes. Independent of P2B/P2C |
| **P2B change tracker** | Deterministic bounded metadata manifest, HMAC identifiers/revisions, changed/renamed/new/missing vs unchanged, incomplete-scan rejection, independent tests | Idempotent replay; no source edit, deletion, provider ID leakage, false byte hashes or false financial facts | Existing metadata contract. Independent of P2A/P2C |
| **P2C source evidence** | Content-hash utility (SHA-256 of *bytes actually read*) + safe format-signature/size limits, parser staging manifest with explicit no-finance-authorization, tests using fake content | Malicious/oversize/unsupported inputs rejected, no financial amounts or real source artifacts in repo | Existing importer/preflight; no Google read permission needed in synthetic CI |
| **P2D permission and organized copies** | Design private read-only source-content OAuth upgrade and future app-owned output-folder creation/copy; no live provider changes until reviewed | Owner approves new scope, all Drive requests pinned to owner folder, file hashes independently verified, originals never edited | Separate real source privacy/G1-G3 review and provider consent |

## Proposed data path, minimal single-owner architecture
```
One private ORIGINAL Google folder (immutable in app)
  -> metadata-only incremental inventory (P2B, can ship before content access)
  -> separately consented read-only source bytes (P2D permission)
  -> bounded isolated preflight, strong SHA-256, version lineage (P2C)
  -> bank-specific reconciled statement adapters, encrypted evidence + amount ledger (G1/G3)
  -> authenticated owner /app (P2A) with verified source-linked values
  -> optional organized COPY folder; bytes must have same SHA-256, filenames may differ
```
The source folder NEVER receives `update`, `delete`, `move`, `rename`. Do not assume copying in Drive implies SHA-256 equality without reading both copies. Virtual categorization comes first. The optional organized folder is a separate, later write-authorized, app-owned destination. Keep an immutable source ID/revision -> copy ID/revision link, encrypted source names/IDs and HMAC indexes; source updates make prior evidence historical, never silently overwrite.

## Refresh behavior
- App open = evaluate last successful metadata inventory and offer refresh, not unbounded provider calls on every render.
- Eventually hourly metadata-only poll, plus manual refresh and retry/backoff, using a **single existing PostgreSQL lease**; avoid Redis/Celery/microservices at single-owner scale.
- Require a COMPLETE Drive page-set before atomically advancing the last-good checkpoint. Missing from a complete snapshot = `missing_in_source`, **not deleted from evidence**. A changed name without content changes = `renamed`; a Google revision/MD5 change means **needs byte verification**, not automatically a changed SHA-256.
- Hash original bytes using SHA-256 *only when content read authorized*; keep Drive MD5 as a weak detection hint and `modifiedTime`/size/revision as provider hints. Reprocess only changed bytes, revalidate parser version and source coverage; no double count from overlaps/replays.

## Real finance dashboard definitions (strict honesty)
- On every card display `value|null`, PKR and reporting period, coverage state (verified/partial/missing/awaiting-source), and source lineage. **Unknown is not PKR 0.**
- First verified outcomes: statement count/account-month coverage, bank balance from latest independently reconciled closing statement, debits/credits by covered period, exceptions and missing documents. Transfers are not income/expenses; accountant draft not filed; withholding and investment return require independent evidence.
- As soon as one bank-format adapter passes with actual source evidence and G1 private canonical encrypted store, enable those verified figures in `/app`. Expand other formats gradually. Tax due, total wealth and portfolio performance remain unavailable until their evidence and rule gates pass.
- No public GitHub/PR data contains owner file names, account details, password, scanned text, monetary amounts or Drive IDs. All CI fixtures are synthetic.

## Release order and no repeated owner setup
1. Parallel P2A/P2B/P2C PRs, code + tests + CI; merge nonconflicting independent changes.
2. Owner sees mobile/desktop `/app` with live document inventory and explicit unverified financial cards **without new consent**.
3. Independently review P2D restricted read scope/G1-G3 storage/parser boundary; request **one** actual Google permission upgrade only when worker ready. Never re-run key generation, owner recovery drills, old OAuth client registration or metadata-only consent.
4. Process first authorized statement format, verify source-backed real numbers, then add scheduled refresh and organized copies. Do not claim P2B pure planner is a durable scheduler.

## Acceptance and rollback
- Frontend new route is exact gated by same existing P1AK owner ingress; API remains existing exact MFA-protected endpoints. JS keeps CSRF in memory and checks signed-in cookie; never cache private response in PWA worker, localStorage or telemetry.
- No `APP_DATA_MODE=real`, unrestricted finance API, automated edits or unapproved Drive writes. Never mix fictional synthetic preview amounts into real owner workspace.
- Keep earlier G1 canonical encryption and G3 authentic adapter acceptance as real-data release gates. The user wants numbers; show verified numbers incrementally rather than fabricating any during metadata-only phase.
