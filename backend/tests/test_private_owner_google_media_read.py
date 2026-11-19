"""P3A source bytes: synthetic trusted transport only, no Google/owner access."""
from datetime import datetime, timezone
from hashlib import sha256
import base64
from urllib.parse import parse_qs,urlsplit

import pytest

from app.drive_inbox_planner import DriveFile,_index,_version
from app.drive_google_oauth import DriveOAuthConfig
from app import private_owner_google_media_read as reader

FOLDER="SYNTHETIC_P3A_APPROVED_OWNER_FOLDER_2026"
FILE_ID="SYNTHETIC_P3A_TEST_FILE_ABCDEF"
RAW=b"date,description,debit,credit,balance\n2026-11-01,Fake,0,1.00,1.00\n"
META={
    "id":FILE_ID,"name":"fake.csv","mimeType":"text/csv",
    "parents":[FOLDER],"size":str(len(RAW)),
    "modifiedTime":"2026-11-19T10:00:00Z","md5Checksum":None,
    "trashed":False,"capabilities":{"canDownload":True},
}


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P3A_PRIVATE_SOURCE_MEDIA_ENABLED","1")
    monkeypatch.setenv("P3A_G3_RESTRICTED_SCOPE_REVIEWED","1")
    monkeypatch.setenv("P3A_OWNER_CONTENT_CONSENT_ACCEPTED","1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
                       base64.urlsafe_b64encode(b"A"*32).decode("ascii"))
    cfg=DriveOAuthConfig(
        client_id="000000000000-test.apps.googleusercontent.com",
        redirect_uri="https://example.invalid/test",folder_id=FOLDER,
        folder_hmac=_index("folder",FOLDER),
    )
    monkeypatch.setattr(reader,"_guard_network",lambda:cfg)


def expected(raw=META):
    record=DriveFile(
        id=raw["id"],name=raw["name"],mime_type=raw["mimeType"],
        parent_ids=tuple(raw["parents"]),
        size_bytes=int(raw["size"]),
        modified_time=datetime.fromisoformat(raw["modifiedTime"].replace("Z","+00:00")),
        md5_checksum=raw["md5Checksum"],trashed=raw["trashed"],
    )
    return _index("file",record.id),_version(record)


def run(metadata=None, body=RAW, *, scope=reader._CONTENT_SCOPE,
        repeat=None, verifier=None, file_id=FILE_ID, **extra):
    h,r=expected()
    calls=[]
    def google(method,url,form,token):
        calls.append(("metadata",method,url))
        assert method=="GET" and form is None and token=="A"*40
        return metadata if metadata is not None else META
    def media(method,url,token):
        calls.append(("media",method,url))
        assert method=="GET" and token=="A"*40
        return body
    if repeat is not None:
        n=[0]
        def google_second(method,url,form,token):
            n[0]+=1
            calls.append(("metadata",method,url))
            return META if n[0]==1 else repeat
        google=google_second
    verify=verifier or (lambda **kw: calls.append(("folder",kw["config"].folder_id)))
    result=reader.read_pinned_google_source_once(
        file_id=file_id,expected_file_hmac=extra.get("hmac",h),
        expected_revision_hmac=extra.get("revision",r),
        access_token=extra.get("token","A"*40),
        granted_scope=scope,
        metadata_transport=google,media_transport=media,
        folder_verifier=verify,
    )
    return result,calls


def test_exact_authenticated_folder_identity_version_sha256_and_no_write():
    result,calls=run()
    assert result.sha256==sha256(RAW).hexdigest()
    assert result.data==RAW and result.byte_count==len(RAW)
    assert result.content_hmac==_index("source-sha256",result.sha256)
    assert result.file_hmac==_index("file",FILE_ID)
    assert result.extension==".csv"
    assert [x[0] for x in calls]==["folder","metadata","media","metadata"]
    assert all("/drive/v3/files/"+FILE_ID in x[2] for x in calls[1:])
    assert parse_qs(urlsplit(calls[2][2]).query)=={
        "alt":["media"],"supportsAllDrives":["false"],
    }
    assert "Fake" not in str(result.sha256)


def test_metadata_only_scope_is_not_sufficient_even_with_google_token():
    for scope in (
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/drive.file",
        reader._CONTENT_SCOPE+" https://www.googleapis.com/auth/drive",
        "",
    ):
        with pytest.raises(reader.PrivateSourceMediaBlocked):
            run(scope=scope)


@pytest.mark.parametrize("key",[
    "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
    "P3A_G3_RESTRICTED_SCOPE_REVIEWED",
    "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
])
def test_independent_release_gates_must_all_be_accepted(monkeypatch,key):
    monkeypatch.setenv(key,"0")
    with pytest.raises(reader.PrivateSourceMediaBlocked):
        run()


def test_real_mode_is_not_implicitly_enabled(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(reader.PrivateSourceMediaBlocked):
        run()


@pytest.mark.parametrize("delta",[
    {"parents":["SYNTHETIC_UNRELATED_FOLDER_2026"]},
    {"parents":[FOLDER,"SYNTHETIC_OTHER_FOLDER_2026"]},
    {"id":"SYNTHETIC_WRONG_SOURCE_ID_2026"},
    {"size":"9999"},
    {"mimeType":"application/pdf"},
    {"trashed":True},
    {"capabilities":{"canDownload":False}},
    {"md5Checksum":"1"*32},
    {"modifiedTime":"2026-11-20T10:00:00Z"},
    {"name":"renamed.csv"},
    {"webContentLink":"https://evil.invalid/leak"},
])
def test_revalidate_provider_metadata_against_signed_revision(delta):
    tampered={**META,**delta}
    with pytest.raises(reader.PrivateSourceMediaBlocked):
        run(metadata=tampered)


def test_mid_download_revision_race_mismatch_aborts_without_receipt():
    with pytest.raises(reader.PrivateSourceMediaBlocked):
        run(repeat={**META,"name":"changed.csv"})


@pytest.mark.parametrize("contents",[
    RAW+b"x",
    RAW[:-1],
    b"",
    b"x"*(4*1024*1024+1),
])
def test_refuse_tampered_or_truncated_media(contents):
    with pytest.raises(reader.PrivateSourceMediaBlocked):
        run(body=contents)


def test_wrong_blinded_inventory_or_untrusted_token_denied():
    for kwargs in ({"hmac":"a"*64},{"revision":"b"*64},
                   {"token":"oops"},{"file_id":"INVALID/../SOURCE"}):
        with pytest.raises(reader.PrivateSourceMediaBlocked):
            run(**kwargs)


def test_no_arbitrary_google_urls_or_post_methods():
    for method,url in [
        ("POST",reader._media_url(FILE_ID)),
        ("GET","https://evil.invalid/"+FILE_ID),
        ("GET","https://www.googleapis.com/drive/v3/files/"+FILE_ID+"?alt=media&x=1"),
    ]:
        with pytest.raises(reader.PrivateSourceMediaBlocked):
            reader._bounded_google_media(method,url,"A"*40)
