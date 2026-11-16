"""G3 B5: fail-closed Docker-isolated SYNTHETIC document preview contract.

Requires an explicitly provisioned local, trusted Docker engine and a previously
built/pinned digest image. No fallback subprocess, network, writable rootfs,
Docker image pull, new cloud provider, genuine bank/IRIS source or data storage.
Container operation is NOT performed in production or Railway by this module.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from typing import Literal

from .synthetic_pdf_adapters import MAX_PDF_BYTES


class DocumentSandboxBlocked(ValueError):
    """Document sandbox not configured, unsupported or failed closed."""


DIGEST_REF = re.compile(r"^[a-z0-9][a-z0-9./_-]*@sha256:[0-9a-f]{64}$")
KIND = {
    "synthetic_bank_pdf_v1": "bank_statement",
    "synthetic_iris_income_pdf_v1": "iris_income_return",
    "synthetic_iris_wealth_pdf_v1": "iris_wealth_statement",
}


def docker_args(image: str) -> list[str]:
    """Explicit minimal container runtime flags, never shell interpolation."""
    if not isinstance(image, str) or not DIGEST_REF.fullmatch(image):
        raise DocumentSandboxBlocked("Trusted digest-pinned worker image required")
    if os.getenv("DOCKER_HOST", "") not in ("", "unix:///var/run/docker.sock") or os.getenv("DOCKER_CONTEXT", ""):
        raise DocumentSandboxBlocked("Remote or alternate Docker runtime prohibited")
    return [
        "docker", "run", "--rm", "-i", "--pull=never",
        "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=48",
        "--memory=512m", "--memory-swap=512m", "--cpus=0.5",
        "--user=65532:65532", "--ipc=none",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m",
        "--env=APP_DATA_MODE=synthetic",
        image,
    ]


def inspect_in_docker(raw: bytes, *, image: str, adapter_key: str,
                      kind: str, synthetic_fixture: bool,
                      tax_year: int | None = None) -> dict:
    """Bounded isolated *synthetic* preview; no real file or ledger mutation."""
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic" or synthetic_fixture is not True:
        raise DocumentSandboxBlocked("Real source files are not accepted")
    if adapter_key not in KIND or KIND[adapter_key] != kind:
        raise DocumentSandboxBlocked("Unapproved document parser profile")
    if tax_year is not None and (type(tax_year) is not int or not 2023 <= tax_year <= 2100):
        raise DocumentSandboxBlocked("Invalid requested synthetic fiscal year")
    if type(raw) is not bytes or not 60 <= len(raw) <= MAX_PDF_BYTES or not raw.startswith(b"%PDF-"):
        raise DocumentSandboxBlocked("Unbounded or malformed synthetic PDF input")
    command = docker_args(image)
    payload = json.dumps({
        "synthetic_fixture": True,
        "raw_b64": base64.b64encode(raw).decode("ascii"),
        "adapter_key": adapter_key, "kind": kind, "tax_year": tax_year,
    }, separators=(",", ":")).encode("ascii")
    try:
        # Stdin only: never print document bytes, passwords, DSNs or file names.
        result = subprocess.run(command, input=payload,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=9, check=False,
                                env={"PATH": "/usr/local/bin:/usr/bin:/bin",
                                     "DOCKER_HOST": "unix:///var/run/docker.sock"})
        if result.returncode != 0 or len(result.stdout) > 4096:
            raise DocumentSandboxBlocked("Isolated synthetic document rejected")
        output = json.loads(result.stdout)
        if (not isinstance(output, dict) or output.get("synthetic_only") is not True
            or output.get("import_performed") is not False
            or output.get("real_source_certified") is not False
            or output.get("owner_source_data_ingested") is not False):
            raise DocumentSandboxBlocked("Uncertified or unsafe worker response")
        # No owner raw numbers, page text, identifiers or file bytes in receipt.
        permitted = {
            "synthetic_only", "adapter", "adapter_revision", "document_kind",
            "format", "import_performed", "owner_source_data_ingested",
            "real_source_certified", "fbr_ready", "tax_due_minor",
            "preview_rows", "balance_validated", "needs_opening_balance",
            "source_marker_verified", "claimed_tax_year",
            "filing_acknowledgement_verified",
        }
        if set(output) - permitted:
            raise DocumentSandboxBlocked("Unexpected worker data in response")
        return {**output, "container_network_disabled": True,
                "worker_image_digest_pinned": True,
                "real_document_acceptance": False,
                "production_sandbox_attested": False}
    except DocumentSandboxBlocked:
        raise
    except Exception:
        raise DocumentSandboxBlocked("Document sandbox unavailable or timed out") from None
