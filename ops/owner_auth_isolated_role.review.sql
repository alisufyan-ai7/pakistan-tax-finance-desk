-- P1Y OWNER AUTH TECHNICAL ROLE - REVIEW ONLY - NEVER AUTO-DEPLOY
--
-- Apply ONLY to a separate, approved empty personal_cfo_owner_auth DB,
-- AFTER executing the P1Y schema SQL and verifying its receipt.
-- NO PASSWORD / LOGIN / REAL OWNER PROFILE is created by this file.
-- No other database or financial table should be affected.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $owner_auth_role_guard$
BEGIN
    IF current_database() <> 'personal_cfo_owner_auth' THEN
        RAISE EXCEPTION 'Owner credential-role target mismatch';
    END IF;
    IF (SELECT revision FROM public.owner_auth_schema_version
        WHERE singleton_id = 1) IS DISTINCT FROM 'p1y_owner_auth_v1' THEN
        RAISE EXCEPTION 'Owner credential schema receipt missing';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles
               WHERE rolname='personal_cfo_owner_credentials') THEN
        RAISE EXCEPTION 'An owner credential role already exists';
    END IF;
    IF (SELECT count(*) FROM pg_catalog.pg_tables
        WHERE schemaname='public' AND tablename IN (
            'owner_private_identities',
            'owner_private_sessions',
            'owner_private_recovery_states',
            'owner_private_recovery_audit',
            'owner_google_metadata_grants',
            'owner_private_oauth_attempts'
        )) <> 6 THEN
        RAISE EXCEPTION 'Required credential tables absent';
    END IF;
END
$owner_auth_role_guard$;
CREATE ROLE personal_cfo_owner_credentials
    NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
-- Safe because this is an isolated logical database: restrict only THIS DB.
REVOKE ALL PRIVILEGES ON DATABASE personal_cfo_owner_auth FROM PUBLIC;
REVOKE ALL PRIVILEGES ON DATABASE personal_cfo_owner_auth
    FROM personal_cfo_owner_credentials;
GRANT CONNECT ON DATABASE personal_cfo_owner_auth
    TO personal_cfo_owner_credentials;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL PRIVILEGES ON SCHEMA public
    FROM personal_cfo_owner_credentials;
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
-- Remaining confidential manual steps, outside GitHub/chat/this script:
--   1. Interactive psql: \password personal_cfo_owner_credentials
--   2. Reviewed privileged action: ALTER ROLE personal_cfo_owner_credentials LOGIN;
--   3. Test actual role access via P1S auditor; only then enroll owner.
-- Never put role password in CLI arguments, SQL files or chat.
