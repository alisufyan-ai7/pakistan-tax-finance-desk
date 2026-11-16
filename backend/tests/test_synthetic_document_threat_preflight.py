"""G3 structural threat tests on fully fictional PDF/OOXML bytes only."""
import io
import zipfile

import pytest

from app.synthetic_document_threat_preflight import (
    SyntheticThreatBlocked, inspect_synthetic_pdf_threats,
    inspect_synthetic_ooxml_threats,
)
from app.private_adapter_registry import genuine_format_candidate_manifest


def workbook(members):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in members:
            archive.writestr(name,data)
    return stream.getvalue()


def innocent():
    return workbook([
        ("[Content_Types].xml",b'<Types xmlns="synthetic"><Default Extension="xml"/></Types>'),
        ("xl/workbook.xml",b'<workbook xmlns="synthetic"><sheets/></workbook>'),
        ("xl/worksheets/sheet1.xml",b'<worksheet xmlns="synthetic"/>'),
    ])


def test_tiny_safe_synthetic_pdf_does_not_certify_malware_safety(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    raw=b"%PDF-1.4\n" + b"fictional pdf fixture safe-only\n"*9
    report=inspect_synthetic_pdf_threats(raw,synthetic_fixture=True)
    assert report["basic_structural_preflight"]
    assert report["private_malware_scan_passed"] is False
    assert report["genuine_source_certified"] is False


@pytest.mark.parametrize("tag",[
    b"/JavaScript",b"/JS",b"/OpenAction",b"/AA",
    b"/Launch",b"/EmbeddedFile",b"/RichMedia",b"/AcroForm",
    b"/XFA",b"/SubmitForm",b"/URI",b"/#4AavaScript",
])
def test_known_active_or_obfuscated_pdf_objects_quarantined(monkeypatch,tag):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_pdf_threats(
            b"%PDF-1.4\n"+b"safe synthetic prefix\n"*8+tag,
            synthetic_fixture=True,
        )


def test_small_minimal_ooxml_is_only_structural_candidate(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    report=inspect_synthetic_ooxml_threats(innocent(),synthetic_fixture=True)
    assert report["zip_members_scanned"]==3
    assert not report["macros_allowed"] and not report["external_links_allowed"]
    assert report["real_excel_or_bank_layout_certified"] is False
    assert genuine_format_candidate_manifest()["certified_real_adapters"]==0


@pytest.mark.parametrize("bad_name,bad_data",[
    ("../outside.xml",b"<x/>"),
    ("xl/vbaProject.bin",b"dummy"),
    ("xl/externalLinks/externalLink1.xml",b"<link/>"),
    ("xl/embeddings/oleObject1.bin",b"fake"),
    ("xl/worksheets/sheet1.xml",b"<!DOCTYPE sheet><sheet/>"),
    ("xl/workbook.xml",b'<Relationship TargetMode="External"/>'),
    ("xl/worksheets/sheet2.xml",b"<x>"+b"A"*9000+b"</x>"),
])
def test_hostile_ooxml_file_or_payload_is_quarantined(monkeypatch,bad_name,bad_data):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    members=[
        ("[Content_Types].xml",b"<Types/>"),
        ("xl/workbook.xml",b"<workbook/>"),
        (bad_name,bad_data),
    ]
    if bad_name=="xl/workbook.xml":
        members.pop(1)  # malicious workbook replaces the otherwise normal one
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_ooxml_threats(workbook(members),synthetic_fixture=True)


def test_bomb_archive_and_duplicate_members_rejected(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    bomb=workbook([
        ("[Content_Types].xml",b"<Types/>"),
        ("xl/workbook.xml",b"<workbook/>"),
        ("xl/worksheets/sheet1.xml",b"Z"*300000),
    ])
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_ooxml_threats(bomb,synthetic_fixture=True)
    duplicate=workbook([
        ("[Content_Types].xml",b"<Types/>"),
        ("xl/workbook.xml",b"<workbook/>"),
        ("xl/workbook.xml",b"<workbook/>"),
    ])
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_ooxml_threats(duplicate,synthetic_fixture=True)


def test_unknown_file_not_reinterpreted_as_ooxml(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_ooxml_threats(b"not-a-zip-file"*6,synthetic_fixture=True)
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_pdf_threats(innocent(),synthetic_fixture=True)


def test_real_mode_blocks_both_preflights(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_ooxml_threats(innocent(),synthetic_fixture=True)
    with pytest.raises(SyntheticThreatBlocked):
        inspect_synthetic_pdf_threats(b"%PDF-1.4\n"+b"x"*70,synthetic_fixture=True)


def test_declarations_cannot_turn_structure_into_authentic_bank_acceptance(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    report=inspect_synthetic_ooxml_threats(innocent(),synthetic_fixture=True)
    assert report["import_performed"] is False
    assert report["private_malware_scan_passed"] is False
    assert report["real_excel_or_bank_layout_certified"] is False
