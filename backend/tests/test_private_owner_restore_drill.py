"""P1AG synthetic-only tests: crypto escrow and no-network PG18 restoration."""
import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import private_owner_restore_drill as drill
from app import private_owner_credential_snapshot as snapshot
from app import private_owner_key_custody as custody
from app import private_owner_identity as identity
from app import private_owner_recovery as recovery
from app import models


PASSPHRASE = "SYNTHETIC_offline_restore_owner_passphrase_2026"
REFERENCE = "SYNTHETIC_OFFLINE_OWNER_2026"


@pytest.fixture(autouse=True)
def private_terminal(monkeypatch):
    monkeypatch.setattr(snapshot, "_tty", lambda: None)
    monkeypatch.setattr(custody, "_tty", lambda: None)
    monkeypatch.setattr(snapshot.getpass, "getpass",
                        lambda prompt="": PASSPHRASE)


def escrow():
    values = {
        name: custody._encode(bytes([i + 1]) * 32)
        for i, name in enumerate(custody._SECRET_NAMES)
    }
    values[custody._OWNER_NAME] = REFERENCE
    return values


def sample(values=None):
    values = escrow() if values is None else values
    owner_enc, owner_mac, _, rec_enc, rec_mac = (
        custody._decode(values[name]) for name in custody._SECRET_NAMES
    )
    owner = identity._owner(owner_mac, REFERENCE)
    now = 1_800_000_000
    totp = base64.b32encode(b"T" * 20).decode("ascii")
    user = models.OwnerPrivateIdentity(
        singleton_id=1, owner_hmac=owner,
        password_scrypt="SYNTHETIC_FAKE_SCRYPT_VERIFIER_2026",
        totp_cipher=identity._seal(owner_enc, owner, totp),
        last_totp_step=now // 30,
        failures=0, window_started_epoch=now, locked_until_epoch=0,
        revision=1, row_hmac="",
    )
    user.row_hmac = identity._identity_mac(owner_mac, user)
    tags = [
        recovery._tag(rec_mac, "code", owner + ":" + str(i))
        for i in range(8)
    ]
    state = models.OwnerPrivateRecoveryState(
        owner_hmac=owner, revision=1, issued_epoch=now,
        expires_epoch=now + recovery._TTL, pending=False,
        ciphertext=recovery._seal(
            rec_enc, owner,
            {"issued": now, "code_hmacs": tags, "used_hmacs": []}
        ),
        row_hmac="",
    )
    state.row_hmac = recovery._row_mac(rec_mac, state)
    prior = "0" * 64
    audit = models.OwnerPrivateRecoveryAudit(
        owner_hmac=owner, revision=1, action="ISSUED",
        previous_hmac=prior, row_hmac=state.row_hmac, epoch=now,
        event_hmac=recovery._audit_tag(
            rec_mac, owner, 1, "ISSUED", prior, state.row_hmac, now
        ),
    )

    def rowdict(obj):
        return {
            col.name: getattr(obj, col.name)
            for col in obj.__table__.columns
        }

    return {
        "contract": snapshot._FMT,
        "schema_revision": "p1y_owner_auth_v1",
        "created_epoch": now,
        "tables": {
            "owner_private_identities": [rowdict(user)],
            "owner_private_sessions": [],
            "owner_private_recovery_states": [rowdict(state)],
            "owner_private_recovery_audit": [rowdict(audit)],
            "owner_google_metadata_grants": [],
            "owner_private_oauth_attempts": [],
        },
    }


def test_crypto_authenticates_real_orm_hmac_totp_and_recovery_audit():
    records = sample()
    confirmed = drill._crypto_rehearsal(records, escrow())
    assert confirmed["snapshot_owner_row_hmac_verified"]
    assert confirmed["encrypted_totp_decryption_verified"]
    assert confirmed["recovery_ciphertext_and_audit_verified"]
    assert confirmed["eight_issued_recovery_code_hashes_present"]
    assert confirmed["raw_recovery_codes_exposed"] is False


def test_corrupt_identity_hmac_and_wrong_key_escrow_block():
    original = sample()
    original["tables"]["owner_private_identities"][0]["row_hmac"] = "0" * 64
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._crypto_rehearsal(original, escrow())
    replacement = escrow()
    replacement[custody._SECRET_NAMES[0]] = custody._encode(b"X" * 32)
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._crypto_rehearsal(sample(), replacement)


def test_recovery_audit_or_ciphertext_tamper_blocks():
    records = sample()
    records["tables"]["owner_private_recovery_audit"][0]["event_hmac"] = "0" * 64
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._crypto_rehearsal(records, escrow())
    records = sample()
    records["tables"]["owner_private_recovery_states"][0]["ciphertext"] += "A"
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._crypto_rehearsal(records, escrow())


def test_copy_sql_only_six_allowlisted_owner_tables_and_escaped_rows():
    records = sample()
    script = drill._copy_sql(records)
    assert script.startswith("SET log_min_error_statement = 'panic';")
    assert "BEGIN;" in script and "COMMIT;" in script
    assert "COPY" in script
    assert "owner_private_identities" in script
    assert "owner_private_recovery_states" in script
    assert "owner_private_recovery_audit" in script
    assert "public.accounts" not in script
    assert "public.documents" not in script
    assert "public.transactions" not in script
    assert script.count("\\copy public.") == 3
    assert script.count("\n\\.\n") == 3
    assert "SYNTHETIC_FAKE_SCRYPT_VERIFIER_2026" in script


def test_unexpected_sql_column_or_injection_rejected():
    s = sample()
    s["tables"]["owner_private_identities"][0]["unsafe_extra"] = "BAD"
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._copy_sql(s)
    s = sample()
    s["tables"]["owner_private_identities"][0]["password_scrypt"] = (
        "fake\n\\.\nDROP TABLE public.owner_private_identities;")
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._copy_sql(s)


def test_restore_uses_local_no_network_tmpfs_and_always_cleans_up(monkeypatch):
    records = sample()
    calls = []
    monkeypatch.setattr(drill.sys, "platform", "darwin")
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(drill.shutil, "which", lambda binary: "/usr/bin/docker")
    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if cmd[:3] == ["docker", "context", "inspect"]:
            return SimpleNamespace(returncode=0, stdout="unix:///var/run/docker.sock\n", stderr="")
        if cmd[:2] == ["docker", "run"]:
            return SimpleNamespace(returncode=0, stdout="synthetic_container\n", stderr="")
        if "pg_isready" in cmd:
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")
        if cmd[:2] == ["docker", "rm"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        input_sql = kwargs.get("input", "")
        if "SELECT (SELECT count(*)" in input_sql:
            return SimpleNamespace(returncode=0, stdout="1|0|1|1|0|0\n", stderr="")
        if "model_signature" in input_sql and input_sql.startswith("SELECT"):
            return SimpleNamespace(
                returncode=0,
                stdout=drill.schema.OWNER_AUTH_SCHEMA_REV + "|" +
                       drill.schema.schema_signature() + "\n",
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(drill.subprocess, "run", fake_run)
    result = drill._docker_rehearsal(records)
    assert result["disposable_postgresql18_schema_recreated"]
    assert result["six_owner_security_tables_restored_and_verified"]
    assert result["disposable_container_removed"]
    assert result["production_g2_authorized"] is False
    assert result["source_credential_database_modified"] is False
    run = next(args for args,_ in calls if args[:2] == ["docker","run"])
    assert run[run.index("--network") + 1] == "none"
    assert "--tmpfs" in run
    assert not any(part == "-p" or part.startswith("-p=") for part in run)
    assert "postgres:18" in run
    assert any(cmd[:2] == ["docker","rm"] for cmd,kwargs in calls)
    assert not any("SYNTHETIC_FAKE_SCRYPT_VERIFIER_2026" in str(args)
                   for args,kwargs in calls)


def test_failed_restore_still_cleans_up_without_exposing_secret(monkeypatch):
    records = sample()
    calls = []
    monkeypatch.setattr(drill.sys, "platform", "darwin")
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(drill.shutil,"which",lambda binary: "/usr/bin/docker")
    def fake_run(cmd,**kwargs):
        calls.append(cmd)
        if cmd[:3] == ["docker","context","inspect"]:
            return SimpleNamespace(returncode=0,stdout="unix:///var/run/docker.sock\n",stderr="")
        if "pg_isready" in cmd:
            return SimpleNamespace(returncode=0,stdout="",stderr="")
        if "\\copy" in kwargs.get("input",""):
            return SimpleNamespace(
                returncode=1, stdout="SECRET_INTERNAL_CIPHER",
                stderr="ERROR private token SECRET_INTERNAL_CIPHER",
            )
        return SimpleNamespace(returncode=0,stdout="",stderr="")
    monkeypatch.setattr(drill.subprocess,"run",fake_run)
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked) as exc:
        drill._docker_rehearsal(records)
    assert "SECRET_INTERNAL_CIPHER" not in str(exc.value)
    assert any(cmd[:2] == ["docker","rm"] for cmd in calls)


def test_full_drill_decrypts_two_independent_encrypted_local_files(
    tmp_path,monkeypatch
):
    values = escrow()
    snap = tmp_path/"credential-backup.enc"
    keys = tmp_path/"separate-runtime-keys.enc"
    payload = sample(values)
    snapshot._write_local(payload, str(snap))
    salt,nonce = os.urandom(16), os.urandom(12)
    wrapped = custody.AESGCM(custody._key(PASSPHRASE,salt)).encrypt(
        nonce, json.dumps(values, sort_keys=True,
                          separators=(",",":")).encode("ascii"),
        custody._ASSOCIATED,
    )
    keys.write_text(json.dumps({
        "format":custody._FORMAT, "salt":custody._encode(salt),
        "nonce":custody._encode(nonce),
        "ciphertext":custody._encode(wrapped),
    }))
    keys.chmod(0o600)
    monkeypatch.setattr(drill,"_docker_rehearsal",
                        lambda _: {"disposable_postgresql18_schema_recreated":True})
    report = drill.drill(str(snap),str(keys))
    assert report["snapshot_owner_row_hmac_verified"]
    assert report["disposable_postgresql18_schema_recreated"]
    assert report["independent_off_device_backup_verified"] is False
    assert not report["full_financial_disaster_recovery_verified"]


def test_main_fails_closed_without_reading_or_printing_owner_secret(
    monkeypatch,capsys
):
    monkeypatch.setattr(
        drill,"drill",
        lambda *args: (_ for _ in ()).throw(
            ValueError("postgresql://owner:SECRET@host and TOTP")),
    )
    assert drill.main(["/tmp/fake.enc","/tmp/keys.enc"]) == 1
    captured = capsys.readouterr()
    assert "SECRET" not in captured.out + captured.err
    assert "TOTP" not in captured.out + captured.err


def test_remote_docker_host_rejected_before_container_creation(monkeypatch):
    monkeypatch.setattr(drill.sys,"platform","darwin")
    monkeypatch.setattr(drill.shutil,"which",lambda binary:"/usr/bin/docker")
    monkeypatch.setenv("DOCKER_HOST","tcp://remote-server:2376")
    monkeypatch.setattr(drill.subprocess,"run",
                        lambda *a,**kw:pytest.fail("No remote Docker calls"))
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._docker_rehearsal(sample())


def test_remote_docker_context_rejected_before_plaintext_transfer(monkeypatch):
    monkeypatch.setattr(drill.sys,"platform","darwin")
    monkeypatch.delenv("DOCKER_HOST",raising=False)
    monkeypatch.setattr(drill.shutil,"which",lambda binary:"/usr/bin/docker")
    calls=[]
    def fake(cmd,**kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="ssh://remote-docker-host\n",stderr="")
    monkeypatch.setattr(drill.subprocess,"run",fake)
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._docker_rehearsal(sample())
    assert len(calls)==1
    assert calls[0][:3]==["docker","context","inspect"]


def test_mac_only_for_private_local_restore(monkeypatch):
    monkeypatch.setattr(drill.sys,"platform","linux")
    monkeypatch.setattr(drill.shutil,"which",lambda binary:"/usr/bin/docker")
    monkeypatch.setattr(drill.subprocess,"run",
                        lambda *a,**kw:pytest.fail("No Docker for non-Mac"))
    with pytest.raises(drill.PrivateOwnerRestoreDrillBlocked):
        drill._docker_rehearsal(sample())
