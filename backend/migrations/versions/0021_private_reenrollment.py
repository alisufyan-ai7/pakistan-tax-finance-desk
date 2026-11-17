"""P1Q: allow a distinct authenticated REENROLLED recovery audit event.

Revision: 0021_private_reenrollment
Down: 0020_private_recovery

No new columns, no automatic data reset and no real owner credentials.
Apply only after separate backup/migration authorization in a private runtime.
"""
from alembic import op

revision = "0021_private_reenrollment"
down_revision = "0020_private_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "ck_owner_private_recovery_audit_action",
        "owner_private_recovery_audit", type_="check")
    op.create_check_constraint(
        "ck_owner_private_recovery_audit_action",
        "owner_private_recovery_audit",
        "action IN ('ISSUED','REDEEMED','REENROLLED')")


def downgrade():
    raise RuntimeError(
        "Do not remove the REENROLLED audit meaning without separately "
        "verifying recovery history and independently restorable backup")
