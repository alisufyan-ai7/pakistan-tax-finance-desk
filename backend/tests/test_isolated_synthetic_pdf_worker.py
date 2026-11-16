"""G3: resource-bounded child never accepts actual/unrecognized PDF source."""
from io import BytesIO
import os

import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4

from app.isolated_synthetic_pdf_worker import IsolatedPdfBlocked, preview_pdf_in_bounded_process
from app.synthetic_pdf_adapters import SYNTHETIC_BANK_MARKER


def pdf(*lines):
    stream=BytesIO()
    page=canvas.Canvas(stream, pagesize=landscape(A4))
    page.setFont("Courier", 9)
    for n, line in enumerate(lines):
        page.drawString(25, 570 - n*17, line)
    page.save()
    return stream.getvalue()


def good():
    return pdf(SYNTHETIC_BANK_MARKER, "Opening Balance: 100.00",
        "Date | Description | Debit | Credit | Balance | Reference",
        "2024-05-01 | Synthetic cash deposit | 0.00 | 30.00 | 130.00 | SYN1")


def run(raw, **opts):
    return preview_pdf_in_bounded_process(raw, adapter_key="synthetic_bank_pdf_v1",
        kind="bank_statement", synthetic_fixture=True, **opts)


@pytest.mark.skipif(os.name != "posix", reason="POSIX isolation only")
def test_bounded_child_accepts_marked_reconciled_fixture(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("DATABASE_URL", "fake-secret-dsn-not-for-child")
    result=run(good())
    assert result["isolated_process_preview"] is True
    assert result["balance_validated"] is True
    assert result["preview_rows"] == 1
    assert result["production_parser_sandbox_certified"] is False
    assert result["import_performed"] is False
    assert "fake-secret-dsn" not in str(result)


@pytest.mark.skipif(os.name != "posix", reason="POSIX isolation only")
def test_unmarked_real_like_and_corrupt_pdf_quarantined_without_echo(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    raw=pdf("Statement bank authentic-looking", "PRIVATE-SENTINEL")
    with pytest.raises(IsolatedPdfBlocked) as exc:
        run(raw)
    assert "PRIVATE-SENTINEL" not in str(exc.value)
    with pytest.raises(IsolatedPdfBlocked):
        run(b"%PDF-broken")


@pytest.mark.parametrize("attrs", [
    {"synthetic_fixture": False},
    {"adapter_key": "unknown_real_bank_pdf"},
    {"kind": "iris_income_return"},
    {"tax_year": 2022},
])
def test_wrong_mode_kind_and_adapter_denied_before_subprocess(monkeypatch, attrs):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    kwargs=dict(adapter_key="synthetic_bank_pdf_v1",kind="bank_statement",
                synthetic_fixture=True)
    kwargs.update(attrs)
    with pytest.raises(IsolatedPdfBlocked):
        preview_pdf_in_bounded_process(good(),**kwargs)


def test_real_mode_denied_without_executing_worker(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(IsolatedPdfBlocked):
        run(good())


def test_timeout_or_exception_is_sanitized(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    def fail(*a, **k):
        raise RuntimeError("leaky SECRET from worker")
    monkeypatch.setattr("app.isolated_synthetic_pdf_worker.subprocess.run", fail)
    with pytest.raises(IsolatedPdfBlocked) as err:
        run(good())
    assert "SECRET" not in str(err.value)
