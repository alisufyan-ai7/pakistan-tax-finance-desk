"""A6: independent encrypted synthetic operational journal.

Revision ID: 0012_canonical_journal
Revises: 0011_canonical_mirror

Additive only: no legacy data copying, no destructive migration or real mode.
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_canonical_journal"
down_revision = "0011_canonical_mirror"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "canonical_journal_key_state",
        sa.Column("id", sa.String(8), primary_key=True),
        sa.Column("verifier_hmac", sa.String(64), nullable=False),
        sa.Column("sentinel", sa.Text(), nullable=False),
    )
    op.create_table(
        "canonical_journal_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_hmac", sa.String(64), nullable=False),
        sa.Column("year_hmac", sa.String(64), nullable=False),
        sa.Column("account_hmac", sa.String(64), nullable=False),
        sa.Column("source_hmac", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_canonical_journal_entries_owner_hmac", "canonical_journal_entries", ["owner_hmac"])
    op.create_index("ix_canonical_journal_entries_year_hmac", "canonical_journal_entries", ["year_hmac"])
    op.create_index("ix_canonical_journal_entries_account_hmac", "canonical_journal_entries", ["account_hmac"])
    op.create_index("uq_canonical_journal_source_hmac", "canonical_journal_entries", ["source_hmac"], unique=True)


def downgrade():
    raise RuntimeError("Cannot discard canonical journal without owner-approved encrypted recovery proof")
