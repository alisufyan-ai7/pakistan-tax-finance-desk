# Priority 1B — Mobile-first Documents review UI (fictional preview)

This PR adds a fully navigable **Documents & reviews** tab in both the sidebar and mobile bottom navigation, using only synthetic examples. The phone view shows a clear one-folder Google Drive explanation, an explicit **Personal CFO Google connection PENDING** state, a review summary, file-type/status cards, and filters for all / needs attention / new / changed / possible duplicate / missing. It includes source follow-up prompts and clear separation of source labels from verified financial data.

**Scope guard:** the 26 source files observed via the ChatGPT Google Drive connector are *not rendered* in this public synthetic preview. The 6 fictional cards are not owner documents, do not derive from the user's private folder and should not be mistaken for synced or reconciled sources. No original file link/name/ID, Google token, OAuth client ID or financial amount is embedded, sent, cached or requested. The PWA retains its no-fetch service worker and same-origin synthetic status check. Files cannot be uploaded from this preview.

**Separate backend connection PR:** the P1B Google OAuth and page-scanning contract is developed separately and remains consent/private-security gated. The public Railway frontend only displays the sample design until owner MFA, secure Google OAuth, an encrypted credential vault, scheduled private synchronization and original-format security acceptance are ready. Do not add public Nginx proxy routes to the private owner ledger or document queue.

**Acceptance:** frontend static/node tests verify mobile tabs and demo labels, status filters, no secret/PII/actual folder link, no new public data route, no PWA offline financial caching; backend tests ensure the added JS module can be served only through the existing authenticated local synthetic app.

Master priority: [Six-item Personal CFO roadmap](PRIORITIZED_PERSONAL_CFO_ROADMAP_2026-11-17.md), [Drive issue #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98). Backblaze B2 remains deferred. The owner still uploads everything to the existing one private folder without sorting.
