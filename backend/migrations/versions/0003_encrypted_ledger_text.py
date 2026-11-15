"""Widen synthetic financial text columns for authenticated encryption envelopes.

Revision ID: 0003_ledger_text
Revises: 0002_owner_mfa

IMPORTANT: This is a *schema-only* migration. Existing synthetic plaintext rows
are NOT automatically converted to ciphertext. Application fails closed for
unsealed values. Use explicit backup/authorized wipe and reimport of synthetic
fixtures. Never treat this as permission to import real financial information.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_ledger_text"
down_revision = "0002_owner_mfa"
branch_labels = None
depends_on = None

COLUMNS = {
    "accounts": {"name": 80, "institution": 80},
    "transactions": {"description": 500, "reference": 120, "category": 48},
    "audit_events": {"old_category": 48, "new_category": 48, "note": None},
}


def upgrade():
    for table, columns in COLUMNS.items():
        with op.batch_alter_table(table) as batch:
            for name, old_length in columns.items():
                if old_length is not None:
                    batch.alter_column(name, existing_type=sa.String(old_length), type_=sa.Text(),
                                       existing_nullable=name == "reference")


def downgrade():
    raise RuntimeError("Financial ciphertext columns cannot be truncated or downgraded")