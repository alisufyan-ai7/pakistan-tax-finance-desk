"""D1 internal repository rule coverage: source index != complete law."""
import pytest
from app.tax_rule_coverage import tax_rule_gap_matrix, TaxCoverageBlocked, TAX_DOMAINS


def test_existing_rule_years_and_all_missing_domains_are_explicit():
    out=tax_rule_gap_matrix()
    assert out["registered_tax_years"]==[2023,2024,2025,2026,2027]
    assert out["coverage_cell_count"]==5*len(TAX_DOMAINS)
    assert out["narrow_salary_preview_cell_count"]==2
    assert out["unimplemented_cell_count"]==out["coverage_cell_count"]-2
    assert out["tax_due_minor"] is None
    assert not out["filing_ready"]
    assert all(not x["official_effective_rule_independently_reviewed"] for x in out["cells"])
    assert all(x["potential_tax_savings_minor"] is None for x in out["cells"])


def test_timeline_requires_source_rules_not_just_a_url():
    out=tax_rule_gap_matrix((2025,2026))
    rows={(x["tax_year"],x["domain"]):x for x in out["cells"]}
    assert rows[(2025,"salary")]["status"]=="NOT_IMPLEMENTED"
    assert rows[(2026,"salary")]["status"]=="NARROW_SALARY_COMPONENT_PREVIEW"
    assert rows[(2026,"final_vs_adjustable_withholding")]["status"]=="NOT_IMPLEMENTED"
    assert rows[(2026,"wealth_opening_closing")]["tax_due_minor"] is None


@pytest.mark.parametrize("years",[(2028,), (2025,2025),(),[2025],(True,),("2026",)])
def test_unknown_or_ambiguous_year_registry_rejected(years):
    with pytest.raises(TaxCoverageBlocked):
        tax_rule_gap_matrix(years)


def test_real_mode_denied_before_any_tax_projection(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(TaxCoverageBlocked,match="Real"):
        tax_rule_gap_matrix()
