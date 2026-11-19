"""P4B: separate read-only content grant row/keys on existing private SQL."""
import base64
import json

import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa F401
from app.private_metadata_grant_custody import (
    store_private_metadata_grant, read_private_metadata_grant,
    PrivateMetadataCustodyBlocked,
)
from app.private_content_grant_custody import (
    GOOGLE_CONTENT_SCOPE, store_private_content_grant,
    read_private_content_grant, revoke_private_content_grant,
    PrivateContentGrantBlocked,
)

OWNER="SYNTHETIC_PRIVATE_CONTENT_OWNER_2026"
FOLDER="SYNTHETIC_OWNER_GOOGLE_SOURCE_FOLDER_2026"
CLIENT="000000000000-syntheticdev.apps.googleusercontent.com"
CONTENT="synthetic_content_refresh_opaque_"+"C"*50
METADATA="synthetic_metadata_refresh_opaque_"+"M"*50
T=1_800_130_000


def b64(c):
    return base64.urlsafe_b64encode(c*32).decode("ascii")


@pytest.fixture
def conf(tmp_path,monkeypatch):
    values={
        "APP_DATA_MODE":"synthetic",
        "P1M_PRIVATE_METADATA_CUSTODY_ONLY":"1",
        "P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED":"1",
        "P1M_SQLITE_FAKE_TEST_ONLY":"1",
        "P1M_METADATA_ENCRYPTION_KEYS_JSON":json.dumps({
            "cfo-google-key-v1":b64(b"A"),
            "cfo-google-key-v2":b64(b"B"),
        }),
        "P1M_METADATA_ACTIVE_KEY_ID":"cfo-google-key-v1",
        "P1M_METADATA_ROW_HMAC_KEY":b64(b"M"),
        "P4B_PRIVATE_CONTENT_GRANT_CUSTODY":"1",
        "P4B_G2_OWNER_CONTENT_GRANT_REVIEWED":"1",
        "P4B_G3_EXACT_CONTENT_SCOPE_ATTESTED":"1",
    }
    for name,value in values.items():
        monkeypatch.setenv(name,value)
    engine=create_engine("sqlite:///"+str(tmp_path/"fake-scoped-grant.db"),
                         connect_args={"timeout":10})
    Base.metadata.create_all(engine)
    yield engine,monkeypatch
    engine.dispose()


def store_content(engine,token=CONTENT,**kw):
    with Session(engine) as db:
        return store_private_content_grant(
            db,owner_ref=kw.get("owner",OWNER),
            folder_id=kw.get("folder",FOLDER),
            client_id=kw.get("client",CLIENT),
            refresh_token=token,
            verified_granted_scope=kw.get("scope",GOOGLE_CONTENT_SCOPE),
            now_epoch=T,
        )


def store_meta(engine,token=METADATA):
    with Session(engine) as db:
        return store_private_metadata_grant(
            db,owner_ref=OWNER,folder_id=FOLDER,client_id=CLIENT,
            refresh_token=token,now_epoch=T,
        )


def read_meta(engine):
    with Session(engine) as db:
        return read_private_metadata_grant(
            db,owner_ref=OWNER,folder_id=FOLDER,client_id=CLIENT,
        )


def read_content(engine,**kw):
    with Session(engine) as db:
        return read_private_content_grant(
            db,owner_ref=kw.get("owner",OWNER),
            folder_id=kw.get("folder",FOLDER),
            client_id=kw.get("client",CLIENT),
        )


def test_distinct_content_grant_keeps_existing_metadata_unchanged(conf):
    engine,_=conf
    store_meta(engine)
    with engine.connect() as c:
        meta_before=c.execute(text(
            "SELECT owner_hmac,ciphertext,row_hmac,revision "
            "FROM owner_google_metadata_grants")).one()
    result=store_content(engine)
    assert result["encrypted_content_grant_committed"] is True
    assert result["existing_metadata_grant_preserved"] is True
    assert result["original_document_bytes_downloaded"] is False
    assert result["google_network_used"] is False
    assert read_content(engine)==CONTENT
    assert read_meta(engine)==METADATA
    with engine.connect() as c:
        rows=c.execute(text(
            "SELECT owner_hmac,folder_hmac,client_hmac,ciphertext,"
            "row_hmac,revision FROM owner_google_metadata_grants"
            " ORDER BY owner_hmac")).all()
    assert len(rows)==2
    assert any(x[0]==meta_before[0] and x[3]==meta_before[1]
               and x[4]==meta_before[2] and x[5]==meta_before[3] for x in rows)
    assert rows[0][0]!=rows[1][0]
    assert any(x[3].startswith("P4C1:") for x in rows)
    assert any(x[3].startswith("P1M1:") for x in rows)
    raw=str(rows)
    for secret in (OWNER,FOLDER,CLIENT,CONTENT,METADATA):
        assert secret not in raw


def test_missing_content_authorization_not_metadata_fallback(conf):
    engine,_=conf
    store_meta(engine)
    with pytest.raises(PrivateContentGrantBlocked):
        read_content(engine)
    assert read_meta(engine)==METADATA


@pytest.mark.parametrize("scope",[
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
    GOOGLE_CONTENT_SCOPE+" https://www.googleapis.com/auth/drive.metadata.readonly",
])
def test_wrong_or_broader_oauth_scope_not_stored(conf,scope):
    engine,_=conf
    store_meta(engine)
    with pytest.raises(PrivateContentGrantBlocked):
        store_content(engine,scope=scope)
    assert read_meta(engine)==METADATA
    with engine.connect() as c:
        assert c.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants")).scalar_one()==1


def test_only_one_scoped_content_row_idempotent_reenrollment(conf):
    engine,_=conf
    first=store_content(engine)
    assert first["revision"]==1
    second=store_content(engine)
    assert second["revision"]==2
    with engine.connect() as c:
        count=c.execute(text(
            "SELECT count(*) FROM owner_google_metadata_grants")).scalar_one()
    assert count==1
    assert read_content(engine)==CONTENT


def test_wrong_identity_and_wrong_key_fail_closed(conf):
    engine,monkeypatch=conf
    store_content(engine)
    for kwargs in (
        {"owner":"SYNTHETIC_OTHER_OWNER_2026"},
        {"folder":"SYNTHETIC_OTHER_FOLDER_2026"},
        {"client":"000000000000-different.apps.googleusercontent.com"},
    ):
        with pytest.raises(PrivateContentGrantBlocked):
            read_content(engine,**kwargs)
    monkeypatch.setenv("P1M_METADATA_ENCRYPTION_KEYS_JSON",json.dumps({
        "cfo-google-key-v1":b64(b"R"),
        "cfo-google-key-v2":b64(b"S"),
    }))
    with pytest.raises(PrivateContentGrantBlocked):
        read_content(engine)


def test_tampered_content_row_does_not_affect_metadata(conf):
    engine,_=conf
    store_meta(engine)
    store_content(engine)
    with engine.begin() as c:
        c.execute(text(
            "UPDATE owner_google_metadata_grants "
            "SET ciphertext=:bad WHERE ciphertext LIKE 'P4C1:%'"),{"bad":"P4C1:bad"})
    with pytest.raises(PrivateContentGrantBlocked):
        read_content(engine)
    assert read_meta(engine)==METADATA


def test_independent_local_revoke_never_touches_metadata(conf):
    engine,_=conf
    store_meta(engine)
    store_content(engine)
    with Session(engine) as s:
        result=revoke_private_content_grant(
            s,owner_ref=OWNER,folder_id=FOLDER,
            client_id=CLIENT,now_epoch=T+1)
    assert result["content_grant_revoked_locally"] is True
    assert result["provider_revoke_performed"] is False
    assert result["metadata_grant_changed"] is False
    with pytest.raises(PrivateContentGrantBlocked):
        read_content(engine)
    assert read_meta(engine)==METADATA
    restored=store_content(engine)
    assert restored["revision"]==3
    assert read_content(engine)==CONTENT


@pytest.mark.parametrize("gate",[
    "P4B_PRIVATE_CONTENT_GRANT_CUSTODY",
    "P4B_G2_OWNER_CONTENT_GRANT_REVIEWED",
    "P4B_G3_EXACT_CONTENT_SCOPE_ATTESTED",
    "P1M_PRIVATE_METADATA_CUSTODY_ONLY",
])
def test_missing_release_or_root_custody_gate_fails(conf,gate):
    engine,monkeypatch=conf
    monkeypatch.setenv(gate,"0")
    with pytest.raises(PrivateContentGrantBlocked):
        store_content(engine)


def test_metadata_ciphertext_is_not_accepted_as_content_grant(conf):
    engine,_=conf
    store_meta(engine)
    store_content(engine)
    with engine.begin() as c:
        metadata_cipher=c.execute(text(
            "SELECT ciphertext FROM owner_google_metadata_grants "
            "WHERE ciphertext LIKE 'P1M1:%'")).scalar_one()
        c.execute(text(
            "UPDATE owner_google_metadata_grants SET ciphertext=:cipher "
            "WHERE ciphertext LIKE 'P4C1:%'"),{"cipher":metadata_cipher})
    with pytest.raises(PrivateContentGrantBlocked):
        read_content(engine)
    assert read_meta(engine)==METADATA
