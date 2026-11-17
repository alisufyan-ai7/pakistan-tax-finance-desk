"""Combined G1/G3/accountant compatibility smoke — fictional fixtures only."""
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.source_contracts import inspect_synthetic_source, SourceContractBlocked
from app.workbook_diagnostics import review_synthetic_draft, WorkbookReviewBlocked
from app.g1c_preflight import SOURCE_COLUMNS, analyze_source_rows
from app.g1c_candidate import create_verified_sealed_candidate, G1CCandidateBlocked


def _fictional_draft():
    book = Workbook()
    sheet = book.active
    sheet.title = "Example only"
    sheet["A1"] = 7
    sheet["A2"] = "=A1+1"
    out = BytesIO()
    book.save(out)
    book.close()
    return out.getvalue()


def _fictional_statement():
    return (b"date,description,debit,credit,balance,reference\n"
            b"2024-07-01,Fictional sample,,5.00,5.00,FAKE-001\n")


def test_three_parallel_capabilities_are_non_authoritative_and_read_only():
    preview = inspect_synthetic_source(
        _fictional_statement(), adapter_key="synthetic_normalized_bank_csv_v1",
        kind="bank_statement", extension=".csv", synthetic_fixture=True,
    )
    review = review_synthetic_draft(
        _fictional_draft(), synthetic_fixture=True, draft_status="draft", tax_year=2025,
    )
    inventory = analyze_source_rows({name: [] for name in SOURCE_COLUMNS})
    assert preview["import_performed"] is False
    assert not preview["balance_validated"] and not preview["real_source_certified"]
    assert review["read_only"] and review["draft_status"] == "draft"
    assert review["missing_cached_result_count"] == 1
    assert not review["filing_status_verified"]
    assert inventory["read_only"] and inventory["source_tables"] == 35
    assert not inventory["actual_private_canonical_ledger_ready"]
    assert preview["tax_due_minor"] is review["tax_due_minor"] is inventory["tax_due_minor"] is None


def test_all_three_new_slices_fail_closed_in_real_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(SourceContractBlocked):
        inspect_synthetic_source(
            _fictional_statement(), adapter_key="synthetic_normalized_bank_csv_v1",
            kind="bank_statement", extension=".csv", synthetic_fixture=True,
        )
    with pytest.raises(WorkbookReviewBlocked):
        review_synthetic_draft(_fictional_draft(), synthetic_fixture=True)
    fake_backup = tmp_path / "must-not-exist.tfpg"
    with pytest.raises(G1CCandidateBlocked):
        create_verified_sealed_candidate(fake_backup)
    assert not fake_backup.exists()
