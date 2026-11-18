# P1AC — Owner PostgreSQL connection triage without sharing secrets

The owner's private P1AB read-only diagnostic returned:
`result=BLOCKED`, `stage=database_connection`. Previous checks accepted the
**presence and shape** of all seven owner key/DSN variables and the restricted
database-URL policy. This response does **not** distinguish DNS, TCP, TLS,
password rejection, database existence or other driver errors; do not guess.

## Separate, bounded read-only connectivity check

The new CLI `python -m app.private_owner_db_connectivity_probe` is intentionally
separate from the original MFA gate. It runs **only** under the approved private
development Railway service, with a one-off
`P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1` check. No public endpoint exists.

From your Mac (do not paste the database URL or keys into chat):

```sh
railway ssh \
  --project 7021b227-f704-43d6-bcff-debdb7255b81 \
  --environment development \
  --service personal-cfo-api-preview \
  -- env P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1 \
  python -m app.private_owner_db_connectivity_probe
```

The utility only validates existing runtime key inventory and DSN policy, the
PostgreSQL driver, private `.railway.internal` DNS resolution, TCP reachability,
and a TLS-required restricted PostgreSQL connection with **SELECT 1** in a
read-only transaction. It prints *only* a fixed failure-stage enum or
`complete`; it never prints the hostname, client password, DSN, key values,
driver exception text, personal financial records or authentication secret.

Possible responses: `runtime_scope_or_keys`, `restricted_dsn_policy`,
`database_driver`, `private_dns_resolution`, `private_tcp_connectivity`,
`postgres_password_rejected`, `postgres_auth_policy`,
`postgres_database_or_role_missing`, `postgres_tls_connection`,
`postgres_connection_other`, or `complete`. Use the returned stage to decide
the *smallest safe correction*. A success from this probe does not bypass the
original full P1AA preflight, owner MFA recovery acceptance, or G2. A SQL role
with `LOGIN` does not alone prove the server enforces password authentication.

If `postgres_password_rejected`, **do not send the password, secret URL or
escrow file to ChatGPT**; inspect the privately stored role password against
the value entered into the local key-custody helper. If necessary, rotate only
that technical PostgreSQL role password in a private attended operator session
then reconfigure **only** the restricted connection URL without touching the
five escrowed encryption/HMAC keys or their backups. Never re-enroll an owner to
repair a transport error. If DNS/TCP/TLS/driver fails, fix its corresponding
underlying infrastructure or runtime issue instead; do not expose Postgres
publicly or downgrade TLS.

## Verified at source handoff

- One-owner isolated database exists, six private tables and version receipt.
- One restricted technical role exists; earlier TCP `psql` connect succeeded.
- Seven owner runtime variable **names** and offline signing public key verified.
- The two staged sealed Google client-secret entries remain **unapplied**.
- No user MFA, eight recovery codes, public OAuth or original financial-data
  cutover has occurred.
