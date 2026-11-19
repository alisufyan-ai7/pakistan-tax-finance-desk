"""Chat 3 A7/A8 G2/G3 combined safety: public synthetic system NEVER live finance.

Use no account records, passwords, real bank documents or external resources.
"""
import pytest
from sqlalchemy import create_engine

from app.db import Base
from app import models  # noqa: F401
from app.pg_recovery import SCHEMA_REVISION
from app.ledger_crypto import ENCRYPTED_COLUMNS
from app.canonical_economic_graph import (
    analyze_synthetic_economic_graph, CanonicalGraphBlocked,
)
from app.canonical_cutover_policy import (
    inspect_synthetic_cutover_readiness, CutoverBlocked,
    refuse_authoritative_cutover,
)
from app.legacy_retirement_preflight import (
    inspect_restored_legacy_schema, LegacyRetirementBlocked,
)
from app.persisted_owner_recovery import (
    issue_persisted_synthetic_codes, RecoveryBlocked,
)
from app.auth_mfa import claim_synthetic_totp_step
from app.docker_document_sandbox import (
    inspect_in_docker, DocumentSandboxBlocked,
)
from app.private_adapter_registry import (
    inspect_candidate_evidence, GenuineFormatBlocked,
)


def test_integrated_all_gates_fail_closed_in_real_data_mode(monkeypatch,tmp_path):
    monkeypatch.setenv("APP_DATA_MODE","real")
    engine=create_engine(f"sqlite:///{tmp_path / 'fake-refused.db'}")
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        with pytest.raises(CanonicalGraphBlocked):
            analyze_synthetic_economic_graph(db)
        with pytest.raises(RecoveryBlocked):
            issue_persisted_synthetic_codes(db,owner_ref="owner",
                mfa_confirmed=True,issued_epoch=1760000000)
        assert claim_synthetic_totp_step(db,100) is False
    with pytest.raises(CutoverBlocked):
        inspect_synthetic_cutover_readiness(
            source_report={},graph_report={},backup_report={},restore_report={})
    with pytest.raises(CutoverBlocked):
        refuse_authoritative_cutover()
    with pytest.raises(LegacyRetirementBlocked):
        inspect_restored_legacy_schema(engine)
    with pytest.raises(DocumentSandboxBlocked):
        inspect_in_docker(b"%PDF-"+b"x"*100,image="local/demo@sha256:"+"a"*64,
            adapter_key="synthetic_bank_pdf_v1",kind="bank_statement",
            synthetic_fixture=True)
    with pytest.raises(GenuineFormatBlocked):
        inspect_candidate_evidence(
            key="pk_bank_structured_candidate_v0",kind="bank_statement",
            extension=".csv",synthetic_fixture=True)
    engine.dispose()


def test_all_known_sensitive_storage_registered_and_recovery_schema_additive():
    assert SCHEMA_REVISION == "0023_drive_revision"
    assert "canonical_journal_entries" in Base.metadata.tables
    assert "owner_recovery_states" in Base.metadata.tables
    assert "owner_recovery_audit" in Base.metadata.tables
    assert ENCRYPTED_COLUMNS["canonical_journal_entries"]==("payload_json",)
    assert ENCRYPTED_COLUMNS["owner_recovery_states"]==("bundle_json",)
    assert ENCRYPTED_COLUMNS["owner_recovery_audit"]==("detail_json",)


def test_no_new_public_finance_or_recovery_endpoint():
    from app.preview_api import create_preview_app
    app=create_preview_app()
    urls={r.path for r in app.routes}
    assert "/healthz" in urls
    assert "/internal/preview/status" in urls
    assert "/api/owner/recovery" not in urls
    assert "/api/finance/canonical" not in urls
    assert "/api/documents/real" not in urls
    assert "/docs" not in urls
    assert "/openapi.json" not in urls
