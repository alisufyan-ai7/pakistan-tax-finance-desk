"""P5H reviewed-candidate Linux bubblewrap command for hostile bank PDFs.

No fallback to the legacy bare child when owner historical analysis is enabled.
The namespace policy is source-only until *independently* exercised against
Railway's actual kernel/runtime and approved malware/network containment.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil

class PrivateBahlSandboxBlocked(ValueError):
    """No reviewed no-network PDF container is available."""

def jailed_bahl_python_command(*, executable: str, root: str, child_script: str) -> list[str]:
    """Provide a fixed-argument, no-shell, no-network, read-only-root command.

    Expose only Python runtime and the static trusted app package. Do not expose
    Railway secrets, host /etc, $HOME, original PDFs or any host mount /var.
    stdin carries PDF+transient password and stdout carries bounded JSON.
    """
    if (os.getenv("P5C_BAHL_OS_JAIL_ENFORCED") != "1"
        or os.getenv("P5C_BAHL_SANDBOX_PROFILE") != "bubblewrap-v1"
        or os.name != "posix" or platform.system() != "Linux"
        or type(executable) is not str or type(root) is not str
        or type(child_script) is not str or not child_script):
        raise PrivateBahlSandboxBlocked("Reviewed Linux bank PDF namespace unavailable")
    rootpath=Path(root).resolve()
    pythonpath=Path(executable).resolve()
    if (str(rootpath) != "/srv/backend" or not
        (str(pythonpath).startswith("/usr/local/bin/")
         or str(pythonpath).startswith("/usr/bin/"))
        or not (rootpath/"app"/"private_bahl_statement_reconciler.py").is_file()
        or not Path("/usr").is_dir()):
        raise PrivateBahlSandboxBlocked("Reviewed bank-reader executable/root mismatch")
    bwrap=shutil.which("bwrap")
    if (not bwrap or not Path(bwrap).is_absolute()
        or not Path(bwrap).is_file()):
        raise PrivateBahlSandboxBlocked("No OS-enforced PDF sandbox installed")
    # --unshare-all creates fresh user, PID, IPC, UTS, cgroup and NET
    # namespaces. Network interfaces are unavailable in the child.
    # The in-memory /tmp and fresh /proc never expose host processes.
    # /usr supplies the python runtime + installed pypdf only;
    # /srv/backend/app contains static nonsecret application code.
    return [
        bwrap,"--die-with-parent","--unshare-all","--new-session",
        "--cap-drop","ALL","--clearenv",
        "--setenv","PYTHONDONTWRITEBYTECODE","1",
        "--setenv","PYTHONIOENCODING","utf-8",
        "--tmpfs","/",
        "--dir","/usr","--ro-bind","/usr","/usr",
        "--dir","/lib","--ro-bind-try","/lib","/lib",
        "--dir","/lib64","--ro-bind-try","/lib64","/lib64",
        "--dir","/srv","--dir","/srv/backend","--dir","/srv/backend/app",
        "--ro-bind","/srv/backend/app","/srv/backend/app",
        "--dir","/tmp","--tmpfs","/tmp",
        "--dir","/proc","--proc","/proc",
        "--dir","/dev","--dev","/dev",
        "--chdir","/tmp",
        "--",str(pythonpath),"-I","-B","-c",child_script,"/srv/backend",
    ]
