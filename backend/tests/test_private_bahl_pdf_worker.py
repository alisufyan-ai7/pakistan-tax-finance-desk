"""P5C worker tests: generated fictional PDF bytes, no bank/owner data."""
from io import BytesIO
import pytest
from reportlab.pdfgen import canvas
from pypdf import PdfReader,PdfWriter

from app.private_bahl_pdf_worker import (
    inspect_private_bahl_pdf,PrivateBahlPdfWorkerBlocked,
)

P1=[
 "Bank AL Habib Limited",
 "STATEMENT OF ACCOUNT",
 "From 01/07/2025 To 30/06/2026",
 "Opening Balance 100.0030/06/2025",
 "02/07/2025 58614697 SYNTHETIC CREDIT",
 "FAKE TEST DESCRIPTION",
 "300.00 400.00",
 "05/07/2025 12345000 SYNTHETIC DEBIT",
 "25.00 375.00",
 "Carried Forward","375.00","Page 1 of 2",
]
P2=[
 "Bank AL Habib Limited",
 "STATEMENT OF ACCOUNT",
 "From 01/07/2025 To 30/06/2026",
 "Brought Forward 375.00",
 "30/06/2026 375.00Closing Balance",
 "Totals: 25.00 300.00",
 "Page 2 of 2",
]


def fakepdf(encrypted=False):
    stream=BytesIO()
    c=canvas.Canvas(stream)
    for page_lines in (P1,P2):
        y=790
        for line in page_lines:
            c.drawString(35,y,line)
            y-=21
        c.showPage()
    c.save()
    raw=stream.getvalue()
    if encrypted:
        reader=PdfReader(BytesIO(raw))
        writer=PdfWriter()
        for page in reader.pages:writer.add_page(page)
        writer.encrypt("synthetic-document-password",algorithm="AES-128")
        stream=BytesIO()
        writer.write(stream)
        return stream.getvalue()
    return raw


def test_generated_bahl_pdf_reconciles_via_bounded_child_process():
    result=inspect_private_bahl_pdf(
        raw_pdf=fakepdf(),approved_isolated_read=True)
    assert result["status"]=="SOURCE_STATEMENT_RECONCILED"
    assert result["closing_minor"]==37500
    assert result["opening_minor"]==10000
    assert result["gross_bank_credits_minor"]==30000
    assert result["gross_bank_debits_minor"]==2500
    assert result["transaction_count"]==2
    assert result["owner_review_required"] is True
    assert result["financial_values_verified"] is False
    assert result["current_available_balance_minor"] is None
    assert result["income_minor"] is None
    assert result["expenses_minor"] is None
    assert "SYNTHETIC CREDIT" not in str(result)


def test_encrypted_pdf_asks_for_password_without_exposing_body():
    raw=fakepdf(encrypted=True)
    need=inspect_private_bahl_pdf(raw_pdf=raw,approved_isolated_read=True)
    assert need=={"status":"PASSWORD_REQUIRED","financial_values_verified":False}
    bad=inspect_private_bahl_pdf(raw_pdf=raw,password="wrong",
                                 approved_isolated_read=True)
    assert bad=={"status":"PASSWORD_REJECTED","financial_values_verified":False}
    okay=inspect_private_bahl_pdf(
        raw_pdf=raw,password="synthetic-document-password",
        approved_isolated_read=True)
    assert okay["closing_minor"]==37500


def test_invalid_pdf_and_unreviewed_invocation_refused():
    raw=fakepdf()
    for kwargs in (
       {"raw_pdf":raw,"approved_isolated_read":False},
       {"raw_pdf":b"<script>"+b"x"*200},
       {"raw_pdf":b"%PDF-1.4"+b"x"*(4*1024*1024+1)},
       {"raw_pdf":raw,"password":"\nsecret","approved_isolated_read":True},
    ):
       with pytest.raises(PrivateBahlPdfWorkerBlocked):
           inspect_private_bahl_pdf(**kwargs)


def test_corrupt_statement_totals_fail_closed_without_untrusted_error():
    saved=P2[-2]
    try:
      P2[-2]="Totals: 25.01 300.00"
      raw=fakepdf()
    finally:
      P2[-2]=saved
    with pytest.raises(PrivateBahlPdfWorkerBlocked) as exc:
      inspect_private_bahl_pdf(raw_pdf=raw,approved_isolated_read=True)
    assert "25.01" not in str(exc.value)
    assert "SYNTHETIC CREDIT" not in str(exc.value)


def test_tampered_child_json_never_enters_historical_report(monkeypatch):
    """Future VM replies must meet the exact same closed evidence contract."""
    import copy
    import json
    from types import SimpleNamespace
    from app import private_bahl_pdf_worker as worker

    raw = fakepdf()
    valid = inspect_private_bahl_pdf(
        raw_pdf=raw, approved_isolated_read=True,
    )
    assert worker._validate_child_result(valid) == valid

    corrupt = []
    for field, replacement in (
        ("closing_minor", valid["closing_minor"] + 1),
        ("opening_minor", -100),
        ("transaction_count", True),
        ("page_count", 101),
        ("statement_end", "2030-01-01"),
        ("financial_values_verified", True),
        ("all_account_coverage_verified", True),
        ("bank", "SYNTHETIC IMPOSTOR"),
        ("gross_bank_debits_minor", "2500"),
    ):
        altered = copy.deepcopy(valid)
        altered[field] = replacement
        corrupt.append(altered)
    unknown = copy.deepcopy(valid)
    unknown["investment_return_minor"] = 100
    corrupt.append(unknown)
    for forged in corrupt:
        monkeypatch.setattr(
            worker.subprocess, "run",
            lambda *a, **kw: SimpleNamespace(
                returncode=0, stdout=json.dumps(forged).encode("utf-8"),
            ),
        )
        with pytest.raises(PrivateBahlPdfWorkerBlocked):
            inspect_private_bahl_pdf(
                raw_pdf=raw, approved_isolated_read=True,
            )
