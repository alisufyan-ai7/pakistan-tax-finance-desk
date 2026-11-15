"""Audited reversals with active-link unique partial indexes.

Revision ID: 0005_link_reversals
Revises: 0004_finance_links
No destructive downgrade or user-data conversion is supported.
"""
from alembic import op
import sqlalchemy as sa

revision = '0005_link_reversals'
down_revision = '0004_finance_links'
branch_labels = None
depends_on = None


def upgrade():
    # batch_alter_table makes named unique-constraint replacement work on both
    # PostgreSQL and disposable synthetic SQLite databases.
    with op.batch_alter_table('loan_allocations') as batch:
        batch.add_column(sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.drop_constraint('uq_loan_allocation_transaction', type_='unique')
    with op.batch_alter_table('transfer_confirmations') as batch:
        batch.add_column(sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.drop_constraint('uq_transfer_debit', type_='unique')
        batch.drop_constraint('uq_transfer_credit', type_='unique')

    op.create_index('uq_active_loan_allocation_transaction', 'loan_allocations',
                    ['transaction_id'], unique=True,
                    postgresql_where=sa.text('active IS TRUE'),
                    sqlite_where=sa.text('active = 1'))
    op.create_index('uq_active_transfer_debit', 'transfer_confirmations',
                    ['debit_transaction_id'], unique=True,
                    postgresql_where=sa.text('active IS TRUE'),
                    sqlite_where=sa.text('active = 1'))
    op.create_index('uq_active_transfer_credit', 'transfer_confirmations',
                    ['credit_transaction_id'], unique=True,
                    postgresql_where=sa.text('active IS TRUE'),
                    sqlite_where=sa.text('active = 1'))

    op.create_table('loan_allocation_reversals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('allocation_id', sa.String(36), sa.ForeignKey('loan_allocations.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('allocation_id', name='uq_loan_allocation_reversal'))
    op.create_table('transfer_revocations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('confirmation_id', sa.String(36), sa.ForeignKey('transfer_confirmations.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('confirmation_id', name='uq_transfer_revocation'))


def downgrade():
    raise RuntimeError('Financial-link reversal records must not be destructively downgraded')
