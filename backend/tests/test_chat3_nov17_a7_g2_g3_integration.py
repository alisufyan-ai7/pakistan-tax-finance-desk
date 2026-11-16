"""Chat 3 November continuation: all new G1/G2/G3 lanes remain real-mode denied.

These tests are separate from each independently verified feature's own tests.
No uploaded records, real owner tokens or Railway endpoints are exercised.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa
from app.canonical_bank_classification import (
    BankCandidate,ClassificationBlocked,annotate_synthetic_bank_candidate,
    reverse_synthetic_bank_candidate,
)
from app.canonical_economic_graph import (
    CanonicalGraphBlocked,analyze_synthetic_economic_graph,
)
from app.persisted_owner_recovery import (
    RecoveryBlocked,issue_persisted_synthetic_codes,consume_persisted_synthetic_code,
)
from app.synthetic_document_threat_preflight import (
    SyntheticThreatBlocked,inspect_synthetic_pdf_threats,
    inspect_synthetic_ooxml_threats,
)
from app.canonical_cutover_policy import CutoverBlocked,refuse_authoritative_cutover


def test_g1_g2_g3_new_code_does_not_enable_real_financial_mode(tmp_path,monkeypatch):
    engine=create_engine(f"sqlite:///{tmp_path / 'integration-must-be-empty.db'}")
    Base.metadata.create_all(engine)
    annotation=BankCandidate.model_validate({
        "synthetic_fixture":True,"source_ref":"SYNTHETIC-NO-OWNER-DATA",
        "row_number":1,"candidate":"income_candidate",
        "explicit_owner_annotation":True,
    })
    monkeypatch.setenv("APP_DATA_MODE","real")
    with Session(engine) as db:
        with pytest.raises(ClassificationBlocked):
            annotate_synthetic_bank_candidate(db,annotation=annotation)
        with pytest.raises(ClassificationBlocked):
            reverse_synthetic_bank_candidate(
                db,source_ref=annotation.source_ref,row_number=1,
                explicit_correction=True)
        with pytest.raises(CanonicalGraphBlocked):
            analyze_synthetic_economic_graph(db)
        with pytest.raises(RecoveryBlocked):
            issue_persisted_synthetic_codes(
                db,owner_ref="owner",mfa_confirmed=True,issued_epoch=1760000100)
        with pytest.raises(RecoveryBlocked):
            consume_persisted_synthetic_code(
                db,owner_ref="owner",presented_code="ABCD-"*7+"ABCD",
                password_confirmed=True,now_epoch=1760000101)
    with pytest.raises(CutoverBlocked):
        refuse_authoritative_cutover()
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_pdf_threats(b"%PDF-1.4\n"+b"x"*90,
                                      synthetic_fixture=True)
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_ooxml_threats(b"PK\x03\x04"+b"x"*100,
                                        synthetic_fixture=True)
    engine.dispose()


def test_synthetic_structural_preflight_never_claims_private_approval(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    report=inspect_synthetic_pdf_threats(
        b"%PDF-1.4\n"+b"synthetic-only-text\n"*6,
        synthetic_fixture=True,
    )
    assert report["genuine_source_certified"] is False
    assert report["private_malware_scan_passed"] is False
    assert report["import_performed"] is False


def test_new_sensitive_finance_and_recovery_modules_have_no_public_routes():
    from app.preview_api import create_preview_app
    app=create_preview_app()
    routes={route.path for route in app.routes}
    for path in (
        "/api/finance/canonical/classify",
        "/api/finance/canonical/reverse",
        "/api/owner/recovery",
        "/api/documents/real",
    ):
        assert path not in routes
