"""Trusted PDF parser code copied from the approved API build into a VM.

Runs ONLY within the no-network Bubblewrap child, never on the VM host.
The VM receives source bytes and transient passwords over child stdin.
"""
import base64
import io
import json
import sys
from pypdf import PdfReader

sys.path.insert(0, "/srv/backend")
from app.private_bahl_statement_reconciler import reconcile_bahl_pdf_pages

incoming = json.loads(sys.stdin.buffer.read())
if type(incoming) is not dict or set(incoming) != {"document_b64", "document_password"}:
    raise ValueError("Unsupported private worker envelope")
raw = base64.b64decode(incoming["document_b64"], validate=True)
if not 80 <= len(raw) <= 4 * 1024 * 1024 or not raw.startswith(b"%PDF-"):
    raise ValueError("Unsupported PDF")
pdf = PdfReader(io.BytesIO(raw), strict=False)
if pdf.is_encrypted:
    pw = incoming["document_password"]
    if not pw:
        print(json.dumps({"status": "PASSWORD_REQUIRED", "financial_values_verified": False}))
        raise SystemExit(0)
    if not pdf.decrypt(pw):
        print(json.dumps({"status": "PASSWORD_REJECTED", "financial_values_verified": False}))
        raise SystemExit(0)
count = len(pdf.pages)
if not 1 <= count <= 100:
    raise ValueError("Unsupported page count")
pages = []
for page in pdf.pages:
    extracted = page.extract_text()
    if type(extracted) is not str or not extracted or len(extracted) > 150000:
        raise ValueError("Unsupported PDF text")
    pages.append(extracted)
result = reconcile_bahl_pdf_pages(pages=tuple(pages))
result.update(
    status="SOURCE_STATEMENT_RECONCILED",
    isolated_process_preview=True,
    financial_values_verified=False,
    gross_bank_movements_only=True,
)
sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")))
