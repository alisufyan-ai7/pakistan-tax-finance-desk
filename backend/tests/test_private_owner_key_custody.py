"""P1Z synthetic-only local escrow security and fail-closed tests."""
import json
import os
import stat
from types import SimpleNamespace

import pytest

from app import private_owner_key_custody as custody


REAL_TTY_GUARD = custody._tty


@pytest.fixture(autouse=True)
def terminal(monkeypatch):
    # Test the user interaction with explicit synthetic TTY authorization.
    # Pytest capture owns sys.stdout, so monkeypatching sys.stdout does not
    # survive capture switching between test and fixture setup.
    monkeypatch.setattr(custody,"_tty",lambda:None)
    answers=iter(["SYNTHETIC owner escrow long offline passphrase 2026"]*20)
    monkeypatch.setattr(custody.getpass,"getpass",lambda prompt="":next(answers))


def test_encrypted_owner_keys_are_distinct_256_bit_and_never_written_plain(tmp_path):
    path=tmp_path/"owner-keys.enc"
    report=custody.create(str(path))
    assert report["encrypted_file_created"]
    assert report["distinct_owner_runtime_keys"]==5
    assert not report["railway_variables_configured"]
    assert stat.S_IMODE(path.stat().st_mode)==0o600
    raw=path.read_bytes()
    data=json.loads(raw)
    assert set(data)=={"format","salt","nonce","ciphertext"}
    assert b"P1N_OWNER_ENCRYPTION_KEY" not in raw
    assert b"P1W_OWNER_REF" not in raw
    assert custody.verify(str(path))["authenticated_decryption"]
    retrieved={
        name:custody.reveal(str(path),name) for name in
        (*custody._SECRET_NAMES,custody._OWNER_NAME)
    }
    assert len(set(retrieved.values()))==6
    for name in custody._SECRET_NAMES:
        assert len(custody._decode(retrieved[name]))==32
        assert retrieved[name].encode() not in raw
    assert len(retrieved[custody._OWNER_NAME])>=16
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create(str(path))


def test_wrong_passphrase_detected_without_leaking_ciphertext(tmp_path,monkeypatch):
    path=tmp_path/"owner-keys.enc"
    custody.create(str(path))
    monkeypatch.setattr(custody.getpass,"getpass",lambda prompt="":"WRONG PASSCODE never use")
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked) as error:
        custody.verify(str(path))
    assert "WRONG PASSCODE" not in str(error.value)


def test_tampered_ciphertext_rejected(tmp_path):
    path=tmp_path/"owner-keys.enc"
    custody.create(str(path))
    obj=json.loads(path.read_text())
    obj["ciphertext"]=obj["ciphertext"][:-4]+"AAAA"
    path.write_text(json.dumps(obj))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.reveal(str(path),"P1N_OWNER_ENCRYPTION_KEY")


def test_paths_are_absolute_and_never_inside_source_tree(tmp_path):
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create("relative-file.enc")
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create(str(tmp_path/"backend"/"secret.enc"))
    (tmp_path/"backend").mkdir()
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create(str(tmp_path/"backend"/"secret.enc"))


def test_invalid_key_name_denied_before_passphrase(tmp_path):
    path=tmp_path/"owner-keys.enc"
    custody.create(str(path))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.reveal(str(path),"POSTGRES_PASSWORD")
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.reveal(str(path),"P1C_GOOGLE_CLIENT_SECRET")


def test_requires_private_attended_tty(monkeypatch,tmp_path):
    monkeypatch.setattr(custody,"_tty",REAL_TTY_GUARD)
    monkeypatch.setattr(custody.sys,"stdin",SimpleNamespace(isatty=lambda:False))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create(str(tmp_path/"keys.enc"))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.verify(str(tmp_path/"keys.enc"))


def test_payload_wrong_key_size_or_duplicate_domains_denied():
    from base64 import urlsafe_b64encode
    v={name:urlsafe_b64encode(bytes([i])*32).decode()
       for i,name in enumerate(custody._SECRET_NAMES)}
    v[custody._OWNER_NAME]="SYNTHETIC_ONE_OWNER_REFERENCE"
    assert custody._validate(v)
    v[custody._SECRET_NAMES[0]]=v[custody._SECRET_NAMES[1]]
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody._validate(v)


def test_password_is_only_prompted_and_url_escapes_metacharacters(monkeypatch):
    monkeypatch.setattr(custody.getpass,"getpass",
                        lambda prompt="":"SYNTHETIC strong password 2026 @:/?&=long")
    url=custody.build_isolated_credential_dsn()
    assert url.startswith(
        "postgresql+psycopg://personal_cfo_owner_credentials:")
    assert "SYNTHETIC%20strong%20password%202026%20%40%3A%2F%3F%26%3Dlong" in url
    assert url.endswith(
        "@postgres-ade30e25.railway.internal:5432/personal_cfo_owner_auth?sslmode=require")


def test_restricted_dsn_refuses_short_db_password(monkeypatch):
    monkeypatch.setattr(custody.getpass,"getpass",lambda prompt="":"short")
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.build_isolated_credential_dsn()


def test_private_railway_upload_uses_stdin_and_never_deploys_or_touches_google(tmp_path,monkeypatch):
    path=tmp_path/"escrow.enc"
    custody.create(str(path))
    received=[]
    monkeypatch.setattr(custody.shutil,"which",lambda name:"/usr/bin/railway")
    monkeypatch.setattr("builtins.input",lambda prompt="":"CONFIGURE PRIVATE API WITHOUT DEPLOY")
    def fake_run(argv,**kwargs):
        received.append((argv,kwargs))
        return SimpleNamespace(returncode=0,stdout="secret-name only",stderr="")
    monkeypatch.setattr(custody.subprocess,"run",fake_run)
    report=custody.configure_private_railway_without_deploy(
        str(path),backed_up_independently=True)
    assert report["private_railway_variables_written"]==7
    assert report["redeployment_triggered_by_this_command"] is False
    assert not report["google_secret_touched"]
    assert len(received)==7
    names={args[3] for args,_ in received}
    assert names==set(custody._SECRET_NAMES)|{
        custody._OWNER_NAME,"P1W_OWNER_CREDENTIAL_DATABASE_URL"}
    for args,kwargs in received:
        assert args[:3]==["railway","variable","set"]
        assert "--stdin" in args
        assert "--skip-deploys" in args
        assert args[args.index("--service")+1]=="personal-cfo-api-preview"
        assert args[args.index("--environment")+1]=="development"
        assert "--project" in args
        assert kwargs["input"] and isinstance(kwargs["input"],str)
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        assert kwargs["input"] not in " ".join(args)
        assert "P1C_GOOGLE_CLIENT_SECRET" not in " ".join(args)


def test_upload_refuses_without_backup_or_final_operator_confirmation(tmp_path,monkeypatch):
    path=tmp_path/"escrow.enc"
    custody.create(str(path))
    monkeypatch.setattr(custody.shutil,"which",lambda name:"/usr/bin/railway")
    monkeypatch.setattr("builtins.input",lambda prompt="":"No")
    monkeypatch.setattr(custody.subprocess,"run",
        lambda *a,**k:pytest.fail("Railway must not be called"))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.configure_private_railway_without_deploy(str(path))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.configure_private_railway_without_deploy(
            str(path),backed_up_independently=True)


def test_verified_private_endpoint_repair_only_changes_one_owner_db_url(monkeypatch):
    from sqlalchemy.engine import make_url
    assert custody._PRIVATE_PG_HOST == "postgres-ade30e25.railway.internal"
    received = []
    monkeypatch.setattr(custody.shutil, "which", lambda cmd:"/usr/bin/railway")
    monkeypatch.setattr(
        custody.getpass, "getpass",
        lambda prompt="": "SYNTHETIC only-existing-role-password 2026"
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": "REPAIR PRIVATE OWNER DATABASE HOST ONLY"
    )
    def fake_run(args, **kwargs):
        received.append((args,kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(custody.subprocess, "run", fake_run)

    report = custody.repair_private_owner_db_hostname_without_deploy()
    assert report["restricted_connection_url_updated"]
    assert report["private_variables_changed"] == 1
    assert not report["escrow_and_recovery_keys_changed"]
    assert not report["database_role_password_rotated"]
    assert not report["google_secret_touched"]
    assert not report["deployment_triggered"]
    assert not report["owner_enrolled"]
    assert len(received) == 1
    argv, args = received[0]
    assert argv[:5] == [
        "railway","variable","set","P1W_OWNER_CREDENTIAL_DATABASE_URL","--stdin"
    ]
    assert "--skip-deploys" in argv
    assert argv[argv.index("--service")+1] == "personal-cfo-api-preview"
    assert argv[argv.index("--environment")+1] == "development"
    assert args["check"] is False
    assert args["capture_output"] is True
    assert args["input"] not in " ".join(argv)
    assert "P1C_GOOGLE_CLIENT_SECRET" not in " ".join(argv)
    assert "P1N_OWNER_ENCRYPTION_KEY" not in " ".join(argv)
    url = make_url(args["input"])
    assert url.username == "personal_cfo_owner_credentials"
    assert url.host == custody._PRIVATE_PG_HOST
    assert url.database == "personal_cfo_owner_auth"
    assert url.query["sslmode"] == "require"
    assert url.password == "SYNTHETIC only-existing-role-password 2026"


def test_private_dns_repair_does_not_change_any_variable_without_approval(monkeypatch):
    monkeypatch.setattr(custody.shutil, "which", lambda cmd:"/usr/bin/railway")
    monkeypatch.setattr("builtins.input",lambda prompt="":"not authorized")
    monkeypatch.setattr(custody.subprocess,"run",
                        lambda *a,**k:pytest.fail("must not run Railway CLI"))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.repair_private_owner_db_hostname_without_deploy()


def test_private_dns_repair_preserves_secret_on_cli_failure(monkeypatch):
    monkeypatch.setattr(custody.shutil,"which",lambda cmd:"/usr/bin/railway")
    monkeypatch.setattr("builtins.input",
                        lambda prompt="":"REPAIR PRIVATE OWNER DATABASE HOST ONLY")
    monkeypatch.setattr(custody.subprocess,"run",
                        lambda *a,**k:SimpleNamespace(returncode=1,stderr="SECRET"))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked) as exc:
        custody.repair_private_owner_db_hostname_without_deploy()
    assert "SECRET" not in str(exc.value)
