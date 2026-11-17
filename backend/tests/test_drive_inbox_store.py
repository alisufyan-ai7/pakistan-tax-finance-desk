"""P1 one-folder encrypted synthetic inbox, SQL atomicity and review queue."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa: F401
from app.drive_inbox_planner import DriveFile, DriveInboxBlocked, _index
from app.drive_inbox_store import (
    apply_synthetic_drive_snapshot, read_synthetic_drive_review_queue,
)

FOLDER = "SYNTHETIC_PERSONAL_CFO_ONLY_FOLDER_2026"
OTHER_FOLDER = "SYNTHETIC_UNRELATED_FOLDER_2026"


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("DRIVE_FAKE_TRANSPORT_ONLY", "1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
                       base64.urlsafe_b64encode(b"D" * 32).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    db = create_engine(f"sqlite:///{tmp_path / 'only-fake-drive.db'}",
                       connect_args={"timeout": 8})
    Base.metadata.create_all(db)
    yield db
    db.dispose()


def fake(idx=1, name="fictional bank statement.pdf",
         modified="2026-11-17T12:00:00+05:00", parent=FOLDER,
         md5=None, mime="application/pdf", size=2222):
    return DriveFile.model_validate({
        "id": f"SYNTHETIC_OWNER_FILE_{idx:05d}",
        "name": name, "mime_type": mime,
        "parent_ids": [parent], "size_bytes": size,
        "modified_time": modified, "md5_checksum": md5,
    })


def apply(db, files, **kwargs):
    return apply_synthetic_drive_snapshot(
        db, folder_id=FOLDER, files=tuple(files),
        snapshot_complete=True, approved_synthetic_fixture=True, **kwargs,
    )


def test_first_scan_idempotent_restart_and_private_review_queue(engine):
    data = [
        fake(1, "fictional bank statement.pdf"),
        fake(2, "FBR FINAL filed income return.pdf"),
        fake(3, "WhatsApp chat.png", mime="image/png"),
        fake(4, "unexpected script.xlsm",
             mime="application/vnd.ms-excel.sheet.macroEnabled.12"),
    ]
    with Session(engine) as db:
        report = apply(db, data)
        assert report["scan_number"] == 1
        assert report["visible_sources"] == 4
        assert report["quarantined_sources"] == 1
        assert not report["ledger_mutated"] and not report["real_data_authorized"]
    with Session(engine) as db:
        again = apply(db, data)
        assert again["idempotent_replay"] is True
        assert again["scan_number"] == 1
        review = read_synthetic_drive_review_queue(db, folder_id=FOLDER)
        assert review["integrity_checked"]
        assert review["tracked_sources"] == 4
        assert review["queue"][0]["review_status"].startswith("quarantined")
        assert any(x["virtual_collection"] == "tax_returns" for x in review["queue"])
        assert all(len(x["file_hmac"]) == 64 for x in review["queue"])
        assert all("filename" not in x and "source_ref" not in x for x in review["queue"])
        assert not review["real_financial_claims_verified"]
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT folder_hmac,file_hmac,revision_hmac,payload_json FROM drive_inbox_items"
        )).all()
        assert len(rows) == 4
        assert all(record[3].startswith("TFLE1:") for record in rows)
        assert all(len(record[0]) == len(record[1]) == len(record[2]) == 64
                   for record in rows)
        for sensitive in ("FBR FINAL", "WhatsApp", "fictional bank", FOLDER):
            assert all(sensitive not in str(row) for row in rows)
        assert conn.execute(text(
            "SELECT COUNT(*) FROM transactions"
        )).scalar_one() == 0


def test_changed_missing_and_reappeared_source_is_never_silently_deleted(engine):
    first = [fake(1), fake(2, "cash receipt.pdf")]
    with Session(engine) as db:
        assert apply(db, first)["tracked_sources"] == 2
        changed = fake(1, modified="2026-11-17T12:05:00+05:00")
        stage2 = apply(db, [changed])
        assert stage2["scan_number"] == 2
        assert stage2["visible_sources"] == 1
        assert stage2["unavailable_sources_need_review"] == 1
        assert stage2["changed_sources_need_review"] == 1
        queue = read_synthetic_drive_review_queue(db, folder_id=FOLDER)
        assert any(not x["visible"] and
                   x["review_status"] == "source_inaccessible_or_removed"
                   for x in queue["queue"])
        assert len(queue["queue"]) == 2
        returned = apply(db, first)
        assert returned["scan_number"] == 3
        assert returned["visible_sources"] == 2
        assert returned["unavailable_sources_need_review"] == 0
        assert returned["changed_sources_need_review"] == 2
        assert all(x["stage"] != "source_deleted_by_app" for x in
                   read_synthetic_drive_review_queue(db, folder_id=FOLDER)["queue"])
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT COUNT(*) FROM drive_inbox_items"
        )).scalar_one() == 2


def test_same_checksum_is_only_duplicate_candidate_never_deleted(engine):
    with Session(engine) as db:
        report = apply(db, [
            fake(1, md5="a" * 32),
            fake(2, name="copy bank statement.pdf", md5="a" * 32),
        ])
        assert report["possible_duplicates_need_review"] == 1
        assert report["tracked_sources"] == 2
        assert not report["originals_moved_or_deleted"]
        queue = read_synthetic_drive_review_queue(db, folder_id=FOLDER)
        assert sum(x["possible_duplicate_unverified"] for x in queue["queue"]) == 1


def test_partial_or_outside_folder_fails_before_any_index_write(engine):
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            apply_synthetic_drive_snapshot(
                db, folder_id=FOLDER, files=(fake(),),
                snapshot_complete=False, approved_synthetic_fixture=True,
            )
        with pytest.raises(DriveInboxBlocked, match="outside approved"):
            apply(db, [fake(1, parent=OTHER_FOLDER)])
        with pytest.raises(DriveInboxBlocked):
            apply(db, [fake(1), fake(1)])
        assert db.query(models.DriveInboxItem).count() == 0


def test_wrong_folder_and_missing_scoped_permission_fail_closed(engine, monkeypatch):
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            apply_synthetic_drive_snapshot(
                db, folder_id=OTHER_FOLDER,
                files=(fake(1, parent=OTHER_FOLDER),), snapshot_complete=True,
                approved_synthetic_fixture=True,
            )
    monkeypatch.delenv("DRIVE_ALLOWED_FOLDER_HMAC")
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            apply(db, [fake(1)])


def test_tampered_ciphertext_and_missing_row_fail_closed(engine):
    with Session(engine) as db:
        apply(db, [fake(1), fake(2)])
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE drive_inbox_items SET payload_json='this-is-not-a-valid-sealed-field' "
            "WHERE file_hmac=(SELECT MIN(file_hmac) FROM drive_inbox_items)"
        ))
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            read_synthetic_drive_review_queue(db, folder_id=FOLDER)


def test_deleted_inventory_row_detected_by_keyed_checkpoint(engine):
    with Session(engine) as db:
        apply(db, [fake(1), fake(2)])
    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM drive_inbox_items WHERE "
            "file_hmac=(SELECT MIN(file_hmac) FROM drive_inbox_items)"
        ))
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked, match="altered"):
            apply(db, [fake(1), fake(2)])


def test_different_source_version_is_not_autopromoted_to_verified(engine):
    with Session(engine) as db:
        apply(db, [fake(1)])
        result = apply(db, [fake(1, modified="2026-11-17T12:20:00+05:00")])
        assert result["changed_sources_need_review"] == 1
        assert result["real_financial_claims_verified"] is False


def test_real_financial_ingestion_and_public_drive_api_remain_disabled(engine, monkeypatch):
    from app.preview_api import create_preview_app
    routes = {r.path for r in create_preview_app().routes}
    assert "/api/drive/ingest" not in routes
    assert "/api/drive/sync" not in routes
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            apply(db, [fake(1)])
        with pytest.raises(DriveInboxBlocked):
            read_synthetic_drive_review_queue(db, folder_id=FOLDER)


def _worker(engine, barrier):
    barrier.wait(timeout=5)
    with Session(engine) as db:
        return apply(db, [fake(1), fake(2)])


def test_two_simultaneous_synthetic_scans_are_serialized(engine):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(_worker, engine, barrier)
        b = pool.submit(_worker, engine, barrier)
        r1 = a.result(timeout=15)
        r2 = b.result(timeout=15)
    assert r1["tracked_sources"] == r2["tracked_sources"] == 2
    assert sorted([r1["idempotent_replay"], r2["idempotent_replay"]]) == [False, True]
    with Session(engine) as db:
        assert read_synthetic_drive_review_queue(
            db, folder_id=FOLDER
        )["scan_number"] == 1
