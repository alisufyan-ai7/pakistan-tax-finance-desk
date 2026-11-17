"""P1B metadata sync worker: retries, private folder, atomic complete batches."""
import base64
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.db import Base
from app.drive_inbox_planner import _index, DriveInboxBlocked
from app.drive_private_sync import (
    DriveProviderFailure, scan_private_synthetic_folder, safe_owner_inbox_status,
)

FOLDER="SYNTHETIC_ONE_OWNER_FOLDER_2026"


@pytest.fixture
def engine(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("DRIVE_FAKE_TRANSPORT_ONLY","1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",base64.urlsafe_b64encode(b"D"*32).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    eng=create_engine("sqlite:///"+str(tmp_path/"drive_sync.db"))
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def file(number, *, folder=FOLDER, modified="2026-11-17T12:00:00+05:00"):
    return {
        "id":f"SYNTHETIC_DRIVE_FILE_{number:06d}",
        "name":("FBR filing.pdf" if number % 2 else "bank statement.pdf"),
        "mimeType":"application/pdf","parents":[folder],
        "size":"1244","modifiedTime":modified,
    }


def sync(db, transport, *, hook=None):
    return scan_private_synthetic_folder(
        db,folder_id=FOLDER,get_page=transport,
        synthetic_authorization_approved=True,on_retry=hook)


def test_full_pagination_retry_then_encrypted_atomic_scan(engine):
    retries=[]
    calls=[]
    def provider(params):
        calls.append(params)
        if len(calls)==1:
            raise DriveProviderFailure(429)
        if "pageToken" not in params:
            return {"files":[file(1)],"nextPageToken":"SECOND"}
        assert params["pageToken"]=="SECOND"
        return {"files":[file(2)],"incompleteSearch":False}
    with Session(engine) as db:
        report=sync(db,provider,hook=retries.append)
        assert report["complete_folder_scan"]
        assert report["scan_number"]==1 and report["tracked_sources"]==2
        assert report["metadata_page_attempts"]==3
        assert retries==[1]
        assert report["google_oauth_connected_to_pwa"] is False
        status=safe_owner_inbox_status(db,folder_id=FOLDER)
        assert status["contract"]=="personal_cfo_synthetic_document_inbox_v1"
        assert status["tracked"]==2
        assert status["review_queue"] and all(len(row["file_hmac"])==64 for row in status["review_queue"])
        assert not status["owner_data_in_use"]
        assert status["connection"]=="NOT_LIVE_CONNECTED"
    assert all(q["q"]==f"'{FOLDER}' in parents and trashed = false" for q in calls)


def test_failed_second_page_preserves_previous_checkpoint_and_evidence(engine):
    with Session(engine) as db:
        sync(db,lambda params:{"files":[file(1)]})
        with pytest.raises(DriveInboxBlocked):
            sync(db,lambda params: {"files":[file(2)],"nextPageToken":"FAIL"} if "pageToken" not in params
                 else (_ for _ in ()).throw(DriveProviderFailure(503)))
        status=safe_owner_inbox_status(db,folder_id=FOLDER)
        assert status["scan_number"]==1
        assert status["tracked"]==1
        assert status["missing_needing_review"]==0


def test_unauthorized_and_provider_outside_folder_refused_without_mutation(engine):
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            scan_private_synthetic_folder(
                db,folder_id=FOLDER,get_page=lambda _:{"files":[]},
                synthetic_authorization_approved=False)
        with pytest.raises(DriveInboxBlocked):
            sync(db,lambda params:{"files":[file(1,folder="UNRELATED_DRIVE_FOLDER_0001")]})
        with pytest.raises(DriveInboxBlocked):
            sync(db,lambda params:{"files":[file(1)],"incompleteSearch":True})
        assert db.query(models.DriveInboxCheckpoint).count()==0


@pytest.mark.parametrize("http_status",[400,401,403,404,410,429,500,502,503,504])
def test_permanent_and_retryable_errors_never_import_partial_data(engine,http_status):
    calls=[]
    def failed(params):
        calls.append(params)
        raise DriveProviderFailure(http_status)
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked) as err:
            sync(db,failed)
        assert len(calls)==(3 if http_status in (429,500,502,503,504) else 1)
        assert "token" not in str(err.value).lower()
        assert db.query(models.DriveInboxItem).count()==0


def test_no_access_to_real_originals_without_security_approval(engine,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            sync(db,lambda params:{"files":[]})
        with pytest.raises(DriveInboxBlocked):
            safe_owner_inbox_status(db,folder_id=FOLDER)
