"""Baseline synthetic ledger / filing tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-15

No destructive automatic migration of pre-existing SQLite prototype databases:
run on a fresh synthetic DB; never use with personal data without a backup.
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('accounts',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('name',sa.String(80),nullable=False),
        sa.Column('institution',sa.String(80),nullable=False),
        sa.Column('currency',sa.String(3),nullable=False),
        sa.Column('legal_owner',sa.String(32),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('historical_filings',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('tax_year',sa.Integer(),nullable=False),
        sa.Column('legal_entity',sa.String(32),nullable=False),
        sa.Column('kind',sa.String(24),nullable=False),
        sa.Column('filing_status',sa.String(24),nullable=False),
        sa.Column('revision_number',sa.Integer(),nullable=False),
        sa.Column('revision_of_id',sa.String(36),sa.ForeignKey('historical_filings.id')),
        sa.Column('source_sha256',sa.String(64),nullable=False),
        sa.Column('fields_json',sa.Text(),nullable=False),
        sa.Column('imported_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('tax_year','kind','source_sha256',name='uq_historical_filing_digest'),
        sa.UniqueConstraint('tax_year','kind','revision_number',name='uq_historical_filing_revision'))
    op.create_index('ix_historical_filings_tax_year','historical_filings',['tax_year'])
    op.create_table('documents',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('account_id',sa.String(36),sa.ForeignKey('accounts.id'),nullable=False),
        sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('file_format',sa.String(8),nullable=False),
        sa.Column('parser_version',sa.String(24),nullable=False),
        sa.Column('period_start',sa.Date()),sa.Column('period_end',sa.Date()),
        sa.Column('coverage_declared',sa.Boolean(),nullable=False),
        sa.Column('imported_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('account_id','sha256',name='uq_document_content_per_account'))
    op.create_index('ix_documents_account_id','documents',['account_id'])
    op.create_table('transactions',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('account_id',sa.String(36),sa.ForeignKey('accounts.id'),nullable=False),
        sa.Column('document_id',sa.String(36),sa.ForeignKey('documents.id'),nullable=False),
        sa.Column('row_number',sa.Integer(),nullable=False),
        sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('posted_on',sa.Date(),nullable=False),
        sa.Column('description',sa.String(500),nullable=False),
        sa.Column('reference',sa.String(120)),
        sa.Column('debit_minor',sa.Integer(),nullable=False),
        sa.Column('credit_minor',sa.Integer(),nullable=False),
        sa.Column('balance_minor',sa.Integer()),
        sa.Column('category',sa.String(48),nullable=False),
        sa.Column('reviewed',sa.Boolean(),nullable=False),
        sa.Column('overlap_possible',sa.Boolean(),nullable=False),
        sa.Column('excluded',sa.Boolean(),nullable=False),
        sa.Column('overlap_resolved',sa.Boolean(),nullable=False),
        sa.UniqueConstraint('account_id','fingerprint',name='uq_account_fingerprint'),
        sa.UniqueConstraint('document_id','row_number',name='uq_document_row'))
    op.create_index('ix_transactions_posted_on','transactions',['posted_on'])
    op.create_index('ix_transactions_account_id','transactions',['account_id'])
    op.create_table('audit_events',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('transaction_id',sa.String(36),sa.ForeignKey('transactions.id'),nullable=False),
        sa.Column('old_category',sa.String(48),nullable=False),
        sa.Column('new_category',sa.String(48),nullable=False),
        sa.Column('old_excluded',sa.Boolean(),nullable=False),
        sa.Column('new_excluded',sa.Boolean(),nullable=False),
        sa.Column('old_overlap_resolved',sa.Boolean(),nullable=False),
        sa.Column('new_overlap_resolved',sa.Boolean(),nullable=False),
        sa.Column('note',sa.Text(),nullable=False),
        sa.Column('changed_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    # Explicitly fail closed: financial records must never be dropped by accident.
    raise RuntimeError('Irreversible financial-ledger baseline; destructive downgrade disabled')
