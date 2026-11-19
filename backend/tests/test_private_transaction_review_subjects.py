"""P5J synthetic one-owner source-row identity planner; no genuine data."""
import base64

import pytest

from app.drive_inbox_planner import _index
from app.private_transaction_review_subjects import (
    plan_synthetic_pinned_transaction_subjects as plan,
    PrivateTransactionSubjectBlocked as Blocked,
)

def fixtures():
    return dict(
        owner_hmac=_index("synthetic-owner","one"),
        account_hmac=_index("synthetic-account","one"),
        original_file_hmac=_index("synthetic-original","one"),
        verified_source_content_hmac=_index("source-sha256","a"*64),
        statement_start="2025-07-01",
        statement_end="2026-06-30",
        opening_minor=10000, printed_closing_minor=37500,
        printed_gross_debits_minor=2500,
        printed_gross_credits_minor=30000,
        rows=(
          dict(page_number=1,source_row_ordinal=1,posted_on="2025-07-02",
               debit_minor=0,credit_minor=30000,running_balance_minor=40000),
          dict(page_number=1,source_row_ordinal=2,posted_on="2025-07-05",
               debit_minor=2500,credit_minor=0,running_balance_minor=37500),
        ),
        source_sha_verified=True,statement_layout_reconciled=True,
        approved_synthetic_fixture=True,
    )

@pytest.fixture(autouse=True)
def fake_mode(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P5J_SYNTHETIC_TRANSACTION_SUBJECTS_ONLY","1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",base64.urlsafe_b64encode(b"S"*32).decode())

def test_stable_bounded_row_targets_never_post_ledger_or_infer_income():
    sample=fixtures()
    a=plan(**sample)
    b=plan(**sample)
    assert a==b
    assert a["transaction_count"]==2
    assert all(len(row["transaction_hmac"])==64 for row in a["review_targets"])
    assert len({row["transaction_hmac"] for row in a["review_targets"]})==2
    assert all(row["review_state"]=="NEEDS_OWNER_CONTEXT" for row in a["review_targets"])
    assert a["income_minor"] is None and a["expenses_minor"] is None
    assert a["current_available_balance_minor"] is None
    assert a["real_financial_ledger_mutated"] is False
    assert a["owner_comments_live"] is False
    rotated=plan(**{**sample,
        "verified_source_content_hmac":_index("source-sha256","b"*64)})
    assert rotated["review_targets"][0]["transaction_hmac"]!=a["review_targets"][0]["transaction_hmac"]
    another=plan(**{**sample,"account_hmac":_index("synthetic-account","two")})
    assert another["review_targets"][0]["transaction_hmac"]!=a["review_targets"][0]["transaction_hmac"]

@pytest.mark.parametrize("problem",[
    "wrong_source","no_layout","different_owner","wrong_close",
    "wrong_total","duplicate_row","out_of_order","inconsistent_balance",
    "both_debit_and_credit","zero_move","outside_period",
    "untrusted_content_hmac","real_mode",
])
def test_missing_or_broken_pinned_bank_evidence_rejected(monkeypatch,problem):
    kw=fixtures()
    rows=list(kw["rows"])
    if problem=="wrong_source":kw["source_sha_verified"]=False
    if problem=="no_layout":kw["statement_layout_reconciled"]=False
    if problem=="different_owner":kw["owner_hmac"]="no-owner"
    if problem=="wrong_close":kw["printed_closing_minor"]+=1
    if problem=="wrong_total":kw["printed_gross_credits_minor"]+=1
    if problem=="duplicate_row":rows[1]={**rows[1],"source_row_ordinal":1}
    if problem=="out_of_order":rows[1]={**rows[1],"posted_on":"2025-07-01"}
    if problem=="inconsistent_balance":rows[1]={**rows[1],"running_balance_minor":37000}
    if problem=="both_debit_and_credit":rows[1]={**rows[1],"credit_minor":20}
    if problem=="zero_move":rows[1]={**rows[1],"debit_minor":0}
    if problem=="outside_period":rows[0]={**rows[0],"posted_on":"2025-06-30"}
    if problem=="untrusted_content_hmac":kw["verified_source_content_hmac"]="x"*63
    if problem=="real_mode":monkeypatch.setenv("APP_DATA_MODE","real")
    kw["rows"]=tuple(rows)
    with pytest.raises(Blocked):
        plan(**kw)

def test_missing_feature_off_and_arbitrary_extra_fields(monkeypatch):
    kw=fixtures()
    monkeypatch.delenv("P5J_SYNTHETIC_TRANSACTION_SUBJECTS_ONLY")
    with pytest.raises(Blocked):plan(**kw)
    monkeypatch.setenv("P5J_SYNTHETIC_TRANSACTION_SUBJECTS_ONLY","1")
    kw["rows"]=({**kw["rows"][0],"raw_name":"INJECTED_OWNER_DATA"},)
    with pytest.raises(Blocked):plan(**kw)
