"""P5C: bounded separate-process PDF extraction for reviewed BAHL layout.

Credentials (if any) move by private stdin only, NOT argv, environment,
stdout, logs or SQL. Child has no inherited owner/session/Google/DB secrets,
cannot write files, and returns a *bounded* JSON summary only. This is an
initial isolated-reader acceptance candidate, not full OS network seccomp.
Requires separate G3 sandbox review before any production activation.
"""
from __future__ import annotations

import base64
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from .private_bahl_os_sandbox import (
    jailed_bahl_python_command, PrivateBahlSandboxBlocked,
)

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



# This exact closed contract also applies to a future isolated VM result.
# Never accept additional labels, forged money, or an isolated child claiming
# to have verified investment profit, current balances, or owner identity.
_RECONCILED_KEYS = frozenset((
    "contract", "bank", "statement_start", "statement_end",
    "opening_minor", "closing_minor", "gross_bank_debits_minor",
    "gross_bank_credits_minor", "transaction_count", "page_count",
    "printed_closing_matches_transactions",
    "printed_gross_totals_match_transactions",
    "transaction_running_balances_match",
    "current_available_balance_minor", "income_minor", "expenses_minor",
    "own_transfers_identified", "source_independent_account_ownership_verified",
    "all_account_coverage_verified", "real_file_sha256_bound_by_caller",
    "original_source_modified", "owner_review_required", "status",
    "isolated_process_preview", "financial_values_verified",
    "gross_bank_movements_only",
))


def _validate_child_result(parsed: object) -> dict:
    """Require a bounded, exact, historically labelled parser result."""
    if type(parsed) is not dict:
        raise ValueError()
    status = parsed.get("status")
    if status in ("PASSWORD_REQUIRED", "PASSWORD_REJECTED"):
        if (set(parsed) != {"status", "financial_values_verified"}
            or parsed["financial_values_verified"] is not False):
            raise ValueError()
        return parsed
    if set(parsed) != _RECONCILED_KEYS:
        raise ValueError()
    required_true = (
        "printed_closing_matches_transactions",
        "printed_gross_totals_match_transactions",
        "transaction_running_balances_match", "owner_review_required",
        "isolated_process_preview", "gross_bank_movements_only",
    )
    required_false = (
        "own_transfers_identified",
        "source_independent_account_ownership_verified",
        "all_account_coverage_verified", "real_file_sha256_bound_by_caller",
        "original_source_modified", "financial_values_verified",
    )
    if (status != "SOURCE_STATEMENT_RECONCILED"
        or parsed["contract"] != "personal_cfo_bahl_reconciled_statement_v1"
        or parsed["bank"] != "Bank AL Habib Limited"
        or any(parsed[k] is not True for k in required_true)
        or any(parsed[k] is not False for k in required_false)
        or any(parsed[k] is not None for k in (
            "income_minor", "expenses_minor", "current_available_balance_minor",
        ))):
        raise ValueError()
    money = (
        "opening_minor", "closing_minor",
        "gross_bank_debits_minor", "gross_bank_credits_minor",
    )
    if any(type(parsed[k]) is not int or not 0 <= parsed[k] <= 10**15 for k in money):
        raise ValueError()
    if (type(parsed["transaction_count"]) is not int
        or not 1 <= parsed["transaction_count"] <= 5000
        or type(parsed["page_count"]) is not int
        or not 1 <= parsed["page_count"] <= 100
        or parsed["opening_minor"] + parsed["gross_bank_credits_minor"]
        - parsed["gross_bank_debits_minor"] != parsed["closing_minor"]):
        raise ValueError()
    if (type(parsed["statement_start"]) is not str
        or type(parsed["statement_end"]) is not str):
        raise ValueError()
    start = date.fromisoformat(parsed["statement_start"])
    end = date.fromisoformat(parsed["statement_end"])
    if (start.isoformat() != parsed["statement_start"]
        or end.isoformat() != parsed["statement_end"]
        or start > end or (end - start).days > 366):
        raise ValueError()
    return parsed

def _limits():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(8,8))
    resource.setrlimit(resource.RLIMIT_AS,(1024*1024*1024,1024*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(36,36))


def _vm_bridge_limits():
    """Trusted SDK host only; hostile PDF parses inside isolated VM child."""
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(45,45))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))


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
            remote=os.getenv("P5H_REMOTE_VM_WORKER_ACTIVE") == "1"
            if remote:
                # This specific provider creates a disposable Railway VM with
                # NO host credentials inside the guest. Actual PDF bytes and
                # password travel from the owner API through ephemeral stdin
                # ONLY after the trusted jailed Python runtime passes probe.
                # Never fall back to in-process parsing on VM/SDK failure.
                if (os.getenv("P5H_REMOTE_VM_G3_REVIEWED") != "1"
                    or os.getenv("APP_DATA_MODE") != "synthetic"
                    or not os.getenv("RAILWAY_TOKEN")
                    or not os.getenv("RAILWAY_ENVIRONMENT_ID")):
                    raise ValueError()
                command=[
                    "/usr/local/bin/node",
                    str(Path(__file__).with_name("p5h_railway_sandbox_bridge.mjs")),
                ]
                env={
                    "PATH":"/usr/local/bin:/usr/bin:/bin",
                    "P5H_REMOTE_VM_WORKER_ACTIVE":"1",
                    "P5H_REMOTE_VM_G3_REVIEWED":"1",
                    "RAILWAY_TOKEN":os.environ["RAILWAY_TOKEN"],
                    "RAILWAY_ENVIRONMENT_ID":os.environ["RAILWAY_ENVIRONMENT_ID"],
                }
                worker_timeout=235
            elif os.getenv("P5E_OWNER_HISTORICAL_REPORT_PILOT") == "1":
                # The known-to-fail ordinary Railway container remains
                # fail-closed. This flag does not authorize an unjailed child.
                command=jailed_bahl_python_command(
                    executable=sys.executable,root=root,child_script=_CHILD)
                worker_timeout=14
            else:
                # Preserved only for unexposed fictional fixture unit tests.
                command=[sys.executable,"-I","-B","-c",_CHILD,root]
                worker_timeout=14
            result=subprocess.run(
                command,
                input=payload,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=cwd,env=env,timeout=worker_timeout,check=False,
                preexec_fn=_vm_bridge_limits if remote else _limits,
                start_new_session=True,
            )
        if result.returncode != 0 or len(result.stdout)>_MAX_JSON:
            raise ValueError()
        return _validate_child_result(json.loads(result.stdout))
    except Exception:
        raise PrivateBahlPdfWorkerBlocked(
            "Bank PDF requires isolated password, format or reconciliation review"
        ) from None
