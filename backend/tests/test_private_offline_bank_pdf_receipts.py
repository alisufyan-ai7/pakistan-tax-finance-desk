"""Fictional-only, no VM/PDF parser, source SHA-bound private receipts."""
import json
from types import SimpleNamespace
from datetime import datetime, timezone
import pytest

from app import private_offline_bank_pdf_receipts as p

NAME="SI-111222333 BAH eStatement(26092026).pdf"
SHA="d"*64
def receipt():
    return {
        "name":NAME,"sha256":SHA,
        "period_start":"2025-07-01","period_end":"2026-06-30",
        "opening_minor":10000,"closing_minor":13000,
        "debits_minor":2000,"credits_minor":5000,
        "transaction_count":2,"page_count":1,
    }

def approved(monkeypatch, record=None):
    monkeypatch.setenv("P6D_OWNER_OFFLINE_PDF_RECEIPTS_ENABLED","1")
    monkeypatch.setenv("P6D_PRIVATE_BAHL_OFFLINE_RECEIPTS_JSON",json.dumps({
        "contract":"personal_cfo_p6d_private_offline_bahl_receipts_v1",
        "receipts":[record if record is not None else receipt()],
    }))

def fake_file():
    return SimpleNamespace(
        id="SYNTHETIC_OWNER_PDF_FILE_X",name=NAME,
        mime_type="application/pdf",size_bytes=320,
        trashed=False,parent_ids=("SYNTHETIC_FOLDER_ONLY",),
        modified_time=datetime(2026,11,15,tzinfo=timezone.utc)
    )

def check(monkeypatch, file=None, sha=SHA):
    calls=[]
    monkeypatch.setattr(p,"_index",lambda kind,value:"a"*64)
    monkeypatch.setattr(p,"_version",lambda file:"b"*64)
    def synthetic_reader(**kw):
        calls.append(kw)
        return SimpleNamespace(extension=".pdf",sha256=sha,
                               content_hmac="c"*64)
    monkeypatch.setattr(p,"read_pinned_google_source_once",synthetic_reader)
    result=p.verify_pinned_offline_receipts(
        files=[file if file is not None else fake_file()],
        folder_id="SYNTHETIC_FOLDER_ONLY",
        access_token="SYNTHETIC_ONLY_ACCESS",
        metadata_transport=lambda *a,**kw:None,
        media_transport=lambda *a,**kw:None,
    )
    return result,calls

def test_exact_pinned_original_hash_accepts_only_offline_historical_snapshot(monkeypatch):
    approved(monkeypatch)
    result,calls=check(monkeypatch)
    assert len(calls)==1
    assert calls[0]["expected_revision_hmac"]=="b"*64
    assert calls[0]["expected_file_hmac"]=="a"*64
    assert result["sources_configured"]==1
    assert result["sources_requiring_review"]==0
    r=result["reports"][0]
    assert r["closing_minor"]==13000
    assert r["transaction_count"]==2
    assert r["source_sha256_verified"] is True
    assert r["offline_reconciliation_attested"] is True
    assert r["automatic_pdf_parsing_performed"] is False
    assert r["isolation_runtime_accepted"] is False
    assert r["current_available_balance_minor"] is None
    assert r["personal_income_minor"] is None
    assert SHA not in str(result)
    assert "SYNTHETIC_ONLY_ACCESS" not in str(result)

@pytest.mark.parametrize("bad",[
    lambda x:{**x,"sha256":"z"*64},
    lambda x:{**x,"closing_minor":13001},
    lambda x:{**x,"closing_minor":True},
    lambda x:{**x,"page_count":0},
    lambda x:{**x,"period_start":"2040-12-20"},
    lambda x:{**x,"name":"other-bank.pdf"},
    lambda x:{**x,"closing_minor":-1},
])
def test_private_receipt_malformed_or_arithmetically_wrong_fails_closed(monkeypatch,bad):
    approved(monkeypatch,bad(receipt()))
    with pytest.raises(p.PrivateOfflineBahlBlocked):
        p._private_receipts()

def test_unapproved_config_default_off_and_no_source_read(monkeypatch):
    monkeypatch.delenv("P6D_PRIVATE_BAHL_OFFLINE_RECEIPTS_JSON",raising=False)
    monkeypatch.delenv("P6D_OWNER_OFFLINE_PDF_RECEIPTS_ENABLED",raising=False)
    result,calls=check(monkeypatch)
    assert result["sources_configured"]==0
    assert result["reports"]==[]
    assert calls==[]

def test_wrong_original_sha_or_folder_suppresses_all_amounts(monkeypatch):
    approved(monkeypatch)
    result,calls=check(monkeypatch,sha="e"*64)
    assert result["reports"]==[]
    assert result["sources_requiring_review"]==1
    wrong=fake_file()
    wrong.parent_ids=("SYNTHETIC_OTHER_FOLDER",)
    result,calls=check(monkeypatch,file=wrong)
    assert result["reports"]==[]
    assert result["sources_requiring_review"]==1
    assert calls==[]

def test_no_original_pdf_parser_or_network_shell_dependency(monkeypatch):
    approved(monkeypatch)
    from pathlib import Path
    contents=Path(p.__file__).read_text()
    assert "from pypdf" not in contents
    assert "import pypdf" not in contents
    assert "subprocess." not in contents
    assert "Sandbox.create" not in contents
    assert "P6D_PRIVATE_BAHL_OFFLINE_RECEIPTS_JSON" in contents
