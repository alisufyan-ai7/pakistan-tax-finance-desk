"""Operator-attended, synthetic-only read-only Linux PDF namespace smoke.

No Google, DB or actual PDF. Designed to run inside the existing Railway API
image via owner-authenticated shell, returning only constant safe booleans.
Passing this is NOT an independent G3 security review or release authorization.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys

from .private_bahl_os_sandbox import jailed_bahl_python_command

_CHILD = r'''
import json, os, socket, sys
sys.path.insert(0,sys.argv[1])
import pypdf
from app import private_bahl_statement_reconciler
network_denied=False
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(0.2)
    network_denied=s.connect_ex(("1.1.1.1",443)) != 0
    s.close()
except OSError:
    network_denied=True
host_etc_unavailable=not os.path.exists("/etc/passwd")
no_home=not os.path.exists("/home/preview")
code_readonly=False
try:
    with open("/srv/backend/app/_sandbox_test_write_","wb") as f:
        f.write(b"NO")
except OSError:
    code_readonly=True
print(json.dumps({
    "network_denied":network_denied,
    "host_etc_unavailable":host_etc_unavailable,
    "no_home":no_home,
    "code_readonly":code_readonly,
    "trusted_pypdf_import":True,
},sort_keys=True,separators=(",",":")))
'''

class PrivateBahlSandboxProbeBlocked(ValueError):
    """Cannot independently attest synthetic Linux parser confinement."""

def run_synthetic_os_jail_probe() -> dict:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P5H_OPERATOR_SANDBOX_PROBE_ONLY") != "1"):
        raise PrivateBahlSandboxProbeBlocked("Synthetic operator sandbox probe disabled")
    try:
        cmd=jailed_bahl_python_command(
            executable=sys.executable,
            root=str(Path(__file__).resolve().parents[1]),
            child_script=_CHILD,
        )
        proc=subprocess.run(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=12,
            check=False, env={"PATH":"/usr/bin:/usr/local/bin"},
            cwd="/tmp",start_new_session=True,
        )
        if proc.returncode != 0 or len(proc.stdout)>1024:
            raise ValueError()
        result=json.loads(proc.stdout)
        expected={"network_denied","host_etc_unavailable","no_home",
                  "code_readonly","trusted_pypdf_import"}
        if type(result) is not dict or set(result)!=expected or any(
            result[k] is not True for k in expected
        ):
            raise ValueError()
        return {
            "contract":"personal_cfo_p5h_synthetic_os_jail_probe_v1",
            "sandbox_synthetic_smoke_passed":True,
            "network_namespace_denied_egress":True,
            "host_credentials_not_mounted":True,
            "readonly_application_code":True,
            "isolated_pypdf_import_ok":True,
            "g3_independent_review_complete":False,
            "historical_bank_runtime_activated":False,
            "genuine_owner_document_read":False,
        }
    except Exception:
        raise PrivateBahlSandboxProbeBlocked(
            "OS PDF sandbox smoke unavailable or isolation failed") from None

if __name__=="__main__":
    try:
        print(json.dumps(run_synthetic_os_jail_probe(),sort_keys=True))
    except PrivateBahlSandboxProbeBlocked:
        print(json.dumps({
            "contract":"personal_cfo_p5h_synthetic_os_jail_probe_v1",
            "sandbox_synthetic_smoke_passed":False,
            "g3_independent_review_complete":False,
            "historical_bank_runtime_activated":False,
        },sort_keys=True))
        raise SystemExit(1)
