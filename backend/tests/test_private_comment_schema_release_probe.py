"""P5D read-only comments migration release gap tests, no owner data."""
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app import models  # noqa
from app.db import Base
from app.private_comment_schema_release_probe import (
    inspect_private_comment_release_gaps as inspect_gaps,
    PrivateCommentReleaseProbeBlocked as Blocked,
)

@pytest.fixture
def db(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P5D_COMMENT_SCHEMA_PROBE_ONLY","1")
    engine=create_engine(f"sqlite:///{tmp_path/'comments-schema.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('0024_review_comments')"))
    with Session(engine) as session:
        yield session
    engine.dispose()

def test_schema_observation_does_not_certify_restore_or_public_comments(db):
    before=db.execute(text("SELECT COUNT(*) FROM owner_financial_review_comments")).scalar_one()
    result=inspect_gaps(db,approved_synthetic_diagnostic=True)
    assert result["schema_table_present"] is True
    assert result["schema_columns_match"] is True
    assert result["alembic_revision_compatible"] is True
    assert result["independent_encrypted_off_device_backup_verified"] is False
    assert result["disposable_full_database_restore_verified"] is False
    assert result["saving_comments_live"] is False
    assert result["release_authorized"] is False
    after=db.execute(text("SELECT COUNT(*) FROM owner_financial_review_comments")).scalar_one()
    assert before==after==0

def test_wrong_revision_and_missing_schema_fail_gates(db):
    db.execute(text("UPDATE alembic_version SET version_num='0023_drive_revision'"))
    db.commit()
    result=inspect_gaps(db,approved_synthetic_diagnostic=True)
    assert not result["alembic_revision_compatible"]
    db.rollback()
    db.execute(text("DROP TABLE owner_financial_review_comments"))
    db.commit()
    result=inspect_gaps(db,approved_synthetic_diagnostic=True)
    assert result["schema_table_present"] is False
    assert result["schema_columns_match"] is False
    assert not result["release_authorized"]

@pytest.mark.parametrize("reason",["real","missing_flag","approval_false"])
def test_probe_requires_explicit_fake_review_mode(db,monkeypatch,reason):
    if reason=="real":monkeypatch.setenv("APP_DATA_MODE","real")
    if reason=="missing_flag":monkeypatch.delenv("P5D_COMMENT_SCHEMA_PROBE_ONLY")
    with pytest.raises(Blocked):
        inspect_gaps(db,approved_synthetic_diagnostic=(reason!="approval_false"))
