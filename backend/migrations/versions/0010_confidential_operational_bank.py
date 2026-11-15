"""G1-a: active AES-GCM operational synthetic bank source, versioned PG/SQLite.

Revision ID: 0010_confidential_bank
Revises: 0009_private_events
No plaintext financial business columns are introduced.
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_confidential_bank"
down_revision = "0009_private_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "confidential_bank_key_state",
        sa.Column("id", sa.String(8), primary_key=True),
        sa.Column("verifier_hmac", sa.String(64), nullable=False),
        sa.Column("sentinel", sa.Text(), nullable=False),
    )
    op.create_table(
        "confidential_bank_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_hmac", sa.String(64), nullable=False),
        sa.Column("account_hmac", sa.String(64), nullable=False),
        sa.Column("source_hmac", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_confidential_bank_batches_owner_hmac", "confidential_bank_batches", ["owner_hmac"])
    op.create_index("ix_confidential_bank_batches_account_hmac", "confidential_bank_batches", ["account_hmac"])
    op.create_index("uq_confidential_bank_source_hmac", "confidential_bank_batches", ["source_hmac"], unique=True)


def downgrade():
    raise RuntimeError("Confidential source downgrades require verified offline backup/restore, not destructive DDL")
