"""Source-checked statutory salary *component* previews, not full FBR tax due.

2026/2027 brackets come from FBR consolidated Income Tax Ordinance 2001,
First Schedule Part I Division I clause (2), PDF pages 526–527.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt

FBR_2027='https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf'
FBR_HISTORIC='https://fbr.gov.pk/Categ/Income-Tax--Income-Tax-Ordinance/326'
FBR_FINANCE='https://www.fbr.gov.pk/Categ/Finance-Acts/620'
FBR_WITHHOLDING='https://www.fbr.gov.pk/withholding-tax-rate-card/174298/174301'
# Lower bound rupees, fixed liability rupees below that bound, marginal rate.
BRACKETS={
 2026:((0,0,'0'),(600000,0,'0.01'),(1200000,6000,'0.11'),
       (2200000,116000,'0.23'),(3200000,346000,'0.30'),(4100000,616000,'0.35')),
 2027:((0,0,'0'),(600000,0,'0.01'),(1200000,6000,'0.11'),
       (2200000,116000,'0.20'),(3200000,316000,'0.25'),
       (4100000,541000,'0.29'),(5600000,976000,'0.32'),(7000000,1424000,'0.35')),
}
HISTORIC_VERSIONS={
 2023:'Finance Act 2022 / Ordinance amended to 2022',
 2024:'Finance Act 2023 / Ordinance amended to 2023',
 2025:'Finance Act 2024 / Ordinance amended to 2024',
 2026:'Finance Act 2025 / Ordinance amended to 2025',
 2027:'Finance Act 2026 / Ordinance amended to 2026',
}

class SalaryPreviewInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    synthetic_fixture: Literal[True]
    tax_year: Literal[2026,2027]
    taxable_income_minor: StrictInt=Field(ge=0,le=1_000_000_000)  # <= PKR 10m
    salary_chargeable_minor: StrictInt=Field(ge=0,le=1_000_000_000)
    confirms_no_separately_taxed_sources: Literal[True]
    confirms_no_other_tax_adjustments: Literal[True]


def tax_rule_registry(tax_year:int)->dict:
    if tax_year not in HISTORIC_VERSIONS:
        raise HTTPException(422,'Rule registry covers tax years 2023–2027 only')
    active=tax_year in BRACKETS
    return {'tax_year':tax_year,'law_version':HISTORIC_VERSIONS[tax_year],
       'source_index':FBR_HISTORIC,'finance_acts_index':FBR_FINANCE,
       'withholding_card_index':FBR_WITHHOLDING,
       'salary_slab_source':FBR_2027 if active else None,
       'salary_slab_preview_available':active,
       'salary_preview_status':'OFFICIAL_SLAB_TEXT_CHECKED_NARROW_SCOPE' if active else 'SOURCE_INDEXED_RULE_NOT_IMPLEMENTED',
       'total_tax_engine_verified':False,'filing_ready':False,
       'coverage_warning':'Mixed income, exemptions, separately taxed sources, surcharge, credits and withholding require evidence and additional rules.'}


def salary_preview(payload:SalaryPreviewInput)->dict:
    income=payload.taxable_income_minor
    salary=payload.salary_chargeable_minor
    if income and salary*4<=income*3:
        raise HTTPException(422,'Salary must strictly exceed 75% of taxable income for this table')
    if income==0 and salary!=0:
        raise HTTPException(422,'Zero taxable income cannot have positive chargeable salary in this scenario')
    if income and salary==0:
        raise HTTPException(422,'Chargeable salary evidence required')
    lower,fixed,rate=next(x for x in reversed(BRACKETS[payload.tax_year]) if income>=x[0]*100)
    result=Decimal(fixed*100)+Decimal(income-lower*100)*Decimal(rate)
    cents=int(result.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    return {'tax_year':payload.tax_year,'synthetic_only':True,
        'source':FBR_2027,'rule_source_section':'First Schedule, Part I, Division I, clause (2)',
        'rule_status':'OFFICIAL_SLAB_TEXT_CHECKED_NARROW_SCOPE',
        'taxable_income_minor':income,'salary_chargeable_minor':salary,
        'applicable_bracket_lower_pkr':lower,'salary_slab_component_minor':cents,
        'tax_due_minor':None,'net_tax_payable_minor':None,'refund_minor':None,
        'potential_tax_savings_minor':None,'fbr_ready':False,
        'warning':'Illustrative slab component, NOT total tax due. No separately taxed income, exemptions, advance payments, credits, super tax, surcharge or adjustments. Never infer taxable income from bank credits.'}


def opportunity_rule_index(category:str,tax_year:int)->dict:
    if tax_year not in HISTORIC_VERSIONS:
        raise HTTPException(422,'Source registry covers tax years 2023–2027 only')
    rules={
       'donation':('61','Charitable tax credit depends on recipient eligibility, limits and evidence'),
       'zakat':('60','Zakat allowance has statutory qualifications; not all gifts qualify'),
       'business_expense':('20/21','Business deductions subject to documented purpose and disallowances'),
       'tax_paid':('149/168','Payment must be classified as final, minimum or adjustable with certificates'),
       'investment_income':('5/7B/37A','Dividend, profit on debt and securities gains require distinct review'),
    }
    if category not in rules:
        raise ValueError('Unknown opportunity category')
    section,caution=rules[category]
    return {'tax_year':tax_year,'law_provision':section,
        'fbr_source_index':FBR_HISTORIC,'law_version':HISTORIC_VERSIONS[tax_year],
        'qualification_status':'EVIDENCE_REQUIRED','legal_eligibility_verified':False,
        'potential_savings_minor':None,'caution':caution}