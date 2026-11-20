"""Synthetic-only P6 bank CSV source reconciliation tests.

No real owner account, amount, filename or private source enters public CI.
"""
from dataclasses import dataclass
from types import SimpleNamespace
import pytest

from app.private_bank_csv_reconciler import (
    PrivateBankCsvBlocked, reconcile_private_bank_csv,
)
from app import private_owner_bank_csv_report as report


def fixture_csv():
    return (
        "\ufeff00000000000000,\n"
        "Opening Balance,PKR      100.00\n"
        "Closing Balance,PKR      125.00\n"
        "Currency,Pakistan Rupee(PKR)\n"
        "Booking Date,Value Date,Doc No,Description,Debit,Credit,Available Balance\n"
        "01 Jan 2026,01 Jan 2026,FICTA,Fictional owner transfer,,50.00,150.00\n"
        "02 Jan 2026,02 Jan 2026,FICTB,Fictional bank charge,20.00,,130.00\n"
        "03 Jan 2026,03 Jan 2026,FICTC,Payment of Profit,,0.50,130.50\n"
        "03 Jan 2026,03 Jan 2026,FICTD,Withholding Tax Debit Example,0.10,,130.40\n"
        "04 Jan 2026,04 Jan 2026,FICTE,Fictional transfer,5.40,,125.00\n"
    ).encode("utf-8")


def test_actual_style_csv_running_balance_and_monthly_aggregates_are_exact():
    proof = reconcile_private_bank_csv(fixture_csv())
    assert proof["contract"] == "personal_cfo_p6_reconciled_bank_csv_v1"
    assert proof["opening_minor"] == 10000
    assert proof["closing_minor"] == 12500
    assert proof["gross_bank_credits_minor"] == 5050
    assert proof["gross_bank_debits_minor"] == 2550
    assert proof["transaction_count"] == 5
    assert proof["statement_end"] == "2026-01-04"
    assert proof["all_running_balances_reconciled"] is True
    assert proof["printed_closing_reconciled"] is True
    assert proof["months"][0]["bank_labelled_profit_minor"] == 50
    assert proof["months"][0]["bank_labelled_profit_tax_minor"] == 10
    assert proof["current_available_balance_minor"] is None
    assert proof["personal_income_minor"] is None
    assert proof["personal_expenses_minor"] is None
    assert proof["investment_current_market_value_minor"] is None
    assert "Fictional" not in str(proof)
    assert "00000000000000" not in str(proof)


@pytest.mark.parametrize("change", [
    lambda x: x.replace(b"125.00\nCurrency", b"125.01\nCurrency"),
    lambda x: x.replace(b"50.00,150.00", b"51.00,150.00"),
    lambda x: x.replace(b",20.00,,130.00", b",20.00,,131.00"),
    lambda x: x.replace(b"01 Jan 2026,01 Jan 2026", b"30 Jan 2026,30 Jan 2026"),
    lambda x: x.replace(b"Payment of Profit,,0.50", b"Payment of Profit,0.50,0.50"),
    lambda x: x.replace(b"Available Balance", b"available_balance"),
    lambda x: x + b"Malicious trailer,1,2,3,4,5,6\n",
    lambda x: b"bad-byte-\xff" + x,
    lambda x: x[:10] + b"\0" + x[10:],
])
def test_rejects_untrusted_or_inconsistent_bank_csv(change):
    with pytest.raises(PrivateBankCsvBlocked):
        reconcile_private_bank_csv(change(fixture_csv()))


def test_rejects_non_bytes_and_overlarge_bombs():
    for raw in ("not bytes", b"", b"\x00csv", b"c"*(4*1024*1024+1)):
        with pytest.raises(PrivateBankCsvBlocked):
            reconcile_private_bank_csv(raw)


def test_real_original_reader_default_off(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1W_OWNER_REF","owner-fake-123456789012345")
    for key in (
        "P6A_OWNER_BANK_CSV_RUNTIME",
        "P6A_G3_BANK_CSV_RECONCILIATION_ACCEPTED",
        "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
        "P3A_G3_RESTRICTED_SCOPE_REVIEWED",
        "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
    ):
        monkeypatch.delenv(key,raising=False)
    with pytest.raises(report.PrivateBankCsvReportBlocked):
        report.get_private_bank_csv_overview(
            session_factory=lambda:None,
            owner_ref="owner-fake-123456789012345",
        )


def test_pinned_approved_folder_report_reconciles_only_csv(monkeypatch):
    monkeypatch.setenv("P7_OWNER_TRANSACTION_ROWS_ENABLED","1")
    owner="owner-fake-123456789012345"
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1W_OWNER_REF",owner)
    for key in (
        "P6A_OWNER_BANK_CSV_RUNTIME",
        "P6A_G3_BANK_CSV_RECONCILIATION_ACCEPTED",
        "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
        "P3A_G3_RESTRICTED_SCOPE_REVIEWED",
        "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
    ):
        monkeypatch.setenv(key,"1")
    config=SimpleNamespace(folder_id="approved-fake-folder",client_id="test-client")
    monkeypatch.setattr(report,"_guard_network",lambda:config)
    monkeypatch.setattr(report,"read_private_content_grant",lambda *a,**k:"fake-token")
    monkeypatch.setattr(report,"refresh_google_content_token",lambda **k:("fake-access",None))
    @dataclass
    class File:
        id:str
        name:str
        mime_type:str
        size_bytes:int
        parent_ids:tuple
        trashed:bool=False
    sources=[
        File("owned-csv-1","fixture.csv","text/csv",len(fixture_csv()),(config.folder_id,)),
        File("owned-pdf-2","original.pdf","application/pdf",2048,(config.folder_id,)),
    ]
    monkeypatch.setattr(report,"_inventory",lambda *a,**k:sources)
    monkeypatch.setattr(report,"_index",lambda purpose,value:"a"*64)
    monkeypatch.setattr(report,"_version",lambda item:"b"*64)
    calls=[]
    def media(**kw):
        calls.append(kw)
        return SimpleNamespace(
            data=fixture_csv(),extension=".csv",
            sha256=__import__("hashlib").sha256(fixture_csv()).hexdigest(),
            content_hmac="c"*64)
    monkeypatch.setattr(report,"read_pinned_google_source_once",media)
    class Session:
        def __enter__(self):return self
        def __exit__(self,*_):return False
    result=report.get_private_bank_csv_overview(
        session_factory=Session,owner_ref=owner,transport=lambda *a,**k:None,
        media_transport=lambda *a,**k:None)
    assert result["source_inventory_complete"] is True
    assert result["csv_sources_found"]==1
    assert len(result["reports"])==1
    assert result["reports"][0]["closing_minor"]==12500
    owner_rows=result["reports"][0]["transactions"]
    assert owner_rows["contract"]=="personal_cfo_p7_reconciled_bank_csv_rows_v1"
    assert owner_rows["transaction_count"]==5
    assert owner_rows["rows"][0]["review_required"] is True
    assert owner_rows["rows"][2]["category"]=="BANK_PROFIT"
    assert owner_rows["rows"][4]["classified_as_personal_expense"] is False
    assert result["reports"][0]["source_sha256_verified"] is True
    assert result["personal_income_minor"] is None
    assert len(calls)==1
    assert calls[0]["file_id"]=="owned-csv-1"
    assert result["originals_modified"] is False


def test_unsupported_csv_quarantined_without_false_money(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1W_OWNER_REF","owner-fake-123456789012345")
    for key in (
        "P6A_OWNER_BANK_CSV_RUNTIME","P6A_G3_BANK_CSV_RECONCILIATION_ACCEPTED",

        "P3A_PRIVATE_SOURCE_MEDIA_ENABLED","P3A_G3_RESTRICTED_SCOPE_REVIEWED",
        "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
    ):
        monkeypatch.setenv(key,"1")
    cfg=SimpleNamespace(folder_id="private-allowed",client_id="fake-client")
    monkeypatch.setattr(report,"_guard_network",lambda:cfg)
    monkeypatch.setattr(report,"read_private_content_grant",lambda *a,**k:"fake-token")
    monkeypatch.setattr(report,"refresh_google_content_token",lambda **k:("fake-access",None))
    file=SimpleNamespace(id="csv1",name="unknown.csv",mime_type="text/csv",size_bytes=500,
            parent_ids=(cfg.folder_id,),trashed=False)
    monkeypatch.setattr(report,"_inventory",lambda *a,**k:[file])
    monkeypatch.setattr(report,"_index",lambda *a:"a"*64)
    monkeypatch.setattr(report,"_version",lambda *a:"b"*64)
    monkeypatch.setattr(report,"read_pinned_google_source_once",lambda **kw:SimpleNamespace(
        data=b"invalid-source",extension=".csv",content_hmac="c"*64))
    class S:
        def __enter__(self):return self
        def __exit__(self,*_):return False
    result=report.get_private_bank_csv_overview(
        session_factory=S,owner_ref="owner-fake-123456789012345",
        transport=lambda *a,**k:None,media_transport=lambda *a,**k:None)
    assert result["csv_sources_found"]==1
    assert result["csv_sources_requiring_review"]==1
    assert result["reports"]==[]
