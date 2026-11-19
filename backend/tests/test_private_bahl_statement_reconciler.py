"""P5C BAHL statement parser accepts fake text only; no owner data in CI."""
import pytest
from app.private_bahl_statement_reconciler import (
    reconcile_bahl_pdf_pages, PrivateBahlStatementBlocked,
)

P1="""Bank AL Habib Limited
STATEMENT OF ACCOUNT
From 01/07/2025 To 30/06/2026
Opening Balance 100.0030/06/2025
DATE VALUE DATE DETAILS DEBIT CREDIT BALANCE
02/07/2025 58614697 SYNTHETIC CREDIT
FAKE BANK REFERENCE ONLY
300.00 400.00
05/07/2025 12345000 SYNTHETIC DEBIT
FAKE TRANSACTION
25.00 375.00
Carried Forward
375.00
Page 1 of 2
"""
P2="""Bank AL Habib Limited
STATEMENT OF ACCOUNT
From 01/07/2025 To 30/06/2026
Brought Forward 375.00
30/06/2026 375.00Closing Balance
Totals: 25.00 300.00
Page 2 of 2
"""

def reconcile(p1=P1,p2=P2):
    return reconcile_bahl_pdf_pages(pages=(p1,p2))

def test_matching_all_running_balances_and_pdf_printed_totals():
    result=reconcile()
    assert result["contract"]=="personal_cfo_bahl_reconciled_statement_v1"
    assert result["bank"]=="Bank AL Habib Limited"
    assert result["statement_start"]=="2025-07-01"
    assert result["statement_end"]=="2026-06-30"
    assert result["opening_minor"]==10000
    assert result["closing_minor"]==37500
    assert result["gross_bank_credits_minor"]==30000
    assert result["gross_bank_debits_minor"]==2500
    assert result["transaction_count"]==2
    assert result["printed_gross_totals_match_transactions"] is True
    assert result["transaction_running_balances_match"] is True
    assert result["current_available_balance_minor"] is None
    assert result["income_minor"] is None
    assert result["expenses_minor"] is None
    assert result["own_transfers_identified"] is False
    assert result["source_independent_account_ownership_verified"] is False
    assert result["all_account_coverage_verified"] is False
    assert result["real_file_sha256_bound_by_caller"] is False
    assert result["owner_review_required"] is True
    assert "FAKE BANK" not in str(result)

@pytest.mark.parametrize("first,second",[
    (P1.replace("300.00 400.00","300.00 399.99"),P2),
    (P1.replace("25.00 375.00","25.00 375.05"),P2),
    (P1,P2.replace("Totals: 25.00 300.00","Totals: 26.00 300.00")),
    (P1,P2.replace("375.00Closing Balance","375.01Closing Balance")),
    (P1.replace("From 01/07/2025 To 30/06/2026","From 02/07/2025 To 30/06/2026"),P2),
    (P1,P2.replace("From 01/07/2025 To 30/06/2026","From 01/07/2025 To 30/07/2026")),
    (P1.replace("Bank AL Habib Limited","Unrelated Bank"),P2),
    (P1.replace("05/07/2025","05/07/2024"),P2),
    (P1.replace("25.00 375.00","250.00 125.00"),P2),
    (P1,P2.replace("30/06/2026 375.00Closing Balance","")),
    (P1,P2.replace("Totals: 25.00 300.00","")),
])
def test_corrupt_or_uncertain_bank_evidence_never_releases_numbers(first,second):
    with pytest.raises(PrivateBahlStatementBlocked):
        reconcile(first,second)

def test_unapproved_empty_or_overlong_source_denied():
    for pages in ((),("junk",),("x"*1_000_001,),
                  ("Bank AL Habib Limited",)*101):
        with pytest.raises(PrivateBahlStatementBlocked):
            reconcile_bahl_pdf_pages(pages=pages)

def test_no_implicit_current_balance_or_source_ownership():
    result=reconcile()
    assert result["statement_end"]=="2026-06-30"
    assert not result["all_account_coverage_verified"]
    assert result["current_available_balance_minor"] is None
    assert result["income_minor"] is None and result["expenses_minor"] is None
