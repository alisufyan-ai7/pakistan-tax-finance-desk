"""G2 F3 synthetic encrypted owner recovery state and chained audit.

Revision ID: 0013_recovery_audit
Revises: 0012_canonical_journal
Additive: no auth endpoint, MFA reset, real-data owner state or role change.
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_recovery_audit"
down_revision = "0012_canonical_journal"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "owner_recovery_states",
        sa.Column("owner_hmac", sa.String(64), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("bundle_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "owner_recovery_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_hmac", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(12), nullable=False),
        sa.Column("previous_hmac", sa.String(64), nullable=False),
        sa.Column("bundle_hmac", sa.String(64), nullable=False),
        sa.Column("event_hmac", sa.String(64), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_hmac", "revision", name="uq_owner_recovery_audit_revision"),
    )
    op.create_index("ix_owner_recovery_audit_owner_hmac", "owner_recovery_audit", ["owner_hmac"])


def downgrade():
    raise RuntimeError("Recovery audit destruction requires independent recovery and owner authorization")
