"""Append-only synthetic loan allocations and explicit own-transfer confirmations.

Revision ID: 0004_finance_links
Revises: 0003_ledger_text
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_finance_links'
down_revision = '0003_ledger_text'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('loan_accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('legal_owner', sa.String(32), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('direction', sa.String(12), nullable=False),
        sa.Column('counterparty_label', sa.Text(), nullable=False),
        sa.Column('opening_as_of', sa.Date(), nullable=False),
        sa.Column('opening_principal_minor', sa.BigInteger(), nullable=False),
        sa.Column('opening_basis', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('opening_principal_minor >= 0', name='ck_loan_opening_nonnegative'))
    op.create_table('loan_allocations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('loan_id', sa.String(36), sa.ForeignKey('loan_accounts.id'), nullable=False),
        sa.Column('transaction_id', sa.String(36), sa.ForeignKey('transactions.id'), nullable=False),
        sa.Column('event_kind', sa.String(12), nullable=False),
        sa.Column('principal_minor', sa.BigInteger(), nullable=False),
        sa.Column('markup_minor', sa.BigInteger(), nullable=False),
        sa.Column('evidence_note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('transaction_id', name='uq_loan_allocation_transaction'),
        sa.CheckConstraint('principal_minor >= 0', name='ck_loan_principal_nonnegative'),
        sa.CheckConstraint('markup_minor >= 0', name='ck_loan_markup_nonnegative'))
    op.create_index('ix_loan_allocations_loan_id', 'loan_allocations', ['loan_id'])
    op.create_table('transfer_confirmations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('debit_transaction_id', sa.String(36), sa.ForeignKey('transactions.id'), nullable=False),
        sa.Column('credit_transaction_id', sa.String(36), sa.ForeignKey('transactions.id'), nullable=False),
        sa.Column('evidence_note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('debit_transaction_id', name='uq_transfer_debit'),
        sa.UniqueConstraint('credit_transaction_id', name='uq_transfer_credit'))


def downgrade():
    raise RuntimeError('Financial-link history must not be destructively downgraded')
