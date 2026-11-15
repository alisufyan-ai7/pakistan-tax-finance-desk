"""Retain legacy status on older imported documents, never silently rekey.

Revision ID: 0007_keyed_import_digests
Revises: 0006_cash_wealth
"""
from alembic import op
import sqlalchemy as sa

revision='0007_keyed_import_digests'
down_revision='0006_cash_wealth'
branch_labels=None
depends_on=None

def upgrade():
    # PostgreSQL 18 / SQLite compatible. Old documents must be explicitly rebuilt;
    # no automatic conversion from unkeyed SHA256 to an undisclosed HMAC key.
    op.add_column('documents', sa.Column('digest_scheme',sa.String(length=24),
        nullable=False,server_default='legacy_sha256'))

def downgrade():
    raise RuntimeError('Do not destructively discard import fingerprint provenance')