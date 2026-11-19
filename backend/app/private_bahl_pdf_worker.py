"""P5C: bounded separate-process PDF extraction for reviewed BAHL layout.

Credentials (if any) move by private stdin only, NOT argv, environment,
stdout, logs or SQL. Child has no inherited owner/session/Google/DB secrets,
cannot write files, and returns a *bounded* JSON summary only. This is an
initial isolated-reader acceptance candidate, not full OS network seccomp.
Requires separate G3 sandbox review before any production activation.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

_MAX_PDF_BYTES = 4 * 1024 * 1024
_MAX_JSON = 5500


class PrivateBahlPdfWorkerBlocked(ValueError):
    """Protected PDF password or source extraction requires further review."""


_CHILD = r'''
import base64
import io
import json
import sys
from pypdf import PdfReader
sys.path.insert(0,sys.argv[1])
from app.private_bahl_statement_reconciler import reconcile_bahl_pdf_pages
incoming=json.loads(sys.stdin.buffer.read())
raw=base64.b64decode(incoming["document_b64"],validate=True)
pdf=PdfReader(io.BytesIO(raw),strict=False)
if pdf.is_encrypted:
    password=incoming.get("document_password","")
    if not password:
        sys.stdout.write(json.dumps({
            "status":"PASSWORD_REQUIRED",
            "financial_values_verified":False,
        },sort_keys=True))
        sys.exit(0)
    if not pdf.decrypt(password):
        sys.stdout.write(json.dumps({
            "status":"PASSWORD_REJECTED",
            "financial_values_verified":False,
        },sort_keys=True))
        sys.exit(0)
count=len(pdf.pages)
if not 1<=count<=100:
    raise ValueError("Unsupported PDF page count")
pages=[]
for page in pdf.pages:
    t=page.extract_text()
    if not isinstance(t,str) or not t or len(t)>150000:
        raise ValueError("Unsupported OCR or PDF text")
    pages.append(t)
result=reconcile_bahl_pdf_pages(pages=tuple(pages))
result["status"]="SOURCE_STATEMENT_RECONCILED"
result["isolated_process_preview"]=True
result["financial_values_verified"]=False
result["gross_bank_movements_only"]=True
sys.stdout.write(json.dumps(result,sort_keys=True,separators=(",",":")))
'''


def _limits():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(8,8))
    resource.setrlimit(resource.RLIMIT_AS,(1024*1024*1024,1024*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(36,36))


def inspect_private_bahl_pdf(
    *, raw_pdf: bytes, password: str | None = None,
    approved_isolated_read: bool = False,
) -> dict:
    """Limited initial format preview. No real finance storage or HTTP route."""
    if (approved_isolated_read is not True
        or type(raw_pdf) is not bytes
        or not 80 <= len(raw_pdf) <= _MAX_PDF_BYTES
        or not raw_pdf.startswith(b"%PDF-")
        or (password is not None and (
            type(password) is not str or not 1<=len(password)<=128
            or any(ord(ch)<33 or ord(ch)>126 for ch in password)
        ))
        or os.name!="posix"):
        raise PrivateBahlPdfWorkerBlocked("Private bounded PDF read not approved")
    payload=json.dumps({
        "document_b64":base64.b64encode(raw_pdf).decode("ascii"),
        "document_password":password or "",
    },separators=(",",":")).encode("ascii")
    env={
        "PYTHONDONTWRITEBYTECODE":"1",
        "PYTHONIOENCODING":"utf-8",
    }
    root=str(Path(__file__).resolve().parents[1])
    try:
        with tempfile.TemporaryDirectory(prefix="cfo-bahl-private-reader-") as cwd:
            result=subprocess.run(
                [sys.executable,"-I","-B","-c",_CHILD,root],
                input=payload,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=cwd,env=env,timeout=14,check=False,
                preexec_fn=_limits,start_new_session=True,
            )
        if result.returncode != 0 or len(result.stdout)>_MAX_JSON:
            raise ValueError()
        parsed=json.loads(result.stdout)
        if type(parsed) is not dict:
            raise ValueError()
        status=parsed.get("status")
        if status in ("PASSWORD_REQUIRED","PASSWORD_REJECTED"):
            if set(parsed)!={"status","financial_values_verified"} or parsed["financial_values_verified"] is not False:
                raise ValueError()
            return parsed
        if (status!="SOURCE_STATEMENT_RECONCILED"
            or parsed.get("contract")!="personal_cfo_bahl_reconciled_statement_v1"
            or parsed.get("financial_values_verified") is not False
            or parsed.get("gross_bank_movements_only") is not True
            or parsed.get("owner_review_required") is not True
            or parsed.get("income_minor") is not None
            or parsed.get("expenses_minor") is not None
            or parsed.get("current_available_balance_minor") is not None
            or parsed.get("real_file_sha256_bound_by_caller") is not False):
            raise ValueError()
        return parsed
    except Exception:
        raise PrivateBahlPdfWorkerBlocked(
            "Bank PDF requires isolated password, format or reconciliation review"
        ) from None
