"""Encrypted synthetic financial events with keyed equality indexes.

Revision ID: 0009_private_events
Revises: 0008_asset_snapshots
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_private_events"
down_revision = "0008_asset_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "private_financial_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_hmac", sa.String(64), nullable=False),
        sa.Column("year_hmac", sa.String(64), nullable=False),
        sa.Column("source_hmac", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_private_financial_events_owner_hmac", "private_financial_events", ["owner_hmac"])
    op.create_index("ix_private_financial_events_year_hmac", "private_financial_events", ["year_hmac"])
    op.create_index("uq_private_financial_events_source_hmac", "private_financial_events", ["source_hmac"], unique=True)


def downgrade():
    raise RuntimeError("Destructive downgrade of private financial evidence is not allowed")