"""Add owner-auth replay and hashed session tables for synthetic MFA gateway.

Revision ID: 0002_owner_mfa
Revises: 0001_initial
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa

revision='0002_owner_mfa'
down_revision='0001_initial'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('owner_auth_state',
        sa.Column('owner_id',sa.String(32),primary_key=True),
        sa.Column('last_totp_step',sa.Integer(),nullable=False))
    op.create_table('owner_sessions',
        sa.Column('token_sha256',sa.String(64),primary_key=True),
        sa.Column('csrf_sha256',sa.String(64),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('revoked',sa.Boolean(),nullable=False))

def downgrade():
    raise RuntimeError('Destructive downgrade of authentication audit/session schema is disabled')
