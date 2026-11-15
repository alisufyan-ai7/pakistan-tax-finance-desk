"""Immutable encrypted owner-declared asset snapshot payloads.

Revision ID: 0008_asset_snapshots
Revises: 0007_keyed_import_digests
"""
from alembic import op
import sqlalchemy as sa
revision='0008_asset_snapshots'
down_revision='0007_keyed_import_digests'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('asset_snapshots',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('payload_json',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    raise RuntimeError('Cannot discard encrypted historical assets through destructive downgrade')