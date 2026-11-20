"""P5E trusted pinned historical source glue: fake Google/files/password only."""
import base64
from datetime import datetime,timezone
from types import SimpleNamespace

import pytest

from app.drive_inbox_planner import DriveFile,_index
from app.drive_google_oauth import DriveOAuthConfig
from app import private_historical_bank_report as b

OWNER="SYNTHETIC_P5E_PRIVATE_OWNER_2026"
FOLDER="SYNTHETIC_P5E_PRIVATE_SOURCE_2026"
FID="SYNTHETIC_P5E_BANK_SOURCE_ABCDEFGHIJK"
CLIENT="000000000000-fake.apps.googleusercontent.com"
NAME="SI-123456789 BAH eStatement(01012026).pdf"


@pytest.fixture
def scope(monkeypatch):
    for key in ("P5E_OWNER_HISTORICAL_REPORT_PILOT",
                "P5E_G3_ISOLATED_BANK_READER_REVIEWED",
 "P5C_BAHL_OS_JAIL_ENFORCED",
                "P5C_BAHL_OS_JAIL_ENFORCED",
            "P5C_BAHL_OS_JAIL_ENFORCED",
                "P5A_ORIGINAL_HASH_PILOT",
                "P3A_PRIVATE_SOURCE_MEDIA_ENABLED"):
        monkeypatch.setenv(key,"1")
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1W_OWNER_REF",OWNER)
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
                       base64.urlsafe_b64encode(b"I"*32).decode("ascii"))
    cfg=DriveOAuthConfig(
        client_id=CLIENT,folder_id=FOLDER,folder_hmac=_index("folder",FOLDER),
        redirect_uri="https://example.invalid/callback",
    )
    file=DriveFile(
        id=FID,name=NAME,mime_type="application/pdf",parent_ids=(FOLDER,),
        modified_time=datetime(2026,11,19,tzinfo=timezone.utc),
        size_bytes=300,md5_checksum=None,trashed=False)
    monkeypatch.setattr(b,"_guard_network",lambda:cfg)
    monkeypatch.setattr(b,"read_private_content_grant",lambda *a,**kw:"R"*60)
    monkeypatch.setattr(b,"refresh_google_content_token",lambda **kw:("A"*55,None))
    monkeypatch.setattr(b,"_inventory",lambda *a,**kw:(file,))
    calls=[]
    def fake_media(**kw):
        calls.append(("media",kw["file_id"],kw["expected_file_hmac"]))
        return SimpleNamespace(
            data=b"%PDF-1.7 FAKE BANK TEST",content_hmac=_index("source-sha256","c"*64))
    monkeypatch.setattr(b,"read_pinned_google_source_once",fake_media)
    def fake_worker(*,raw_pdf,password,approved_isolated_read):
        assert approved_isolated_read is True
        assert raw_pdf.startswith(b"%PDF-")
        if password is None:return {"status":"PASSWORD_REQUIRED"}
        if password!="FAKE_PRIVATE_PASSWORD":return {"status":"PASSWORD_REJECTED"}
        return {
            "status":"SOURCE_STATEMENT_RECONCILED",
            "contract":"personal_cfo_bahl_reconciled_statement_v1",
            "statement_start":"2025-07-01","statement_end":"2026-06-30",
            "opening_minor":10000,"closing_minor":37500,
            "gross_bank_debits_minor":2500,"gross_bank_credits_minor":30000,
            "transaction_count":2,
            "printed_closing_matches_transactions":True,
            "printed_gross_totals_match_transactions":True,
            "transaction_running_balances_match":True,
            "financial_values_verified":False,
            "income_minor":None,"expenses_minor":None,
            "current_available_balance_minor":None,
        }
    monkeypatch.setattr(b,"inspect_private_bahl_pdf",fake_worker)
    return calls,file


def analyze(scope,subject=None,password=None):
    _,file=scope
    from contextlib import nullcontext
    return b.analyze_pinned_bahl_historical_report(
        session_factory=lambda:nullcontext(None),
        owner_ref=OWNER,source_hmac=subject or _index("file",file.id),
        password=password,
    )


def test_transient_password_required_no_figures_until_entered(scope):
    result=analyze(scope)
    assert result["status"]=="PASSWORD_REQUIRED"
    assert result["income_minor"] is None
    assert result["current_available_balance_minor"] is None
    assert result["content_retained_on_server"] is False
    assert result["original_source_modified"] is False
    wrong=analyze(scope,password="INCORRECT_PASSWORD")
    assert wrong["status"]=="PASSWORD_REJECTED"
    real=analyze(scope,password="FAKE_PRIVATE_PASSWORD")
    assert real["historical_opening_minor"]==10000
    assert real["historical_closing_minor"]==37500
    assert real["gross_bank_credits_minor"]==30000
    assert real["gross_bank_debits_minor"]==2500
    assert real["transaction_count"]==2
    assert real["source_sha256_verified"] is True
    assert real["historical_only"] is True
    assert real["transfers_excluded"] is False
    assert real["ledger_mutated"] is False
    assert real["income_minor"] is None
    assert real["expenses_minor"] is None
    assert real["current_available_balance_minor"] is None
    assert "FAKE_PRIVATE_PASSWORD" not in str(real)


def test_no_arbitrary_file_identity_and_account_wide_search(scope,monkeypatch):
    with pytest.raises(b.PrivateHistoricalBankReportBlocked):
        analyze(scope,subject="f"*64,password="FAKE_PRIVATE_PASSWORD")
    calls,file=scope
    altered=file.model_copy(update={"name":"SI-123456789 OTHER BANK.pdf"})
    monkeypatch.setattr(b,"_inventory",lambda *a,**kw:(altered,))
    with pytest.raises(b.PrivateHistoricalBankReportBlocked):
        analyze(scope,password="FAKE_PRIVATE_PASSWORD")
    assert len(calls)==0


@pytest.mark.parametrize("flag",[
 "P5E_OWNER_HISTORICAL_REPORT_PILOT",
 "P5E_G3_ISOLATED_BANK_READER_REVIEWED",
 "P5A_ORIGINAL_HASH_PILOT",
 "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
])
def test_release_flags_required(scope,monkeypatch,flag):
    monkeypatch.setenv(flag,"0")
    with pytest.raises(b.PrivateHistoricalBankReportBlocked):
        analyze(scope)


def test_wrong_owner_or_invalid_password_rejected(scope,monkeypatch):
    from contextlib import nullcontext
    with pytest.raises(b.PrivateHistoricalBankReportBlocked):
        b.analyze_pinned_bahl_historical_report(
            session_factory=lambda:nullcontext(None),
            owner_ref="SYNTHETIC_WRONG_OWNER_2026",
            source_hmac=_index("file",FID),
        )
    with pytest.raises(b.PrivateHistoricalBankReportBlocked):
        analyze(scope,password="bad\npassword")



def test_separately_reviewed_ephemeral_vm_can_replace_failed_standard_os_jail(scope,monkeypatch):
    monkeypatch.setenv("P5C_BAHL_OS_JAIL_ENFORCED","0")
    monkeypatch.setenv("P5H_REMOTE_VM_WORKER_ACTIVE","1")
    monkeypatch.setenv("P5H_REMOTE_VM_G3_REVIEWED","1")
    assert analyze(scope)["status"]=="PASSWORD_REQUIRED"
    monkeypatch.setenv("P5H_REMOTE_VM_G3_REVIEWED","0")
    with pytest.raises(b.PrivateHistoricalBankReportBlocked):
        analyze(scope)
