"""Fixed synthetic-only in-guest isolation and Python/pypdf probe."""
import json
import os
import socket
import sys
import pypdf

sys.path.insert(0, "/srv/backend")
from app import private_bahl_statement_reconciler  # noqa: F401

network_denied = False
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        conn.settimeout(0.2)
        network_denied = conn.connect_ex(("1.1.1.1", 443)) != 0
except OSError:
    network_denied = True
try:
    interfaces = [line.split(":", 1)[0].strip() for line in open("/proc/net/dev").read().splitlines()[2:] if ":" in line]
except OSError:
    interfaces = []
isolated_loopback_only = bool(interfaces) and set(interfaces) <= {"lo"}
host_hidden = not any(os.path.exists(x) for x in ("/etc/passwd", "/root/.bashrc", "/var/lib", "/home"))
code_readonly = False
try:
    with open("/srv/backend/app/_p5h_forbidden_probe_write", "wb") as file:
        file.write(b"x")
except OSError:
    code_readonly = True
secret_env_hidden = not any(
    any(k.startswith(prefix) for prefix in ("RAILWAY_", "P1", "P3", "P5", "DATABASE_", "GOOGLE_"))
    for k in os.environ
)
print(json.dumps({
    "network_denied": network_denied,
    "isolated_loopback_only": isolated_loopback_only,
    "host_hidden": host_hidden,
    "code_readonly": code_readonly,
    "secret_env_hidden": secret_env_hidden,
    "python_pypdf_imported": bool(pypdf.__version__),
}, sort_keys=True, separators=(",", ":")))
