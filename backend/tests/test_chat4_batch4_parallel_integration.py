"""Chat04 batch4: independent G2/P1+G3+G4 cannot combine into real access."""
import base64
from pathlib import Path
import pytest

from app.fake_credential_keyring import (
    make_fake_keyring,seal_fake_grant,FakeKeyCustodyBlocked,
)
from app.fake_oauth_ingress_review import (
    FakeIngressRequest,FakeOAuthIngressBlocked,
    plan_fake_exact_oauth_ingress,audit_current_public_nginx,
)
from app.synthetic_format_triage import (
    SyntheticFormatTriageBlocked,triage_fake_document_container,
)
from app.fake_accountant_evidence_lineage import (
    FictionalEvidence,SyntheticEvidenceBlocked,
    evaluate_fake_accountant_evidence,
)
from app.drive_cloud_owner_gateway import HOST,ORIGIN
from app.preview_api import create_preview_app

FICTITIOUS_CSV=(b"PERSONAL_CFO_SYNTHETIC_BANK_CSV_V1\n"
                 b"date,description,debit,credit,balance,reference\n"
                 b"2026-04-03,Fictional source row,1,0,0,FAKE-2\n")
KEY=lambda x:base64.urlsafe_b64encode(x*32).decode("ascii")


def enabled(monkeypatch):
    for key in ("P1K_FAKE_KEY_CUSTODY_ONLY",
                "P1L_FAKE_OAUTH_INGRESS_REVIEW_ONLY",
                "G3_FAKE_FORMAT_TRIAGE_ONLY",
                "G4_FAKE_ACCOUNTANT_EVIDENCE_ONLY"):
        monkeypatch.setenv(key,"1")
    monkeypatch.setenv("APP_DATA_MODE","synthetic")


def test_all_four_candidate_contracts_coexist_without_real_owner_data(monkeypatch):
    enabled(monkeypatch)
    ring=make_fake_keyring(active_id="fixture-key-v1",encoded_keys={
        "fixture-key-v1":KEY(b"A"),"fixture-key-v2":KEY(b"B")})
    envelope=seal_fake_grant(ring=ring,owner_hmac="a"*64,
        folder_hmac="b"*64,fictional_token="SYNTHETIC_FAKE_REFRESH_"+"X"*44)
    assert "SYNTHETIC_FAKE_REFRESH_" not in envelope
    allowed=plan_fake_exact_oauth_ingress(FakeIngressRequest(
        method="POST",path="/api/drive/oauth/start",scheme="https",host=HOST,
        origin=ORIGIN,query="",owner_session_present=True,csrf_verified=True))
    assert allowed["real_google_redirect_routed"] is False
    review=triage_fake_document_container(
        raw=FICTITIOUS_CSV,claimed_extension=".csv",
        candidate_key="pk_bank_structured_candidate_v0",
        document_kind="bank_statement",synthetic_fixture=True)
    assert review["quarantine_policy"]=="QUARANTINE_PENDING_G3"
    ledger=evaluate_fake_accountant_evidence(
        tax_year=2026,artifacts=(FictionalEvidence(
            True,"c"*64,2026,"accountant_workbook",1,None,"DRAFT"),))
    assert ledger["actual_tax_due_minor"] is None
    assert not ledger["official_fbr_filing_independently_verified"]
    nginx=(Path(__file__).parents[2]/"frontend/nginx.railway.conf").read_text()
    assert audit_current_public_nginx(nginx_source=nginx)["public_google_oauth_route_active"] is False


def test_every_candidate_independently_refuses_real_mode(monkeypatch):
    enabled(monkeypatch)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(FakeKeyCustodyBlocked):
        make_fake_keyring(active_id="fixture-key-v1",encoded_keys={
            "fixture-key-v1":KEY(b"A"),"fixture-key-v2":KEY(b"B")})
    with pytest.raises(FakeOAuthIngressBlocked):
        plan_fake_exact_oauth_ingress(FakeIngressRequest(
            method="GET",path="/api/drive/oauth/status",scheme="https",
            host=HOST,origin=None,query="",owner_session_present=True,
            csrf_verified=False))
    with pytest.raises(SyntheticFormatTriageBlocked):
        triage_fake_document_container(raw=FICTITIOUS_CSV,
            claimed_extension=".csv",candidate_key="pk_bank_structured_candidate_v0",
            document_kind="bank_statement",synthetic_fixture=True)
    with pytest.raises(SyntheticEvidenceBlocked):
        evaluate_fake_accountant_evidence(tax_year=2026,artifacts=())


def test_no_public_oauth_auth_key_recovery_or_real_document_routes():
    paths={route.path for route in create_preview_app().routes}
    for path in (
        "/api/drive/oauth/start","/api/drive/oauth/callback",
        "/api/owner/login","/api/owner/recover",
        "/api/document/import","/api/fbr/file",
    ):
        assert path not in paths
    nginx=(Path(__file__).parents[2]/"frontend/nginx.railway.conf").read_text()
    assert "location = /api/preview/status" in nginx
    assert "location /api/" not in nginx
