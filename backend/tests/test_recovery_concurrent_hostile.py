"""G2 F4 hostile concurrent replay of one synthetic recovery code.

Two separate connections attack the same one-use token simultaneously.
At most one database transaction may commit, with one final audit record.
No live user login, tokens, account identifiers or Railway resources.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import pytest

from app.db import Base
from app import models  # noqa: F401
from app.owner_recovery_codes import RecoveryBlocked
from app.persisted_owner_recovery import (
    issue_persisted_synthetic_codes,consume_persisted_synthetic_code,
    attest_synthetic_recovery_chain,
)

OWNER="owner"
EPOCH=1760000100


def _consume(engine, code, barrier):
    barrier.wait(timeout=5)
    with Session(engine) as db:
        try:
            return bool(consume_persisted_synthetic_code(
                db,owner_ref=OWNER,presented_code=code,
                password_confirmed=True,now_epoch=EPOCH+1,
            )["consumed_once_in_transaction"])
        except RecoveryBlocked:
            return False


def test_simultaneous_recovery_redemption_creates_only_one_commit(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    engine=create_engine(f"sqlite:///{tmp_path / 'concurrent-owner-only.db'}",
                         connect_args={"timeout":10})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _,codes=issue_persisted_synthetic_codes(db,
            owner_ref=OWNER,mfa_confirmed=True,issued_epoch=EPOCH)
    try:
        barrier=Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(_consume,engine,codes[0],barrier)
            second=pool.submit(_consume,engine,codes[0],barrier)
            results=[first.result(timeout=12),second.result(timeout=12)]
        assert sorted(results)==[False,True]
        with Session(engine) as db:
            report=attest_synthetic_recovery_chain(db,owner_ref=OWNER)
            assert report["audit_revision"]==2
            assert report["active_code_count"]==7
        with engine.connect() as c:
            assert c.execute(text("SELECT COUNT(*) FROM owner_recovery_audit")).scalar_one()==2
            assert c.execute(text("SELECT revision FROM owner_recovery_states")).scalar_one()==2
    finally:
        engine.dispose()


def test_failed_redeem_does_not_consume_or_revoke_sessions(tmp_path,monkeypatch):
    from datetime import datetime,timezone,timedelta
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    engine=create_engine(f"sqlite:///{tmp_path / 'invalid-owner-recovery.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _,codes=issue_persisted_synthetic_codes(db,
            owner_ref=OWNER,mfa_confirmed=True,issued_epoch=EPOCH)
        db.add(models.OwnerSession(
            token_sha256="f"*64,csrf_sha256="e"*64,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)+timedelta(hours=1),
            revoked=False))
        db.commit()
    with Session(engine) as db:
        with pytest.raises(RecoveryBlocked):
            consume_persisted_synthetic_code(db,
                owner_ref=OWNER,presented_code="ABCD-"*7+"ABCD",
                password_confirmed=False,now_epoch=EPOCH+1)
        with pytest.raises(RecoveryBlocked):
            consume_persisted_synthetic_code(db,
                owner_ref=OWNER,presented_code=codes[0],
                password_confirmed=True,now_epoch=EPOCH+366*86400)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM owner_recovery_audit")).scalar_one()==1
        assert c.execute(text("SELECT revoked FROM owner_sessions")).scalar_one()==0
    engine.dispose()
