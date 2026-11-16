"""G1 A8 cloned rehearsal refuses fake, live, missing, or tampered backups."""
from pathlib import Path

import pytest

from app.synthetic_clone_cutover_rehearsal import (
    SyntheticCutoverRehearsalBlocked, rehearse_synthetic_clone_switch,
)


def _fake_receipt():
    return {
        "synthetic_only": True, "independent_restore_verified": True,
        "full_source_row_parity_verified": True,
        "original_database_untouched": True,
        "candidate_on_restored_clone_only": True,
        "legacy_plaintext_still_present": True,
        "active_ledger_cutover": False,
        "encrypted_snapshot_sha256": "0"*64,
    }


def test_real_mode_never_attempts_cutover(monkeypatch,tmp_path):
    monkeypatch.setenv("CI","true")
    monkeypatch.setenv("G1_A8_EPHEMERAL_CI_ONLY","1")
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(SyntheticCutoverRehearsalBlocked,match="Only explicit"):
        rehearse_synthetic_clone_switch(tmp_path/"does-not-exist",candidate_receipt=_fake_receipt())


@pytest.mark.parametrize("env,value",[
    ("CI","false"),("G1_A8_EPHEMERAL_CI_ONLY","0"),("APP_DATA_MODE","real")
])
def test_ephemeral_environment_gate_required(monkeypatch,tmp_path,env,value):
    monkeypatch.setenv("CI","true")
    monkeypatch.setenv("G1_A8_EPHEMERAL_CI_ONLY","1")
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv(env,value)
    with pytest.raises(SyntheticCutoverRehearsalBlocked,match="Only explicit"):
        rehearse_synthetic_clone_switch(tmp_path/"not-present",candidate_receipt=_fake_receipt())


def test_fake_receipt_and_wrong_snapshot_never_open_pg(monkeypatch,tmp_path):
    monkeypatch.setenv("CI","true")
    monkeypatch.setenv("G1_A8_EPHEMERAL_CI_ONLY","1")
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    file=tmp_path/"fake.tfpg"
    file.write_bytes(b"FAKE-NEVER-A-SNAPSHOT"*4)
    with pytest.raises(SyntheticCutoverRehearsalBlocked,match="changed"):
        rehearse_synthetic_clone_switch(file,candidate_receipt=_fake_receipt())
    false_receipt={**_fake_receipt(),"independent_restore_verified":False}
    with pytest.raises(SyntheticCutoverRehearsalBlocked,match="Missing authenticated"):
        rehearse_synthetic_clone_switch(file,candidate_receipt=false_receipt)


@pytest.mark.parametrize("phase",[
    "incorrect","preflight","on_production","after_retire"
])
def test_no_unknown_failure_injection_phase(monkeypatch,tmp_path,phase):
    monkeypatch.setenv("CI","true")
    monkeypatch.setenv("G1_A8_EPHEMERAL_CI_ONLY","1")
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    with pytest.raises(SyntheticCutoverRehearsalBlocked,match="Unknown"):
        rehearse_synthetic_clone_switch(tmp_path/"missing.tfpg",
            candidate_receipt=_fake_receipt(),inject_failure_at=phase)
