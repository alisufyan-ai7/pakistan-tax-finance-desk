"""P2C synthetic statement evidence. No user's Drive file or private amounts."""
import base64
from hashlib import sha256

import pytest

from app.private_statement_evidence_preflight import (
    PrivateStatementPreflightBlocked, assess_synthetic_source_bytes,
)

RAW = (
    b"date,description,debit,credit,balance,reference\n"
    b"2026-11-01,Fictional inflow,0,125.00,225.00,FIXTURE-1\n"
    b"2026-11-02,Fictional outflow,35.00,0,190.00,FIXTURE-2\n"
)

@pytest.fixture(autouse=True)
def scope(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv(
        "DRIVE_INDEX_HMAC_KEY",
        base64.urlsafe_b64encode(b"Z"*32).decode("ascii"),
    )


def scan(raw=RAW, **extra):
    return assess_synthetic_source_bytes(
        content=raw,
        extension=extra.get("extension",".csv"),
        date_format=extra.get("date_format","%Y-%m-%d"),
        opening_balance=extra.get("opening_balance","100.00"),
        approved_synthetic_fixture=extra.get("approved",True),
    )


def test_real_sha256_of_fake_source_bytes_and_balance_evidence():
    result=scan()
    assert result["file_sha256"] == sha256(RAW).hexdigest()
    assert result["file_sha256"] != result["source_sha256_hmac"]
    assert result["content_hash_from_actual_bytes"] is True
    assert result["source_row_count"] == 2
    assert result["period_start"] == "2026-11-01"
    assert result["period_end"] == "2026-11-02"
    assert result["balance_check"] == "opening_and_running_verified"
    assert result["opening_balance_verified"] is True
    assert result["synthetic_candidate_credit_minor"] == 12500
    assert result["synthetic_candidate_debit_minor"] == 3500
    assert result["synthetic_candidate_closing_minor"] == 19000
    assert result["real_financial_data_enabled"] is False
    assert result["financial_ledger_mutated"] is False
    assert result["bank_or_owner_identity_verified"] is False
    assert result["cross_document_overlap_reconciled"] is False
    assert result["source_original_modified"] is False
    assert "Fictional inflow" not in str(result)


def test_unknown_opening_is_not_an_accepted_balance_or_zero():
    result=scan(opening_balance=None)
    assert result["opening_balance_verified"] is False
    assert result["synthetic_candidate_credit_minor"] is None
    assert result["synthetic_candidate_debit_minor"] is None
    assert result["synthetic_candidate_closing_minor"] is None
    assert result["source_row_count"] == 2
    assert result["balance_check"] != "opening_and_running_verified"


@pytest.mark.parametrize("reason",[
    "not_approved","real_mode","pdf","xls","wrong_signature",
    "formula","bad_balance","bad_date","oversized","unsafe_binary",
    "duplicate_header",
])
def test_source_preflight_fails_closed_without_exposing_content(monkeypatch,reason):
    raw=RAW
    kw={}
    if reason=="not_approved":kw["approved"]=False
    if reason=="real_mode":monkeypatch.setenv("APP_DATA_MODE","real")
    if reason=="pdf":kw["extension"]=".pdf"
    if reason=="xls":kw["extension"]=".xls"
    if reason=="wrong_signature":raw=b"%PDF-"+RAW
    if reason=="formula":raw=RAW.replace(b"Fictional inflow",b"=WEBSERVICE(SECRET)")
    if reason=="bad_balance":raw=RAW.replace(b"225.00",b"999.00")
    if reason=="bad_date":raw=RAW.replace(b"2026-11-01",b"2026-99-01")
    if reason=="oversized":raw=b"a"*(4*1024*1024+1)
    if reason=="unsafe_binary":raw=RAW+b"\x00"
    if reason=="duplicate_header":raw=RAW.replace(b"date,description,debit",b"date,date,debit")
    with pytest.raises(PrivateStatementPreflightBlocked) as exc:
        scan(raw,**kw)
    error=str(exc.value)
    assert "WEBSERVICE" not in error
    assert "Fictional inflow" not in error
    assert "999.00" not in error


def test_source_replay_same_digest_single_byte_change_not_same_hash():
    original=scan()
    modified=scan(RAW.replace(b"FIXTURE-1",b"FIXTURE-A"))
    assert original["source_row_count"] == modified["source_row_count"]
    assert original["file_sha256"] != modified["file_sha256"]
    assert original["source_sha256_hmac"] != modified["source_sha256_hmac"]
    assert original["synthetic_candidate_closing_minor"] == modified[
        "synthetic_candidate_closing_minor"]
