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
    assert "FICTIONAL PARTNER A" not in str(result)


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

def test_authenticated_owner_report_pins_source_and_does_not_ingest_pdf(monkeypatch):
    from types import SimpleNamespace
    import hashlib
    from app import private_owner_property_inventory_report as owner_report

    owner="synthetic-owner-123456789012345"
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1W_OWNER_REF",owner)
    for flag in (
        "P6B_OWNER_INVESTMENT_RUNTIME",
        "P6B_G3_PROPERTY_REGISTER_RECONCILIATION_ACCEPTED",
        "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
        "P3A_G3_RESTRICTED_SCOPE_REVIEWED",
        "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
    ):
        monkeypatch.setenv(flag,"1")
    groups={
        "property_register_group_id":"property_group",
        "groups":[
            {"id":"property_group","title":"Fictional property partner",
             "ventures":[{"id":"property_venture","title":"Fictional properties",
                          "category":"property"}]},
            {"id":"fictional_partner","title":"Fictional second partner",
             "ventures":[{"id":"other_venture","title":"Fictional venture",
                          "category":"business"}]},
        ],
    }
    monkeypatch.setenv("P6B_PRIVATE_RELATIONSHIPS_JSON",json.dumps(groups))
    monkeypatch.setenv("P6C_PRIVATE_BANK_MATCH_PHRASES_JSON",
                       json.dumps({"fictional_partner":["to FICTIONAL PARTNER A "]}))
    cfg=SimpleNamespace(folder_id="synthetic-approved-folder",
                        client_id="synthetic-client")
    monkeypatch.setattr(owner_report,"_guard_network",lambda:cfg)
    monkeypatch.setattr(owner_report,"read_private_content_grant",
                        lambda *args,**kwargs:"synthetic-private-refresh")
    monkeypatch.setattr(owner_report,"refresh_google_content_token",
                        lambda **kwargs:("synthetic-access",None))
    csv_source=SimpleNamespace(
        id="synthetic-file-a",name="synthetic.csv",
        mime_type="text/csv",size_bytes=len(fixture_csv()),
        parent_ids=(cfg.folder_id,),trashed=False)
    pdf_source=SimpleNamespace(
        id="synthetic-file-b",name="synthetic.pdf",
        mime_type="application/pdf",size_bytes=1024,
        parent_ids=(cfg.folder_id,),trashed=False)
    monkeypatch.setattr(owner_report,"_inventory",
                        lambda *a,**kw:[csv_source,pdf_source])
    monkeypatch.setattr(owner_report,"_index",
        lambda domain,value:hashlib.sha256(
            (domain+":"+value).encode("utf8")).hexdigest())
    monkeypatch.setattr(owner_report,"_version",lambda *a:"d"*64)
    read=[]
    def media(**kw):
        read.append(kw)
        return SimpleNamespace(data=fixture_csv(),extension=".csv",
                               content_hmac="e"*64)
    monkeypatch.setattr(owner_report,"read_pinned_google_source_once",media)
    class DB:
        def __enter__(self):return self
        def __exit__(self,*args):return False
    report=owner_report.get_private_property_inventory_overview(
        session_factory=DB,owner_ref=owner,
        transport=lambda *a,**kw:None,
        media_transport=lambda *a,**kw:None)
    assert report["property_register_sources_verified"]==0
    assert len(read)==1
    assert read[0]["file_id"]==csv_source.id
    assert report["candidate_bank_movements"]["source_reconciliation_verified"] is True
    assert len(report["candidate_bank_movements"]["groups"])==1
    assert report["candidate_bank_movements"]["groups"][0]["candidate_count"]==1
    assert report["candidate_bank_movements"]["groups"][0]["outgoing_bank_movements_minor"]==2000
    assert report["candidate_bank_movements"]["outstanding_investment_balance_minor"] is None
    assert report["owner_relationships"]["groups"][1]["ventures"][0]["confirmed_invested_principal_minor"] is None
