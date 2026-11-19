"""P5A original-byte pilot: fake source transport, no genuine owner's data."""
import base64
from datetime import datetime,timezone
from contextlib import nullcontext
from types import SimpleNamespace
import pytest

from app.drive_google_oauth import DriveOAuthConfig
from app.drive_inbox_planner import _index,_version,DriveFile
from app import private_original_source_preflight as p

FOLDER="SYNTHETIC_P5A_OWNER_FOLDER_2026"
OWNER="SYNTHETIC_P5A_PRIVATE_OWNER_2026"
CLIENT="000000000000-test.apps.googleusercontent.com"
TOKEN="FAKE_PRIVATE_ACCESS_"+"X"*40
CSV=b"date,description,debit,credit,balance,reference\n2026-11-01,FAKE,0,10.00,10.00,R1\n"
PDF=b"%PDF-1.7\nTHIS IS NOT A REAL PDF\n"
OTHER=b"x"*54
META=[
 {"id":"SYNTHETIC_P5A_FILE_ABCDEFGHIJKL","name":"fake.csv",
  "mimeType":"text/csv","parents":[FOLDER],"size":str(len(CSV)),
  "modifiedTime":"2026-11-19T08:00:00Z","md5Checksum":None,"trashed":False},
 {"id":"SYNTHETIC_P5A_FILE_MNOPQRSTUVWX","name":"fake.pdf",
  "mimeType":"application/pdf","parents":[FOLDER],"size":str(len(PDF)),
  "modifiedTime":"2026-11-19T08:00:00Z","md5Checksum":None,"trashed":False},
 {"id":"SYNTHETIC_P5A_FILE_YZABCDEFGHIJ","name":"unsupported.xls",
  "mimeType":"application/vnd.ms-excel","parents":[FOLDER],"size":str(len(OTHER)),
  "modifiedTime":"2026-11-19T08:00:00Z","md5Checksum":None,"trashed":False},
 {"id":"SYNTHETIC_P5A_FILE_KLMNOPQRSTUV","name":"oversized.csv",
  "mimeType":"text/csv","parents":[FOLDER],"size":str(4*1024*1024+1),
  "modifiedTime":"2026-11-19T08:00:00Z","md5Checksum":None,"trashed":False},
]


@pytest.fixture
def cfg(monkeypatch):
    for key in ("P5A_ORIGINAL_HASH_PILOT","P5A_G3_SINGLE_FOLDER_BYTES_REVIEWED",
                "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
                "P3A_G3_RESTRICTED_SCOPE_REVIEWED",
                "P3A_OWNER_CONTENT_CONSENT_ACCEPTED"):
        monkeypatch.setenv(key,"1")
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1W_OWNER_REF",OWNER)
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
                       base64.urlsafe_b64encode(b"H"*32).decode("ascii"))
    config=DriveOAuthConfig(
        client_id=CLIENT,
        redirect_uri="https://example.invalid/callback",
        folder_id=FOLDER,
        folder_hmac=_index("folder",FOLDER),
    )
    monkeypatch.setattr(p,"_guard_network",lambda:config)
    monkeypatch.setattr(p,"read_private_content_grant",lambda *a,**kw:"Z"*60)
    monkeypatch.setattr(p,"refresh_google_content_token",
                        lambda **kw:(TOKEN,None))
    monkeypatch.setattr(p,"verify_owner_private_folder",lambda **kw:None)
    count={"downloads":[],"requests":0}
    def fake_reader(**kw):
        count["downloads"].append(kw["file_id"])
        assert kw["granted_scope"]=="https://www.googleapis.com/auth/drive.readonly"
        assert kw["expected_file_hmac"]==_index("file",kw["file_id"])
        assert kw["expected_name_hmac"]
        return SimpleNamespace(data=CSV,extension=".csv",
                               content_hmac=_index("source-sha256","f"*64),
                               byte_count=len(CSV))
    monkeypatch.setattr(p,"read_pinned_google_source_once",fake_reader)
    monkeypatch.setattr(p,"list_private_owner_folder_page",
      lambda **kw:{"incompleteSearch":False,"files":META})
    return config,count


def scan():
    return p.preflight_original_owner_batch(
       session_factory=lambda:nullcontext(None),owner_ref=OWNER,batch_index=0)


def test_private_content_grant_hashes_only_first_three_by_fixed_order(cfg):
    _,calls=cfg
    result=scan()
    assert result["contract"]=="personal_cfo_private_original_byte_preflight_v1"
    assert result["total_source_files"]==4
    assert result["next_batch"]==1
    assert len(result["results"])==3
    assert result["source_bytes_returned_to_browser"] is False
    assert result["source_hashes_persisted"] is False
    assert result["financial_figures_verified"] is False
    assert result["originals_modified"] is False
    assert len(calls["downloads"])==2
    assert not any("FAKE_PRIVATE_ACCESS" in str(x) for x in result["results"])
    assert all("source_hmac" in x and "revision_hmac" in x for x in result["results"])
    assert not any("data" in x or "raw_bytes" in x for x in result["results"])


def test_next_batch_skips_unsupported_and_does_not_download(cfg):
    _,calls=cfg
    result=p.preflight_original_owner_batch(
        session_factory=lambda:nullcontext(None),owner_ref=OWNER,batch_index=1)
    assert result["next_batch"] is None
    assert len(result["results"])==1
    assert result["results"][0]["state"]=="UNSUPPORTED_FORMAT_REVIEW"
    assert calls["downloads"]==[]


@pytest.mark.parametrize("key",[
 "P5A_ORIGINAL_HASH_PILOT","P5A_G3_SINGLE_FOLDER_BYTES_REVIEWED",
 "P3A_PRIVATE_SOURCE_MEDIA_ENABLED","P3A_G3_RESTRICTED_SCOPE_REVIEWED",
 "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
])
def test_each_gate_required(monkeypatch,cfg,key):
    monkeypatch.setenv(key,"0")
    with pytest.raises(p.PrivateSourcePreflightBlocked):
        scan()


def test_owner_pin_and_real_mode_reject(monkeypatch,cfg):
    with pytest.raises(p.PrivateSourcePreflightBlocked):
        p.preflight_original_owner_batch(
           session_factory=lambda:nullcontext(None),owner_ref="OTHER_PRIVATE_OWNER_2026",
           batch_index=0)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(p.PrivateSourcePreflightBlocked):
        scan()


def test_invalid_batch_rejected(cfg):
    for index in (-1,True,334,"0"):
        with pytest.raises(p.PrivateSourcePreflightBlocked):
            p.preflight_original_owner_batch(
              session_factory=lambda:nullcontext(None),owner_ref=OWNER,batch_index=index)


def test_complete_inventory_required_before_any_download(monkeypatch,cfg):
    _,calls=cfg
    monkeypatch.setattr(p,"list_private_owner_folder_page",
      lambda **kw:{"incompleteSearch":False,
                   "files":[META[0],META[0]],"nextPageToken":None})
    with pytest.raises(p.PrivateSourcePreflightBlocked):
        scan()
    assert calls["downloads"]==[]


def test_outside_folder_metadata_rejected(monkeypatch,cfg):
    _,calls=cfg
    wrong={**META[0],"parents":["SYNTHETIC_UNRELATED_FOLDER_2026"]}
    monkeypatch.setattr(p,"list_private_owner_folder_page",
      lambda **kw:{"incompleteSearch":False,"files":[wrong]})
    with pytest.raises(p.PrivateSourcePreflightBlocked):
        scan()
    assert calls["downloads"]==[]
