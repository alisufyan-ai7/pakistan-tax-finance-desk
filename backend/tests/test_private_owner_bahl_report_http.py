"""P5F HTTP contracts: fake owner session and fake bank analyzer only."""
from contextlib import nullcontext
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import private_owner_bahl_report_http as c

H="d"*64
NOTE="SYNTHETIC_PRIVATE_PDF_PASSWORD"


@pytest.fixture
def fake(monkeypatch):
    for key in (
        "P5F_OWNER_BAHL_HTTP_RUNTIME",
        "P5F_G2_TRANSIENT_PASSWORD_INGRESS_REVIEWED",
        "P5F_G3_BANK_SOURCE_REPORT_REVIEWED",
        "P5E_OWNER_HISTORICAL_REPORT_PILOT",
        "P5E_G3_ISOLATED_BANK_READER_REVIEWED",
        "P5A_ORIGINAL_HASH_PILOT",
        "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
    ):
        monkeypatch.setenv(key,"1")
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    calls=[]
    def boundary(req,mutation=False):
        if req.headers.get("origin")=="https://evil.invalid":
            raise c.HTTPException(403,"Forbidden origin")
        if mutation and req.headers.get("x-csrf-token")!="FAKE_CSRF":
            raise c.HTTPException(401,"MFA/CSRF required")
        if req.cookies.get("owner")!="fake-auth":
            raise c.HTTPException(401,"Private owner required")
        return "SYNTHETIC_FAKE_OWNER_2026"
    monkeypatch.setattr(c,"_boundary",boundary)
    monkeypatch.setattr(c,"verify_private_owner_session",lambda *a,**kw:True)
    def analyzer(**kw):
        calls.append(kw)
        if kw["source_hmac"]!=H:
            raise c.PrivateHistoricalBankReportBlocked("fake unapproved")
        if kw["password"] is None:
            return {"contract":"personal_cfo_owner_historical_bahl_report_v1",
                    "status":"PASSWORD_REQUIRED","source_hmac":H,
                    "income_minor":None,"expenses_minor":None}
        return {
            "contract":"personal_cfo_owner_historical_bahl_report_v1",
            "status":"SOURCE_STATEMENT_RECONCILED",
            "source_hmac":H,
            "statement_start":"2025-07-01","statement_end":"2026-06-30",
            "historical_closing_minor":37500,
            "current_available_balance_minor":None,
            "income_minor":None,"expenses_minor":None,
        }
    monkeypatch.setattr(c,"analyze_pinned_bahl_historical_report",analyzer)
    app=FastAPI()
    c.install_owner_bahl_report_http(
        app,session_factory=lambda:nullcontext(None),
        transport=lambda *a,**kw:None,
    )
    with TestClient(app,base_url="https://personal-cfo.example.invalid") as client:
        yield client,calls


def test_bahl_status_requires_owner_and_is_historical_only(fake):
    client,_=fake
    assert client.get("/internal/finance/bahl/status").status_code==401
    client.cookies.set("owner","fake-auth")
    r=client.get("/internal/finance/bahl/status")
    assert r.status_code==200
    assert r.json()["historical_source_reports_enabled"] is True
    assert r.json()["requires_private_pdf_password_on_demand"] is True
    assert r.json()["current_bank_balances_verified"] is False
    assert r.json()["income_expenses_verified"] is False
    assert r.json()["original_drive_writes_allowed"] is False


def test_password_from_private_post_is_not_echoed_or_stored(fake):
    client,calls=fake
    client.cookies.set("owner","fake-auth")
    csrf={"origin":"https://personal-cfo.example.invalid","x-csrf-token":"FAKE_CSRF"}
    first=client.post("/internal/finance/bahl/analyze",
                      json={"source_hmac":H},headers=csrf)
    assert first.status_code==200
    assert first.json()["status"]=="PASSWORD_REQUIRED"
    value=client.post("/internal/finance/bahl/analyze",
                      json={"source_hmac":H,"password":NOTE},headers=csrf)
    assert value.status_code==200
    assert value.json()["historical_closing_minor"]==37500
    assert value.json()["current_available_balance_minor"] is None
    assert value.json()["income_minor"] is None
    assert NOTE not in value.text
    assert calls[-1]["password"]==NOTE


@pytest.mark.parametrize("payload",[
    {"source_hmac":"FAKE"},
    {"source_hmac":"f"*64,"file_id":"not_allowed"},
    {"source_hmac":H,"password":""},
    {"source_hmac":H,"password":"invalid\ninput"},
    {"source_hmac":H,"password":"x"*129},
    {"source_hmac":H,"password":123},
])
def test_bad_source_reference_and_password_rejected(fake,payload):
    client,calls=fake
    client.cookies.set("owner","fake-auth")
    r=client.post("/internal/finance/bahl/analyze",
                  json=payload,headers={"x-csrf-token":"FAKE_CSRF"})
    assert r.status_code==400
    assert calls==[]


def test_foreign_origin_and_missing_csrf_rejected(fake):
    client,calls=fake
    client.cookies.set("owner","fake-auth")
    a=client.post("/internal/finance/bahl/analyze",
                  json={"source_hmac":H},headers={"origin":"https://evil.invalid",
                                                   "x-csrf-token":"FAKE_CSRF"})
    b=client.post("/internal/finance/bahl/analyze",json={"source_hmac":H})
    assert a.status_code==403
    assert b.status_code==401
    assert calls==[]


def test_public_routes_not_implicitly_mounted():
    from app.preview_api import create_preview_app
    routes={r.path for r in create_preview_app().routes}
    assert "/internal/finance/bahl/analyze" not in routes
    assert "/internal/finance/bahl/status" not in routes
