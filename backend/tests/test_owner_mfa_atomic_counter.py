"""G2: atomic single-owner TOTP counter, no two sessions for same OTP step."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.db import Base
from app.auth_mfa import claim_synthetic_totp_step


@pytest.fixture
def engine(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    db=create_engine(f"sqlite:///{tmp_path / 'synthetic-mfa-cas.db'}")
    Base.metadata.create_all(db)
    yield db
    db.dispose()


def test_successive_totp_counter_claims_are_atomic_and_monotone(engine):
    with Session(engine) as db:
        assert claim_synthetic_totp_step(db,100)
        db.commit()
    with Session(engine) as db:
        assert claim_synthetic_totp_step(db,100) is False
        assert claim_synthetic_totp_step(db,99) is False
        assert claim_synthetic_totp_step(db,101)
        db.commit()
    with Session(engine) as db:
        assert claim_synthetic_totp_step(db,100) is False
        assert db.get(models.OwnerAuthState,"owner").last_totp_step==101


def test_failed_otp_claim_cannot_create_session(engine):
    with Session(engine) as db:
        assert claim_synthetic_totp_step(db,100)
        db.commit()
    with Session(engine) as db:
        assert claim_synthetic_totp_step(db,100) is False
        db.rollback()
    with Session(engine) as db:
        assert db.query(models.OwnerSession).count()==0


@pytest.mark.parametrize("step", [-1, True, "100", 1.5])
def test_invalid_totp_counter_rejected(engine,step):
    with Session(engine) as db:
        assert claim_synthetic_totp_step(db,step) is False


def test_production_owner_mfa_not_enabled_by_synthetic_counter(engine,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with Session(engine) as db:
        assert claim_synthetic_totp_step(db,100) is False
        assert db.query(models.OwnerAuthState).count()==0
