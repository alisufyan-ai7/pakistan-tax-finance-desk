"""Text-first fake PDFs. No taxpayer data or real bank/FBR document layouts."""
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape,A4
import pytest
from pypdf import PdfWriter
from app.synthetic_pdf_adapters import (preview_synthetic_bank,preview_synthetic_fbr,SyntheticPdfError,
    SYNTHETIC_BANK_MARKER,SYNTHETIC_IRIS_MARKER)


def fixture_pdf(*lines):
    stream=BytesIO()
    pdf=canvas.Canvas(stream,pagesize=landscape(A4))
    pdf.setFont('Courier',9)
    for i,line in enumerate(lines):
        pdf.drawString(25,570-i*17,line)
    pdf.save()
    return stream.getvalue()


def test_pdf_bank_balance_reconciles_without_import(client):
    raw=fixture_pdf(SYNTHETIC_BANK_MARKER,'Opening Balance: 100.00',
        'Date | Description | Debit | Credit | Balance | Reference',
        '2024-05-01 | Synthetic cash deposit | 0.00 | 30.00 | 130.00 | SYN1',
        '2024-05-02 | Synthetic purchase | 25.00 | 0.00 | 105.00 | SYN2')
    out=preview_synthetic_bank(raw)
    assert out['rows']==2 and out['reconciliation']=='opening_and_running_verified'
    assert out['imported'] is False and out['supported_real_bank'] is False
    r=client.post('/api/documents/synthetic-pdf/preview',files={'file':('statement.pdf',raw,'application/pdf')},data={'document_type':'bank'})
    assert r.status_code==200 and r.json()['rows']==2
    assert client.get('/api/accounts').json()==[]


def test_pdf_rejects_bank_balance_difference():
    bad=fixture_pdf(SYNTHETIC_BANK_MARKER,'Opening Balance: 100.00',
        'Date | Description | Debit | Credit | Balance | Reference',
        '2024-05-01 | Synthetic bad balance | 50.00 | 0.00 | 90.00 | FAIL')
    with pytest.raises(SyntheticPdfError,match='reconciliation'):
        preview_synthetic_bank(bad)


def test_pdf_rejects_non_synthetic_real_like_statement(client):
    raw=fixture_pdf('BANK STATEMENT','Opening Balance: 100.00',
        'Date | Description | Debit | Credit | Balance | Reference',
        '2024-05-01 | salary | 0.00 | 100.00 | 200.00 | 123')
    with pytest.raises(SyntheticPdfError,match='synthetic'):
        preview_synthetic_bank(raw)
    r=client.post('/api/documents/synthetic-pdf/preview',files={'file':('real.pdf',raw,'application/pdf')},data={'document_type':'bank'})
    assert r.status_code==422


def test_fbr_synthetic_historical_income_and_wealth(client):
    for kind,field in [('income_return','salary_income_minor'),('wealth_statement','closing_wealth_minor')]:
        raw=fixture_pdf(SYNTHETIC_IRIS_MARKER,'tax_year: 2025',f'kind: {kind}',
            'status: filed_original',f'{field}: 1200000','cash_in_hand_minor: NULL')
        out=preview_synthetic_fbr(raw,kind)
        assert out['tax_year']==2025 and not out['filing_verified']
        assert out['tax_due_minor'] is None
        r=client.post('/api/documents/synthetic-pdf/preview',files={'file':('filing.pdf',raw,'application/pdf')},data={'document_type':kind})
        assert r.status_code==200 and not r.json()['imported']


def test_fbr_rejects_malformed_and_duplicate_fields():
    raw=fixture_pdf(SYNTHETIC_IRIS_MARKER,'tax_year: 2025','kind: income_return',
        'status: filed_original','salary_income_minor: 100','salary_income_minor: 200')
    with pytest.raises(SyntheticPdfError,match='Duplicate'):
        preview_synthetic_fbr(raw,'income_return')


def test_pdf_rejects_javascript_and_password_protected():
    stream=BytesIO(); w=PdfWriter();w.add_blank_page(width=500,height=700);w.add_js('app.alert(1)');w.write(stream)
    with pytest.raises(SyntheticPdfError):
        preview_synthetic_bank(stream.getvalue())
    password=BytesIO();v=PdfWriter();v.add_blank_page(width=500,height=700);v.encrypt('synthetic')
    v.write(password)
    with pytest.raises(SyntheticPdfError,match='Encrypted'):
        preview_synthetic_bank(password.getvalue())


def test_pdf_rejects_wrong_type_or_oversize(client):
    assert client.post('/api/documents/synthetic-pdf/preview',files={'file':('bad.txt',b'text','text/plain')},data={'document_type':'bank'}).status_code==415
    assert client.post('/api/documents/synthetic-pdf/preview',files={'file':('bad.pdf',b'%PDF-\x00','application/pdf')},data={'document_type':'bank'}).status_code==422
    assert client.post('/api/documents/synthetic-pdf/preview',files={'file':('bad.pdf',b'A'*600000,'application/pdf')},data={'document_type':'bank'}).status_code==413