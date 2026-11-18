"""P1AM: synthetic-only attended gateway secret custody rehearsal."""
from types import SimpleNamespace

import pytest

from app import private_owner_gateway_prepare_cli as prep


def configure(monkeypatch):
    monkeypatch.setattr(prep, "sys", SimpleNamespace(
        platform="darwin",
        stdin=SimpleNamespace(isatty=lambda: True),
        stdout=SimpleNamespace(isatty=lambda: True),
    ))
    monkeypatch.setattr(prep.shutil, "which",
                        lambda name: "/usr/local/bin/railway" if name == "railway" else None)
    monkeypatch.setattr("builtins.input", lambda prompt: prep.APPROVAL)


def test_two_existing_services_share_one_unprinted_strong_random_key(monkeypatch, capsys):
    configure(monkeypatch)
    monkeypatch.setattr(prep.secrets, "token_urlsafe", lambda n: "X"*86)
    commands, secrets_in_stdin = [], []

    def fake_run(cmd, **kw):
        commands.append(cmd)
        secrets_in_stdin.append(kw.get("input"))
        assert kw["capture_output"] is True
        assert kw["text"] is True
        assert kw["check"] is False
        assert kw["timeout"] == 60
        return SimpleNamespace(returncode=0, stdout="never printed",
                               stderr="hidden provider error")
    monkeypatch.setattr(prep.subprocess, "run", fake_run)
    outcome = prep.prepare()
    assert outcome["existing_approved_services_configured"] == 2
    assert outcome["railway_deploys_triggered"] is False
    assert outcome["staged_google_oauth_secret_applied"] is False
    assert outcome["public_owner_login_activated"] is False
    assert secrets_in_stdin == ["X"*86, "X"*86]
    for cmd, service in zip(commands, prep.SERVICES):
        assert cmd == [
            "railway", "variable", "set",
            "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", "--stdin",
            "--project", prep.PROJECT, "--environment", "development",
            "--service", service, "--skip-deploys",
        ]
        assert not any("X"*20 in str(part) for part in cmd)
        assert "P1AK_OWNER_INGRESS_ENABLED" not in str(cmd)
        assert "P1C_GOOGLE_CLIENT_SECRET" not in str(cmd)
    stdout = capsys.readouterr().out
    assert "X"*40 not in stdout
    assert "never printed" not in stdout


@pytest.mark.parametrize("reason", ["not_mac", "no_tty", "no_cli", "denied"])
def test_private_prepare_fails_before_generating_secret(monkeypatch, reason):
    configure(monkeypatch)
    if reason == "not_mac":
        prep.sys.platform = "linux"
    elif reason == "no_tty":
        prep.sys.stdin.isatty = lambda: False
    elif reason == "no_cli":
        prep.shutil.which = lambda name: None
    elif reason == "denied":
        monkeypatch.setattr("builtins.input", lambda prompt: "not approved")
    monkeypatch.setattr(prep.secrets, "token_urlsafe",
                        lambda n: (_ for _ in ()).throw(AssertionError(
                            "No secret should be generated before review")))
    with pytest.raises(prep.PrivateGatewayPreparationBlocked):
        prep.prepare()


def test_partial_second_service_failure_never_activates_g2(monkeypatch, capsys):
    configure(monkeypatch)
    monkeypatch.setattr(prep.secrets, "token_urlsafe", lambda n: "A"*64)
    calls = []

    def fake_run(cmd, **kw):
        calls.append((cmd, kw))
        return SimpleNamespace(returncode=0 if len(calls)==1 else 1)
    monkeypatch.setattr(prep.subprocess, "run", fake_run)
    with pytest.raises(prep.PrivateGatewayPreparationBlocked):
        prep.prepare()
    assert len(calls) == 2
    assert all("--skip-deploys" in command for command,_ in calls)
    assert all("P1AK_OWNER_INGRESS_ENABLED" not in str(command)
               for command,_ in calls)
    assert "A"*40 not in capsys.readouterr().out
