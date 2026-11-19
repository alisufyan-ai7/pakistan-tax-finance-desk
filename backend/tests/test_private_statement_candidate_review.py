"""P3B source-backed review: fake bytes only, never finance ledger release."""
import base64
from hashlib import sha256
import pytest
from app.drive_inbox_planner import _index
from app.private_statement_candidate_review import (
    review_synthetic_statement_candidate,StatementCandidateReviewBlocked,
)

H="b"*64
NORMAL=(
 b"date,description,debit,credit,balance,reference\n"
 b"2026-11-02,fictional incoming,0,125.00,225.00,FAKE-1\n"
 b"2026-11-29,fictional outgoing,35.00,0,190.00,FAKE-2\n"
)
SPLIT=(
 b"Post Date,Narration,Withdrawals,Deposits,Running Balance,Transaction Ref\n"
 b"02/11/2026,Fictional credit,,125.00,225.00,FAKE-1\n"
 b"29/11/2026,Fictional debit,35.00,,190.00,FAKE-2\n"
)


@pytest.fixture(autouse=True)
def synthetic(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
        base64.urlsafe_b64encode(b"Y"*32).decode("ascii"))


def review(raw=NORMAL,**kw):
    return review_synthetic_statement_candidate(
        original_bytes=raw,
        extension=kw.pop("extension",".csv"),
        layout=kw.pop("layout","normalized"),
        date_format=kw.pop("date_format","%Y-%m-%d"),
        opening_balance=kw.pop("opening_balance","100.00"),
        account_ref_hmac=kw.pop("account_ref_hmac",H),
        declared_period=kw.pop("declared_period",
                               ("2026-11-01","2026-11-30")),
        independent_account_verified=kw.pop("independent_account_verified",True),
        independent_period_verified=kw.pop("independent_period_verified",True),
        approved_synthetic_fixture=kw.pop("approved_synthetic_fixture",True),
    )


def test_synthetic_good_evidence_counts_not_real_income_or_expense():
    result=review()
    assert result["content_sha256_hmac"]==_index(
        "source-sha256",sha256(NORMAL).hexdigest())
    assert sha256(NORMAL).hexdigest()!=result["content_sha256_hmac"]
    assert result["source_row_count"]==2
    assert result["source_status"]=="SYNTHETIC_REVIEW_CANDIDATE"
    assert result["observed_first_transaction"]=="2026-11-02"
    assert result["declared_statement_start"]=="2026-11-01"
    assert result["declared_statement_end"]=="2026-11-30"
    assert result["synthetic_candidate_bank_credits_minor"]==12500
    assert result["synthetic_candidate_bank_debits_minor"]==3500
    assert result["synthetic_candidate_closing_minor"]==19000
    assert result["actual_income_minor"] is None
    assert result["actual_expense_minor"] is None
    assert result["cross_statement_overlap_reconciled"] is False
    assert result["account_month_completeness_proven"] is False
    assert result["profile_certified_for_real_bank"] is False
    assert result["real_financial_data_enabled"] is False
    assert result["ledger_mutated"] is False
    assert "fictional incoming" not in str(result)


def test_opening_unknown_or_no_declared_period_withholds_all_bank_movements():
    for kw in (
        {"opening_balance":None},
        {"declared_period":None},
        {"account_ref_hmac":None},
        {"independent_account_verified":False},
        {"independent_period_verified":False},
    ):
        result=review(**kw)
        assert result["source_status"]=="EVIDENCE_INCOMPLETE"
        assert result["synthetic_candidate_bank_credits_minor"] is None
        assert result["synthetic_candidate_bank_debits_minor"] is None
        assert result["synthetic_candidate_closing_minor"] is None
        assert result["actual_income_minor"] is None
        assert result["review_flags"]


def test_supported_fake_header_mapping_never_certifies_real_bank_format():
    result=review(SPLIT,layout="synthetic_split",date_format="%d/%m/%Y")
    assert result["source_row_count"]==2
    assert result["layout_candidate"]=="synthetic_split"
    assert result["profile_certified_for_real_bank"] is False
    assert result["synthetic_candidate_closing_minor"]==19000


def test_replayed_reference_is_review_flag_not_a_auto_deleted_record():
    duplicate=NORMAL.replace(b"FAKE-2",b"FAKE-1")
    result=review(duplicate)
    assert result["repeated_reference_candidates"]==1
    assert "REPEATED_TRANSACTION_REFERENCES_REQUIRE_REVIEW" in result["review_flags"]
    assert result["source_row_count"]==2


@pytest.mark.parametrize("kwargs",[
    {"approved_synthetic_fixture":False},
    {"extension":".pdf"},
    {"extension":".xls"},
    {"layout":"unapproved_bank"},
    {"date_format":"%m-%d-%Y"},
    {"declared_period":("2026-11-10","2026-11-30")},
    {"declared_period":("2026-11-01","2026-11-03")},
    {"declared_period":("2026-11-30","2026-11-01")},
    {"declared_period":("not-a-date","2026-11-30")},
])
def test_invalid_profile_and_unsupported_period_block(kwargs):
    with pytest.raises(StatementCandidateReviewBlocked):
        review(**kwargs)


def test_wrong_balance_and_malicious_content_block_without_leaking():
    for raw in (
        NORMAL.replace(b"225.00",b"999.00"),
        NORMAL.replace(b"fictional incoming",b"=HYPERLINK('http://evil.invalid')"),
        b"<html>not a real bank export</html>",
        NORMAL+b"\x00",
        b"x"*(4*1024*1024+1),
    ):
        with pytest.raises(StatementCandidateReviewBlocked) as e:
            review(raw)
        assert "999.00" not in str(e.value)
        assert "HYPERLINK" not in str(e.value)


def test_real_mode_disabled_even_with_good_fake_evidence(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(StatementCandidateReviewBlocked):
        review()
