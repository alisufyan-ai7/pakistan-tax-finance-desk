# Chat 04 / Issue #114 — phone-friendly fictional Documents follow-up states

**Date:** 2026-11-17. **Base:** verified #113. This lane edits frontend `document-inbox.mjs`, `ui.mjs`, `pwa.css`, and Node tests plus a new `document-review-states.mjs`. No private backend auth/API, migration, Google token, document file or financial database changes.

## What is included
Six strictly fictional, untrusted-owner-data-free document health examples: never scanned, stale, permission revoked, changed, missing and possible duplicates. Buttons are keyboard accessible, keep at least 44px touch targets, explain uncertainty and a clear follow-up, and explicitly say **demo / no running scan**. Selectors accept only fixed known scenarios; no external JSON status, raw Google filename/ID or actual financial numbers can be rendered in public synthetic PWA. Old demo document filter is retained; UI integration uses existing event delegation without a new fetch. Current service worker continues caching no API data.
Node tests cover state availability, no owner financial claims, incomplete coverage, mobile/navigation, keyboard focus, no API caching and restricted public routes.

## Pending acceptance / limits
These are **not** current live Google Drive states and cannot claim owner review queue is populated. Actual auth, real metadata scanning, original bytes, G3 certified parsing and G1 finance reconciliation remain behind independent G2/G3/G1 acceptance and explicit owner approval. Public frontend may auto-deploy static synthetic source after a reviewed merge; never interpret this as enabling genuine Google OAuth. Finalize exact-head frontend-static-ci before merge, then combined GitHub handoff.
