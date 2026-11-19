"""P5G private HTTP test with invented bank facts and password, never owner data."""
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import private_historical_bahl_http as h

SUBJECT="a"*64
CONTENT="b"*64
OWNER="SYNTHETIC_PRIVATE_OWNER_REPORT_2026"
FAKE={
 "contract":"personal_cfo_owner_historical_bahl_report_v1",
 "source_hmac":SUBJECT,"source_content_hmac":CONTENT,
 "source_name":"SI-123456789 BAH eStatement(01012026).pdf",
 "original_source_modified":False,"content_retained_on_server":False,
 "financial_values_verified":False,
 "income_minor":None,"expenses_minor":None,
 "current_available_balance_minor":None,
 "status":"SOURCE_STATEMENT_RECONCILED",
 "statement_start":"2025-07-01","statement_end":"2026-06-30",
 "historical_opening_minor":10000,
 "historical_closing_minor":37500,
 "gross_bank_debits_minor":2500,
 "gross_bank_credits_minor":30000,
 "transaction_count":2,
 "source_sha256_verified":True,
 "running_balance_reconciled":True,
 "printed_gross_totals_match_transactions":True,
 "historical_only":True,
 "owner_review_required":True,
 "transfers_excluded":False,
 "all_account_coverage_verified":False,
 "ledger_mutated":False,
}


@pytest.mark.parametrize("value",[
 b"{}",b'{"source_hmac":"a"}',
 b'{"source_hmac":"'+b"a"*64+b'","other":"reject"}',
 b'{"source_hmac":"'+b"a"*64+b'","source_hmac":"'+b"a"*64+b'"}',
 b'{"source_hmac":"'+b"a"*64+b'","password":""}',
 b'{"source_hmac":"'+b"a"*64+b'","password":"abc\\nxyz"}',
 b'{"source_hmac":"'+b"a"*64+b'","password":12}',
 b'{"source_hmac":"'+b"a"*64+b'","password":"'+b"x"*129+b'"}',
 b'{"source_hmac":"'+b"a"*64+b'","file_id":"SECRET"}',
 b"x"*1000,
])
def test_strict_body_refuses_unknown_keys_duplicates_control_password(value):
    with pytest.raises(h.PrivateHistoricalHttpBlocked):
        h._strict_body(value)


def test_only_pinned_hmac_and_ephemeral_password_parse():
    subject,password=h._strict_body(json.dumps({
      "source_hmac":SUBJECT,"password":"SYNTHETIC-ONLY-123",
    }).encode())
    assert subject==SUBJECT
    assert password=="SYNTHETIC-ONLY-123"
    assert h._strict_body(json.dumps({"source_hmac":SUBJECT}).encode())==(SUBJECT,None)


def test_historical_values_explicitly_not_income_or_current_balance():
    result=h._validate_report(FAKE,SUBJECT)
    assert result["historical_opening_minor"]==10000
    assert result["historical_closing_minor"]==37500
    assert result["historical_only"] is True
    assert result["current_available_balance_minor"] is None
    assert result["income_minor"] is None
    assert result["expenses_minor"] is None
    assert result["financial_values_verified"] is False
    assert result["all_account_coverage_verified"] is False
    assert result["transfers_excluded"] is False
    assert "password" not in str(result).lower()
    assert "fake" not in str(result).lower()


@pytest.mark.parametrize("change",[
 {"source_hmac":"b"*64},
 {"source_content_hmac":"not a hash"},
 {"income_minor":2500},
 {"expenses_minor":2200},
 {"current_available_balance_minor":37500},
 {"financial_values_verified":True},
 {"status":"UNVERIFIED"},
 {"source_sha256_verified":False},
 {"running_balance_reconciled":False},
 {"printed_gross_totals_match_transactions":False},
 {"transfers_excluded":True},
 {"all_account_coverage_verified":True},
 {"ledger_mutated":True},
 {"historical_only":False},
 {"historical_closing_minor":-1},
 {"historical_closing_minor":"37500"},
 {"statement_start":"3025-07-01"},
])
def test_refuses_partial_false_financial_claims(change):
    with pytest.raises(h.PrivateHistoricalHttpBlocked):
        h._validate_report({**FAKE,**change},SUBJECT)


def test_password_required_status_never_returns_any_amounts():
    result=h._validate_report({k:v for k,v in FAKE.items()
        if k not in {
          "statement_start","statement_end",
          "historical_opening_minor","historical_closing_minor",
          "gross_bank_debits_minor","gross_bank_credits_minor",
          "transaction_count",
        }} | {"status":"PASSWORD_REQUIRED"}, SUBJECT)
    assert result["status"]=="PASSWORD_REQUIRED"
    assert "historical_opening_minor" not in result
    assert "historical_closing_minor" not in result
    assert result["current_available_balance_minor"] is None


def test_disabled_without_all_exact_release_flags(monkeypatch):
    app=FastAPI()
    with pytest.raises(h.PrivateHistoricalHttpBlocked):
        h.mount_private_historical_bahl_http(
            app,session_factory=lambda:None,
            report_callback=lambda **kwargs: FAKE)
    assert "/internal/finance/historical/bahl" not in {x.path for x in app.routes}


@pytest.fixture
def fake_route(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    for flag in ("P5G_OWNER_HISTORICAL_HTTP_RUNTIME",
                 "P5G_G2_HISTORICAL_EXACT_INGRESS_REVIEWED",
                 "P5G_G3_PASSWORD_AND_SOURCE_ISOLATION_ACCEPTED",
                 "P4C_CONTENT_OAUTH_RUNTIME"):
        monkeypatch.setenv(flag,"1")
    monkeypatch.setattr(h,"_boundary",lambda *args,**kwargs: OWNER)
    monkeypatch.setattr(h,"verify_private_owner_session",lambda *args,**kwargs:None)
    from contextlib import nullcontext
    app=FastAPI()
    calls=[]
    def report(**kwargs):
        calls.append(kwargs)
        if kwargs["password"] is None:
            return {k:v for k,v in FAKE.items() if k not in (
                "historical_opening_minor","historical_closing_minor",
                "gross_bank_debits_minor","gross_bank_credits_minor","transaction_count",
                "statement_start","statement_end")} | {"status":"PASSWORD_REQUIRED"}
        return FAKE
    h.mount_private_historical_bahl_http(
        app,session_factory=lambda:nullcontext(None),report_callback=report)
    return TestClient(app),calls


def test_one_time_password_only_private_post_no_logs_or_income(fake_route):
    client,calls=fake_route
    resp=client.post("/internal/finance/historical/bahl",
        headers={"Content-Type":"application/json"},
        json={"source_hmac":SUBJECT})
    assert resp.status_code==200
    assert resp.json()["status"]=="PASSWORD_REQUIRED"
    assert "historical_closing_minor" not in resp.json()
    res=client.post("/internal/finance/historical/bahl",
        headers={"Content-Type":"application/json"},
        json={"source_hmac":SUBJECT,"password":"SYNTHETIC-ONLY-123"})
    assert res.status_code==200
    assert res.json()["historical_closing_minor"]==37500
    assert "SYNTHETIC-ONLY-123" not in res.text
    assert res.headers["cache-control"]=="no-store, private"
    assert calls[0]["password"] is None
    assert calls[1]["password"]=="SYNTHETIC-ONLY-123"
    assert all(x["source_hmac"]==SUBJECT for x in calls)


def test_invalid_or_unsafe_request_never_reaches_private_parser(fake_route):
    c,calls=fake_route
    assert c.get("/internal/finance/historical/bahl").status_code==405
    assert c.post("/internal/finance/historical/bahl",
        data="source_hmac="+SUBJECT,
        headers={"Content-Type":"application/x-www-form-urlencoded"}).status_code==400
    assert c.post("/internal/finance/historical/bahl",
        headers={"Content-Type":"application/json"},
        content=b'{"source_hmac":"a"}').status_code==400
    assert calls==[]
