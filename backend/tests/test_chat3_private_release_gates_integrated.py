"""Chat 3: independent G1/G2/G3 synthetic privacy release boundary.

This integration deliberately tests that even a passing PG18 clone rehearsal,
owner recovery audit and document preflight do not authorize real owner data.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa
from app.canonical_typed_economic_postings import (
    OwnerEconomicMovement, EconomicMovementBlocked,
    record_owner_economic_proposal, inspect_synthetic_bank_transfer_pair,
)
from app.synthetic_clone_cutover_rehearsal import (
    rehearse_synthetic_clone_switch, SyntheticCutoverRehearsalBlocked,
)
from app.persisted_owner_recovery import (
    issue_persisted_synthetic_codes, RecoveryBlocked,
)
from app.private_format_release_gate import (
    inspect_private_format_release_gap, PrivateFormatCertificationBlocked,
    refuse_genuine_format_release,
)
from app.private_adapter_registry import BANK, IRIS_INCOME, IRIS_WEALTH


def test_all_release_tracks_refuse_real_mode(monkeypatch,tmp_path):
    engine=create_engine(f"sqlite:///{tmp_path/'gates-never-real.db'}")
    Base.metadata.create_all(engine)
    candidate=OwnerEconomicMovement.model_validate({
        "synthetic_fixture":True,
        "source_ref":"SYNTHETIC-UNVERIFIED-CLAIM-01",
        "account_ref":"SYNTHETIC-UNVERIFIED-CASH-01",
        "posted_on":"2025-07-15","movement_kind":"cash_movement",
        "amount_minor":1000,"direction":"increase",
        "explicit_owner_annotation":True,
    })
    monkeypatch.setenv("APP_DATA_MODE","real")
    monkeypatch.setenv("CI","true")
    monkeypatch.setenv("G1_A8_EPHEMERAL_CI_ONLY","1")
    with Session(engine) as db:
        with pytest.raises(EconomicMovementBlocked):
            record_owner_economic_proposal(db,movement=candidate)
        with pytest.raises(EconomicMovementBlocked):
            inspect_synthetic_bank_transfer_pair(
                db,debit_source_ref="SYNTHETIC-BANK-A",
                debit_row_number=1,credit_source_ref="SYNTHETIC-BANK-B",
                credit_row_number=1,explicit_owner_annotation=True,
            )
        with pytest.raises(RecoveryBlocked):
            issue_persisted_synthetic_codes(
                db,owner_ref="owner",mfa_confirmed=True,issued_epoch=1760000100)
    with pytest.raises(SyntheticCutoverRehearsalBlocked):
        rehearse_synthetic_clone_switch(
            tmp_path/"not-a-backup.tfpg",candidate_receipt={})
    with pytest.raises(PrivateFormatCertificationBlocked):
        inspect_private_format_release_gap(candidate_key=BANK.key)
    with pytest.raises(PrivateFormatCertificationBlocked):
        refuse_genuine_format_release()
    engine.dispose()


def test_no_profile_can_self_certify_real_bank_iris(monkeypatch):
    from app.private_format_release_gate import _RELEASE_CONTROLS
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    for profile in (BANK,IRIS_INCOME,IRIS_WEALTH):
        result=inspect_private_format_release_gap(
            candidate_key=profile.key, declared_controls=_RELEASE_CONTROLS,
        )
        assert result["genuine_bank_or_fbr_sources_certified"] is False
        assert result["release_blocked"] is True
        assert result["owner_source_data_imported"] is False


def test_no_live_authority_or_certification_http_route_created():
    from app.preview_api import create_preview_app
    app=create_preview_app()
    paths={r.path for r in app.routes}
    for forbidden in (
        "/api/finance/authority/cutover",
        "/api/finance/economic-proposals",
        "/api/owner/mfa/recover",
        "/api/documents/real/certify",
    ):
        assert forbidden not in paths
    from app.pg_recovery import SCHEMA_REVISION
    assert SCHEMA_REVISION=="0024_review_comments"
