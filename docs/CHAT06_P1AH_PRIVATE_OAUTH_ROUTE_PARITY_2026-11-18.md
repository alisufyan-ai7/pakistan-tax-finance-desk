# Chat06 P1AH — Exact-route owner/OAuth candidate parity and fail-closed login input

**Status:** Source-only candidate, no operator action, no public route activation, no Google consent or original document intake. Tracking [G2 #126](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/126), [OAuth #132](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/132) and [Drive #98](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/98).

## Specific discovered implementation gap

The unmounted `ops/nginx.personal-cfo-oauth.candidate.conf` contained a public `POST /api/drive/oauth/disconnect` route, but `create_synthetic_private_owner_oauth_gateway` explicitly did **not** implement an internal `/internal/drive/oauth/disconnect` handler (and the live `app.preview_api` never mounted any owner HTTP routes). Including a nonfunctional public endpoint in a future operator release candidate would be misleading, risky and hard to reason about when dealing with grant revocation. This milestone **removes** it until proper authenticated grant-disconnect/revocation semantics are separately implemented.

The same review found the private MFA login parser relied on Python JSON's last-member-wins behavior for duplicate password/TOTP keys. It now **rejects any repeated JSON member**, even when both values are syntactically valid, and refuses transfer-encoding on the small JSON login body rather than allowing ambiguous request framing.

## Change and synthetic acceptance

- Keep exactly six source-only public owner/OAuth candidate paths: owner login/session/logout and Drive OAuth start/callback/status. Retain the existing preview/status path, preserve exact Host, method, private upstream, gateway-secret server replacement and query/credential scrubbing. No wildcard API forwarding.
- Explicitly scrub browser-supplied `Forwarded`, `X-Forwarded-Host`, `X-Forwarded-For`, `X-Real-IP`, `X-Original-URI`, `X-Original-URL`, `X-Rewrite-URL` and `X-Forwarded-Prefix` before proxying only those six future approved exact routes.
- Add synthetic route-parity test that instantiates `create_synthetic_private_owner_oauth_gateway` with no credentials and verifies **every** private ASGI path+method is represented by the candidate. Independently assert that no private route is enabled through `create_preview_app`, `frontend/nginx.railway.conf` or its live Dockerfile.
- Align private owner HTTP gateway to the already escrowed `P1W_OWNER_REF`, removing dependency on an unconfigured second `P1Q_PRIVATE_OWNER_REF` that could otherwise block real owner login after enrollment. A synthetic negative test rejects an alias-only owner setting.
- Add duplicate-JSON request tests that construct valid-looking repeated `password` and `totp_code` values and confirm rejection **without consuming** the authentic synthetic TOTP counter; a subsequent well-formed synthetic login must still pass.
- Existing full backend synthetic regression + disposable PostgreSQL18 security migrations must pass on the exact PR head before merge. No real Google client, private source identifiers, original financial files or secrets go to CI.

## Required later operational acceptance (not done by this PR)

This PR **cannot** confer production G2. The real Railway edge, platform/upstream access/error logs, query/code/state/cookie privacy, actual TLS and trusted header policy, CSRF/Origin/session/rate and abuse limits, isolated credential restoration, and private API process command/permissions still need owner-scoped review. The reviewed candidate is intentionally **not deployed**. The existing sealed Google client secret remains unapplied; no Google token exchange, one-folder metadata heartbeat or genuine financial upload is performed.

**Chat06 owner direction:** the owner confirms existing encrypted credential snapshot, key escrow and encrypted offline signer are copied to two places. Do **not** repeatedly request backup or local Docker exercises in order to perform independent source-only engineering; owner-local actual restore verification remains untested and can be evaluated at the appropriate security release acceptance checkpoint. The owner requires progress in the application, not more backup chores.

**Next engineering slice:** implement and independently accept an actual one-owner private ASGI service entrypoint/configuration and reviewable no-sensitive-access-log posture (without exposing the public callback prematurely), followed by exact Railway ingress acceptance and then owner-driven Google consent. Real document bytes remain gated by separate G1/G3 security/source certification.
