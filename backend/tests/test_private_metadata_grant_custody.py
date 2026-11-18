"""P1M isolated, real-compatible encrypted grant custody with fictional inputs.

No Google account/refresh token, client secret, owner ID or bank source is used.
Production security flags remain absent in Railway and no route is mounted.
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.private_metadata_grant_custody import (
    PrivateMetadataCustodyBlocked,
    store_private_metadata_grant, read_private_metadata_grant,
    rotate_private_metadata_grant, revoke_private_metadata_grant,
)

OWNER="SYNTHETIC_OWNER_PRIVATE_2026"
FOLDER="SYNTHETIC_P1M_FOLDER_ABCDEF2026"
CLIENT="000000000000-syntheticdev.apps.googleusercontent.com"
FAKE_REFRESH="SYNTHETIC_FAKE_REFRESH_" + "X"*72
NOW=1_800_000_000


def encoded(byte: bytes) -> str:
    return base64.urlsafe_b64encode(byte*32).decode("ascii")


@pytest.fixture
def env(tmp_path,monkeypatch):
    values={
        "APP_DATA_MODE":"synthetic",
        "P1M_PRIVATE_METADATA_CUSTODY_ONLY":"1",
        "P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED":"1",
        "P1M_SQLITE_FAKE_TEST_ONLY":"1",
        "P1M_METADATA_ENCRYPTION_KEYS_JSON":json.dumps({
            "cfo-google-key-v1":encoded(b"A"),
            "cfo-google-key-v2":encoded(b"B"),
        }),
        "P1M_METADATA_ACTIVE_KEY_ID":"cfo-google-key-v1",
        "P1M_METADATA_ROW_HMAC_KEY":encoded(b"H"),
    }
    for key,value in values.items():
        monkeypatch.setenv(key,value)
    engine=create_engine("sqlite:///"+str(tmp_path/"metadata-grants-fake.db"),
                         connect_args={"timeout":10})
    Base.metadata.create_all(engine)
    yield engine,monkeypatch
    engine.dispose()


def save(engine,token=FAKE_REFRESH,**kwargs):
    with Session(engine) as db:
        return store_private_metadata_grant(
            db,owner_ref=kwargs.get("owner",OWNER),
            folder_id=kwargs.get("folder",FOLDER),
            client_id=kwargs.get("client",CLIENT),
            refresh_token=token,now_epoch=kwargs.get("now",NOW))


def read(engine,**kwargs):
    with Session(engine) as db:
        return read_private_metadata_grant(
            db,owner_ref=kwargs.get("owner",OWNER),
            folder_id=kwargs.get("folder",FOLDER),
            client_id=kwargs.get("client",CLIENT))


def test_ciphertext_only_no_original_identifiers_or_plain_refresh(env):
    engine,_=env
    receipt=save(engine)
    assert receipt=={
        "metadata_only":True,"sealed_in_private_database":True,
        "revision":1,"connected_to_google":False,
        "original_bytes_authorized":False,"real_finance_authorized":False}
    assert read(engine)==FAKE_REFRESH
    with engine.connect() as db:
        row=db.execute(text("SELECT owner_hmac,folder_hmac,client_hmac,"
            "ciphertext,key_version,revision,revoked,row_hmac "
            "FROM owner_google_metadata_grants")).one()
    assert len(row[0])==len(row[1])==len(row[2])==len(row[7])==64
    assert row[3].startswith("P1M1:")
    assert row[4]=="cfo-google-key-v1" and row[5]==1 and row[6] in (False, 0)
    assert not any(v in str(row) for v in (OWNER,FOLDER,CLIENT,FAKE_REFRESH))


def test_wrong_owner_folder_client_and_key_cannot_decrypt(env):
    engine,monkeypatch=env
    save(engine)
    for kwargs in [{"owner":"SYNTHETIC_OTHER_OWNER_2026"},
                   {"folder":"SYNTHETIC_OTHER_FOLDER_2026"},
                   {"client":"111111111111-syntheticdev.apps.googleusercontent.com"}]:
        with pytest.raises(PrivateMetadataCustodyBlocked):
            read(engine,**kwargs)
    with pytest.raises(PrivateMetadataCustodyBlocked):
        save(engine,folder="SYNTHETIC_OTHER_FOLDER_2026")
    assert read(engine)==FAKE_REFRESH
    monkeypatch.setenv("P1M_METADATA_ENCRYPTION_KEYS_JSON",json.dumps({
        "cfo-google-key-v1":encoded(b"Q"),
        "cfo-google-key-v2":encoded(b"R"),
    }))
    with pytest.raises(PrivateMetadataCustodyBlocked):
        read(engine)


def test_random_nonce_and_transactional_reenrollment(env):
    engine,_=env
    save(engine)
    with engine.connect() as db:
        first=db.execute(text(
            "SELECT ciphertext FROM owner_google_metadata_grants")).scalar_one()
    second=save(engine)
    with engine.connect() as db:
        later=db.execute(text(
            "SELECT ciphertext,revision FROM owner_google_metadata_grants")).one()
    assert later[0]!=first and later[1]==2
    assert second["revision"]==2
    assert read(engine)==FAKE_REFRESH


def test_rotate_to_new_active_key_and_old_backup_retirement_is_explicit(env):
    engine,monkeypatch=env
    save(engine)
    monkeypatch.setenv("P1M_METADATA_ACTIVE_KEY_ID","cfo-google-key-v2")
    with Session(engine) as db:
        rotated=rotate_private_metadata_grant(
            db,owner_ref=OWNER,folder_id=FOLDER,client_id=CLIENT,now_epoch=NOW+1)
    assert rotated["ciphertext_rotated"]
    assert rotated["revision"]==2
    assert not rotated["old_key_removed_from_configuration"]
    assert not rotated["independent_recovery_test_passed"]
    with pytest.raises(PrivateMetadataCustodyBlocked):
        with Session(engine) as db:
            rotate_private_metadata_grant(db,owner_ref=OWNER,folder_id=FOLDER,
                                          client_id=CLIENT,now_epoch=NOW+2)
    assert read(engine)==FAKE_REFRESH
    monkeypatch.setenv("P1M_METADATA_ENCRYPTION_KEYS_JSON",json.dumps({
        "cfo-google-key-v2":encoded(b"B"),
        "cfo-google-key-v3":encoded(b"C"),
    }))
    assert read(engine)==FAKE_REFRESH


def test_revoke_erases_ciphertext_and_reconnect_requires_new_grant(env):
    engine,_=env
    save(engine)
    with Session(engine) as db:
        receipt=revoke_private_metadata_grant(
            db,owner_ref=OWNER,folder_id=FOLDER,client_id=CLIENT,now_epoch=NOW+2)
    assert receipt["local_ciphertext_erased"]
    assert receipt["provider_token_revoked"] is False
    with engine.connect() as db:
        item=db.execute(text(
            "SELECT ciphertext,revoked,revision FROM owner_google_metadata_grants")).one()
    assert item[0]=="" and bool(item[1]) and item[2]==2
    with pytest.raises(PrivateMetadataCustodyBlocked):
        read(engine)
    assert save(engine,now=NOW+3)["revision"]==3
    assert read(engine)==FAKE_REFRESH


@pytest.mark.parametrize("column",[
    "ciphertext","row_hmac","revision","folder_hmac","revoked",
])
def test_sql_row_tamper_is_authentication_failure(env,column):
    engine,_=env
    save(engine)
    new_val={"ciphertext":"P1M1:garbage","row_hmac":"0"*64,
             "revision":9,"folder_hmac":"0"*64,"revoked":True}[column]
    with engine.begin() as db:
        db.execute(text(f"UPDATE owner_google_metadata_grants SET {column}=:value"),
                   {"value":new_val})
    with pytest.raises(PrivateMetadataCustodyBlocked):
        read(engine)
    with pytest.raises(PrivateMetadataCustodyBlocked):
        save(engine)


def test_concurrent_first_writer_atomic_and_no_plaintext(env):
    engine,_=env
    gate=Barrier(2)
    def worker(_):
        gate.wait(timeout=10)
        return save(engine)
    with ThreadPoolExecutor(max_workers=2) as pool:
        versions=list(pool.map(worker,(0,1)))
    assert sorted(x["revision"] for x in versions)==[1,2]
    assert read(engine)==FAKE_REFRESH
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants")).scalar_one()==1


@pytest.mark.parametrize("key,value",[
    ("APP_DATA_MODE","real"),
    ("P1M_PRIVATE_METADATA_CUSTODY_ONLY","0"),
    ("P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED","0"),
    ("P1M_METADATA_ACTIVE_KEY_ID","cfo-google-key-v3"),
    ("P1M_METADATA_ROW_HMAC_KEY",""),
])
def test_default_off_missing_key_and_real_finance_mode_refused(env,key,value):
    engine,monkeypatch=env
    monkeypatch.setenv(key,value)
    with pytest.raises(PrivateMetadataCustodyBlocked):
        save(engine)
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants")).scalar_one()==0


@pytest.mark.parametrize("invalid",[
    "x"*12,
    "bad\nsynthetic_grant",
    "",
    "has space"+"X"*40,
    "X"*4097,
])
def test_invalid_token_does_not_leave_partial_ciphertext(env,invalid):
    engine,_=env
    with pytest.raises(PrivateMetadataCustodyBlocked):
        save(engine,token=invalid)
    with engine.connect() as db:
        assert db.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants")).scalar_one()==0


def test_no_live_google_or_public_route_or_staged_client_secret_access(env):
    from app.preview_api import create_preview_app
    paths={route.path for route in create_preview_app().routes}
    assert "/api/drive/oauth/callback" not in paths
    assert "/api/owner/login" not in paths
    assert "/api/google/metadata" not in paths
    from pathlib import Path
    nginx=(Path(__file__).parents[2]/"frontend/nginx.railway.conf").read_text()
    assert "location = /api/drive/oauth/callback" in nginx
    assert 'if ($p1ao_google_ingress != "1") { return 404; }' in nginx
    source=(Path(__file__).parents[1]/"app/private_metadata_grant_custody.py").read_text()
    assert "os.getenv(\"P1C_GOOGLE_CLIENT_SECRET\"" not in source
    assert "urllib.request" not in source
