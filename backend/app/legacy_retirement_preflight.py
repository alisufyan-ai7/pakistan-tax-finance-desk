"""G1 A8: read-only PostgreSQL restored-clone legacy plaintext retirement probe.

This explicitly detects old finance tables/rows and NEVER drops, truncates,
renames, copies or zeroes the original/restored source. It cannot attest
production retirement or enable real-data financial mode. Only a database with
a reviewed synthetic_restore_* name may be scanned.
"""
from __future__ import annotations

import os
import re

from sqlalchemy import inspect, select, func

from .db import Base
from . import models  # noqa: F401
from .g1c_preflight import LEGACY_FINANCE_TABLES, MAX_ROWS
from .pg_recovery import SCHEMA_REVISION


class LegacyRetirementBlocked(ValueError):
    """Ineligible or unverified independently restored synthetic finance clone."""


_ALLOWED_RESTORE = re.compile(r"^synthetic_restore_[a-z0-9_]{3,48}$")


def inspect_restored_legacy_schema(engine) -> dict:
    """Bounded READ ONLY inventory. No row values, account IDs or table names emitted."""
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise LegacyRetirementBlocked("Real-data retirement is not authorized")
    try:
        if (engine.dialect.name != "postgresql"
            or engine.url.drivername != "postgresql+psycopg"
            or not _ALLOWED_RESTORE.fullmatch(engine.url.database or "")):
            raise LegacyRetirementBlocked("Only independent synthetic PostgreSQL restore clones allowed")
        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            found = set(inspect(connection).get_table_names())
            expected = set(Base.metadata.tables) | {"alembic_version"}
            if found != expected:
                raise LegacyRetirementBlocked("Unknown/missing source tables: schema drift")
            version = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one_or_none()
            if version != SCHEMA_REVISION:
                raise LegacyRetirementBlocked("Restored PostgreSQL schema revision mismatch")
            present = 0
            populated = 0
            rows = 0
            for name in sorted(LEGACY_FINANCE_TABLES):
                # Static reviewed table names only: never format user-controlled SQL.
                if name not in Base.metadata.tables:
                    raise LegacyRetirementBlocked("Legacy finance source inventory changed")
                table = Base.metadata.tables[name]
                count = connection.scalar(select(func.count()).select_from(table))
                if type(count) is not int or count < 0:
                    raise LegacyRetirementBlocked("Unreadable legacy source census")
                rows += count
                if rows > MAX_ROWS:
                    raise LegacyRetirementBlocked("Legacy source too large to prove complete")
                present += 1
                populated += int(count > 0)
        return {
            "synthetic_only": True,
            "read_only": True,
            "restored_clone_only": True,
            "legacy_finance_tables_present": present,
            "legacy_finance_tables_containing_rows": populated,
            "legacy_financial_rows_still_present": rows,
            "plaintext_legacy_schema_retired": False,
            "legacy_finance_ownership_cutover": False,
            "drop_or_truncate_performed": False,
            "source_records_deleted": False,
            "g1_release_accepted": False,
            "real_data_authorized": False,
        }
    except LegacyRetirementBlocked:
        raise
    except Exception:
        raise LegacyRetirementBlocked("Read-only legacy retirement rehearsal unavailable") from None
