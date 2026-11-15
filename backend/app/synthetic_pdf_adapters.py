"""Strict TEXT-FIRST synthetic bank/IRIS PDF preview. NOT a real-document importer.

This module intentionally requires conspicuous synthetic markers and recognizes
only fixed synthetic layouts. No OCR, external fetches, embedded attachments,
or modification of existing financial/tax ledgers occurs.

For real untrusted PDFs, a separate isolated converter (with CPU/memory budgets,
malware scanning, and format acceptance) is mandatory. Parsing in the API worker
is suitable only for synthetic fixtures, and should never be enabled on real mode.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from io import BytesIO, StringIO
import csv
import re
from pypdf import PdfReader
from .importer import ImportErrorDetail, parse_statement
from .historical import FIELD_NAMES, SyntheticFilingInput

MAX_PDF_BYTES = 512 * 1024
MAX_PAGES = 3
MAX_CHARS = 24000
SYNTHETIC_BANK_MARKER = 'TAXFIN SYNTHETIC BANK STATEMENT V1'
SYNTHETIC_IRIS_MARKER = 'TAXFIN SYNTHETIC FBR IRIS V1'
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
MONEY_RE = re.compile(r'^\d+(?:\.\d{1,2})?$')

class SyntheticPdfError(ValueError):
    pass


def _text(raw: bytes) -> str:
    if not isinstance(raw, bytes) or not raw.startswith(b'%PDF-') or len(raw) > MAX_PDF_BYTES or len(raw) < 60:
        raise SyntheticPdfError('Expected bounded nonempty PDF bytes, at most 512 KiB')
    # Fail closed on hints of active/embedded content, even if they are quoted.
    if any(tok in raw for tok in [b'/JavaScript',b'/JS ',b'/OpenAction',b'/AA ',b'/Launch',b'/EmbeddedFiles',b'/RichMedia',b'/XFA']):
        raise SyntheticPdfError('Interactive actions and embedded content are unsupported')
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PAGES:
            raise SyntheticPdfError('Encrypted or too many/empty PDF pages')
        parts=[]
        for page in reader.pages:
            # This is not CPU/memory isolation; production requires a sandbox.
            extracted = page.extract_text() or ''
            if len(extracted) > MAX_CHARS:
                raise SyntheticPdfError('Extracted text exceeds limit')
            parts.append(extracted)
        text = '\n'.join(parts)
        if len(text) > MAX_CHARS:
            raise SyntheticPdfError('Extracted text exceeds limit')
        return text
    except SyntheticPdfError:
        raise
    except Exception as exc:
        raise SyntheticPdfError('PDF could not be read as a supported synthetic text document') from exc


def preview_synthetic_bank(raw: bytes) -> dict:
    text = _text(raw)
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    if not lines or lines[0] != SYNTHETIC_BANK_MARKER:
        raise SyntheticPdfError('Unsupported bank PDF: only explicit synthetic layout V1 is supported')
    if len(lines) < 4 or not lines[1].startswith('Opening Balance:'):
        raise SyntheticPdfError('Synthetic opening balance missing')
    opening=lines[1].split(':',1)[1].strip()
    if not MONEY_RE.fullmatch(opening):
        raise SyntheticPdfError('Synthetic opening balance invalid')
    if lines[2] != 'Date | Description | Debit | Credit | Balance | Reference':
        raise SyntheticPdfError('Unsupported synthetic bank columns')
    details=[]
    if len(lines[3:]) > 100:
        raise SyntheticPdfError('Synthetic bank PDF exceeds supported rows')
    for line in lines[3:]:
        columns=[s.strip() for s in line.split('|')]
        if len(columns)!=6 or not DATE_RE.fullmatch(columns[0]):
            raise SyntheticPdfError('Unsupported bank row or date: manual review required')
        if not columns[1] or len(columns[1])>200 or '\x00' in line:
            raise SyntheticPdfError('Unsafe/empty bank narrative')
        if any(s and not MONEY_RE.fullmatch(s) for s in columns[2:5]):
            raise SyntheticPdfError('Invalid bank amount in synthetic PDF')
        details.append(columns)
    output=StringIO()
    writer=csv.writer(output)
    writer.writerow(['date','description','debit','credit','balance','reference'])
    writer.writerows(details)
    try:
        parsed,status,warnings=parse_statement(output.getvalue().encode('utf-8'),'.csv','%Y-%m-%d',opening)
    except ImportErrorDetail as exc:
        raise SyntheticPdfError(f'Synthetic bank reconciliation rejected: {exc}') from None
    return {'document_type':'synthetic_bank_statement','synthetic_only':True,
        'recognized_layout':SYNTHETIC_BANK_MARKER,'rows':len(parsed),
        'first_date':parsed[0].posted_on.isoformat(),'last_date':parsed[-1].posted_on.isoformat(),
        'reconciliation':status,'warnings':warnings,'imported':False,
        'supported_real_bank':False, 'next_step':'Private real-bank adapter validation pending'}


def preview_synthetic_fbr(raw: bytes, kind: str) -> dict:
    if kind not in {'income_return','wealth_statement'}:
        raise SyntheticPdfError('Unknown FBR form type')
    text=_text(raw)
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    if not lines or lines[0]!=SYNTHETIC_IRIS_MARKER:
        raise SyntheticPdfError('Only explicit synthetic FBR IRIS fixture format V1 supported')
    pairs={}
    for line in lines[1:]:
        if ':' not in line:
            raise SyntheticPdfError('Unrecognized synthetic IRIS line')
        key,value=[v.strip() for v in line.split(':',1)]
        if key in pairs or key not in FIELD_NAMES|{'tax_year','kind','status'}:
            raise SyntheticPdfError('Duplicate/unrecognized synthetic IRIS field')
        pairs[key]=value
    try:
        tax_year=int(pairs.pop('tax_year'))
        form=pairs.pop('kind')
        status=pairs.pop('status')
        if form!=kind or status not in {'filed_original','filed_revision'}:
            raise SyntheticPdfError('Form kind/status mismatch; human review required')
        fields={}
        for k,value in pairs.items():
            if not re.fullmatch(r'-?\d{1,16}|NULL',value):
                raise SyntheticPdfError('FBR amount is not a strict integer paisa or NULL')
            fields[k]=int(value) if value!='NULL' else None
        if not fields or not 2023<=tax_year<=2100:
            raise SyntheticPdfError('Missing fields or unsupported tax year')
        filing = SyntheticFilingInput(synthetic_fixture=True,tax_year=tax_year,
            kind=kind,filing_status=status,revision_of_id=None if status=='filed_original' else 'synthetic-placeholder',fields=fields)
    except (ValueError,TypeError,KeyError) as exc:
        raise SyntheticPdfError('Unsupported or invalid synthetic IRIS format') from exc
    # Do not claim submitted/acknowledged status from PDF text without IRIS proof.
    return {'document_type':kind,'synthetic_only':True,'tax_year':filing.tax_year,
        'recognized_layout':SYNTHETIC_IRIS_MARKER,'field_names':sorted(filing.fields),
        'filing_status_claimed_in_fixture':status,'filing_verified':False,
        'wealth_reconciled':False,'tax_due_minor':None,'estimated_tax_savings_minor':None,
        'imported':False,'supported_real_fbr_form':False}