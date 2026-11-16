"""G2 F3 persisted synthetic recovery: atomic one-use, encrypted and chained audit."""
import base64
import json
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa: F401
from app.persisted_owner_recovery import (
    issue_persisted_synthetic_codes,
    consume_persisted_synthetic_code,
    attest_synthetic_recovery_chain,
)
from app.owner_recovery_codes import RecoveryBlocked, _tag

OWNER = "owner"
EPOCH = 1760000000


@pytest.fixture
def engine(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("OWNER_RECOVERY_HMAC_KEY",
                       base64.urlsafe_b64encode(b"Q"*32).decode("ascii"))
    eng=create_engine(f"sqlite:///{tmp_path / 'only-fake-recovery.db'}")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def issue(db,**opts):
    return issue_persisted_synthetic_codes(
        db, owner_ref=OWNER, mfa_confirmed=True, issued_epoch=EPOCH, **opts
    )


def redeem(db,code,**opts):
    return consume_persisted_synthetic_code(
        db, owner_ref=OWNER, presented_code=code,
        password_confirmed=True, now_epoch=EPOCH+1, **opts
    )


def test_persist_one_time_codes_and_authenticated_history(engine):
    with Session(engine) as db:
        report,codes=issue(db)
        assert report["persisted_atomically"] and len(codes)==8
        assert report["recovery_revision"]==1
        recovered=redeem(db,codes[0])
        assert recovered["recovery_revision"]==2
        assert recovered["login_session_issued"] is False
        assert recovered["totp_reset"] is False
    with Session(engine) as db:
        with pytest.raises(RecoveryBlocked,match="already used"):
            redeem(db,codes[0])
        next_report=redeem(db,codes[1])
        assert next_report["recovery_revision"]==3
        checked=attest_synthetic_recovery_chain(db,owner_ref=OWNER)
        assert checked["audit_revision"]==3
        assert checked["active_code_count"]==6
        assert checked["prod_owner_recovery_certified"] is False
    with engine.connect() as c:
        stored=c.execute(text("SELECT bundle_json FROM owner_recovery_states")).scalar_one()
        details=c.execute(text("SELECT detail_json FROM owner_recovery_audit")).all()
        assert stored.startswith("TFLE1:") and len(details)==3
        assert all(item[0].startswith("TFLE1:") for item in details)
        assert all(code.replace("-","") not in stored for code in codes)
        assert all(code not in stored for code in codes)
        assert c.execute(text("SELECT count(*) FROM owner_sessions")).scalar_one()==0


def test_code_reissuance_revokes_all_prior_codes(engine):
    with Session(engine) as db:
        _,first=issue(db)
        second,codes=issue_persisted_synthetic_codes(
            db,owner_ref=OWNER,mfa_confirmed=True,issued_epoch=EPOCH+100)
        assert second["recovery_revision"]==2
        with pytest.raises(RecoveryBlocked):
            consume_persisted_synthetic_code(
                db, owner_ref=OWNER,presented_code=first[0],
                password_confirmed=True,now_epoch=EPOCH+101)
        assert consume_persisted_synthetic_code(
            db,owner_ref=OWNER,presented_code=codes[0],
            password_confirmed=True,now_epoch=EPOCH+101
        )["consumed_once_in_transaction"]
        assert attest_synthetic_recovery_chain(db,owner_ref=OWNER)["audit_revision"]==3


def test_password_and_mfa_proof_are_both_required(engine):
    with Session(engine) as db:
        with pytest.raises(RecoveryBlocked):
            issue_persisted_synthetic_codes(db,owner_ref=OWNER,
                                            mfa_confirmed=False,issued_epoch=EPOCH)
        _,codes=issue(db)
        with pytest.raises(RecoveryBlocked):
            consume_persisted_synthetic_code(
                db,owner_ref=OWNER,presented_code=codes[0],
                password_confirmed=False,now_epoch=EPOCH+1)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM owner_recovery_audit")).scalar_one()==1


def test_recovery_audit_row_deletion_is_detected(engine):
    with Session(engine) as db:
        _,codes=issue(db)
        redeem(db,codes[0])
    with engine.begin() as c:
        c.execute(text("DELETE FROM owner_recovery_audit WHERE revision=1"))
    with Session(engine) as db:
        with pytest.raises(RecoveryBlocked,match="incomplete"):
            attest_synthetic_recovery_chain(db,owner_ref=OWNER)
        with pytest.raises(RecoveryBlocked):
            redeem(db,codes[1])


def test_altered_chain_or_state_ciphertext_denied(engine):
    with Session(engine) as db:
        _,codes=issue(db)
    with engine.begin() as c:
        c.execute(text("UPDATE owner_recovery_audit SET bundle_hmac = :bad"),
                  {"bad":"0"*64})
    with Session(engine) as db:
        with pytest.raises(RecoveryBlocked,match="authenticity"):
            redeem(db,codes[0])


def test_real_mode_no_recovery_write_or_owner_login(engine,monkeypatch):
    with Session(engine) as db:
        _,codes=issue(db)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with Session(engine) as db:
        with pytest.raises(RecoveryBlocked,match="Real"):
            issue(db)
        with pytest.raises(RecoveryBlocked):
            redeem(db,codes[0])
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM owner_recovery_audit")).scalar_one()==1


def test_owner_hmac_only_no_plain_owner_fields(engine):
    with Session(engine) as db:
        _,codes=issue(db)
    with engine.connect() as conn:
        owner=conn.execute(text("SELECT owner_hmac FROM owner_recovery_states")).scalar_one()
        assert owner==_tag(b"owner",OWNER)
        assert OWNER not in owner
        assert len(owner)==64


def test_recovery_code_redemption_revokes_existing_synthetic_sessions(engine):
    from datetime import datetime, timedelta, timezone
    from app.models import OwnerSession
    with Session(engine) as db:
        _,codes=issue(db)
        db.add(OwnerSession(
            token_sha256="a"*64, csrf_sha256="b"*64,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)+timedelta(hours=2),
            revoked=False))
        db.commit()
        result=redeem(db,codes[0])
        assert result["active_sessions_revoked"]==1
        assert result["login_session_issued"] is False
    with engine.connect() as c:
        assert c.execute(text("SELECT revoked FROM owner_sessions")).scalar_one() == 1
