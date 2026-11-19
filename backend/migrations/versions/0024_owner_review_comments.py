"""P5B genuine owner review comments: additive encrypted app-owned evidence.

DO NOT auto-run in Railway startup. Run only after reviewed ciphertext backup,
disposable restore and exact-schema acceptance, using migration role.
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_review_comments"
down_revision = "0023_drive_revision"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "owner_financial_review_comments",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("owner_hmac",sa.String(64),nullable=False),
        sa.Column("subject_hmac",sa.String(64),nullable=False),
        sa.Column("subject_kind",sa.String(16),nullable=False),
        sa.Column("revision",sa.Integer(),nullable=False),
        sa.Column("ciphertext",sa.Text(),nullable=False),
        sa.Column("row_hmac",sa.String(64),nullable=False),
        sa.Column("created_epoch",sa.BigInteger(),nullable=False),
        sa.CheckConstraint("revision > 0",name="ck_owner_review_revision_positive"),
        sa.CheckConstraint("created_epoch > 0",name="ck_owner_review_created_positive"),
    )
    op.create_index("ix_owner_review_subject",
                    "owner_financial_review_comments",
                    ["owner_hmac","subject_hmac"],unique=False)
    op.create_index(op.f("ix_owner_financial_review_comments_owner_hmac"),
                    "owner_financial_review_comments",["owner_hmac"],unique=False)

def downgrade():
    raise RuntimeError("Private owner review comments are append-only evidence: protected backup and owner-reviewed archival required before any drop")
