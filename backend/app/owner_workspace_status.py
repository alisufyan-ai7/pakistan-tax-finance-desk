"""G5/F1: source-privacy-first owner workspace status contract, synthetic-only.

The API may summarize structural evidence from separately validated in-memory
synthetic domain receipts. It NEVER reads the old plaintext financial SQL,
infers missing balances as zero, certifies tax due/FILED returns or authorizes
upload/write actions. Future private owner dashboard requires G1/G2/G3 release.
"""
from __future__ import annotations

from collections import Counter
import os

from .tax_rule_coverage import tax_rule_gap_matrix
from .accountant_review import ReviewCase, DraftWorkbook
from .accountant_review_package import review_package_manifest


class OwnerWorkspaceBlocked(ValueError):
    """Illegal entity boundary, untrusted source receipt or unsupported mode."""


STATUS_ORDER = ("OBSERVED","PARTIAL","MISSING","CONFLICTING","UNSUPPORTED")


def _scope_coverage(coverage: dict | None, legal_owner: str) -> dict:
    if coverage is None:
        return {
            "state":"UNAVAILABLE",
            "account_month_count":None,
            "status_counts":{k:None for k in STATUS_ORDER},
            "coverage_complete_and_verified":False,
            "missing_is_zero":False,
        }
    if (not isinstance(coverage,dict) or coverage.get("synthetic_only") is not True
        or coverage.get("read_only") is not True or
        not isinstance(coverage.get("coverage_rows"),list) or
        len(coverage["coverage_rows"])>7200):
        raise OwnerWorkspaceBlocked("Untrusted coverage receipt")
    rows=coverage["coverage_rows"]
    tally=Counter()
    for row in rows:
        if (not isinstance(row,dict) or row.get("status") not in STATUS_ORDER or
            row.get("legal_owner")!=legal_owner or
            row.get("financial_balance_minor") is not None or
            row.get("transaction_count") is not None or
            row.get("source_facts_verified") is not (row["status"]=="OBSERVED")):
            raise OwnerWorkspaceBlocked("Unknown or mixed-owner coverage facts")
        tally[row["status"]]+=1
    return {
        "state":"REVIEW_REQUIRED" if any(tally[k] for k in STATUS_ORDER[1:]) else
                "OBSERVED_SOURCE_COVERAGE_ONLY",
        "account_month_count":len(rows),
        "status_counts":{k:tally[k] for k in STATUS_ORDER},
        "coverage_complete_and_verified":False,
        "missing_is_zero":False,
    }


def build_owner_workspace_status(
    tax_year: int, *,
    legal_owner: str = "individual",
    coverage_receipt: dict | None = None,
    review_cases: list[ReviewCase] | None = None,
    draft_workbooks: list[DraftWorkbook] | None = None,
) -> dict:
    """A versioned redacted dashboard model; money remains intentionally NULL.

    Unknown/absent source inventory, accountant events and FBR evidence MUST be
    represented as unavailable (not zero or implicitly complete).
    """
    if os.getenv("APP_DATA_MODE","synthetic") != "synthetic":
        raise OwnerWorkspaceBlocked("Real-data owner dashboard is not authorized")
    if legal_owner not in ("individual","company","aop"):
        raise OwnerWorkspaceBlocked("Unknown legal-person scope")
    try:
        gaps=tax_rule_gap_matrix((tax_year,))
    except Exception:
        raise OwnerWorkspaceBlocked("Unsupported or unreviewed tax-year contract") from None
    coverage=_scope_coverage(coverage_receipt,legal_owner)
    review={
        "state":"UNAVAILABLE",
        "case_count":None,
        "pending_count":None,
        "draft_version_count":None,
        "official_filing_verified":False,
    }
    if review_cases is not None or draft_workbooks is not None:
        if review_cases is None or draft_workbooks is None or coverage_receipt is None:
            raise OwnerWorkspaceBlocked("Review evidence requires complete verified structural inputs")
        try:
            pkg=review_package_manifest(review_cases,draft_workbooks,coverage_receipt)
        except Exception:
            raise OwnerWorkspaceBlocked("Untrusted accountant review receipt") from None
        review={
            "state":"PROVISIONAL_REVIEW",
            "case_count":pkg["case_count"],
            "pending_count":pkg["pending_review_case_count"],
            "draft_version_count":pkg["draft_version_count"],
            "official_filing_verified":False,
        }
    return {
        "contract":"owner_workspace_status_v1",
        "synthetic_only":True,
        "read_only":True,
        "tax_year":tax_year,
        "legal_owner":legal_owner,
        "data_source":"NO_CONNECTED_OWNER_FINANCIAL_EVIDENCE",
        "coverage":coverage,
        "accountant":review,
        "tax_rule_coverage":{
            "state":"NOT_FULLY_VERIFIED",
            "domain_count":gaps["coverage_cell_count"],
            "unimplemented_domain_count":gaps["unimplemented_cell_count"],
            "narrow_preview_domain_count":gaps["narrow_salary_preview_cell_count"],
            "statutory_liability_ready":False,
        },
        "financial_facts":{
            "bank_balance_minor":None,
            "cash_balance_minor":None,
            "assets_value_minor":None,
            "liabilities_minor":None,
            "net_worth_minor":None,
            "income_minor":None,
            "spending_minor":None,
            "tax_due_minor":None,
        },
        "actions":{
            "real_evidence_upload_enabled":False,
            "accountant_filing_enabled":False,
            "payments_or_trading_enabled":False,
            "private_production_ready":False,
        },
        "required_gates":{
            "G1_confidential_active_ledger":False,
            "G2_private_runtime_mfa":False,
            "G3_genuine_evidence_adapters":False,
            "G4_complete_tax_rules":False,
            "G5_private_owner_end_to_end":False,
        },
    }
