"""Synthetic-only cashflow classification: source labels, not assumed spending."""
from copy import deepcopy
import pytest
from app.private_bank_csv_reconciler import (
    reconcile_private_bank_csv,PrivateBankCsvBlocked)
from app.private_bank_csv_transaction_classifier import (
    classify_reconciled_private_bank_csv)

def source():
    return (
      "00000000000000,\n"
      "Opening Balance,PKR      100.00\n"
      "Closing Balance,PKR      235.00\n"
      "Currency,Pakistan Rupee(PKR)\n"
      "Booking Date,Value Date,Doc No,Description,Debit,Credit,Available Balance\n"
      "01 Jan 2026,01 Jan 2026,SYN1,Raast P2P Fund transfer from fictional source,,50.00,150.00\n"
      "02 Jan 2026,02 Jan 2026,SYN2,Cheque Book Issuance Charges,20.00,,130.00\n"
      "03 Jan 2026,03 Jan 2026,SYN3,Payment of Profit,,0.50,130.50\n"
      "03 Jan 2026,03 Jan 2026,SYN3,Withholding Tax Debit AC-12345678,0.10,,130.40\n"
      "04 Jan 2026,04 Jan 2026,SYN4,Money Transferred to fictional recipient,5.40,,125.00\n"
      "04 Jan 2026,04 Jan 2026,SYN5,Charges Taxes Plus FED STAN(123456),10.00,,115.00\n"
      "05 Jan 2026,05 Jan 2026,SYN6,Money Received from fictional counterparty,,120.00,235.00\n"
    ).encode("utf-8")

def test_classifies_only_confirmed_bank_components_after_full_reconciliation():
    original=source()
    b=reconcile_private_bank_csv(original)
    c=classify_reconciled_private_bank_csv(original,report=b)
    assert c["contract"]=="personal_cfo_p6_bank_cashflow_classification_v1"
    assert c["transaction_count"]==7
    assert c["bank_profit_received_minor"]==50
    assert c["bank_profit_withholding_tax_minor"]==10
    assert c["bank_fees_and_combined_levies_minor"]==3000
    assert c["unclassified_credit_minor"]==17000
    assert c["unclassified_debit_minor"]==540
    assert c["confirmed_bank_event_count"]==4
    assert c["pending_review_count"]==3
    assert c["transfer_candidate_count"]==3
    assert c["all_movements_accounted_for"] is True
    assert c["personal_monthly_income_minor"] is None
    assert c["personal_monthly_expenses_minor"] is None
    assert c["all_account_coverage_verified"] is False
    assert "fictional" not in str(c)
    assert "SYN" not in str(c)

@pytest.mark.parametrize("changed",[
    ("Closing Balance,PKR      235.00","Closing Balance,PKR      235.01"),
    ("0.50,130.50","0.51,130.50"),
    ("20.00,,130.00","20.01,,130.00"),
])
def test_tampered_source_is_not_classified(changed):
    invalid=source().replace(changed[0].encode(),changed[1].encode())
    with pytest.raises(PrivateBankCsvBlocked):
        reconcile_private_bank_csv(invalid)

def test_report_monthly_totals_must_match_full_source():
    original=source()
    proof=reconcile_private_bank_csv(original)
    changes=[
        lambda r:r.update({"transaction_count":r["transaction_count"]+1}),
        lambda r:r["months"][0].update({"bank_labelled_profit_minor":999}),
        lambda r:r["months"][0].update({"gross_bank_debits_minor":200}),
        lambda r:r.update({"all_running_balances_reconciled":False}),
        lambda r:r.update({"personal_income_minor":100}),
    ]
    for fn in changes:
        changed=deepcopy(proof)
        fn(changed)
        with pytest.raises(PrivateBankCsvBlocked):
            classify_reconciled_private_bank_csv(original,report=changed)

def test_labeled_transfer_is_not_imputed_income_or_expense():
    original=source()
    proof=reconcile_private_bank_csv(original)
    c=classify_reconciled_private_bank_csv(original,report=proof)
    assert c["unclassified_credit_minor"]==17000
    assert c["unclassified_debit_minor"]==540
    assert c["bank_profit_received_minor"]==50
    assert c["owner_review_required"] is True

def test_invalid_bank_label_direction_never_confirms_profit():
    original=source()
    replaced=original.replace(
      b"SYN2,Cheque Book Issuance Charges,20.00",
      b"SYN2,Payment of Profit,20.00")
    proof=reconcile_private_bank_csv(replaced)
    c=classify_reconciled_private_bank_csv(replaced,report=proof)
    assert c["bank_profit_received_minor"]==50
    assert c["bank_fees_and_combined_levies_minor"]==1000
    assert c["pending_review_count"]==4
