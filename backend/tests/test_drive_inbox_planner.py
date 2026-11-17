"""Drive one-folder acceptance: synthetic metadata only, fail-closed owner facts."""
import base64
from datetime import datetime,timezone
import pytest

from app.drive_inbox_planner import (
    DriveFile, DriveInboxBlocked, plan_synthetic_drive_inbox,
)

FOLDER="SYNTHETIC_PERSONAL_CFO_DROPBOX_2026"
KEY=base64.urlsafe_b64encode(b"D"*32).decode("ascii")


@pytest.fixture(autouse=True)
def private_fake_index(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",KEY)


def item(identifier,name,mime,size=1000,md5=None,parent=FOLDER,trashed=False,modified="2026-11-17T12:00:00+05:00"):
    return DriveFile.model_validate({
        "id":identifier,"name":name,"mime_type":mime,"parent_ids":[parent],
        "size_bytes":size,"modified_time":modified,
        "md5_checksum":md5,"trashed":trashed,
    })


def plan(items,**params):
    return plan_synthetic_drive_inbox(
        folder_id=FOLDER,files=tuple(items),snapshot_complete=True,
        approved_synthetic_fixture=True,**params,
    )


def test_mixed_unorganized_documents_virtual_organize_only():
    data=[
        item("SIMULATEDFILEBANK0001","Monthly_bank_statement.pdf","application/pdf"),
        item("SIMULATEDFILETAX0002","IRIS income tax return.pdf","application/pdf"),
        item("SIMULATEDFILEWEALTH03","FBR wealth 2025.pdf","application/pdf"),
        item("SIMULATEDFILEEXCEL04","accountant working paper.xlsx",
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        item("SIMULATEDFILELOAN005","personal loan.pdf","application/pdf"),
        item("SIMULATEDFILEPHOTO06","WhatsApp screenshot.png","image/png"),
        item("SIMULATEDFILEBAD0007","statement.xlsm","application/vnd.ms-excel.sheet.macroEnabled.12"),
        item("SIMULATEDFILEUNC0008","random.pdf","application/pdf"),
    ]
    report=plan(data)
    assert report["count"]==8 and report["new_count"]==8
    assert report["virtual_collection_counts"]["bank_statements"]==1
    assert report["virtual_collection_counts"]["tax_returns"]==1
    assert report["virtual_collection_counts"]["wealth_statements"]==1
    assert report["virtual_collection_counts"]["accountant_working"]==1
    assert report["virtual_collection_counts"]["loans_and_cash"]==1
    assert report["virtual_collection_counts"]["screenshots_and_correspondence"]==1
    assert report["quarantined_count"]==1
    assert all(row["original_kept_in_inbox"] for row in report["indexed_rows"])
    assert all(row["source_financial_claims_verified"] is False for row in report["indexed_rows"])
    assert report["owner_tax_or_fbr_filing_verified"] is False
    assert report["original_content_downloaded"] is False
    assert report["background_monitor_started"] is False
    assert "Monthly_bank_statement.pdf" not in str(report)
    assert "SIMULATEDFILEBANK0001" not in str(report)


def test_duplicate_candidates_never_silently_removed():
    same="a"*32
    data=[
        item("SIMULATEDFILEBANK0001","bank statement.pdf","application/pdf",md5=same),
        item("SIMULATEDFILEBANK0002","copy bank statement.pdf","application/pdf",md5=same),
    ]
    report=plan(data)
    assert report["duplicate_candidates_needing_review"]==1
    assert report["count"]==2
    assert report["indexed_rows"][0]["possible_duplicate_unverified"] is False
    assert report["indexed_rows"][1]["possible_duplicate_unverified"] is True
    assert report["originals_never_moved_or_deleted"]


def test_idempotent_metadata_revisions_and_change_without_rewrite():
    f=item("SIMULATEDFILEBANK0001","bank statement.pdf","application/pdf")
    first=plan([f])
    row=first["indexed_rows"][0]
    previous={row["file_hmac"]:row["revision_hmac"]}
    second=plan([f],known_versions=previous)
    assert second["unchanged_count"]==1 and second["changed_count"]==0
    changed=item("SIMULATEDFILEBANK0001","bank statement.pdf","application/pdf",
                 modified="2026-11-17T12:05:00+05:00")
    third=plan([changed],known_versions=previous)
    assert third["changed_count"]==1 and third["new_count"]==0
    assert third["indexed_rows"][0]["file_hmac"]==row["file_hmac"]
    assert third["indexed_rows"][0]["revision_hmac"]!=row["revision_hmac"]
    assert third["ledger_mutated"] is False


def test_untrusted_outside_folder_and_incomplete_snapshot_refused():
    stranger=item("SIMULATEDFILEBANK0001","statement.pdf","application/pdf",
                  parent="OTHER_DRIVE_FOLDER_001")
    with pytest.raises(DriveInboxBlocked,match="outside approved"):
        plan([stranger])
    with pytest.raises(DriveInboxBlocked):
        plan_synthetic_drive_inbox(
            folder_id=FOLDER,files=(),snapshot_complete=False,approved_synthetic_fixture=True)
    with pytest.raises(DriveInboxBlocked):
        plan([item("SIMULATEDFILEBANK0001","bank statement.pdf","application/pdf")]*2)


@pytest.mark.parametrize("name,mime",[
    ("suspect.zip","application/zip"),
    ("instructions.exe","application/octet-stream"),
    ("sheet.xlsm","application/vnd.ms-excel.sheet.macroEnabled.12"),
    ("bank_statement.pdf","text/html"),
    ("tax.xml","application/xml"),
])
def test_unsafe_formats_are_quarantined_without_execution(name,mime):
    report=plan([item("SIMULATEDFILEBANK0001",name,mime)])
    assert report["quarantined_count"]==1
    assert report["indexed_rows"][0]["source_content_processed"] is False


def test_name_never_certifies_tax_filing_or_bank_expense():
    report=plan([item("SIMULATEDFILETAX0002","FBR FINAL FILED TAX RETURN.pdf","application/pdf")])
    assert report["virtual_collection_counts"]["tax_returns"]==1
    assert report["owner_tax_or_fbr_filing_verified"] is False
    assert report["indexed_rows"][0]["review_status"]=="awaiting_private_document_verification"


def test_unauthorized_real_mode_fails_closed(monkeypatch):
    fake=item("SIMULATEDFILEBANK0001","statement.pdf","application/pdf")
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(DriveInboxBlocked):
        plan([fake])
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.delenv("DRIVE_INDEX_HMAC_KEY")
    with pytest.raises(DriveInboxBlocked):
        plan([fake])


def test_no_new_real_drive_or_financial_api_exposed():
    from app.preview_api import create_preview_app
    routes={r.path for r in create_preview_app().routes}
    assert "/api/drive/connect" not in routes
    assert "/api/drive/ingest" not in routes
    assert "/api/documents/real" not in routes
    assert "/api/finance/import" not in routes
