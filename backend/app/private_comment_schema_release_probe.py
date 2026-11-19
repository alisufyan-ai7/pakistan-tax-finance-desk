"""P5D fail-closed, read-only owner-comments schema and restore gap report.

An existing table and green CI cannot substitute for an encrypted independent
off-device backup and disposable PostgreSQL restore. This operator diagnostic
performs NO DDL/DML and NEVER authorizes release flags.
"""
from __future__ import annotations

import os
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

_TABLE = "owner_financial_review_comments"
_REQUIRED = frozenset({
    "id","owner_hmac","subject_hmac","subject_kind",
    "revision","ciphertext","row_hmac","created_epoch",
})
_REVISIONS = frozenset({"0024_review_comments","0025_private_source_sha"})

class PrivateCommentReleaseProbeBlocked(ValueError):
    """Comment readiness cannot be safely determined."""

def inspect_private_comment_release_gaps(
    db: Session, *, approved_synthetic_diagnostic: bool,
) -> dict:
    """Observe only table structure and migration head. No secrets/rows returned."""
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P5D_COMMENT_SCHEMA_PROBE_ONLY") != "1"
        or approved_synthetic_diagnostic is not True
        or not isinstance(db, Session)
        or db.bind is None or db.bind.dialect.name not in ("postgresql","sqlite")):
        raise PrivateCommentReleaseProbeBlocked("Private comments probe disabled")
    try:
        inspector=inspect(db.bind)
        present=_TABLE in inspector.get_table_names()
        columns=frozenset(col["name"] for col in inspector.get_columns(_TABLE)) if present else frozenset()
        schema_columns_match=present and columns == _REQUIRED
        if "alembic_version" in inspector.get_table_names():
            versions=tuple(row[0] for row in db.execute(text(
                "SELECT version_num FROM alembic_version LIMIT 2")).all())
        else:
            versions=()
        migration_compatible=(len(versions)==1 and versions[0] in _REVISIONS)
        return {
            "contract":"personal_cfo_owner_comments_release_gaps_v1",
            "synthetic_diagnostic_only":True,
            "schema_table_present":present,
            "schema_columns_match":schema_columns_match,
            "alembic_revision_compatible":migration_compatible,
            "migration_revision_count":len(versions),
            "independent_encrypted_off_device_backup_verified":False,
            "disposable_full_database_restore_verified":False,
            "least_privilege_ddl_role_independently_reviewed":False,
            "owner_authenticated_comment_roundtrip_verified":False,
            "review_public_ingress_accepted":False,
            "saving_comments_live":False,
            "release_authorized":False,
            "original_drive_modified":False,
            "user_financial_values_exposed":False,
        }
    except Exception:
        raise PrivateCommentReleaseProbeBlocked(
            "Protected comment migration inspection unavailable") from None
