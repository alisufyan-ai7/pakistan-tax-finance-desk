"""Read-only synthetic accountant DRAFT workbook structural tests."""
from io import BytesIO
import zipfile
import pytest
from openpyxl import Workbook

from app.workbook_diagnostics import WorkbookReviewBlocked, review_synthetic_draft


def _workbook(*, formula="=A2*2", title="Private fictional statement", many=0):
    wb = Workbook()
    ws = wb.active
    ws.title = title
    ws["A2"] = 2  # deliberately synthetic numeric fixture
    ws["B2"] = formula
    for i in range(many):
        wb.create_sheet(title=f"Fixture_{i}")
    stream = BytesIO()
    wb.save(stream)
    wb.close()
    return stream.getvalue()


def _replace_sheet_xml(blob, old: bytes, new: bytes) -> bytes:
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(blob)) as source, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                assert old in data, data[:500]
                data = data.replace(old, new)
            target.writestr(info.filename, data)
    return out.getvalue()


def test_only_structure_no_sheet_title_formula_or_values_leak():
    original = _workbook()
    found = review_synthetic_draft(original, synthetic_fixture=True, tax_year=2026)
    assert found["read_only"] is True
    assert not found["workbook_modified"]
    assert found["draft_status"] == "draft"
    assert found["formula_count"] == 1
    assert found["missing_cached_result_count"] == 1
    assert found["issues"] == [{"sheet_index": 0, "cell": "B2", "code": "MISSING_CACHED_RESULT"}]
    assert not found["filing_status_verified"] and found["tax_due_minor"] is None
    assert "Private fictional statement" not in str(found)
    assert "=A2*2" not in str(found) and original == _workbook()


def test_broken_ref_and_uncertified_cached_value():
    src = _workbook(formula="=#REF!+1")
    res = review_synthetic_draft(src, synthetic_fixture=True)
    assert res["broken_reference_count"] == 1
    assert {v["code"] for v in res["issues"]} == {"BROKEN_REFERENCE", "MISSING_CACHED_RESULT"}
    formula = _workbook()
    cached = _replace_sheet_xml(formula, b"<v />", b"<v>4</v>")
    res = review_synthetic_draft(cached, synthetic_fixture=True)
    assert res["missing_cached_result_count"] == 0
    assert res["issues"] == [{"sheet_index": 0, "cell": "B2", "code": "CACHE_PRESENT_UNVERIFIED"}]
    assert res["cached_results_trusted"] is False
    assert res["formula_recalculated"] is False


@pytest.mark.parametrize("status", ["filed_original", "filed_revision", "finalized"])
def test_draft_never_promotes_to_filed_status(status):
    with pytest.raises(WorkbookReviewBlocked, match="Filed"):
        review_synthetic_draft(_workbook(), synthetic_fixture=True, draft_status=status)


@pytest.mark.parametrize("bad", [
    b"<html>download blocked</html>",
    b"PK\x03\x04garbage",
    b"%PDF-1.7",
])
def test_unsupported_or_fake_workbook_rejected(bad):
    with pytest.raises(WorkbookReviewBlocked):
        review_synthetic_draft(bad, synthetic_fixture=True)


def test_missing_synthetic_flag_or_real_mode_rejected(monkeypatch):
    with pytest.raises(WorkbookReviewBlocked, match="Synthetic"):
        review_synthetic_draft(_workbook(), synthetic_fixture=False)
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(WorkbookReviewBlocked, match="Synthetic"):
        review_synthetic_draft(_workbook(), synthetic_fixture=True)


def test_external_formula_reference_rejected():
    with pytest.raises(WorkbookReviewBlocked, match="External"):
        review_synthetic_draft(_workbook(formula="='[external.xlsx]Sheet1'!A1"),
                              synthetic_fixture=True)


def test_unbounded_dimensions_and_excess_sheet_count_rejected():
    with pytest.raises(WorkbookReviewBlocked, match="sheet count"):
        review_synthetic_draft(_workbook(many=16), synthetic_fixture=True)
    wb = Workbook()
    ws = wb.active
    ws["B13000"] = "=1+1"
    stream = BytesIO()
    wb.save(stream)
    wb.close()
    with pytest.raises(WorkbookReviewBlocked, match="dimensions"):
        review_synthetic_draft(stream.getvalue(), synthetic_fixture=True)
