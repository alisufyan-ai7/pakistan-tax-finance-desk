"""P2C bank chain tests: fully fictional, no owner's original files."""
import base64
import pytest

from app.private_statement_evidence_preflight import assess_synthetic_source_bytes
from app.private_statement_chain import (
    reconcile_synthetic_statement_chain,PrivateStatementChainBlocked,
)

RAW1=(
 b"date,description,debit,credit,balance,reference\n"
 b"2026-11-01,synthetic credit,0,125.00,225.00,FAKE-1\n"
 b"2026-11-02,synthetic debit,35.00,0,190.00,FAKE-2\n"
)
RAW2=(
 b"date,description,debit,credit,balance,reference\n"
 b"2026-11-03,synthetic credit,0,50.00,240.00,FAKE-3\n"
 b"2026-11-04,synthetic debit,20.00,0,220.00,FAKE-4\n"
)
ACCOUNT="e"*64


@pytest.fixture(autouse=True)
def scope(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
        base64.urlsafe_b64encode(b"S"*32).decode("ascii"))


def report(raw, opening):
    return assess_synthetic_source_bytes(
        content=raw,extension=".csv",date_format="%Y-%m-%d",
        opening_balance=opening,approved_synthetic_fixture=True,
    )


def chain(reports,periods,complete=None):
    return reconcile_synthetic_statement_chain(
        account_hmac=ACCOUNT,sources=tuple(reports),
        declared_periods=tuple(periods),
        independently_declared_complete=tuple(
            [True]*len(reports) if complete is None else complete),
        approved_synthetic_fixture=True,
    )


def test_two_contiguous_sources_reconcile_only_bank_movement_not_income():
    first=report(RAW1,"100.00")
    second=report(RAW2,"190.00")
    result=chain([first,second],[
        ("2026-11-01","2026-11-02"),("2026-11-03","2026-11-04"),
    ])
    assert result["status"]=="SYNTHETIC_CHAIN_RECONCILED"
    assert result["chain_coverage_verified_synthetically"] is True
    assert result["candidate_opening_minor"]==10000
    assert result["candidate_closing_minor"]==22000
    assert result["candidate_bank_credits_minor"]==17500
    assert result["candidate_bank_debits_minor"]==5500
    assert result["real_income_minor"] is None
    assert result["real_expenses_minor"] is None
    assert result["own_transfers_classified"] is False
    assert result["real_financial_data_enabled"] is False
    assert result["ledger_mutated"] is False
    assert result["genuine_bank_and_owner_verified"] is False
    assert "synthetic debit" not in str(result)


def test_identical_replay_does_not_double_count():
    a,b=report(RAW1,"100.00"),report(RAW2,"190.00")
    periods=[("2026-11-01","2026-11-02"),
             ("2026-11-03","2026-11-04")]
    single=chain([a,b],periods)
    duplicated=chain([a,a,b],[periods[0],periods[0],periods[1]])
    assert duplicated["idempotent_replays"]==1
    assert duplicated["distinct_sources"]==2
    assert duplicated["candidate_bank_credits_minor"]==single["candidate_bank_credits_minor"]
    assert duplicated["source_chain_hmac"]==single["source_chain_hmac"]
    with pytest.raises(PrivateStatementChainBlocked):
        chain([a,a],[periods[0],("2026-11-01","2026-11-03")])


def test_gaps_and_overlap_leave_balances_and_totals_unknown():
    a,b=report(RAW1,"100.00"),report(RAW2,"190.00")
    # Declared first statement covers three days, colliding with second.
    overlap=chain([a,b],[("2026-11-01","2026-11-03"),
                         ("2026-11-03","2026-11-04")])
    assert overlap["status"]=="OVERLAP_REVIEW"
    assert overlap["candidate_closing_minor"] is None
    assert overlap["candidate_bank_debits_minor"] is None
    # Synthetic second statement begins 11-05; gap on 11-03/04.
    later=RAW2.replace(b"2026-11-03",b"2026-11-05").replace(
        b"2026-11-04",b"2026-11-06")
    b_later=report(later,"190.00")
    gap=chain([a,b_later],[("2026-11-01","2026-11-02"),
                           ("2026-11-05","2026-11-06")])
    assert gap["status"]=="MISSING_PERIOD_REVIEW"
    assert gap["candidate_bank_credits_minor"] is None
    assert gap["candidate_opening_minor"] is None


def test_carry_forward_mismatch_and_uncertified_statement_period():
    a=report(RAW1,"100.00")
    mismatched=RAW2.replace(b"240.00",b"230.00").replace(b"220.00",b"210.00")
    b=report(mismatched,"180.00")
    periods=[("2026-11-01","2026-11-02"),
             ("2026-11-03","2026-11-04")]
    bad=chain([a,b],periods)
    assert bad["status"]=="CARRY_FORWARD_MISMATCH_REVIEW"
    assert bad["candidate_closing_minor"] is None
    unconfirmed=chain([a,report(RAW2,"190.00")],periods,[True,False])
    assert unconfirmed["status"]=="UNCONFIRMED_STATEMENT_PERIOD_REVIEW"
    assert unconfirmed["candidate_bank_credits_minor"] is None


def test_wrong_scope_missing_opening_real_mode_and_invalid_period_fail_closed(monkeypatch):
    a=report(RAW1,"100.00")
    partial=report(RAW1,None)
    periods=[("2026-11-01","2026-11-02")]
    with pytest.raises(PrivateStatementChainBlocked):
        chain([partial],periods)
    with pytest.raises(PrivateStatementChainBlocked):
        chain([a],[("2026-11-02","2026-11-03")])
    with pytest.raises(PrivateStatementChainBlocked):
        reconcile_synthetic_statement_chain(
            account_hmac="unblinded",sources=(a,),
            declared_periods=tuple(periods),
            independently_declared_complete=(True,),
            approved_synthetic_fixture=True)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(PrivateStatementChainBlocked):
        chain([a],periods)
