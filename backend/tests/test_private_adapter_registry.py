"""G3 real-format roadmap contract never certifies actual source from assertions."""
import pytest

from app.private_adapter_registry import (
    GenuineFormatBlocked, BANK, IRIS_INCOME, IRIS_WEALTH,
    genuine_format_candidate_manifest, inspect_candidate_evidence,
)


def test_registry_requires_explicit_private_acceptance_and_no_authentic_samples():
    manifest=genuine_format_candidate_manifest()
    assert manifest["certified_real_adapters"]==0
    assert len(manifest["candidate_layouts"])==3
    for profile in (BANK, IRIS_INCOME, IRIS_WEALTH):
        assert not profile.real_source_certified
        assert "authorized_owner_private_sample_acceptance" in profile.required_private_evidence


def test_even_declaring_all_checks_does_not_certify_real_source(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    info=inspect_candidate_evidence(
        key=BANK.key,kind=BANK.kind,extension=".pdf",synthetic_fixture=True,
        declared_steps=BANK.required_private_evidence,
    )
    assert info["declared_step_count"]==len(BANK.required_private_evidence)
    assert info["missing_private_acceptance_steps"]==[]
    assert info["certified_real_adapter"] is False
    assert info["private_evidence_independently_verified"] is False
    assert info["actual_bank_or_fbr_data_imported"] is False


@pytest.mark.parametrize("profile", [BANK, IRIS_INCOME, IRIS_WEALTH])
def test_missing_real_provenance_visible_without_source_data(profile,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    info=inspect_candidate_evidence(
        key=profile.key,kind=profile.kind,
        extension=profile.extensions[0],synthetic_fixture=True)
    assert "encrypted_immutable_original_vault_verified" in info["missing_private_acceptance_steps"]
    assert info["real_data_authorized"] is False


def test_wrong_bank_iris_extension_and_unapproved_acceptance_rejected(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    for opts in [
        {"key":"unknown"},{"kind":"iris_income_return"},
        {"extension":".exe"},{"declared_steps":("certified_real_adapter",)},
        {"declared_steps":("bounded_size_and_malware_checks",)*2},
        {"synthetic_fixture":False},
    ]:
        kwargs=dict(key=BANK.key,kind=BANK.kind,extension=".xlsx",synthetic_fixture=True)
        kwargs.update(opts)
        with pytest.raises(GenuineFormatBlocked):
            inspect_candidate_evidence(**kwargs)


def test_real_mode_never_uses_public_candidate_registry_to_import(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(GenuineFormatBlocked):
        inspect_candidate_evidence(
            key=BANK.key,kind=BANK.kind,extension=".csv",synthetic_fixture=True)
