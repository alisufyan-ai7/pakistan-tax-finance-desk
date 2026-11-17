"""P1J fictional scan lease and last-good HMAC receipt, additive schema.

Revision: 0017_drive_scan_leases
Down: 0016_owner_login_throttle
No migration is run on Railway by this file's GitHub commit.
"""
from alembic import op
import sqlalchemy as sa

revision="0017_drive_scan_leases"
down_revision="0016_owner_login_throttle"
branch_labels=None
depends_on=None


def upgrade():
    op.create_table(
        "drive_scan_leases",
        sa.Column("folder_hmac", sa.String(64), primary_key=True),
        sa.Column("lease_hmac", sa.String(64), nullable=True),
        sa.Column("lease_expires_epoch", sa.BigInteger(), nullable=False),
        sa.Column("last_success_epoch", sa.BigInteger(), nullable=True),
        sa.Column("last_source_hmac", sa.String(64), nullable=True),
        sa.Column("last_scan_number", sa.Integer(), nullable=False),
        sa.Column("last_attempt_epoch", sa.BigInteger(), nullable=True),
        sa.Column("last_outcome", sa.String(12), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("permission_revoked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("last_outcome IN ('never','success','retryable','denied')",
                           name="ck_drive_scan_lease_outcome"),
        sa.CheckConstraint("failure_count >= 0 AND failure_count <= 100",
                           name="ck_drive_scan_lease_failures"),
    )


def downgrade():
    raise RuntimeError(
        "Owner approval and independently verified backup needed before removing scan receipts"
    )
