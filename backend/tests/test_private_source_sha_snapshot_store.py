"""P5I fixture-only encrypted, owner-bound source SHA snapshot persistence."""
import base64
import json
from datetime import datetime,timezone

import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session

from app import models  # noqa
from app.db import Base
from app.drive_inbox_planner import DriveFile, _index, _version
from app.private_source_sha_snapshot_store import (
    PrivateSourceShaStoreBlocked as Blocked,
    persist_complete_synthetic_source_sha_snapshot as persist,
    read_synthetic_source_sha_snapshot_status as status,
)

OWNER="SYNTHETIC_P5I_ENCRYPTED_OWNER_2026"
OTHER="SYNTHETIC_P5I_DIFFERENT_OWNER_2026"
FOLDER="SYNTHETIC_P5I_ENCRYPTED_FOLDER_2026"
ID1="SYNTHETIC_P5I_SHA_SOURCE_ABCDEFGHIJKL"
ID2="SYNTHETIC_P5I_SHA_SOURCE_ZYXWVUTSRQPO"

@pytest.fixture
def engine(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P5I_FAKE_SHA_STORE_ONLY","1")
    monkeypatch.setenv("P5I_SYNTHETIC_SHA_PLANNER_ONLY","1")
    monkeypatch.setenv("P1W_OWNER_REF",OWNER)
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
                       base64.urlsafe_b64encode(b"I"*32).decode("ascii"))
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    monkeypatch.setenv("LEDGER_FIELD_KEYS_JSON",json.dumps({
        "fake":base64.urlsafe_b64encode(b"E"*32).decode("ascii")
    }))
    monkeypatch.setenv("LEDGER_FIELD_ACTIVE_KEY","fake")
    engine=create_engine(f"sqlite:///{tmp_path/'sealed-sha.sqlite'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

def f(fid=ID1,name="synthetic bank.pdf"):
    return DriveFile(id=fid,name=name,mime_type="application/pdf",
        parent_ids=(FOLDER,),modified_time=datetime(2026,11,19,tzinfo=timezone.utc),
        size_bytes=420,md5_checksum="a"*32,trashed=False)

def proof(item,content="a"):
    return {
      "source_hmac":_index("file",item.id),
      "revision_hmac":_version(item),
      "source_content_hmac":_index("source-sha256",content*64),
      "byte_hash_verified":True,
    }

def run(db,files,proofs=None,**kwargs):
    files=tuple(files)
    if proofs is None: proofs=tuple(proof(item) for item in files)
    return persist(db,owner_ref=kwargs.pop("owner",OWNER),
        folder_id=FOLDER,files=files,proof_receipts=tuple(proofs),
        inventory_complete=kwargs.pop("complete",True),
        proofs_complete=kwargs.pop("proven",True),
        approved_synthetic_fixture=kwargs.pop("approved",True))

def test_encrypted_complete_scan_replay_and_change_is_atomic(engine):
    a,b=f(),f(ID2,"second synthetic.pdf")
    with Session(engine) as db:
        first=run(db,[a,b])
        assert first["scan_number"]==1
        assert first["manifest_ciphertext_persisted"]
        assert first["visible_sources"]==2
        assert first["financial_values_verified"] is False
        again=run(db,[b,a])
        assert again["idempotent_replay"] is True
        assert again["scan_number"]==1
        renamed=run(db,[f(name="renamed synthetic.pdf"),b])
        assert renamed["scan_number"]==2
        assert renamed["stage_counts"]["renamed_needs_review"]==1
        changed=run(db,[a,b],proofs=[proof(a,"b"),proof(b)])
        assert changed["scan_number"]==3
        assert changed["stage_counts"]["content_changed_needs_review"]==1
    with engine.connect() as conn:
        table=str(conn.execute(text("SELECT * FROM private_source_sha_snapshots")).all())
        assert "TFLE1:" in table
        for secret in (OWNER,FOLDER,ID1,ID2,"synthetic bank.pdf","second synthetic.pdf"):
            assert secret not in table
        assert conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar_one()==0
    with Session(engine) as db:
        s=status(db,owner_ref=OWNER,folder_id=FOLDER)
        assert s["scan_number"]==3 and s["tracked_sources"]==2

def test_partial_bad_owner_and_tamper_fail_closed(engine,monkeypatch):
    a=f()
    with Session(engine) as db:
        run(db,[a])
        for kwargs,proofs in [
          ({"complete":False},[proof(a)]),
          ({"proven":False},[proof(a)]),
          ({},[]),
          ({},[dict(proof(a),byte_hash_verified=False)]),
          ({"owner":OTHER},[proof(a)]),
        ]:
            with pytest.raises(Blocked):
                run(db,[a],proofs,**kwargs)
    with Session(engine) as db:
        assert status(db,owner_ref=OWNER,folder_id=FOLDER)["scan_number"]==1
    with engine.begin() as conn:
        conn.execute(text(
          "UPDATE private_source_sha_snapshots SET state_hmac=:tampered"),
          {"tampered":"f"*64})
    with Session(engine) as db:
        with pytest.raises(Blocked):
            status(db,owner_ref=OWNER,folder_id=FOLDER)
        with pytest.raises(Blocked):
            run(db,[a])
    with engine.connect() as conn:
        assert conn.execute(text(
          "SELECT scan_number FROM private_source_sha_snapshots")).scalar_one()==1

def test_no_activation_outside_synthetic_mode(engine,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with Session(engine) as db:
        with pytest.raises(Blocked):
            run(db,[f()])
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.delenv("P5I_FAKE_SHA_STORE_ONLY")
    with Session(engine) as db:
        with pytest.raises(Blocked):
            run(db,[f()])
