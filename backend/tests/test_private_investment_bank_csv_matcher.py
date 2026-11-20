"""Synthetic-only bank partner movement matching tests; no owner amounts/names."""
import json
import pytest

from app.private_bank_csv_reconciler import reconcile_private_bank_csv
from app.private_investment_bank_csv_matcher import (
    PrivateBankInvestmentMatchBlocked,private_investment_bank_match_config,
    match_reconciled_bank_csv_candidates,
)


def fixture_csv():
    return (
        "00000000000000,\n"
        "Opening Balance,PKR      100.00\n"
        "Closing Balance,PKR      125.00\n"
        "Currency,Pakistan Rupee(PKR)\n"
        "Booking Date,Value Date,Doc No,Description,Debit,Credit,Available Balance\n"
        "01 Jan 2026,01 Jan 2026,TEST1,Money Received from FICTIONAL PARTNER A BANK,,50.00,150.00\n"
        "02 Jan 2026,02 Jan 2026,TEST2,Money Transferred to FICTIONAL PARTNER A BANK,20.00,,130.00\n"
        "03 Jan 2026,03 Jan 2026,TEST3,Payment of Profit,,0.50,130.50\n"
        "03 Jan 2026,03 Jan 2026,TEST4,Withholding Tax Debit Example,0.10,,130.40\n"
        "04 Jan 2026,04 Jan 2026,TEST5,Money Transferred to UNRELATED VENDOR BANK,5.40,,125.00\n"
    ).encode()


def test_two_directional_bank_events_are_candidates_not_repayments():
    data=fixture_csv()
    proof=reconcile_private_bank_csv(data)
    result=match_reconciled_bank_csv_candidates(
        data,report=proof,source_hmac="b"*64,
        matching={"fictional_partner":[
            "to FICTIONAL PARTNER A ","from FICTIONAL PARTNER A "]},
        hmac_index=lambda *a:"c"*64)
    assert result["contract"]=="personal_cfo_p6_investment_bank_candidates_v1"
    assert result["source_reconciliation_verified"] is True
    assert result["all_investment_sources_covered"] is False
    assert result["personal_investment_principal_verified"] is False
    assert result["repayments_verified"] is False
    assert result["outstanding_investment_balance_minor"] is None
    assert result["realized_investment_return_minor"] is None
    g=result["groups"][0]
    assert g["group_id"]=="fictional_partner"
    assert g["outgoing_bank_movements_minor"]==2000
    assert g["incoming_bank_movements_minor"]==5000
    assert g["candidate_count"]==2
    assert [r["direction"] for r in g["rows"]]==["INBOUND","OUTBOUND"]
    assert all(r["source_hmac"]=="b"*64 for r in g["rows"])
    assert "FICTIONAL" not in str(result)
    assert "BANK" not in str(result)


def test_unknown_ledger_incomplete_is_never_a_zero_balance():
    data=fixture_csv()
    proof=reconcile_private_bank_csv(data)
    r=match_reconciled_bank_csv_candidates(
        data,report=proof,source_hmac="b"*64,
        matching={"unmatched_partner":["to NOBODY MATCHES "]},
        hmac_index=lambda *a:"c"*64)
    assert r["groups"][0]["candidate_count"]==0
    assert r["groups"][0]["rows"]==[]
    assert r["outstanding_investment_balance_minor"] is None


def test_config_private_and_strict(monkeypatch):
    groups=[{"id":"fictional_partner"}]
    monkeypatch.setenv("P6C_PRIVATE_BANK_MATCH_PHRASES_JSON",
      json.dumps({"fictional_partner":["to FICTIONAL PARTNER A "]}))
    assert private_investment_bank_match_config(groups=groups)=={
        "fictional_partner":["to FICTIONAL PARTNER A "]}
    monkeypatch.delenv("P6C_PRIVATE_BANK_MATCH_PHRASES_JSON")
    assert private_investment_bank_match_config(groups=groups)=={}


@pytest.mark.parametrize("raw",[
    '{"missing_group":["to A LONG NAME "]}',
    '{"fictional_partner":["partner A"]}',
    '{"fictional_partner":["to XYZ .* "]}',
    '{"fictional_partner":["to FICTIONAL PARTNER A ","to FICTIONAL PARTNER A "]}',
    '{"fictional_partner":["to FICTIONAL PARTNER A "],"fictional_partner":["to OTHER PARTNER B "]}',
    '{"fictional_partner":[{"name":"FICTIONAL"}]}',
    '{"fictional_partner":[]}',
    'not json',
    "x"*3001,
])
def test_config_cannot_use_regex_or_unknown_partner(monkeypatch,raw):
    monkeypatch.setenv("P6C_PRIVATE_BANK_MATCH_PHRASES_JSON",raw)
    with pytest.raises(PrivateBankInvestmentMatchBlocked):
        private_investment_bank_match_config(groups=[{"id":"fictional_partner"}])


def test_overlapping_partner_mappings_are_blocked_instead_of_double_counted():
    data=fixture_csv()
    proof=reconcile_private_bank_csv(data)
    with pytest.raises(PrivateBankInvestmentMatchBlocked):
        match_reconciled_bank_csv_candidates(
            data,report=proof,source_hmac="b"*64,
            matching={"first_partner":["to FICTIONAL PARTNER A "],
                "second_partner":["to FICTIONAL PARTNER A "]},
            hmac_index=lambda *a:"c"*64)


def test_no_unverified_source_proof_is_accepted():
    data=fixture_csv()
    proof=reconcile_private_bank_csv(data)
    proof["all_running_balances_reconciled"]=False
    with pytest.raises(PrivateBankInvestmentMatchBlocked):
        match_reconciled_bank_csv_candidates(
            data,report=proof,source_hmac="b"*64,
            matching={"fictional_partner":["to FICTIONAL PARTNER A "]},
            hmac_index=lambda *a:"c"*64)
