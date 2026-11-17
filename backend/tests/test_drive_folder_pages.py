"""Google Drive v3 inbox pagination is complete, bounded and synthetic."""
import base64
import pytest

from app.drive_folder_pages import (
    DriveInboxBlocked, collect_synthetic_drive_folder,
    plan_synthetic_folder_from_pages, PAGE_SIZE, FIELDS,
)

FOLDER="SYNTHETIC_PERSONAL_CFO_DROPBOX_2026"


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("DRIVE_FAKE_TRANSPORT_ONLY","1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",base64.urlsafe_b64encode(b"D"*32).decode())


def file(i):
    return {
        "id":f"SIMULATEDFILEBANK{i:08d}", "name":f"bank statement {i}.pdf",
        "mimeType":"application/pdf","parents":[FOLDER],
        "size":"1111","modifiedTime":"2026-11-17T12:00:00+05:00",
        "md5Checksum":"1"*32,"trashed":False,
    }


def test_all_pages_consumed_before_commit_or_index():
    calls=[]
    def fake(params):
        calls.append(params)
        if "pageToken" not in params:
            return {"files":[file(i) for i in range(PAGE_SIZE)],
                    "nextPageToken":"TOKEN_PAGE2"}
        return {"files":[file(PAGE_SIZE)],"incompleteSearch":False}
    received=collect_synthetic_drive_folder(folder_id=FOLDER,list_page=fake)
    assert len(received)==PAGE_SIZE+1
    assert calls[0]["q"]==f"'{FOLDER}' in parents and trashed = false"
    assert calls[0]["fields"]==FIELDS
    assert calls[1]["pageToken"]=="TOKEN_PAGE2"
    receipt=plan_synthetic_folder_from_pages(folder_id=FOLDER,list_page=fake)
    assert receipt["count"]==PAGE_SIZE+1
    assert receipt["ledger_mutated"] is False
    assert receipt["background_monitor_started"] is False
    assert receipt["drive_oauth_connected"] is False


def test_incomplete_search_or_repeated_page_is_rejected_without_partial_plan():
    with pytest.raises(DriveInboxBlocked,match="Truncated"):
        collect_synthetic_drive_folder(folder_id=FOLDER,list_page=lambda params:{
            "files":[file(1)],"incompleteSearch":True,
        })
    with pytest.raises(DriveInboxBlocked,match="pagination loop"):
        collect_synthetic_drive_folder(folder_id=FOLDER,list_page=lambda params:{
            "files":[],"nextPageToken":"REPEAT",
        })
    with pytest.raises(DriveInboxBlocked,match="Incomplete Drive pagination"):
        collect_synthetic_drive_folder(folder_id=FOLDER,max_pages=1,list_page=lambda params:{
            "files":[file(1)],"nextPageToken":"PAGE2",
        })


def test_unexpected_provider_field_and_outside_folder_fail_closed():
    with pytest.raises(DriveInboxBlocked,match="Unexpected provider"):
        collect_synthetic_drive_folder(folder_id=FOLDER,list_page=lambda params:{
            "files":[{**file(1),"webContentLink":"https://example.com/private"}],
        })
    with pytest.raises(DriveInboxBlocked,match="outside-folder"):
        collect_synthetic_drive_folder(folder_id=FOLDER,list_page=lambda params:{
            "files":[{**file(1),"parents":["SOME_OTHER_FOLDER_NOT_ALLOWED"]}],
        })


def test_unexpected_file_count_refuses_processing():
    with pytest.raises(DriveInboxBlocked,match="Truncated"):
        collect_synthetic_drive_folder(folder_id=FOLDER,list_page=lambda params:{
            "files":[file(i) for i in range(PAGE_SIZE+1)],
        })


def test_real_mode_or_missing_fake_transport_disallowed(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(DriveInboxBlocked,match="synthetic-only"):
        collect_synthetic_drive_folder(folder_id=FOLDER,list_page=lambda params:{"files":[]})
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.delenv("DRIVE_FAKE_TRANSPORT_ONLY")
    with pytest.raises(DriveInboxBlocked):
        collect_synthetic_drive_folder(folder_id=FOLDER,list_page=lambda params:{"files":[]})


def test_no_network_credential_or_original_document_required():
    empty=collect_synthetic_drive_folder(folder_id=FOLDER,list_page=lambda p:{"files":[]})
    assert empty==()
