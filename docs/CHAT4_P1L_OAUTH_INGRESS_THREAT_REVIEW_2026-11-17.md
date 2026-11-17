# Chat 04 — P1L exact OAuth ingress threat rehearsal

**2026-11-17 · Priority 1 and G2 · standalone fake-only branch after #119.**

`backend/app/fake_oauth_ingress_review.py` specifies **non-deployed** public candidate paths: POST start, GET provider callback, GET status and POST disconnect, each with one exact internal path. It rejects wildcard paths, wrong methods, untrusted Host/TLS, client-provided forwarding headers, duplicate/unexpected callback query fields, non-fake provider code, missing owner cookie, wrong Origin and missing CSRF for mutations. A genuine cross-site Google GET callback has no Origin/POST CSRF requirement; it must have a browser SameSite=Lax session and a state that the separately encrypted store verifies against the initiating session.

The review planner returns only redacted route IDs and negative security flags: **NO raw code/state, token, query string, cookie, or claim of a verified session, deployed gateway or actual provider exchange**. Public Nginx must remain unchanged: the sole preview GET proxy remains `/api/preview/status`. This helper is not a proxy generator and cannot perform actual HTTPS termination or inspect Railway access logs.

**G2 acceptance remains BLOCKED** until independent operational validation of trusted TLS boundaries, location exactness, no request-target logs/callback code storage, state-binding anti-replay, session rotation/MFA recovery, DB least privilege, live key lifecycle, no generic /api proxy, and explicit owner consent. CI fake tests cannot attest Railway log redaction or approve real Google OAuth. No manual Railway, Google Cloud or owner-source action.
