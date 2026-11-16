"""B3 purely fictitious statement source registry boundary acceptance."""
from datetime import date
import pytest
from app.source_batch_evidence import (
    SourceLine,SyntheticStatementBatch,BatchEvidenceBlocked,validate_synthetic_batch_registry,
)


def batch(ref="synthetic-source-a",digest="a"*64,account="synthetic-account-a",
          start=date(2024,7,1),balance=10500,status="candidate"):
    row=SourceLine(row_number=1,posted_on=start,debit_minor=0,credit_minor=500,
                   balance_minor=balance,source_row_ref="synthetic-row-1")
    return SyntheticStatementBatch(synthetic_fixture=True,
       account_ref=account,legal_owner="individual",currency="PKR",
       source_ref=ref,digest_hmac=digest,parser_version="fictional-v1",
       period_start=start,period_end=start,opening_balance_minor=10000,
       closing_balance_minor=10500,rows=(row,),candidate_status=status)


def test_exact_replay_dedup_and_no_automatic_acceptance():
    b=batch()
    report=validate_synthetic_batch_registry([b,b,b])
    assert report["unique_source_batch_count"]==1
    assert report["total_source_row_count"]==1
    assert report["verified_running_balance_batch_count"]==1
    assert report["review_required_batch_count"]==0
    assert not report["import_performed"] and not report["accounting_accepted"]
    assert "10500" not in str(report) and "synthetic-account-a" not in str(report)


def test_changed_source_same_id_or_content_different_id_blocks():
    with pytest.raises(BatchEvidenceBlocked,match="Conflicting source replay"):
        validate_synthetic_batch_registry([batch(),batch(digest="b"*64)])
    with pytest.raises(BatchEvidenceBlocked,match="Identical account content"):
        validate_synthetic_batch_registry([batch(),batch(ref="synthetic-source-b")])


def test_overlapping_candidates_not_counted_as_independently_safe():
    result=validate_synthetic_batch_registry([
        batch(),batch(ref="synthetic-source-b",digest="b"*64)])
    assert result["review_required_batch_count"]==2
    assert result["issue_counts"]["SOURCE_PERIOD_OVERLAP"]==2
    assert result["accounting_accepted"] is False


def test_bank_balance_mismatch_and_quarantine_never_imported():
    out=validate_synthetic_batch_registry([batch(balance=11000,status="quarantined")])
    assert out["verified_running_balance_batch_count"]==0
    assert out["issue_counts"]["QUARANTINED"]==1
    assert out["issue_counts"]["RUNNING_BALANCE_MISMATCH"]==1


def test_distinct_account_sources_not_overlaps():
    a=batch()
    b=batch(ref="synthetic-source-b",digest="b"*64,account="synthetic-account-b")
    r=validate_synthetic_batch_registry([a,b])
    assert r["issue_counts"]["SOURCE_PERIOD_OVERLAP"]==0


def test_invalid_row_money_and_dates_block_before_registry():
    with pytest.raises(ValueError):
        SourceLine(row_number=1,posted_on=date(2024,7,1),debit_minor=100,
                   credit_minor=200,balance_minor=500,source_row_ref="synthetic-row-1")
    with pytest.raises(ValueError):
        batch(start=date(2022,1,1))


def test_real_data_mode_is_blocked(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(BatchEvidenceBlocked,match="Real"):
        validate_synthetic_batch_registry([batch()])
