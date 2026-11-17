"""P1S: independent read-only PostgreSQL credential-role privilege attestation.

The candidate runtime role may operate ONLY the five private owner/metadata
tables. It MUST NOT read/write economic tables, create objects, inherit more
powerful roles, use PUBLIC TEMP privileges, or use SQL DELETE/TRUNCATE.

No role creation, DB mutations, Railway access or live finance mode. Invoke
from a separately approved private operator connection; a passing report is
one subcheck and never by itself grants real Google or document access.
"""
from __future__ import annotations

import os

from sqlalchemy import text

from . import models  # noqa: F401
from .db import Base


class PrivateCredentialRoleBlocked(ValueError):
    """Candidate owner credential DB role failed independent least privilege."""


PRIVATE_TABLES = frozenset({
    "owner_private_identities",
    "owner_private_sessions",
    "owner_private_recovery_states",
    "owner_private_recovery_audit",
    "owner_google_metadata_grants",
    "owner_private_oauth_attempts",
})

_ROLE = text("""
/* P1S_ROLE */
SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication,
       rolbypassrls, rolinherit,
       (SELECT count(*) FROM pg_catalog.pg_auth_members m WHERE m.member=r.oid)
FROM pg_catalog.pg_roles r WHERE rolname=current_user
""")
_DATABASE = text("""
/* P1S_DB */
SELECT has_database_privilege(current_user,current_database(),'CREATE')
       OR has_database_privilege(current_user,current_database(),'TEMP')
""")
_SCHEMA = text("""
/* P1S_SCHEMA */
SELECT has_schema_privilege(current_user,'public','USAGE'),
       has_schema_privilege(current_user,'public','CREATE')
""")
_TABLES = text("""
/* P1S_TABLES */
SELECT c.relname,
       has_table_privilege(current_user,c.oid,'SELECT'),
       has_table_privilege(current_user,c.oid,'INSERT'),
       has_table_privilege(current_user,c.oid,'UPDATE'),
       has_table_privilege(current_user,c.oid,'DELETE'),
       has_table_privilege(current_user,c.oid,'TRUNCATE'),
       has_table_privilege(current_user,c.oid,'REFERENCES'),
       has_table_privilege(current_user,c.oid,'TRIGGER'),
       has_any_column_privilege(current_user,c.oid,'SELECT'),
       has_any_column_privilege(current_user,c.oid,'INSERT'),
       has_any_column_privilege(current_user,c.oid,'UPDATE'),
       has_any_column_privilege(current_user,c.oid,'REFERENCES')
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')
""")
_SEQUENCES = text("""
/* P1S_SEQUENCES */
SELECT count(*) FILTER (
    WHERE has_sequence_privilege(current_user,c.oid,'USAGE')
       OR has_sequence_privilege(current_user,c.oid,'SELECT')
       OR has_sequence_privilege(current_user,c.oid,'UPDATE')
)
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='S'
""")


def attest_private_credential_role(connection) -> dict:
    """Inspect effective SQL rights, not application read-only connection flags.

    No table data is read. The returned report deliberately omits database
    host/user names, table names, personal rows and any credentials.
    """
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT") != "1"
        or connection.dialect.name != "postgresql"):
        raise PrivateCredentialRoleBlocked("Private credential role audit unavailable")
    try:
        role = connection.execute(_ROLE).one_or_none()
        db_create = connection.execute(_DATABASE).scalar_one()
        schema = connection.execute(_SCHEMA).one()
        rows = connection.execute(_TABLES).all()
        seq_access = connection.execute(_SEQUENCES).scalar_one()
        if (role is None or len(role) != 7 or len(schema) != 2
            or any(value is not False for value in role[:6])
            or type(role[6]) is not int or role[6] != 0
            or db_create is not False
            or schema[0] is not True or schema[1] is not False
            or type(seq_access) is not int or seq_access != 0
            or len(rows) < len(Base.metadata.tables)):
            raise PrivateCredentialRoleBlocked("Credential role privileges not accepted")
        visible = set()
        for row in rows:
            if len(row) != 12 or type(row[0]) is not str or row[0] in visible:
                raise PrivateCredentialRoleBlocked("Credential schema inventory unsafe")
            name = row[0]
            visible.add(name)
            rights = row[1:]
            if any(type(v) is not bool for v in rights):
                raise PrivateCredentialRoleBlocked("Credential role rights indeterminate")
            if name in PRIVATE_TABLES:
                # True: SELECT/INSERT/UPDATE and their equivalent column
                # checks. False: DELETE/TRUNCATE/REFERENCES/TRIGGER and
                # column REFERENCES; no all-purpose GRANT ALL.
                if (rights[0:3] != (True, True, True)
                    or rights[3:7] != (False, False, False, False)
                    or rights[7:10] != (True, True, True)
                    or rights[10] is not False):
                    raise PrivateCredentialRoleBlocked("Private table grants unsafe")
            elif any(rights):
                raise PrivateCredentialRoleBlocked(
                    "Credential role can access unrelated application tables")
        if not PRIVATE_TABLES <= visible:
            raise PrivateCredentialRoleBlocked("Private credential tables missing")
    except PrivateCredentialRoleBlocked:
        raise
    except Exception:
        raise PrivateCredentialRoleBlocked(
            "PostgreSQL credential role audit failed closed") from None
    return {
        "candidate_credential_tables_attested": len(PRIVATE_TABLES),
        "unexpected_table_privileges": False,
        "database_create_or_temp_allowed": False,
        "schema_create_allowed": False,
        "role_inheritance_or_membership_allowed": False,
        "sequence_privileges_allowed": False,
        "production_role_activated_by_this_check": False,
        "production_g2_accepted": False,
    }
