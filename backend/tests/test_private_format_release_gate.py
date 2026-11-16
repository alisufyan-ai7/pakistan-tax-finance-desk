"""G3: private genuine-format certification cannot be self-granted in CI."""
from importlib.metadata import version

import pytest

from app.private_adapter_registry import BANK, IRIS_INCOME, IRIS_WEALTH
from app.private_format_release_gate import (
    _RELEASE_CONTROLS, inspect_private_format_release_gap,
    refuse_genuine_format_release, PrivateFormatCertificationBlocked,
)


def test_pdf_security_dependency_has_known_fixed_minor_range():
    # This is a MINIMUM patch-level guard, not a complete vulnerability audit.
    numbers=tuple(int(x) for x in version("pypdf").split(".")[:3])
    assert (6,18,1) <= numbers < (7,0,0)


@pytest.mark.parametrize("profile",[BANK,IRIS_INCOME,IRIS_WEALTH])
def test_positive_self_attestation_cannot_certify_private_layout(profile,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    report=inspect_private_format_release_gap(
        candidate_key=profile.key,declared_controls=_RELEASE_CONTROLS)
    assert report["self_declared_control_count"]==len(_RELEASE_CONTROLS)
    assert report["missing_private_controls"]==()
    assert report["genuine_bank_or_fbr_sources_certified"] is False
    assert report["private_environment_independently_verified"] is False
    assert report["release_blocked"] is True
    with pytest.raises(PrivateFormatCertificationBlocked):
        refuse_genuine_format_release(profile=profile)


@pytest.mark.parametrize("profile",[BANK,IRIS_INCOME,IRIS_WEALTH])
def test_private_review_controls_missing_without_approval(profile,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    gap=inspect_private_format_release_gap(candidate_key=profile.key)
    assert len(gap["missing_private_controls"])==len(_RELEASE_CONTROLS)
    assert not gap["owner_source_data_imported"]


def test_no_fake_control_or_genuine_mode_can_enable_import(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    with pytest.raises(PrivateFormatCertificationBlocked):
        inspect_private_format_release_gap(
            candidate_key=BANK.key,declared_controls=("official_verified",))
    with pytest.raises(PrivateFormatCertificationBlocked):
        inspect_private_format_release_gap(
            candidate_key=BANK.key,
            declared_controls=("independent_owner_authorized_release",)*2)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(PrivateFormatCertificationBlocked):
        inspect_private_format_release_gap(candidate_key=BANK.key)
