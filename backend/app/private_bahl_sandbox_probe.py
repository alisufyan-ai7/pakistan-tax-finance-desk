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

# Fixed public codes only; never return subprocess stderr, host paths, tokens,
# environment variables, PDFs, passwords or arbitrary exception messages.
_SAFE_REASONS = frozenset((
    "PROBE_NOT_ENABLED", "JAIL_COMMAND_UNAVAILABLE", "JAIL_CANNOT_START",
    "ISOLATED_CHILD_FAILED", "CHILD_TIMED_OUT", "CHILD_RESULT_INVALID",
    "ISOLATION_POLICY_FAILED", "JAIL_LAUNCH_ERROR",
))
_START_CHILD = 'print("P5H_NAMESPACE_BOOTED")'


class PrivateBahlSandboxProbeBlocked(ValueError):
    """Synthetic-only reason code; nothing from the host or child is exposed."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code if reason_code in _SAFE_REASONS else "JAIL_LAUNCH_ERROR"
        super().__init__("OS PDF sandbox synthetic check failed")


def _run_in_jail(command):
    """Never inherit private environment, owner data, filesystem cwd or stderr."""
    return subprocess.run(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=12, check=False,
        env={"PATH":"/usr/bin:/usr/local/bin"},
        cwd="/tmp", start_new_session=True,
    )


def _safe_failure_reason_after_child_error() -> str:
    """Separate 'no namespace' from 'namespace boots but imports fail'.

    Both runs are fixed synthetic code under the *same* reviewed jail plan;
    neither can read original PDFs, Google/DB credentials or private files.
    Never print the child's stderr, stdout, return code or exception string.
    """
    try:
        command = jailed_bahl_python_command(
            executable=sys.executable,
            root=str(Path(__file__).resolve().parents[1]),
            child_script=_START_CHILD,
        )
        proc = _run_in_jail(command)
        if proc.returncode == 0 and proc.stdout == b"P5H_NAMESPACE_BOOTED\n":
            return "ISOLATED_CHILD_FAILED"
        return "JAIL_CANNOT_START"
    except subprocess.TimeoutExpired:
        return "CHILD_TIMED_OUT"
    except Exception:
        return "JAIL_CANNOT_START"


def run_synthetic_os_jail_probe() -> dict:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P5H_OPERATOR_SANDBOX_PROBE_ONLY") != "1"):
        raise PrivateBahlSandboxProbeBlocked("PROBE_NOT_ENABLED")
    try:
        cmd = jailed_bahl_python_command(
            executable=sys.executable,
            root=str(Path(__file__).resolve().parents[1]),
            child_script=_CHILD,
        )
    except Exception:
        raise PrivateBahlSandboxProbeBlocked("JAIL_COMMAND_UNAVAILABLE") from None
    try:
        proc = _run_in_jail(cmd)
    except subprocess.TimeoutExpired:
        raise PrivateBahlSandboxProbeBlocked("CHILD_TIMED_OUT") from None
    except Exception:
        raise PrivateBahlSandboxProbeBlocked("JAIL_LAUNCH_ERROR") from None
    if proc.returncode != 0:
        raise PrivateBahlSandboxProbeBlocked(
            _safe_failure_reason_after_child_error()
        )
    if len(proc.stdout) > 1024:
        raise PrivateBahlSandboxProbeBlocked("CHILD_RESULT_INVALID")
    try:
        result = json.loads(proc.stdout)
    except (ValueError, UnicodeError, TypeError):
        raise PrivateBahlSandboxProbeBlocked("CHILD_RESULT_INVALID") from None
    expected = {"network_denied", "host_etc_unavailable", "no_home",
                "code_readonly", "trusted_pypdf_import"}
    if (type(result) is not dict or set(result) != expected
        or any(result[key] is not True for key in expected)):
        raise PrivateBahlSandboxProbeBlocked("ISOLATION_POLICY_FAILED")
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

if __name__=="__main__":
    try:
        print(json.dumps(run_synthetic_os_jail_probe(),sort_keys=True))
    except PrivateBahlSandboxProbeBlocked as exc:
        print(json.dumps({
            "contract":"personal_cfo_p5h_synthetic_os_jail_probe_v1",
            "safe_failure_reason":exc.reason_code,
            "sandbox_synthetic_smoke_passed":False,
            "g3_independent_review_complete":False,
            "historical_bank_runtime_activated":False,
        },sort_keys=True))
        raise SystemExit(1)
