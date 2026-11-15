"""Synthetic cash-in-hand records and append-only reversal evidence.

Revision ID: 0006_cash_wealth
Revises: 0005_link_reversals
No destructive downgrade. Must not accept real financial records.
"""
from alembic import op
import sqlalchemy as sa

revision = '0006_cash_wealth'
down_revision = '0005_link_reversals'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('cash_holdings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('legal_owner', sa.String(32), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('opening_as_of', sa.Date(), nullable=False),
        sa.Column('opening_minor', sa.BigInteger(), nullable=False),
        sa.Column('evidence_basis', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('opening_minor >= 0', name='ck_cash_opening_nonnegative'))
    op.create_table('cash_movements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('cash_id', sa.String(36), sa.ForeignKey('cash_holdings.id'), nullable=False),
        sa.Column('transaction_id', sa.String(36), sa.ForeignKey('transactions.id')),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('posted_on', sa.Date(), nullable=False),
        sa.Column('evidence_note', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('amount_minor > 0', name='ck_cash_movement_positive'),
        sa.CheckConstraint("kind IN ('bank_withdrawal','bank_deposit','manual_receipt','manual_spend')", name='ck_cash_kind_supported'),
        sa.CheckConstraint("(kind IN ('bank_withdrawal','bank_deposit') AND transaction_id IS NOT NULL) OR (kind IN ('manual_receipt','manual_spend') AND transaction_id IS NULL)", name='ck_cash_source_kind'))
    op.create_index('ix_cash_movements_cash_id', 'cash_movements', ['cash_id'])
    op.create_index('uq_active_cash_bank_transaction','cash_movements',['transaction_id'],
        unique=True, postgresql_where=sa.text('active IS TRUE AND transaction_id IS NOT NULL'),
        sqlite_where=sa.text('active = 1 AND transaction_id IS NOT NULL'))
    op.create_table('cash_movement_reversals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('movement_id', sa.String(36), sa.ForeignKey('cash_movements.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('movement_id', name='uq_cash_movement_reversal'))


def downgrade():
    raise RuntimeError('Cash and wealth evidence may not be destructively downgraded')