"""Content-signature and OOXML safety checks with fabricated files only."""
from io import BytesIO
import warnings
import zipfile

import pytest
from openpyxl import Workbook

from app.document_preflight import PreflightError, preflight_tabular
from app.importer import ImportErrorDetail, parse_statement
from test_imports import csv_bytes, upload


def _zip(parts):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts:
            z.writestr(name, data)
    return stream.getvalue()


def _minimal_parts(extra=()):
    return [
        ("[Content_Types].xml", b"<Types/>"),
        ("xl/workbook.xml", b"<workbook/>"),
        ("xl/worksheets/sheet1.xml", b"<worksheet/>"),
        *extra,
    ]


def _valid_workbook():
    wb = Workbook()
    ws = wb.active
    ws.append(["date", "description", "debit", "credit", "balance", "reference"])
    ws.append(["2024-01-02", "Synthetic only", "", "50.00", "50.00", "S1"])
    buf = BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def test_valid_csv_and_real_ooxml_synthetic_import():
    raw = csv_bytes([["2024-01-02", "Synthetic receipt", "", "50.00", "50.00", "S1"]])
    preflight_tabular(raw, ".csv")
    preflight_tabular(b"\xef\xbb\xbf" + raw, ".csv")
    workbook = _valid_workbook()
    preflight_tabular(workbook, ".xlsx")
    rows, status, _ = parse_statement(workbook, ".xlsx", "%Y-%m-%d", "0.00")
    assert len(rows) == 1 and status == "opening_and_running_verified"


@pytest.mark.parametrize("raw, ext", [
    (b"%PDF-1.7", ".csv"),
    (b"PK\x03\x04" + b"not a csv", ".csv"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", ".csv"),
    (b"<!DOCTYPE html><html>download failed</html>", ".csv"),
    (b"\xef\xbb\xbf   <html>error</html>", ".csv"),
    (b"\x00date,description", ".csv"),
    (b"date,description\x01,debit", ".csv"),
    (b"date,\xff,credit", ".csv"),
    (b"HTML download failed", ".xls"),
    (b"%PDF-1.7", ".xlsx"),
    (b"PK\x03\x04not a ZIP", ".xlsx"),
])
def test_content_signature_rejects_masquerading_or_invalid_file(raw, ext):
    with pytest.raises(PreflightError):
        preflight_tabular(raw, ext)


@pytest.mark.parametrize("name", [
    "../financial.csv", "/temp/source.xml", "xl/../sheet.xml",
    "xl\\sheet.xml", "xl/externalLinks/one.xml",
    "xl/embeddings/sheet.bin", "xl/vbaProject.bin", "xl/connections.xml",
])
def test_xlsx_rejects_unsafe_members(name):
    with pytest.raises(PreflightError):
        preflight_tabular(_zip(_minimal_parts([(name, b"fake")])), ".xlsx")


def test_ordinary_zip_not_recognized_as_workbook():
    with pytest.raises(PreflightError, match="OOXML"):
        preflight_tabular(_zip([("file.txt", b"not an Excel workbook")]), ".xlsx")


def test_zip_bomb_rejected_by_compression_ratio_and_size():
    suspicious = _zip(_minimal_parts([("xl/worksheets/sheet2.xml", b"0" * (3 * 1024 * 1024))]))
    with pytest.raises(PreflightError, match="ratio"):
        preflight_tabular(suspicious, ".xlsx")
    huge = _zip(_minimal_parts([("xl/worksheets/sheet2.xml", b"A" * (17 * 1024 * 1024))]))
    with pytest.raises(PreflightError, match="limit"):
        preflight_tabular(huge, ".xlsx")


def test_external_relationships_and_macros_rejected():
    rel = b'<Relationships><Relationship TargetMode="External" Target="https://invalid.example/file.csv"/></Relationships>'
    with pytest.raises(PreflightError, match="External"):
        preflight_tabular(_zip(_minimal_parts([("xl/_rels/workbook.xml.rels", rel)])), ".xlsx")
    macro = [("[Content_Types].xml", b"<Types>macroEnabled</Types>"),
             ("xl/workbook.xml", b"<workbook/>"), ("xl/worksheets/sheet1.xml", b"<worksheet/>")]
    with pytest.raises(PreflightError, match="Macro"):
        preflight_tabular(_zip(macro), ".xlsx")


def test_duplicates_and_symlinks_rejected():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        duplicate = _zip(_minimal_parts([("xl/workbook.xml", b"<other/>")]))
    with pytest.raises(PreflightError, match="Duplicate"):
        preflight_tabular(duplicate, ".xlsx")
    stream = BytesIO()
    link = zipfile.ZipInfo("xl/worksheets/link.xml")
    link.create_system = 3
    link.external_attr = (0o120777 << 16)
    with zipfile.ZipFile(stream, "w") as z:
        for name, data in _minimal_parts():
            z.writestr(name, data)
        z.writestr(link, b"target")
    with pytest.raises(PreflightError, match="Links"):
        preflight_tabular(stream.getvalue(), ".xlsx")


def test_bad_statement_never_mutates_financial_ledger(client, account):
    invalid = _zip(_minimal_parts([("xl/externalLinks/link.xml", b"synthetic")]))
    response = upload(client, account, invalid, "xlsx")
    assert response.status_code == 422
    assert client.get("/api/accounts").json()[0]["id"] == account
    assert client.get("/api/transactions?tax_year=2024").json()["rows"] == []
    with pytest.raises(ImportErrorDetail, match="Active"):
        parse_statement(invalid, ".xlsx", "%Y-%m-%d", None)
