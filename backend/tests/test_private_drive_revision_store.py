"""P2B sealed revision snapshot integration: fake files only, never live Google."""
from datetime import datetime, timezone, timedelta
import base64
import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models  # noqa
from app.db import Base
from app.drive_inbox_planner import DriveFile, _index
from app.private_drive_revision_manifest import PrivateDriveRevisionBlocked
from app.private_drive_revision_store import (
    persist_complete_synthetic_revision_snapshot as persist,
    read_synthetic_private_revision_status as read_status,
)

FOLDER = "SYNTHETIC_P2B_DURABLE_OWNER_FOLDER_2026"
OTHER = "SYNTHETIC_OTHER_OWNER_FOLDER_2026"


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("DRIVE_FAKE_TRANSPORT_ONLY","1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
        base64.urlsafe_b64encode(b"I"*32).decode("ascii"))
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    monkeypatch.setenv("LEDGER_FIELD_KEYS_JSON",json.dumps({
        "fake":base64.urlsafe_b64encode(b"E"*32).decode("ascii")}))
    monkeypatch.setenv("LEDGER_FIELD_ACTIVE_KEY","fake")
    db=create_engine(f"sqlite:///{tmp_path/'synthetic-revision.db'}",
                     connect_args={"timeout":8})
    Base.metadata.create_all(db)
    yield db
    db.dispose()


def file(id="SYNTHETIC_DRIVE_SOURCE_ABCDEFGHIJKLMNOP", *,
         name="fake statement.pdf", md5="a"*32, parent=FOLDER,
         clock=None):
    return DriveFile(
        id=id,name=name,mime_type="application/pdf",parent_ids=(parent,),
        modified_time=clock or datetime(2026,11,18,tzinfo=timezone.utc),
        size_bytes=250,md5_checksum=md5,trashed=False,
    )


def run(db,files,**kw):
    return persist(db,folder_id=kw.pop("folder_id",FOLDER), files=tuple(files),
                   snapshot_complete=kw.pop("complete",True),
                   approved_synthetic_fixture=kw.pop("approved",True))


def test_complete_first_scan_restart_and_ciphertext_is_sealed(engine):
    first=file()
    with Session(engine) as db:
        a=run(db,[first])
        assert a["scan_number"]==1
        assert a["stage_counts"]["new"]==1
        assert a["snapshot_persisted_encrypted"] is True
        assert a["visible_sources"]==1
        assert a["provider_network_used"] is False
        assert a["source_content_sha256_computed"] is False
    with Session(engine) as db:
        again=run(db,[first])
        assert again["idempotent_replay"] is True
        assert again["scan_number"]==1
        assert again["stage_counts"]["unchanged"]==1
        status=read_status(db,folder_id=FOLDER)
        assert status["scan_number"]==1
        assert status["tracked_sources"]==1
    with engine.connect() as conn:
        raw=str(conn.execute(text(
            "SELECT * FROM private_drive_revision_snapshots")).all())
        assert "TFLE1:" in raw
        for secret in (FOLDER,first.name,first.id,"fake statement"):
            assert secret not in raw
        assert conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar_one()==0


def test_rename_modified_version_md5_missing_return_preserved(engine):
    first=file()
    second=file(id="SYNTHETIC_DRIVE_SOURCE_ZYXWVUTSRQPONMLK",name="second.pdf")
    with Session(engine) as db:
        run(db,[first,second])
    with Session(engine) as db:
        renamed=run(db,[file(name="renamed.pdf"),second])
        assert renamed["stage_counts"]["name_changed_needs_review"]==1
        assert renamed["scan_number"]==2
        changed=run(db,[file(name="renamed.pdf",md5="b"*32),second])
        assert changed["stage_counts"]["content_hint_changed_needs_sha256"]==1
        later=run(db,[file(name="renamed.pdf",md5="b"*32,
                           clock=datetime(2026,11,19,tzinfo=timezone.utc)),second])
        assert later["stage_counts"]["metadata_changed_needs_review"]==1
        missing=run(db,[second])
        assert missing["missing_historical_sources"]==1
        assert missing["tracked_sources"]==2
        replay=run(db,[second])
        assert replay["idempotent_replay"] is True
        assert replay["missing_historical_sources"]==1
        restored=run(db,[first,second])
        assert restored["stage_counts"]["new"]==1
        assert restored["missing_historical_sources"]==0


def test_failed_or_incomplete_snapshots_do_not_touch_last_good(engine):
    with Session(engine) as db:
        run(db,[file()])
        for kw,files in [
            ({"complete":False},[file(name="changed.pdf")]),
            ({"approved":False},[file(name="changed.pdf")]),
            ({},[file(parent=OTHER)]),
            ({},[file(),file()]),
        ]:
            with pytest.raises(PrivateDriveRevisionBlocked):
                run(db,files,**kw)
    with Session(engine) as db:
        assert read_status(db,folder_id=FOLDER)["scan_number"]==1


def test_wrong_folder_real_mode_and_tamper_fail_closed(engine,monkeypatch):
    with Session(engine) as db:
        run(db,[file()])
        with pytest.raises(PrivateDriveRevisionBlocked):
            run(db,[file(parent=OTHER)],folder_id=OTHER)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with Session(engine) as db:
        with pytest.raises(PrivateDriveRevisionBlocked):
            read_status(db,folder_id=FOLDER)
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    with engine.begin() as conn:
        conn.execute(text(
          "UPDATE private_drive_revision_snapshots SET state_hmac=:fake"),
          {"fake":"a"*64})
    with Session(engine) as db:
        with pytest.raises(PrivateDriveRevisionBlocked,match="integrity"):
            read_status(db,folder_id=FOLDER)
        with pytest.raises(PrivateDriveRevisionBlocked,match="integrity"):
            run(db,[file(name="attempted overwrite.pdf")])
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT scan_number FROM private_drive_revision_snapshots")).scalar_one()==1
