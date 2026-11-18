"""P1AR: all private Google/G2 keys prepared once without browser secret output."""
import base64
import sys as actual_sys
import hmac
from hashlib import sha256
from types import SimpleNamespace

import pytest

from app import private_owner_google_keys_prepare_cli as prep

CLIENT="717001562537-b5ot38lac68nu4atlt3grvatg92p3ql4.apps.googleusercontent.com"
FOLDER="SYNTHETIC_NOT_REAL_P1AR_GOOGLE_FOLDER_2026"


def baseline(monkeypatch, *, backend=None, frontend=None):
    monkeypatch.setattr(prep,"sys", SimpleNamespace(
        platform="darwin",
        stdin=SimpleNamespace(isatty=lambda: True),
        stdout=SimpleNamespace(isatty=lambda: True),
        stderr=actual_sys.stderr,
    ))
    monkeypatch.setattr(prep.shutil,"which",
                        lambda n: "/usr/local/bin/railway" if n=="railway" else None)
    monkeypatch.setattr("builtins.input",lambda _: prep.APPROVAL)
    backend=backend or {
        "P1B_GOOGLE_CLIENT_ID": CLIENT,
        "P1B_GOOGLE_REDIRECT_URI": prep._CALLBACK,
        "P1B_GOOGLE_FOLDER_ID": FOLDER,
        "PREVIEW_INTERNAL_TOKEN":"SYNTHETIC_NEVER_REAL_PREVIEW_KEY",
    }
    frontend=frontend or {"PREVIEW_INTERNAL_TOKEN": "SYNTHETIC_INDEPENDENT_KEY"}
    seen=[]
    values={prep.BACKEND:dict(backend),prep.FRONTEND:dict(frontend)}
    def fake_run(command,**kw):
        seen.append((list(command),dict(kw)))
        assert "--skip-deploys" in command or "--kv" in command
        if command[1:4]==["variable","list","--kv"]:
            service=command[command.index("--service")+1]
            return SimpleNamespace(returncode=0,
                stdout="".join(f"{k}={v}\n" for k,v in values[service].items()),
                stderr="")
        if command[1:3]==["variable","set"]:
            service=command[command.index("--service")+1]
            assert "input" in kw
            values[service][command[3]]=kw["input"]
            return SimpleNamespace(returncode=0,stdout="Secret value must not be printed",
                                   stderr="Possible provider failure secret omitted")
        raise AssertionError("unexpected command")
    monkeypatch.setattr(prep.subprocess,"run",fake_run)
    return seen,values


def fixed_keys(monkeypatch):
    values=iter(bytes([n])*32 for n in range(1,7))
    monkeypatch.setattr(prep,"_new_key",lambda: next(values))
    monkeypatch.setattr(prep.secrets,"token_urlsafe",lambda n: "G"*86)


def test_entire_private_railway_connector_prepared_without_deploy_or_key_output(
    monkeypatch,capsys,
):
    seen,values=baseline(monkeypatch)
    fixed_keys(monkeypatch)
    result=prep.prepare()
    assert result["new_private_key_domains_prepared"]==6
    assert result["railway_deployments_triggered"] is False
    assert result["google_client_secret_staged_patch_applied"] is False
    assert result["public_owner_or_google_routes_activated"] is False
    assert result["original_document_bytes_accessed"] is False
    assert result["private_secret_values_printed"] is False
    assert result["owner_identity_and_recovery_keys_unchanged"] is True
    backend,frontend=values[prep.BACKEND],values[prep.FRONTEND]
    assert backend["P1Q_PRIVATE_GATEWAY_SHARED_TOKEN"]=="G"*86
    assert frontend["P1Q_PRIVATE_GATEWAY_SHARED_TOKEN"]=="G"*86
    assert backend["P1B_GOOGLE_FOLDER_ID"]==FOLDER
    assert frontend.get("P1B_GOOGLE_FOLDER_ID") is None
    assert backend["P1B_PRIVATE_OAUTH_CONTRACT_ONLY"]=="1"
    assert backend["P1D_RAILWAY_CALLBACK_CONTRACT_ONLY"]=="1"
    expected_tag=hmac.new(bytes([6])*32,
        ("personal-cfo:drive-inbox:v1:folder:"+FOLDER).encode(),
        sha256).hexdigest()
    assert backend["DRIVE_ALLOWED_FOLDER_HMAC"]==expected_tag
    for name,byte in [
        ("P1R_OAUTH_STATE_ENCRYPTION_KEY",1),
        ("P1R_OAUTH_STATE_HMAC_KEY",2),
        ("P1M_METADATA_ROW_HMAC_KEY",5),
        ("DRIVE_INDEX_HMAC_KEY",6),
    ]:
        assert base64.urlsafe_b64decode(backend[name])==bytes([byte])*32
    assert "cfo-google-key-v1" in backend["P1M_METADATA_ENCRYPTION_KEYS_JSON"]
    assert backend["P1M_METADATA_ACTIVE_KEY_ID"]=="cfo-google-key-v1"
    assert len(seen)==13  # two nonprinting reads, nine backend + two gateway writes
    for command,kwargs in seen:
        assert "--project" in command and prep.PROJECT in command
        assert "--environment" in command and prep.ENV in command
        if "set" in command:
            assert "--stdin" in command
            assert "--skip-deploys" in command
            assert kwargs["capture_output"] and kwargs["text"]
            assert kwargs["check"] is False
            assert FOLDER not in " ".join(command)
            assert "G"*30 not in " ".join(command)
            assert "P1C_GOOGLE_CLIENT_SECRET" not in command
            assert "P1AK_OWNER_INGRESS_ENABLED" not in command
    stdout=capsys.readouterr().out
    for secret in (FOLDER,"G"*86,backend["P1M_METADATA_ENCRYPTION_KEYS_JSON"],
                   backend["DRIVE_INDEX_HMAC_KEY"]):
        assert secret not in stdout
    assert "Secret value must not be printed" not in stdout
    assert "Approval phrase: " + prep.APPROVAL in stdout


@pytest.mark.parametrize("case",[
    "wrong_callback","bad_folder","active_backend","active_frontend",
    "no_mac","no_tty","no_cli","not_approved",
])
def test_refuse_before_any_key_write(monkeypatch,case):
    backend={"P1B_GOOGLE_CLIENT_ID":CLIENT,
             "P1B_GOOGLE_REDIRECT_URI":prep._CALLBACK,
             "P1B_GOOGLE_FOLDER_ID":FOLDER}
    frontend={"PREVIEW_INTERNAL_TOKEN":"F"*48}
    if case=="wrong_callback":
        backend["P1B_GOOGLE_REDIRECT_URI"]="https://attacker.invalid/callback"
    if case=="bad_folder":
        backend["P1B_GOOGLE_FOLDER_ID"]="x"
    if case=="active_backend":
        backend["P1AN_GOOGLE_METADATA_RUNTIME"]="1"
    if case=="active_frontend":
        frontend["P1AK_OWNER_INGRESS_ENABLED"]="1"
    seen,_=baseline(monkeypatch,backend=backend,frontend=frontend)
    if case=="no_mac":
        prep.sys.platform="linux"
    if case=="no_tty":
        prep.sys.stdin.isatty=lambda: False
    if case=="no_cli":
        prep.shutil.which=lambda _: None
    if case=="not_approved":
        monkeypatch.setattr("builtins.input",lambda _: "no")
    monkeypatch.setattr(prep,"_new_key",lambda: (_ for _ in ()).throw(
        AssertionError("No key generation before valid config")))
    with pytest.raises(prep.PrivateGoogleKeyPreparationBlocked):
        prep.prepare()
    assert not any("set" in command for command,_ in seen)


def test_existing_identical_gateway_is_preserved(monkeypatch):
    backend={
        "P1B_GOOGLE_CLIENT_ID":CLIENT,
        "P1B_GOOGLE_REDIRECT_URI":prep._CALLBACK,
        "P1B_GOOGLE_FOLDER_ID":FOLDER,
        "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN":"E"*86,
    }
    frontend={"P1Q_PRIVATE_GATEWAY_SHARED_TOKEN":"E"*86}
    seen,values=baseline(monkeypatch,backend=backend,frontend=frontend)
    fixed_keys(monkeypatch)
    result=prep.prepare()
    assert result["gateway_proof_prepared_for_both_services"]
    assert values[prep.BACKEND]["P1Q_PRIVATE_GATEWAY_SHARED_TOKEN"]=="E"*86
    assert values[prep.FRONTEND]["P1Q_PRIVATE_GATEWAY_SHARED_TOKEN"]=="E"*86
    assert not any(command[3]=="P1Q_PRIVATE_GATEWAY_SHARED_TOKEN"
                   for command,_ in seen if "set" in command)


def test_incomplete_provider_write_does_not_claim_public_activation(monkeypatch,capsys):
    baseline(monkeypatch)
    fixed_keys(monkeypatch)
    original=prep.subprocess.run
    attempts=0
    def fails_midway(cmd,**kw):
        nonlocal attempts
        if "set" in cmd:
            attempts+=1
            if attempts==3:
                return SimpleNamespace(returncode=1,stdout="SECRET_WOULD_LEAK",
                                       stderr="FOLDER_SHOULD_NEVER_LOG")
        return original(cmd,**kw)
    monkeypatch.setattr(prep.subprocess,"run",fails_midway)
    assert prep.main()==1
    captured=capsys.readouterr()
    assert "SECRET_WOULD_LEAK" not in captured.err+captured.out
    assert "FOLDER_SHOULD_NEVER_LOG" not in captured.err+captured.out
    assert "public login and Google consent remain disabled" in captured.err
    assert attempts==3
