"""P1N: single-owner private identity and session tables, unmounted code only.

Revision: 0019_private_owner_auth
Down: 0018_owner_google_grants

Additive and audited in disposable PostgreSQL18 CI. Does not auto-apply
to existing Railway PostgreSQL or enroll actual owner credentials.
"""
from alembic import op
import sqlalchemy as sa

revision="0019_private_owner_auth"
down_revision="0018_owner_google_grants"
branch_labels=None
depends_on=None


def upgrade():
    op.create_table(
        "owner_private_identities",
        sa.Column("singleton_id",sa.Integer(),primary_key=True),
        sa.Column("owner_hmac",sa.String(64),nullable=False,unique=True),
        sa.Column("password_scrypt",sa.Text(),nullable=False),
        sa.Column("totp_cipher",sa.Text(),nullable=False),
        sa.Column("last_totp_step",sa.BigInteger(),nullable=False),
        sa.Column("failures",sa.Integer(),nullable=False),
        sa.Column("window_started_epoch",sa.BigInteger(),nullable=False),
        sa.Column("locked_until_epoch",sa.BigInteger(),nullable=False),
        sa.Column("revision",sa.Integer(),nullable=False),
        sa.Column("row_hmac",sa.String(64),nullable=False),
        sa.CheckConstraint("singleton_id = 1",name="ck_owner_private_singleton"),
        sa.CheckConstraint("failures >= 0 AND failures <= 100",
                           name="ck_owner_private_failures"),
        sa.CheckConstraint("revision > 0",name="ck_owner_private_revision"),
    )
    op.create_table(
        "owner_private_sessions",
        sa.Column("token_hmac",sa.String(64),primary_key=True),
        sa.Column("owner_hmac",sa.String(64),nullable=False),
        sa.Column("csrf_hmac",sa.String(64),nullable=False),
        sa.Column("issued_epoch",sa.BigInteger(),nullable=False),
        sa.Column("expires_epoch",sa.BigInteger(),nullable=False),
        sa.Column("revoked",sa.Boolean(),nullable=False),
        sa.CheckConstraint("expires_epoch > issued_epoch",
                           name="ck_owner_private_session_ttl"),
    )
    op.create_index("ix_owner_private_sessions_owner_hmac",
                    "owner_private_sessions",["owner_hmac"])


def downgrade():
    raise RuntimeError(
        "Private owner MFA identity may only be deleted after independently "
        "reviewed session revocation, encrypted backup and account recovery"
    )
