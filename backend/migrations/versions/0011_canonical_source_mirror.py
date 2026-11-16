"""G1-c: sealed source mirrors on independently restored synthetic PG candidate.

Revision ID: 0011_canonical_mirror
Revises: 0010_confidential_bank
This is a NEW table only: source legacy tables are not rewritten or dropped.
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_canonical_mirror"
down_revision = "0010_confidential_bank"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "canonical_source_mirrors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_hmac", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_canonical_source_mirrors_source_hmac",
                    "canonical_source_mirrors", ["source_hmac"], unique=True)


def downgrade():
    raise RuntimeError("Candidate mirror deletion requires explicit verified recovery; no destructive downgrade")
