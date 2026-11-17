"""P1G synthetic multiworker owner login throttle state (additive only).

Revision ID: 0016_owner_login_throttle
Revises: 0015_drive_cloud_oauth_custody

The table NEVER receives a real owner username, password, OAuth token or IP.
Migrated only in disposable CI until independent G2 real-mode approval.
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_owner_login_throttle"
down_revision = "0015_drive_cloud_oauth_custody"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "owner_login_throttles",
        sa.Column("owner_hmac", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_started_epoch", sa.BigInteger(), nullable=False),
        sa.Column("locked_until_epoch", sa.BigInteger(), nullable=False),
        sa.Column("updated_epoch", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("failures >= 0 AND failures <= 100", name="ck_owner_login_throttle_failures"),
    )


def downgrade():
    raise RuntimeError(
        "Throttle deletion requires explicit, audited owner-security review"
    )
