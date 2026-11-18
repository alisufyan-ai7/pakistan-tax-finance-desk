"""P2B fictional-only revision planning; no Google requests or owner data."""
from datetime import datetime, timezone, timedelta
import base64

import pytest

from app.drive_inbox_planner import DriveFile, _index
from app.private_drive_revision_manifest import (
    PrivateDriveRevisionBlocked, plan_complete_owner_folder_revision,
)

FOLDER = "SYNTHETIC_P2B_PRIVATE_FOLDER_2026"
FILE_A = "SYNTHETIC_P2B_FILE_ABCDEFGHIJKLMNOP"
FILE_B = "SYNTHETIC_P2B_FILE_ZYXWVUTSRQPONMLK"
FILE_C = "SYNTHETIC_P2B_FILE_1234567890123456"
STAMP = datetime(2026, 11, 18, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def scope(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY", base64.urlsafe_b64encode(
        b"D" * 32
    ).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))


def source(fid=FILE_A, name="first.pdf", md5="a"*32, date=STAMP):
    return DriveFile(id=fid, name=name, mime_type="application/pdf",
                     parent_ids=(FOLDER,), modified_time=date,
                     size_bytes=1234, md5_checksum=md5, trashed=False)


def run(files, previous=None, **flags):
    return plan_complete_owner_folder_revision(
        folder_id=FOLDER, files=tuple(files), previous=previous,
        snapshot_complete=flags.get("complete", True),
        approved_synthetic_fixture=flags.get("approved", True),
    )


def test_new_replay_rename_version_and_missing_are_distinct():
    first=run([source(), source(FILE_B, "second.pdf")])
    assert first["stage_counts"]["new"] == 2
    assert len(first["next_manifest"]) == 2
    assert first["content_sha256_computed"] is False
    assert first["original_files_mutated"] is False
    assert first["durable_index_written"] is False
    assert first["background_sync_running"] is False
    assert first["financial_data_authorized"] is False
    assert all(len(k)==64 and k not in (FILE_A,FILE_B) for k in first["next_manifest"])
    assert FILE_A not in str(first) and FILE_B not in str(first)
    assert "first.pdf" not in str(first) and "second.pdf" not in str(first)
    second=run([source(FILE_B,"second.pdf"),source()], first["next_manifest"])
    assert second["stage_counts"]["unchanged"] == 2
    assert second["next_manifest"] == first["next_manifest"]
    renamed=run([source(name="renamed.pdf"),source(FILE_B,"second.pdf")],
                first["next_manifest"])
    assert renamed["stage_counts"]["name_changed_needs_review"] == 1
    # ModifiedTime alone is a revision hint, NOT content SHA.
    altered=run([source(date=STAMP+timedelta(days=1)),
                 source(FILE_B,"second.pdf")], first["next_manifest"])
    assert altered["stage_counts"]["metadata_changed_needs_review"] == 1
    changed=run([source(md5="b"*32),source(FILE_B,"second.pdf")],
                first["next_manifest"])
    assert changed["stage_counts"]["content_hint_changed_needs_sha256"] == 1
    missing=run([source()], first["next_manifest"])
    assert missing["stage_counts"]["missing_in_source"] == 1
    assert len(missing["next_manifest"]) == 2
    assert missing["next_manifest"][_index("file",FILE_B)]["present"] is False
    # A file reappearing is reviewed as NEW, not automatically restored ledger evidence.
    back=run([source(),source(FILE_B,"second.pdf")],missing["next_manifest"])
    assert back["stage_counts"]["new"] == 1


@pytest.mark.parametrize("reason",[
    "incomplete","unapproved","wrong_folder","duplicate_id",
    "outside_parent","multi_parent","trashed","bad_prior","too_many",
    "real_mode",
])
def test_fail_closed_no_partial_changes(monkeypatch,reason):
    files=[source()]
    previous=None
    kw={}
    if reason=="incomplete":kw["complete"]=False
    elif reason=="unapproved":kw["approved"]=False
    elif reason=="wrong_folder":monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC","f"*64)
    elif reason=="duplicate_id":files.append(source())
    elif reason=="outside_parent":
        files=[source().model_copy(update={"parent_ids":("SYNTHETIC_UNRELATED_FOLDER_2026",)})]
    elif reason=="multi_parent":
        files=[source().model_copy(update={"parent_ids":(FOLDER,"SYNTHETIC_OTHER_FOLDER_2026")})]
    elif reason=="trashed":
        files=[source().model_copy(update={"trashed":True})]
    elif reason=="bad_prior":previous={"user-visible-raw-id":{"revision_hmac":"f"*64}}
    elif reason=="too_many":files=[source(fid=f"SYNTHETIC_P2B_FILE_{i:012d}") for i in range(1001)]
    elif reason=="real_mode":monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(PrivateDriveRevisionBlocked):
        run(files,previous,**kw)


def test_md5_is_weak_hint_not_content_hash():
    old=run([source()])
    new=run([source(name="same-binary-new-name.pdf")],old["next_manifest"])
    assert new["stage_counts"]["name_changed_needs_review"] == 1
    assert not new["provider_md5_is_content_proof"]
    assert not new["content_sha256_computed"]
    assert _index("file",FILE_A) in new["next_manifest"]
    assert not any("sha256" in value for value in new["next_manifest"][_index("file",FILE_A)])
