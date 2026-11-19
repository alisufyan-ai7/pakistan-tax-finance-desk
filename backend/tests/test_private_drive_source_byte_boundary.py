"""P2D pinned source byte preflight; fake-only. Never call Google."""
import base64
from datetime import datetime, timezone
from hashlib import sha256

import pytest

from app.drive_inbox_planner import DriveFile,_index
from app.private_drive_source_byte_boundary import (
    PrivateDriveSourceReadBlocked,preflight_synthetic_pinned_source_bytes,
)

FOLDER="SYNTHETIC_P2D_APPROVED_INBOX_2026"
FID="SYNTHETIC_P2D_FILE_ABCDEFGHIJKLMNOP"
RAW=(b"date,description,debit,credit,balance,reference\n"
     b"2026-11-01,fictional salary,0,10.00,110.00,SYNTH-1\n")


@pytest.fixture(autouse=True)
def scope(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P2D_FAKE_ORIGINAL_CONTENT_ONLY","1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
        base64.urlsafe_b64encode(b"G"*32).decode("ascii"))
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))


def metadata(*,name="fictional.csv",mime="text/csv",raw=RAW,
             parent=FOLDER,filesize=None,trashed=False,id=FID):
    return DriveFile(id=id,name=name,mime_type=mime,parent_ids=(parent,),
                     modified_time=datetime(2026,11,19,tzinfo=timezone.utc),
                     size_bytes=len(raw) if filesize is None else filesize,
                     md5_checksum=None,trashed=trashed)


def proof(raw=RAW,meta=None,**kw):
    return preflight_synthetic_pinned_source_bytes(
        folder_id=kw.pop("folder_id",FOLDER),
        file_id=kw.pop("file_id",FID),
        metadata=meta or metadata(raw=raw),
        content=raw,approved_synthetic_fixture=kw.pop("approved",True),
    )


def test_bounded_csv_byte_proof_preserves_hmac_and_immutable_source():
    data=proof()
    assert data["byte_sha256"]==sha256(RAW).hexdigest()
    assert data["byte_sha256_hmac"]!=data["byte_sha256"]
    assert data["file_hmac"]==_index("file",FID)
    assert data["byte_length"]==len(RAW)
    assert data["preflight_status"]=="TABULAR_SIGNATURE_PREFLIGHT_ONLY"
    assert data["complete_source_proof"] is True
    for k in ("provider_network_used","financial_facts_verified",
              "real_finance_enabled","originals_modified",
              "private_encrypted_storage_committed"):
        assert data[k] is False
    assert "fictional salary" not in str(data)
    assert FID not in str(data) and FOLDER not in str(data)
    assert data==proof()


@pytest.mark.parametrize("kwargs",[
    {"meta":metadata.__name__}, # replaced below with an invalid metadata object
    {"approved":False},
    {"folder_id":"SYNTHETIC_UNRELATED_INBOX_2026"},
    {"file_id":"SYNTHETIC_WRONG_FILE_ABCDEFGHIJKL"},
])
def test_authority_fail_closed(kwargs):
    if kwargs.get("meta")==metadata.__name__:
        kwargs={"meta":object()}
    with pytest.raises(PrivateDriveSourceReadBlocked):
        proof(**kwargs)


def test_untrusted_metadata_size_parent_mime_trashed_and_signature():
    for meta in (
        metadata(filesize=len(RAW)+1),
        metadata(parent="SYNTHETIC_WRONG_PARENT_2026"),
        metadata(mime="application/pdf"),
        metadata(trashed=True),
        metadata(name="fictional.pdf"),
    ):
        with pytest.raises(PrivateDriveSourceReadBlocked):
            proof(meta=meta)
    with pytest.raises(PrivateDriveSourceReadBlocked):
        proof(raw=b"%PDF-1.7 wrong format",meta=metadata(raw=b"%PDF-1.7 wrong format"))
    with pytest.raises(PrivateDriveSourceReadBlocked):
        proof(raw=RAW+b"\x00",meta=metadata(raw=RAW+b"\x00"))
    with pytest.raises(PrivateDriveSourceReadBlocked):
        proof(raw=b"x"*(4*1024*1024+1))


def test_fake_pdf_is_quarantined_for_isolated_parser_not_financial_claim():
    raw=b"%PDF-1.7\nSynthetic only mock bytes; NOT parsed.\n"
    data=proof(raw=raw,meta=metadata(name="fake.pdf",mime="application/pdf",raw=raw))
    assert data["format"]=="pdf"
    assert data["preflight_status"]=="ISOLATED_BINARY_PARSER_NOT_YET_APPROVED"
    assert data["financial_facts_verified"] is False


def test_private_gate_never_activated_for_real_data(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(PrivateDriveSourceReadBlocked):
        proof()
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P2D_FAKE_ORIGINAL_CONTENT_ONLY","0")
    with pytest.raises(PrivateDriveSourceReadBlocked):
        proof()
