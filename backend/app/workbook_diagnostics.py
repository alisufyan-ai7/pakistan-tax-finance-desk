"""Read-only synthetic accountant DRAFT workbook formula/cache diagnostics.

This is a *review aid*, not an Excel recalculation engine, financial classifier,
official filing verification, or a way to store/modify genuine accountant files.
All results are structural; sheet titles, formulas, cell values, and amounts are
never included in the receipt.
"""
from __future__ import annotations

from io import BytesIO
import os
import re

from openpyxl import load_workbook

from .document_preflight import PreflightError, preflight_tabular

MAX_SHEETS = 16
MAX_CELLS_PER_SHEET = 12_000
MAX_FORMULA_ISSUES = 120
_EXTERNAL_REFERENCE = re.compile(r"\[[^\]]+\]|https?://|\\\\", re.IGNORECASE)


class WorkbookReviewBlocked(ValueError):
    """Workbook cannot be safely reviewed as a synthetic draft."""


def review_synthetic_draft(raw: bytes, *, synthetic_fixture: bool,
                           draft_status: str = "draft", tax_year: int | None = None) -> dict:
    """Compare formula surfaces with cached values *without* executing formulas.

    A formula cache can be stale even if present; no financial totals, source
    completeness, or claimed filing status can be verified by this function.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic" or synthetic_fixture is not True:
        raise WorkbookReviewBlocked("Synthetic-only workbook diagnostics")
    if draft_status != "draft":
        raise WorkbookReviewBlocked("Filed or finalized status cannot be claimed from a workbook")
    if tax_year is not None and (type(tax_year) is not int or not 2023 <= tax_year <= 2100):
        raise WorkbookReviewBlocked("Invalid synthetic draft tax year")
    try:
        preflight_tabular(raw, ".xlsx")
        formulas = load_workbook(BytesIO(raw), data_only=False, read_only=True, keep_links=False)
        cached = load_workbook(BytesIO(raw), data_only=True, read_only=True, keep_links=False)
    except Exception:
        raise WorkbookReviewBlocked("Unsafe or unsupported synthetic workbook") from None

    try:
        if not 1 <= len(formulas.worksheets) <= MAX_SHEETS or len(formulas.worksheets) != len(cached.worksheets):
            raise WorkbookReviewBlocked("Unsupported draft sheet count")
        issues: list[dict] = []
        sheet_stats = []
        formula_total = 0
        missing_cache = 0
        broken_reference = 0
        for i, (sheet, values) in enumerate(zip(formulas.worksheets, cached.worksheets)):
            if (sheet.max_row is None or sheet.max_column is None or
                sheet.max_row * sheet.max_column > MAX_CELLS_PER_SHEET or
                sheet.max_row != values.max_row or sheet.max_column != values.max_column):
                raise WorkbookReviewBlocked("Unbounded or mismatched worksheet dimensions")
            count = 0
            for formula_row, value_row in zip(
                sheet.iter_rows(min_row=1, max_row=sheet.max_row, max_col=sheet.max_column),
                values.iter_rows(min_row=1, max_row=values.max_row, max_col=values.max_column),
            ):
                for cell, cache_cell in zip(formula_row, value_row):
                    if cell.data_type != "f":
                        continue
                    count += 1
                    formula_total += 1
                    expression = cell.value
                    if not isinstance(expression, str) or len(expression) > 2000:
                        raise WorkbookReviewBlocked("Invalid or oversized draft formula")
                    if _EXTERNAL_REFERENCE.search(expression):
                        raise WorkbookReviewBlocked("External formula references unsupported")
                    reasons = []
                    if "#REF!" in expression.upper():
                        reasons.append("BROKEN_REFERENCE")
                        broken_reference += 1
                    if cache_cell.value is None:
                        reasons.append("MISSING_CACHED_RESULT")
                        missing_cache += 1
                    else:
                        reasons.append("CACHE_PRESENT_UNVERIFIED")
                    if len(issues) < MAX_FORMULA_ISSUES:
                        for code in reasons:
                            issues.append({"sheet_index": i, "cell": cell.coordinate, "code": code})
            sheet_stats.append({"sheet_index": i, "formula_count": count})
        return {
            "synthetic_only": True,
            "read_only": True,
            "draft_status": "draft",
            "filing_status_verified": False,
            "workbook_modified": False,
            "formula_recalculated": False,
            "cached_results_trusted": False,
            "formula_count": formula_total,
            "missing_cached_result_count": missing_cache,
            "broken_reference_count": broken_reference,
            "issue_list_truncated": len(issues) == MAX_FORMULA_ISSUES and formula_total > MAX_FORMULA_ISSUES,
            "issues": issues,
            "sheet_summary": sheet_stats,
            "tax_due_minor": None,
            "fbr_ready": False,
            "warning": "Formula values and cached results require independent review; no filed status inferred.",
        }
    except WorkbookReviewBlocked:
        raise
    except Exception:
        raise WorkbookReviewBlocked("Synthetic workbook diagnostics failed safely") from None
    finally:
        formulas.close()
        cached.close()
