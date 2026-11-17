"""P1P: real-compatible, unmounted one-time owner recovery state/audit.

Revision: 0020_private_recovery
Down: 0019_private_owner_auth
NO live Railway schema or owner credential is changed by this source file.
"""
from alembic import op
import sqlalchemy as sa

revision="0020_private_recovery"
down_revision="0019_private_owner_auth"
branch_labels=None
depends_on=None


def upgrade():
    op.create_table(
        "owner_private_recovery_states",
        sa.Column("owner_hmac",sa.String(64),primary_key=True),
        sa.Column("revision",sa.Integer(),nullable=False),
        sa.Column("issued_epoch",sa.BigInteger(),nullable=False),
        sa.Column("expires_epoch",sa.BigInteger(),nullable=False),
        sa.Column("ciphertext",sa.Text(),nullable=False),
        sa.Column("pending",sa.Boolean(),nullable=False),
        sa.Column("row_hmac",sa.String(64),nullable=False),
        sa.CheckConstraint("revision > 0",
                           name="ck_owner_private_recovery_revision"),
        sa.CheckConstraint("expires_epoch > issued_epoch",
                           name="ck_owner_private_recovery_expiry"),
    )
    op.create_table(
        "owner_private_recovery_audit",
        sa.Column("owner_hmac",sa.String(64),primary_key=True),
        sa.Column("revision",sa.Integer(),primary_key=True),
        sa.Column("action",sa.String(12),nullable=False),
        sa.Column("previous_hmac",sa.String(64),nullable=False),
        sa.Column("row_hmac",sa.String(64),nullable=False),
        sa.Column("event_hmac",sa.String(64),nullable=False),
        sa.Column("epoch",sa.BigInteger(),nullable=False),
        sa.CheckConstraint("action IN ('ISSUED','REDEEMED')",
                           name="ck_owner_private_recovery_audit_action"),
    )


def downgrade():
    raise RuntimeError(
        "Owner private recovery audit/history may not be deleted without "
        "independent backup and owner security acceptance"
    )
