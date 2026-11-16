"""G2 F1: explicit PostgreSQL runtime privilege attestation (OFFLINE, synthetic-only).

This is an operator-invoked check, NOT wired into the live Railway preview.
A read-only session flag is insufficient when the connected DB role can still
write after changing its transaction mode. The preview must NOT be superuser,
DB/schema owner, DDL capable, or able to read ANY financial application table.
A green result is only one G2 subcheck; MFA, backup and owner recovery remain.
"""
from __future__ import annotations

import os
from sqlalchemy import text

from .db import Base
from . import models  # noqa: F401


class RoleAttestationBlocked(ValueError):
    """Private preview database role has unapproved capabilities."""


_ROLE_SQL = text("""
SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
FROM pg_catalog.pg_roles WHERE rolname = current_user
""")
_DATABASE_SQL = text("""
SELECT has_database_privilege(current_user, current_database(), 'CREATE')
       OR has_database_privilege(current_user, current_database(), 'TEMP')
""")
_SCHEMA_SQL = text("""
SELECT has_schema_privilege(current_user, 'public', 'CREATE')
""")
_TABLE_SQL = text("""
SELECT count(*) AS inspected_count,
       count(*) FILTER (WHERE
          has_table_privilege(current_user,
              format('%I.%I', n.nspname, c.relname), 'SELECT')
          OR has_table_privilege(current_user,
              format('%I.%I', n.nspname, c.relname), 'INSERT')
          OR has_table_privilege(current_user,
              format('%I.%I', n.nspname, c.relname), 'UPDATE')
          OR has_table_privilege(current_user,
              format('%I.%I', n.nspname, c.relname), 'DELETE')
          OR has_table_privilege(current_user,
              format('%I.%I', n.nspname, c.relname), 'TRUNCATE')
          OR has_table_privilege(current_user,
              format('%I.%I', n.nspname, c.relname), 'REFERENCES')
          OR has_table_privilege(current_user,
              format('%I.%I', n.nspname, c.relname), 'TRIGGER')
       ) AS accessible_count
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')
""")


def attest_synthetic_preview_role(connection) -> dict:
    """Fail closed for a privileged DB role; return NO usernames, tables or DSNs.

    Use with an authenticated direct PostgreSQL Connection belonging to the
    *candidate preview-only* role. It performs read-only privilege introspection.
    It does not create/alter any role, reconfigure Railway, or certify G2.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise RoleAttestationBlocked("Real financial mode is forbidden")
    if connection.dialect.name != "postgresql":
        raise RoleAttestationBlocked("PostgreSQL connection required")
    try:
        role = connection.execute(_ROLE_SQL).one_or_none()
        db_can_create_or_temp = connection.execute(_DATABASE_SQL).scalar_one()
        schema_can_create = connection.execute(_SCHEMA_SQL).scalar_one()
        tables = connection.execute(_TABLE_SQL).one()
        count, accessible = tables[0], tables[1]
        # The expected physical inventory must be present: no 'SELECT 1'
        # cosmetic success against a misconfigured empty database.
        if role is None or type(count) is not int or count < len(Base.metadata.tables):
            raise RoleAttestationBlocked("Expected finance schema is not independently checked")
        if any(v is not False for v in role) or db_can_create_or_temp is not False or schema_can_create is not False:
            raise RoleAttestationBlocked("Preview database role has elevated privileges")
        if type(accessible) is not int or accessible != 0:
            raise RoleAttestationBlocked("Preview role can access finance/application tables")
    except RoleAttestationBlocked:
        raise
    except Exception:
        raise RoleAttestationBlocked("PostgreSQL role attestation failed closed") from None
    return {
        "synthetic_only": True,
        "preview_role_privileges": "NO_APP_TABLE_ACCESS",
        "database_create_or_temp_allowed": False,
        "schema_create_allowed": False,
        "finance_table_access_allowed": False,
        "application_tables_inspected": count,
        "g2_full_security_accepted": False,
        "real_data_authorized": False,
    }
