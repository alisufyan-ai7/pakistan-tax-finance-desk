"""P1E separate synthetic-only OAuth state and grant vault.

Revision ID: 0015_drive_cloud_oauth_custody
Revises: 0014_drive_inbox

Additive SQL only. No Google credential, OAuth endpoint, live authentication,
database privilege migration, financial record or Railway variable is changed.
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_drive_cloud_oauth_custody"
down_revision = "0014_drive_inbox"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "drive_cloud_oauth_attempts",
        sa.Column("state_hmac", sa.String(64), primary_key=True),
        sa.Column("folder_hmac", sa.String(64), nullable=False),
        sa.Column("payload_cipher", sa.Text(), nullable=False),
        sa.Column("expires_epoch", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.CheckConstraint("status IN ('pending','claimed')", name="ck_drive_cloud_oauth_attempt_status"),
    )
    op.create_index("ix_drive_cloud_oauth_attempts_folder_hmac",
                    "drive_cloud_oauth_attempts", ["folder_hmac"])
    op.create_table(
        "drive_cloud_oauth_grants",
        sa.Column("folder_hmac", sa.String(64), primary_key=True),
        sa.Column("payload_cipher", sa.Text(), nullable=False),
        sa.Column("granted_epoch", sa.BigInteger(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
    )


def downgrade():
    raise RuntimeError(
        "OAuth custody deletion requires independent encrypted backup, "
        "key lifecycle and explicit owner-reviewed secure data retirement"
    )
