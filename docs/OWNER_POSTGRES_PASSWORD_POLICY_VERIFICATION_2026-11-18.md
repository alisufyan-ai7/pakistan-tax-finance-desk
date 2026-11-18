# P1AE — Test enforced PostgreSQL password authentication before owner MFA

**Date:** 18 November 2026. One-human-owner, private synthetic Railway service.
Owner confirmed P1AC `result=PASS` and P1AA `authenticated_tls_tcp_connection=true`,
`least_privilege_attestation_passed=true`, `owner_security_tables_empty=true`,
five distinct runtime encryption/HMAC keys and offline operator signing
public key. `production_g2_accepted=false`: no real owner MFA enrollment or
Google OAuth consent has happened.

## Why the test is necessary

A previous `psql -W` TCP command prompted for a password, but `-W` requests
a prompt regardless of the PostgreSQL server's `pg_hba` policy. Correct
authentication must be proven from the actual **private API to isolated
Postgres** network, not only from the Postgres container loopback.

A new **CLI-only, read-only** probe creates two physically separate
`NullPool` PostgreSQL sessions using the current approved TLS private
`P1W_OWNER_CREDENTIAL_DATABASE_URL`:

1. An ordinary session using the existing restricted role secret verifies
   exact `personal_cfo_owner_auth` database/role, remote TCP, SSL and read-only
   transaction mode. It never emits the credential or URL.
2. A second session uses the same hostname/role/database/TLS policy with a
   well-known intentionally invalid test password in memory. It MUST be
   rejected explicitly for wrong password (`28P01` or precise libpq rejected
   password message). If it connects, the check fails closed with
   `wrong_password_accepted`. If it fails due to DNS, timeout or `pg_hba`
   policy not explicitly proving password rejection, it fails closed with
   `wrong_password_rejection_unproven`.

No SQL writes, key edits, recovery issuance, owner enrollment, finance table
access, public HTTP endpoints, Google consent or migrations. Do not pass real
passwords/DSNs to chat/GitHub/logs.

## Owner-run exact command

After PR merge with successful full CI and Railway private API deployment,
run only on the already authenticated Mac:

```sh
railway ssh \
  --project 7021b227-f704-43d6-bcff-debdb7255b81 \
  --environment development \
  --service personal-cfo-api-preview \
  -- env P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1 \
  python -m app.private_owner_pg_password_policy
```

This prints a sanitized JSON report containing
`result: PASS`, `stage: complete`,
`server_rejects_intentionally_wrong_password: true` on success. Any
`BLOCKED` is a hard stop; do not proceed to password/TOTP enrollment, do
not reset the five encryption/HMAC keys, do not disable TLS, and do not
modify `pg_hba.conf` without independent review.

Next verify owner-authenticated private SSH interactive TTY (both standard
input and output), avoid terminal logging/recording, recheck the offline
encrypted Ed25519 signer and independent escrow backup, then individually
review **one-shot private operator** G2 flags for the existing unmounted
`app.private_owner_setup_cli enroll`. Only the one owner supplies a **new
app password** (distinct from the Postgres role password), manually enrolls
the TOTP URI into an authenticator, enters a code and saves the eight
one-time recovery codes separately from the phone. Verify owner credentials
and prepare a privately restorable encrypted minimal snapshot of the
credential SQL state; full financial DB disaster recovery can remain later.

Keep the two separately staged `P1C_GOOGLE_CLIENT_SECRET` values unapplied.
Real Google OAuth consent still requires exact-route ingress security
acceptance; this check does not grant G2 or G1/G3.
