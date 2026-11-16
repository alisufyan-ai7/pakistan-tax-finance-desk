"""Chat 3 combined synthetic lanes: no cross-gate real-data escape."""
import pytest
from app.g1c_balance_parity import EconomicParityBlocked, proof_from_source_rows
from app.preview_role_policy import RoleAttestationBlocked, attest_synthetic_preview_role
from app.isolated_synthetic_pdf_worker import IsolatedPdfBlocked, preview_pdf_in_bounded_process


def test_three_independent_gates_fail_closed_for_real_records(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(EconomicParityBlocked):
        proof_from_source_rows({}, {})
    with pytest.raises(RoleAttestationBlocked):
        attest_synthetic_preview_role(None)
    with pytest.raises(IsolatedPdfBlocked):
        preview_pdf_in_bounded_process(
            b"%PDF-private-data", adapter_key="synthetic_bank_pdf_v1",
            kind="bank_statement", synthetic_fixture=True,
        )


def test_integrated_artifacts_cannot_report_real_private_release(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    with pytest.raises(EconomicParityBlocked):
        proof_from_source_rows({}, {"read_only": True, "migration_performed": False})
    with pytest.raises(IsolatedPdfBlocked):
        preview_pdf_in_bounded_process(
            b"%PDF-real-like", adapter_key="unregistered_bank_v1",
            kind="bank_statement", synthetic_fixture=True,
        )
