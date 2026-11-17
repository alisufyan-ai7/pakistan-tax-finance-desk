"""P1M: isolated encrypted owner Google metadata grant custody (unmounted).

Revision: 0018_owner_google_grants
Down: 0017_drive_scan_leases

Additive schema only, no owner secrets or data migration. This is executed in
disposable PostgreSQL18 CI, NOT automatically on existing Railway PostgreSQL.
Independent backup, restricted DB role and G2 approval precede live use.
"""
from alembic import op
import sqlalchemy as sa

revision="0018_owner_google_grants"
down_revision="0017_drive_scan_leases"
branch_labels=None
depends_on=None


def upgrade():
    op.create_table(
        "owner_google_metadata_grants",
        sa.Column("owner_hmac", sa.String(64), primary_key=True),
        sa.Column("folder_hmac", sa.String(64), nullable=False),
        sa.Column("client_hmac", sa.String(64), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("key_version", sa.String(36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.BigInteger(), nullable=False),
        sa.Column("row_hmac", sa.String(64), nullable=False),
        sa.CheckConstraint("revision > 0", name="ck_owner_google_grant_revision"),
    )


def downgrade():
    raise RuntimeError(
        "Encrypted owner Google metadata custody requires approved backup and "
        "revocation review before schema deletion"
    )
