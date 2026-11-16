"""D1: synthetic-only inventory of existing tax-engine rule COVERAGE, not tax due.

Reads only the repository's own version registry, never contacts FBR or
confuses a source URL/narrow salary preview with independently verified law,
eligibility, withholding treatment, full liability or a filed return.
"""
from __future__ import annotations
import os

from .tax_rules import BRACKETS, HISTORIC_VERSIONS, FBR_HISTORIC, FBR_FINANCE, FBR_WITHHOLDING


class TaxCoverageBlocked(ValueError):
    """Requested tax-law coverage is unsupported or real-data dependent."""


TAX_DOMAINS = (
    "salary", "business_income", "rental_income", "foreign_income",
    "profit_on_debt", "dividend", "capital_gains", "property_disposal",
    "investment_disposal", "salary_withholding", "business_withholding",
    "final_vs_adjustable_withholding", "donation_zakat_credits",
    "foreign_tax_credit", "wealth_opening_closing",
    "advance_tax_and_refunds",
)


def tax_rule_gap_matrix(years: tuple[int, ...] = (2023,2024,2025,2026,2027)) -> dict:
    if os.getenv("APP_DATA_MODE","synthetic")!="synthetic":
        raise TaxCoverageBlocked("Real owner tax computations are prohibited")
    if (not isinstance(years,tuple) or not years or len(years)>10 or
        len(years)!=len(set(years)) or any(type(y) is not int or
        y not in HISTORIC_VERSIONS for y in years)):
        raise TaxCoverageBlocked("Only explicitly registered synthetic TY versions supported")
    if not all(x.startswith("https://") for x in (FBR_HISTORIC,FBR_FINANCE,FBR_WITHHOLDING)):
        raise TaxCoverageBlocked("Official source registry incomplete")
    entries=[]
    for year in sorted(years):
        for domain in TAX_DOMAINS:
            preview=domain=="salary" and year in BRACKETS
            entries.append({
                "tax_year":year,
                "domain":domain,
                "status":"NARROW_SALARY_COMPONENT_PREVIEW" if preview else "NOT_IMPLEMENTED",
                "published_source_index_exists":True,
                "official_effective_rule_independently_reviewed":False,
                "mixed_income_tax_verified":False,
                "owner_evidence_verified":False,
                "legal_eligibility_verified":False,
                "golden_vector_signoff_required":True,
                "tax_due_minor":None,
                "potential_tax_savings_minor":None,
            })
    return {
        "synthetic_only":True,"read_only":True,
        "registered_tax_years":list(sorted(years)),
        "coverage_cell_count":len(entries),
        "narrow_salary_preview_cell_count":sum(x["status"]=="NARROW_SALARY_COMPONENT_PREVIEW" for x in entries),
        "unimplemented_cell_count":sum(x["status"]=="NOT_IMPLEMENTED" for x in entries),
        "cells":entries,
        "total_tax_engine_verified":False,
        "filing_ready":False,
        "real_data_authorized":False,
        "tax_due_minor":None,
    }
