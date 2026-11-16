"""G3 B5: bounded separate-process synthetic PDF adapter acceptance harness.

This is NOT a production parser sandbox: OS-level network/file-system sandbox,
malware inspection, document-password handling and genuine bank/FBR adapters
remain blocked. It deliberately refuses real-mode and non-fixture documents,
and NEVER runs this parser from a live finance API or Railway preview.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .synthetic_pdf_adapters import MAX_PDF_BYTES


class IsolatedPdfBlocked(ValueError):
    """Unapproved or unparseable synthetic PDF remains quarantined."""


# Run from Python isolated mode (-I), fixed source root (NOT from document bytes).
# Inbound PDF bytes travel only on stdin, never CLI args; only bounded summary on stdout.
_CHILD = """
import base64
import json
import sys
sys.path.insert(0, sys.argv[1])
from app.source_contracts import inspect_synthetic_source
payload = json.loads(sys.stdin.buffer.read())
raw = base64.b64decode(payload["document_b64"], validate=True)
result = inspect_synthetic_source(
    raw, adapter_key=payload["adapter_key"], extension=".pdf",
    kind=payload["kind"], synthetic_fixture=True, tax_year=payload["tax_year"])
sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")))
"""
_ALLOWED = {
    "synthetic_bank_pdf_v1": "bank_statement",
    "synthetic_iris_income_pdf_v1": "iris_income_return",
    "synthetic_iris_wealth_pdf_v1": "iris_wealth_statement",
}


def _limits():
    """Posix resource limits: fail closed if they are unavailable."""
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (48, 48))


def preview_pdf_in_bounded_process(raw: bytes, *, adapter_key: str,
                                   kind: str, synthetic_fixture: bool,
                                   tax_year: int | None = None) -> dict:
    """Opt-in isolated-process synthetic PDF PREVIEW: no DB write or raw echo."""
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic" or synthetic_fixture is not True:
        raise IsolatedPdfBlocked("Uncertified real source input prohibited")
    if adapter_key not in _ALLOWED or _ALLOWED[adapter_key] != kind:
        raise IsolatedPdfBlocked("Unknown or incompatible synthetic PDF adapter")
    if tax_year is not None and (type(tax_year) is not int or not 2023 <= tax_year <= 2100):
        raise IsolatedPdfBlocked("Unapproved tax-year range")
    if (type(raw) is not bytes or not 60 <= len(raw) <= MAX_PDF_BYTES
        or not raw.startswith(b"%PDF-")):
        raise IsolatedPdfBlocked("Invalid bounded synthetic PDF content")
    if os.name != "posix":
        raise IsolatedPdfBlocked("POSIX resource-budget worker required")
    # Reject unsupported PDFs in child. No real data may enter this harness.
    encoded = json.dumps({
        "document_b64": base64.b64encode(raw).decode("ascii"),
        "adapter_key": adapter_key, "kind": kind, "tax_year": tax_year,
    }, separators=(",", ":")).encode("ascii")
    # No parent secrets/DSNs inherited: APP_DATA_MODE is explicit, no HOME,
    # Python path or environment-provided configuration reaches child.
    env = {"APP_DATA_MODE": "synthetic", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONIOENCODING": "utf-8"}
    root = str(Path(__file__).resolve().parents[1])
    try:
        with tempfile.TemporaryDirectory(prefix="cfo-synthetic-worker-") as cwd:
            completed = subprocess.run(
                [sys.executable, "-I", "-B", "-c", _CHILD, root],
                input=encoded, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=6, check=False, cwd=cwd, env=env,
                preexec_fn=_limits, start_new_session=True,
            )
        if completed.returncode != 0 or len(completed.stdout) > 8192:
            raise IsolatedPdfBlocked("Synthetic PDF worker rejected untrusted content")
        result = json.loads(completed.stdout)
        if (not isinstance(result, dict) or result.get("synthetic_only") is not True
            or result.get("real_source_certified") is not False
            or result.get("owner_source_data_ingested") is not False
            or result.get("import_performed") is not False):
            raise IsolatedPdfBlocked("Synthetic worker output violated safety contract")
        return {**result, "isolated_process_preview": True,
                "production_parser_sandbox_certified": False}
    except IsolatedPdfBlocked:
        raise
    except Exception:
        raise IsolatedPdfBlocked("Synthetic PDF worker unavailable or timed out") from None
