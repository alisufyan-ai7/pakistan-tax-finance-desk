"""Integrated Chat 3 G1-G2-G3 deny-real-mode and no-production-write acceptance."""
from io import BytesIO
import base64

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa: F401
from app.canonical_journal import CanonicalJournalBlocked, record_synthetic_journal_batch
from app.canonical_bank_posting import accept_recorded_synthetic_bank
from app.owner_recovery_codes import RecoveryBlocked, issue_recovery_bundle
from app.synthetic_preview_role_bootstrap import (
    PreviewRoleBootstrapBlocked, provision_synthetic_preview_role,
)
from app.docker_document_sandbox import DocumentSandboxBlocked, inspect_in_docker, docker_args


def test_all_three_parallel_gates_deny_real_mode_without_escaping(monkeypatch,tmp_path):
    engine=create_engine(f"sqlite:///{tmp_path / 'must-stay-empty.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with Session(engine) as db:
        with pytest.raises(CanonicalJournalBlocked):
            record_synthetic_journal_batch(db, ())
        with pytest.raises(CanonicalJournalBlocked):
            accept_recorded_synthetic_bank(db,source_ref="SYNTHETIC-FAKE-ONLY")
    with pytest.raises(RecoveryBlocked):
        issue_recovery_bundle(owner_ref="owner",mfa_confirmed=True,issued_epoch=10)
    with pytest.raises(PreviewRoleBootstrapBlocked):
        provision_synthetic_preview_role(None,password="synthetic_ci_only_credential_123456")
    with pytest.raises(DocumentSandboxBlocked):
        inspect_in_docker(b"%PDF-" + b"x"*100,
            image="local/worker@sha256:"+"f"*64,
            adapter_key="synthetic_bank_pdf_v1", kind="bank_statement",
            synthetic_fixture=True)
    engine.dispose()


def test_docker_policy_is_not_real_document_authorization(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.delenv("DOCKER_HOST",raising=False)
    monkeypatch.delenv("DOCKER_CONTEXT",raising=False)
    image="local/personal-cfo-document-worker@sha256:"+"a"*64
    args=docker_args(image)
    assert "--network=none" in args and "--read-only" in args
    assert "--pull=never" in args and "--cap-drop=ALL" in args
    # A secure command-line policy is NOT real host sandbox attestation.
    assert args[-1]==image
