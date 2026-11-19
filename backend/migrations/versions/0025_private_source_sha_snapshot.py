"""P5I protected candidate source SHA state; never migrate automatically.

Before production: full encrypted off-device backup, disposable restore,
restricted DDL role, source snapshot parity, approved retention/key custody.
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_private_source_sha"
down_revision = "0024_review_comments"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "private_source_sha_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_hmac", sa.String(64), nullable=False),
        sa.Column("folder_hmac", sa.String(64), nullable=False),
        sa.Column("scan_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_hmac", sa.String(64), nullable=False),
        sa.Column("state_hmac", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scan_number > 0", name="ck_private_sha_snapshot_sequence"),
        sa.UniqueConstraint("owner_hmac","folder_hmac",name="uq_private_sha_owner_folder"),
    )
    op.create_index("ix_private_source_sha_snapshots_owner_hmac",
                    "private_source_sha_snapshots", ["owner_hmac"], unique=False)

def downgrade():
    raise RuntimeError(
        "Protected source SHA history requires verified encrypted backup, "
        "owner-approved archival and reviewed migration rollback before removal")
