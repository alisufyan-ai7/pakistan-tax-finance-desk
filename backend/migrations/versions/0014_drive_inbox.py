"""P1 Google Drive synthetic private metadata inbox.

Revision ID: 0014_drive_inbox
Revises: 0013_recovery_audit

Additive only; this does NOT authorize real Drive OAuth, document processing,
PWA financial import, field-key rotation or live legacy ledger migration.
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_drive_inbox"
down_revision = "0013_recovery_audit"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "drive_inbox_checkpoints",
        sa.Column("folder_hmac", sa.String(64), primary_key=True),
        sa.Column("scan_number", sa.Integer(), nullable=False),
        sa.Column("source_snapshot_hmac", sa.String(64), nullable=False),
        sa.Column("state_hmac", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "drive_inbox_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("folder_hmac", sa.String(64), nullable=False),
        sa.Column("file_hmac", sa.String(64), nullable=False),
        sa.Column("revision_hmac", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("file_hmac", name="uq_drive_inbox_file_hmac"),
    )
    op.create_index("ix_drive_inbox_items_folder_hmac",
                    "drive_inbox_items", ["folder_hmac"])


def downgrade():
    raise RuntimeError(
        "Destroying encrypted Drive inbox provenance requires an independent "
        "backup, explicit owner authorization and reviewed recovery"
    )
