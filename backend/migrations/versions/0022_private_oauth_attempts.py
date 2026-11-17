"""P1R: private persistent OAuth state, owned by a genuine MFA session.

Revision 0022 depends on P1Q 0021 (security-migration serialization).
Tests use fictional identities and never call Google or real owner sources.
No live Railway DDL may be applied without an independent encrypted backup.
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_private_oauth_attempts"
down_revision = "0021_private_reenrollment"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "owner_private_oauth_attempts",
        sa.Column("state_hmac", sa.String(64), primary_key=True),
        sa.Column("owner_hmac", sa.String(64), nullable=False),
        sa.Column("session_hmac", sa.String(64), nullable=False),
        sa.Column("folder_hmac", sa.String(64), nullable=False),
        sa.Column("client_hmac", sa.String(64), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("issued_epoch", sa.BigInteger(), nullable=False),
        sa.Column("expires_epoch", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("row_hmac", sa.String(64), nullable=False),
        sa.CheckConstraint("expires_epoch > issued_epoch",
                           name="ck_owner_private_oauth_expiry"),
        sa.CheckConstraint("status IN ('pending','claimed','expired')",
                           name="ck_owner_private_oauth_status"),
    )
    op.create_index("ix_owner_private_oauth_attempts_owner_hmac",
                    "owner_private_oauth_attempts", ["owner_hmac"])


def downgrade():
    raise RuntimeError(
        "Pending or used OAuth state must not be silently discarded; "
        "require an independently verified encrypted backup and credential review")
