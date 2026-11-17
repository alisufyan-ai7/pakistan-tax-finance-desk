-- P1W SOURCE REVIEW PLAN ONLY. NEVER apply automatically from CI/app startup.
-- This is a PostgreSQL SERVICE credential, not a second human app user.
-- The app has exactly one human role: owner.
--
-- Run only in a privileged, private Personal CFO PostgreSQL session AFTER:
--  * independent admin verification and DB schema head 0022 audit
--  * reviewing any existing credential role and full effective PUBLIC grants
--  * securing the new password via an attended psql \password prompt
--  * recording a minimal encrypted owner-identity key / recovery-kit copy
--
-- The role is created NOLOGIN intentionally; no secrets are embedded here.
-- It cannot authenticate until separately approved/passworded/activated.
BEGIN;
DO $cfo_role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles
                   WHERE rolname='personal_cfo_owner_credentials') THEN
        CREATE ROLE personal_cfo_owner_credentials
            NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOREPLICATION NOBYPASSRLS;
    END IF;
END
$cfo_role$;
ALTER ROLE personal_cfo_owner_credentials
    NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
REVOKE ALL PRIVILEGES ON SCHEMA public FROM personal_cfo_owner_credentials;
GRANT USAGE ON SCHEMA public TO personal_cfo_owner_credentials;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public
    FROM personal_cfo_owner_credentials;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public
    FROM personal_cfo_owner_credentials;
GRANT SELECT, INSERT, UPDATE ON TABLE
    public.owner_private_identities,
    public.owner_private_sessions,
    public.owner_private_recovery_states,
    public.owner_private_recovery_audit,
    public.owner_google_metadata_grants,
    public.owner_private_oauth_attempts
    TO personal_cfo_owner_credentials;
COMMIT;
-- Separate REQUIRED review:
--   PUBLIC has PostgreSQL TEMP permission by default. The strict P1S
--   attestor will reject this role while it has effective TEMP privileges.
--   Revoke TEMP FROM PUBLIC for this dedicated DB only after verifying all
--   other Personal CFO consumers tolerate the restriction.
--   Also inspect direct/column/public grants and role membership. If any
--   unexpected grant exists, the auditor must reject; never bypass it.
--
-- Only after explicit operator/owner authorization:
--   In interactive psql, run: \password personal_cfo_owner_credentials
--   Then enable LOGIN using a separate privileged command.
--   Supply its URL privately as P1W_OWNER_CREDENTIAL_DATABASE_URL,
--   NEVER overwrite the financial application DATABASE_URL.
--   Attest with private_credential_role_policy BEFORE initial enrollment.
