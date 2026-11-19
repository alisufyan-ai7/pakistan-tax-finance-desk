"""P2B: single encrypted synthetic Drive revision manifest, no live source access.

Revision 0023 is additive, never applied by app startup. Actual Railway DDL
requires independent protected backup/restore and a reviewed migration job.
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_private_drive_revision_snapshot"
down_revision = "0022_private_oauth_attempts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "private_drive_revision_snapshots",
        sa.Column("folder_hmac", sa.String(64), primary_key=True),
        sa.Column("id", sa.String(36), unique=True, nullable=False),
        sa.Column("scan_number", sa.Integer(), nullable=False),
        sa.Column("source_snapshot_hmac", sa.String(64), nullable=False),
        sa.Column("state_hmac", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scan_number > 0",
                           name="ck_private_drive_revision_sequence"),
    )


def downgrade():
    raise RuntimeError(
        "Protected historical Drive revision manifests cannot be dropped "
        "without a reviewed encrypted recovery and owner approval")
