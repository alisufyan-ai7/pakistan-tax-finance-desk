"""P5H synthetic-only operator namespace smoke interface and safe failures."""
import json
from types import SimpleNamespace
import pytest
from app import private_bahl_sandbox_probe as p

def test_cli_probe_only_uses_synthetic_child_without_owner_data(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P5H_OPERATOR_SANDBOX_PROBE_ONLY","1")
    def command(**kwargs):
        assert kwargs["root"].endswith("/backend") or "/backend" in kwargs["root"]
        assert "PRIVATE" not in kwargs["child_script"]
        return ["/usr/bin/bwrap","--unshare-all","--","/usr/bin/python"]
    monkeypatch.setattr(p,"jailed_bahl_python_command",command)
    payload={key:True for key in (
        "network_denied","host_etc_unavailable","no_home",
        "code_readonly","trusted_pypdf_import")}
    def run(cmd,**kwargs):
        assert cmd[0]=="/usr/bin/bwrap"
        assert kwargs["stdin"] is p.subprocess.DEVNULL
        assert kwargs["stderr"] is p.subprocess.DEVNULL
        assert kwargs["timeout"] <= 12
        return SimpleNamespace(returncode=0,stdout=json.dumps(payload).encode())
    monkeypatch.setattr(p.subprocess,"run",run)
    result=p.run_synthetic_os_jail_probe()
    assert result["sandbox_synthetic_smoke_passed"]
    assert not result["g3_independent_review_complete"]
    assert not result["historical_bank_runtime_activated"]
    assert "token" not in str(result).lower()

@pytest.mark.parametrize("reason",["flag_off","real_mode","egress_possible","child_fail"])
def test_fails_closed_no_independent_release(monkeypatch,reason):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P5H_OPERATOR_SANDBOX_PROBE_ONLY","1")
    monkeypatch.setattr(p,"jailed_bahl_python_command",lambda **kw:["bwrap"])
    contents={key:True for key in (
        "network_denied","host_etc_unavailable","no_home",
        "code_readonly","trusted_pypdf_import")}
    if reason=="egress_possible":contents["network_denied"]=False
    rc=1 if reason=="child_fail" else 0
    monkeypatch.setattr(p.subprocess,"run",lambda *a,**kw:
        SimpleNamespace(returncode=rc,stdout=json.dumps(contents).encode()))
    if reason=="flag_off":monkeypatch.delenv("P5H_OPERATOR_SANDBOX_PROBE_ONLY")
    if reason=="real_mode":monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(p.PrivateBahlSandboxProbeBlocked):
        p.run_synthetic_os_jail_probe()
