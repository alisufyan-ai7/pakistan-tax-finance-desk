"""P1J: hostile fake scan leases, last-good integrity, failure and restart tests."""
import base64
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.drive_inbox_planner import _index,DriveInboxBlocked
from app.drive_private_sync import scan_private_synthetic_folder,DriveProviderFailure
from app.drive_scan_lease import (
    acquire_fake_scan_lease,finish_fake_scan_lease,fake_scan_lease_status,
)

FOLDER="SYNTHETIC_P1J_APPROVED_DROP_FOLDER_2026"
T=1800000000


@pytest.fixture
def engine(tmp_path,monkeypatch):
    env={
        "APP_DATA_MODE":"synthetic",
        "DRIVE_FAKE_TRANSPORT_ONLY":"1",
        "P1J_FAKE_SCAN_LEASE_ONLY":"1",
        "P1J_SQLITE_TEST_ONLY":"1",
        "DRIVE_INDEX_HMAC_KEY":base64.urlsafe_b64encode(b"D"*32).decode(),
    }
    for name,value in env.items():
        monkeypatch.setenv(name,value)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    db=create_engine("sqlite:///"+str(tmp_path/"synthetic-scan-lease.db"),
                     connect_args={"timeout":10})
    Base.metadata.create_all(db)
    yield db
    db.dispose()


def fake_page(params):
    return {"files":[{
        "id":"SYNTHETIC_P1J_FILE_00000001",
        "name":"fictional bank statement.pdf",
        "mimeType":"application/pdf",
        "parents":[FOLDER],
        "size":"1214",
        "modifiedTime":"2026-11-17T12:00:00+05:00",
    }]}


def scan(engine,provider=fake_page):
    with Session(engine) as db:
        return scan_private_synthetic_folder(
            db,folder_id=FOLDER,get_page=provider,
            synthetic_authorization_approved=True)


def acquire(engine,at=T):
    with Session(engine) as db:
        return acquire_fake_scan_lease(db,folder_id=FOLDER,now_epoch=at)


def finish(engine,token,outcome="success",receipt=None,at=T+1):
    with Session(engine) as db:
        return finish_fake_scan_lease(
            db,folder_id=FOLDER,lease_token=token,outcome=outcome,
            complete_receipt=receipt,now_epoch=at)


def status(engine,at=T):
    with Session(engine) as db:
        return fake_scan_lease_status(db,folder_id=FOLDER,now_epoch=at)


def test_initial_lease_complete_scan_stores_only_keyed_last_good_receipt(engine):
    first=status(engine)
    assert first["last_scan_number"]==0
    assert first["last_success_epoch"] is None
    token=acquire(engine)
    assert status(engine)["lease_active"]
    receipt=scan(engine)
    assert receipt["complete_folder_scan"] is True
    assert receipt["scan_number"]==1
    done=finish(engine,token,receipt=receipt)
    assert done["last_complete_scan_preserved"] is True
    assert done["google_drive_connected"] is False
    final=status(engine,T+2)
    assert final["last_success_epoch"]==T+1
    assert final["last_scan_number"]==1
    assert not final["heartbeat_is_real"]
    assert not final["background_job_started"]
    with engine.connect() as db:
        row=db.execute(text(
            "SELECT folder_hmac,lease_hmac,last_source_hmac,last_receipt_hmac FROM drive_scan_leases"
        )).one()
        assert len(row[0])==64 and row[1] is None
        assert len(row[2])==64 and len(row[3])==64
        assert token not in str(row) and FOLDER not in str(row)
        assert "bank statement" not in str(row)


def test_concurrent_fresh_acquisition_only_one_worker_wins(engine):
    gate=Barrier(2)
    def worker(_):
        gate.wait(timeout=10)
        with Session(engine) as db:
            try:
                return acquire_fake_scan_lease(db,folder_id=FOLDER,now_epoch=T)
            except DriveInboxBlocked:
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(worker,range(2)))
    assert sum(token is not None for token in results)==1
    assert status(engine)["lease_active"]


def test_expired_takeover_rejects_stale_worker_and_replay(engine):
    old=acquire(engine)
    with pytest.raises(DriveInboxBlocked):
        acquire(engine,T+299)
    newer=acquire(engine,T+301)
    assert newer!=old
    with pytest.raises(DriveInboxBlocked):
        finish(engine,old,outcome="retryable",at=T+302)
    receipt=scan(engine)
    assert finish(engine,newer,receipt=receipt,at=T+303)["outcome"]=="success"
    with pytest.raises(DriveInboxBlocked):
        finish(engine,newer,receipt=receipt,at=T+304)
    assert status(engine,T+304)["last_success_epoch"]==T+303


def test_incomplete_second_page_and_retry_preserves_previous_good_scan(engine):
    old=acquire(engine)
    receipt=scan(engine)
    finish(engine,old,receipt=receipt)
    new=acquire(engine,T+600)
    calls=[]
    def flaky(params):
        calls.append(params)
        if "pageToken" not in params:
            return {"files":fake_page(params)["files"],"nextPageToken":"SECOND"}
        raise DriveProviderFailure(503)
    with pytest.raises(DriveInboxBlocked):
        scan(engine,flaky)
    assert len(calls)==4  # one first page + three bounded retries
    with pytest.raises(DriveInboxBlocked):
        finish(engine,new,receipt={"complete_folder_scan":False},at=T+601)
    finish(engine,new,outcome="retryable",at=T+602)
    latest=status(engine,T+603)
    assert latest["last_scan_number"]==1
    assert latest["last_success_epoch"]==T+1
    assert latest["permission_state"]=="FICTIONAL_TEST_ONLY"
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT scan_number FROM drive_inbox_checkpoints"
        )).scalar_one()==1


def test_complete_idempotent_replay_refreshes_only_last_good_time(engine):
    one=acquire(engine)
    first=scan(engine)
    finish(engine,one,receipt=first)
    again=acquire(engine,T+601)
    second=scan(engine)
    assert second["idempotent_replay"] is True
    assert second["scan_number"]==first["scan_number"]
    finish(engine,again,receipt=second,at=T+602)
    saved=status(engine,T+603)
    assert saved["last_scan_number"]==1
    assert saved["last_success_epoch"]==T+602


def test_denied_access_halts_new_leases_retains_last_success(engine):
    one=acquire(engine)
    done=scan(engine)
    finish(engine,one,receipt=done)
    another=acquire(engine,T+600)
    finish(engine,another,outcome="denied",at=T+601)
    health=status(engine,T+90000)
    assert health["permission_state"]=="REAUTHORIZATION_REQUIRED"
    assert health["last_scan_number"]==1
    assert health["last_success_epoch"]==T+1
    with pytest.raises(DriveInboxBlocked):
        acquire(engine,T+90000)


def test_corrupted_last_good_hmac_refused_even_after_restart(engine):
    one=acquire(engine)
    finish(engine,one,receipt=scan(engine))
    with engine.begin() as db:
        db.execute(text(
            "UPDATE drive_scan_leases SET last_success_epoch=:x"),{"x":T+99})
    with pytest.raises(DriveInboxBlocked,match="authenticated"):
        status(engine,T+120)
    with pytest.raises(DriveInboxBlocked,match="authenticated"):
        acquire(engine,T+600)


def test_success_requires_actual_committed_integrity_checked_snapshot(engine):
    token=acquire(engine)
    forged={"complete_folder_scan":True,"scan_number":1,"tracked_sources":1,
        "google_oauth_connected_to_pwa":False,"source_content_imported":False,
        "reconciliation_ready":False}
    with pytest.raises(DriveInboxBlocked):
        finish(engine,token,receipt=forged)
    assert status(engine)["last_success_epoch"] is None
    with pytest.raises(DriveInboxBlocked):
        finish(engine,token,outcome="retryable",receipt=forged)


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("DRIVE_FAKE_TRANSPORT_ONLY","0"),
    ("P1J_FAKE_SCAN_LEASE_ONLY","0"),
    ("DRIVE_ALLOWED_FOLDER_HMAC","0"*64),
])
def test_real_mode_and_wrong_permission_fail_closed(engine,monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            acquire_fake_scan_lease(db,folder_id=FOLDER,now_epoch=T)
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            fake_scan_lease_status(db,folder_id=FOLDER,now_epoch=T)


def test_no_public_scheduler_or_google_callback(engine):
    from app.preview_api import create_preview_app
    routes={route.path for route in create_preview_app().routes}
    assert "/api/drive/scheduler/run" not in routes
    assert "/api/drive/oauth/callback" not in routes
    assert "/internal/drive/sync/run" not in routes
