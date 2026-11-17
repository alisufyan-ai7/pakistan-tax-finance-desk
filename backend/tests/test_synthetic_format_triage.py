"""G3: malicious/unknown fictional bank/IRIS container quarantine contracts."""
import io
import zipfile
import pytest

from app.synthetic_format_triage import (
    triage_fake_document_container,SyntheticFormatTriageBlocked,
)

CSV=(b"PERSONAL_CFO_SYNTHETIC_BANK_CSV_V1\n"
     b"date,description,debit,credit,balance,reference\n"
     b"2026-01-01,Fictional payment,10,0,90,FAKE-1\n")


def fake_pdf(payload=b""):
    return (b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"% PERSONAL_CFO_SYNTHETIC_FIXTURE\n"+payload+
            b"trailer\n<< /Root 1 0 R >>\n%%EOF\n")


def fake_xlsx(payload=b"<workbook/>",extra=()):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_STORED) as arc:
        arc.writestr("[Content_Types].xml",b"<Types/>")
        arc.writestr("xl/workbook.xml",payload)
        for name,data in extra:
            arc.writestr(name,data)
    return stream.getvalue()


@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("G3_FAKE_FORMAT_TRIAGE_ONLY","1")


def review(raw,extension=".csv",profile="pk_bank_structured_candidate_v0",
           kind="bank_statement",**opts):
    return triage_fake_document_container(
        raw=raw,claimed_extension=extension,candidate_key=profile,
        document_kind=kind,synthetic_fixture=True,**opts)


def test_fake_csv_cannot_become_certified_or_finance_fact():
    result=review(CSV)
    assert result["preflight_kind"]=="synthetic_csv_structure"
    assert result["quarantine_policy"]=="QUARANTINE_PENDING_G3"
    assert result["g3_private_review_required"]
    assert not result["real_bank_fbr_layout_certified"]
    assert not result["source_rows_parsed_for_finance"]
    assert not result["actual_fbr_filing_verified"]
    assert not result["real_data_authorized"]
    assert b"Fictional payment".decode() not in str(result)
    assert "90" not in str(result)


def test_fake_pdf_and_xlsx_are_only_structural_quarantine_candidates():
    p=review(fake_pdf(),extension=".pdf",
             profile="pk_iris_income_candidate_v0",kind="iris_income_return")
    assert p["preflight_kind"]=="synthetic_pdf_structural"
    assert p["actual_fbr_filing_verified"] is False
    x=review(fake_xlsx(),extension=".xlsx")
    assert x["preflight_kind"]=="synthetic_xlsx_container"
    assert x["independent_malware_scan_verified"] is False


@pytest.mark.parametrize("payload",[
    b"/JavaScript",b"/OpenAction",b"/EmbeddedFiles",
    b"/JS",b"/Launch",b"/XFA",b"/AA",b"/URI"
])
def test_active_pdf_quarantined(payload):
    with pytest.raises(SyntheticFormatTriageBlocked):
        review(fake_pdf(payload),extension=".pdf")


@pytest.mark.parametrize("payload",[
    b'<!DOCTYPE workbook [<!ENTITY x SYSTEM "file:///etc/passwd">]>',
    b'<workbook><externallinks/></workbook>',
    b'<worksheet>HYPERLINK("file://bad")</worksheet>',
])
def test_active_ooxml_quarantined(payload):
    with pytest.raises(SyntheticFormatTriageBlocked):
        review(fake_xlsx(payload),extension=".xlsx")


def test_macro_external_member_and_zip_path_quarantined():
    for extras in [(("xl/vbaProject.bin",b"macro"),),
                   (("../escape.xml",b"bad"),),
                   (("xl/externalLinks/externalLink1.xml",b"link"),)]:
        with pytest.raises(SyntheticFormatTriageBlocked):
            review(fake_xlsx(extra=extras),extension=".xlsx")


@pytest.mark.parametrize("bad",[
    b'=HYPERLINK("https://evil.invalid")',
    b'@SUM(1+1)', b'+CMD', b'\tBAD'
])
def test_csv_formula_injection_quarantined(bad):
    attacked=CSV.replace(b"Fictional payment",bad)
    with pytest.raises(SyntheticFormatTriageBlocked):
        review(attacked)


def test_csv_mislabeled_real_and_unknown_layouts_are_denied():
    with pytest.raises(SyntheticFormatTriageBlocked):
        review(CSV,extension=".pdf")
    with pytest.raises(SyntheticFormatTriageBlocked):
        review(b"Date,Value\n2026-01-01,100\n")
    with pytest.raises(SyntheticFormatTriageBlocked):
        review(CSV,profile="unknown")
    with pytest.raises(SyntheticFormatTriageBlocked):
        review(CSV,kind="iris_wealth_statement")


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("G3_FAKE_FORMAT_TRIAGE_ONLY","0"),
])
def test_no_originals_without_private_g3_certification(monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    with pytest.raises(SyntheticFormatTriageBlocked):
        review(CSV)


def test_no_implicit_adapter_import_into_public_preview():
    from app.preview_api import create_preview_app
    routes={r.path for r in create_preview_app().routes}
    assert "/api/documents/import" not in routes
    assert "/api/fbr/submit" not in routes
