"""P5H default-off OS-level PDF sandbox contract, synthetic-only negatives."""
import pytest
from app import private_bahl_os_sandbox as jail
from app.private_bahl_pdf_worker import (
    inspect_private_bahl_pdf, PrivateBahlPdfWorkerBlocked,
)

def config(monkeypatch):
    monkeypatch.setenv("P5C_BAHL_OS_JAIL_ENFORCED","1")
    monkeypatch.setenv("P5C_BAHL_SANDBOX_PROFILE","bubblewrap-v1")
    # Command construction only: never execute a purported OS jail in CI.
    monkeypatch.setattr(jail.Path,"is_file",lambda *_:True)
    monkeypatch.setattr(jail.Path,"is_dir",lambda *_:True)
    monkeypatch.setattr(jail.shutil,"which",lambda *_:"/usr/bin/bwrap")

def test_explicit_bubblewrap_plan_unshares_network_and_host_root(monkeypatch):
    config(monkeypatch)
    cmd=jail.jailed_bahl_python_command(
        executable="/usr/local/bin/python",root="/srv/backend",
        child_script="print('FAKE_SCRIPT')",
    )
    assert cmd[0]=="/usr/bin/bwrap"
    assert "--unshare-all" in cmd and "--die-with-parent" in cmd
    assert ["--cap-drop","ALL"]==cmd[cmd.index("--cap-drop"):cmd.index("--cap-drop")+2]
    assert ["--clearenv"]==cmd[cmd.index("--clearenv"):cmd.index("--clearenv")+1]
    assert ["--tmpfs","/"]==cmd[cmd.index("--tmpfs"):cmd.index("--tmpfs")+2]
    assert ["--ro-bind","/usr","/usr"]==cmd[cmd.index("--ro-bind"):cmd.index("--ro-bind")+3]
    assert not any(x in cmd for x in ("--share-net","--bind","--setenv", "DATABASE_URL"))
    assert not any(x in cmd for x in ("/home","/var","/etc","SECRET_PASSWORD"))
    assert cmd[-2]=="print('FAKE_SCRIPT')"
    assert cmd[-1]=="/srv/backend"

@pytest.mark.parametrize("issue",[
    "jail_flag_missing","profile_missing","binary_missing","wrong_root",
    "wrong_python",
])
def test_sandbox_unavailable_rejects_instead_of_fallback(monkeypatch,issue):
    config(monkeypatch)
    root="/srv/backend"
    python="/usr/local/bin/python"
    if issue=="jail_flag_missing":
        monkeypatch.delenv("P5C_BAHL_OS_JAIL_ENFORCED")
    if issue=="profile_missing":
        monkeypatch.delenv("P5C_BAHL_SANDBOX_PROFILE")
    if issue=="binary_missing":
        monkeypatch.setattr(jail.shutil,"which",lambda *_:None)
    if issue=="wrong_root":root="/tmp/untrusted"
    if issue=="wrong_python":python="/tmp/bank.pdf"
    with pytest.raises(jail.PrivateBahlSandboxBlocked):
        jail.jailed_bahl_python_command(
            executable=python,root=root,child_script="print('fake')")

def test_historical_pdf_never_falls_back_to_unjailed_worker(monkeypatch):
    monkeypatch.setenv("P5E_OWNER_HISTORICAL_REPORT_PILOT","1")
    monkeypatch.delenv("P5C_BAHL_OS_JAIL_ENFORCED",raising=False)
    with pytest.raises(PrivateBahlPdfWorkerBlocked):
        inspect_private_bahl_pdf(
            raw_pdf=b"%PDF-1.7\n"+b"x"*130,
            approved_isolated_read=True)
