# Chat08 — Google restricted content scope CONFIRMED by owner, 19 Nov 2026

## Authoritative owner-provided screenshots

The owner shared Google Auth Platform screenshots for the existing Google Cloud project **`personal-cfo-drive-connector`**. Screenshots show:

- **Data Access → Restricted Drive scopes** includes **both** `https://www.googleapis.com/auth/drive.readonly` and existing `https://www.googleapis.com/auth/drive.metadata.readonly`. Disabled **Save** button suggests the scope declarations are saved.
- **Audience**: User type **External**, publishing status **Testing**, **one existing test user**. No further users, secrets, IDs or screenshots should be committed to public GitHub.
- **This is NOT an OAuth content grant.** The actual private Personal CFO OAuth request must explicitly ask for `drive.readonly`; owner must approve Google's consent screen; token exchange must cryptographically bind one-use owner MFA/CSRF+PKCE and verify returned exact scope. Existing metadata-only refresh grants MUST NOT be reused as file-content authority. Original approved folder is immutable and app must refuse access to any other folder even though Google's read scope is account-wide.

## Google platform behavior verified against current docs

- Google documents **External / Testing** refresh tokens with Drive scopes as generally expiring after **7 days**, so hourly unattended sync cannot silently assume permanent credentials. [Google OAuth](https://developers.google.com/identity/protocols/oauth2).
- **Personal mode** is now a supported one-user option without that test-user 7-day token expiration or OAuth verification, but Google documents that an **existing External project cannot be switched to Personal**. It requires a new Personal-mode project/client and a deliberate, reviewed OAuth credential switchover. [Manage App Audience](https://support.google.com/cloud/answer/15549945) and [Personal mode quick setup](https://support.google.com/cloud/answer/15544987). Do not ask owner to change the active client just to unblock first content ingestion; preserve current working metadata service until separately tested replacement.
- Google restricted-scope rules still apply; a personal-use/development exception may avoid external OAuth verification, but is not permission to expose private financial data or ignore source/secret controls. [Restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification).

## New parallel engineering evidence

- [PR #207](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/207) **MERGED** squash `08fd93e7a75bff5ea0a1291501edafbb69a99509`. It reuses session-bound encrypted single-use OAuth attempts with independently reviewed fixed **content** scope, provides exact-scope Google content PKCE+token exchange/refresh contract, and refuses cross-claiming metadata attempts. [CI run 44519087261](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/actions/runs/44519087261) passed on rerun following one CI disposable-database test failure unrelated to new code.
- [PR #208](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/208) separate HMAC and HKDF-derived AES-GCM content refresh-token custody in the **already deployed owner grant SQL table**, using different blinded row identity from metadata. Old metadata grant is not overwritten and no new key generation or live migration is needed. Treat as **unmerged until green CI and exact-head merge evidence**. A Docker disposable PostgreSQL restore test was flaky/failing in one environment. Do not bypass it to merge.
- [PR #203](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/pull/203) remains the bounded, default-off, exact approved-folder `alt=media` SHA-256 reader; no owner originals accessed.
- Existing live owner MFA/mobile PWA and metadata preview remain in service. This checkpoint **does not activate** content Google provider OAuth, store actual tokens, run original-byte imports, turn on a scheduler or provide real PKR financial figures.

## Next release critical path

1. Merge #208 only after full security CI. Then wire **both** #207 and #208 through the existing session-bound OAuth callback, fixed same-origin POST+CSRF, no-query/no-access-logs ingress and a content status endpoint. Only after independent exact-route tests and operator acceptance should the owner see a **Connect read-only documents** button in `/app`. The existing metadata OAuth must continue working without interruption.
2. Owner clicks the Personal CFO-generated Google consent URL from a currently logged-in owner session. Validate returned exact content scope, pinned single unshared owner folder and vault encryption. Do not paste Google authorization URL, code, secret or token in chat.
3. Fetch only vetted direct children of approved folder using #203. Record independently hashed immutable bytes, evidence statuses and unsupported/password-protected-format review under isolated parser/bounded worker; do not expose raw content in GitHub/CI/logs.
4. Run source-linked CSV/XLSX/PDF/screenshot/IRIS/accountant evidence review and encrypted canonical ledger + reversible source provenance; progressively expose genuine PKR dashboard account, expense/income, investment, bills and tax reports with `VERIFIED` / `PARTIAL` / `MISSING`, never fake zero.
5. Separate scheduled hourly refresh and version index after reviewed backup/restore, still one-owner, no SaaS or new databases.
