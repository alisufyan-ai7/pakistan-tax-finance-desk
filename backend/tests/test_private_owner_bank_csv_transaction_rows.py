"""Only fictional CSV records. No owner PDF, identity, token or bank fixture."""
import hashlib
import pytest

from app.private_bank_csv_reconciler import (
    reconcile_private_bank_csv,PrivateBankCsvBlocked,
)
from app.private_owner_bank_csv_transaction_rows import (
    project_reconciled_bank_csv_transactions,
)

SOURCE="a"*64

def private_fixture():
    return (
        "\ufeff00000000000000,\n"
        "Opening Balance,PKR      100.00\n"
        "Closing Balance,PKR      125.00\n"
        "Currency,Pakistan Rupee(PKR)\n"
        "Booking Date,Value Date,Doc No,Description,Debit,Credit,Available Balance\n"
        "01 Jan 2026,01 Jan 2026,X1,Money Received from Fictional 12345678901,,50.00,150.00\n"
        "02 Jan 2026,02 Jan 2026,X2,Cheque Book Issuance Charges,20.00,,130.00\n"
        "03 Jan 2026,03 Jan 2026,X3,Payment of Profit,,0.50,130.50\n"
        "03 Jan 2026,03 Jan 2026,X4,Withholding Tax Debit Example,0.10,,130.40\n"
        "04 Jan 2026,04 Jan 2026,X5,Money Transferred to Imaginary 9876543210,5.40,,125.00\n"
    ).encode()

def synthetic_hash(kind,text):
    return hashlib.sha256((kind+":"+text).encode()).hexdigest()

def project(raw=None,report=None,expected_sha=None):
    raw=raw if raw is not None else private_fixture()
    proof=report if report is not None else reconcile_private_bank_csv(raw)
    expected_sha=expected_sha or hashlib.sha256(private_fixture()).hexdigest()
    return project_reconciled_bank_csv_transactions(
        raw,report=proof,source_hmac=SOURCE,
        expected_source_sha256=expected_sha,hmac_index=synthetic_hash)

def test_owner_rows_are_exact_reconciled_and_masked_with_stable_source_id():
    x=project()
    assert x["contract"]=="personal_cfo_p7_reconciled_bank_csv_rows_v1"
    assert x["transaction_count"]==5
    assert len(x["rows"])==5
    assert x["all_running_balances_reconciled"] is True
    assert x["current_available_balance_minor"] is None
    assert x["personal_income_minor"] is None
    assert x["personal_expenses_minor"] is None
    assert x["rows"][0]["category"]=="TRANSFER_CANDIDATE"
    assert x["rows"][0]["review_required"] is True
    assert "[account]" in x["rows"][0]["description"]
    assert "12345678901" not in str(x)
    assert "9876543210" not in str(x)
    assert x["rows"][1]["category"]=="BANK_CHARGE"
    assert x["rows"][1]["review_required"] is False
    assert x["rows"][2]["category"]=="BANK_PROFIT"
    assert x["rows"][3]["category"]=="BANK_WITHHOLDING"
    assert x["rows"][-1]["balance_after_minor"]==12500
    assert all(row["classified_as_personal_income"] is False for row in x["rows"])
    assert all(row["classified_as_personal_expense"] is False for row in x["rows"])
    assert all(row["investment_purpose_verified"] is False for row in x["rows"])
    assert x["rows"][0]["event_hmac"]==project()["rows"][0]["event_hmac"]
    assert x["rows"][0]["event_hmac"]!=x["rows"][1]["event_hmac"]

@pytest.mark.parametrize("corruption",[
    lambda b:b.replace(b"50.00,150.00",b"50.00,150.01"),
    lambda b:b.replace(b"Cheque Book Issuance Charges",b"Unsupported text"),
    lambda b:b.replace(b"04 Jan 2026",b"01 Jan 2026"),
    lambda b:b.replace(b"125.00",b"124.99"),
    lambda b:b[:-2],
])
def test_projection_rejects_modified_original_even_with_prior_reconciled_summary(corruption):
    raw=corruption(private_fixture())
    proof=reconcile_private_bank_csv(private_fixture())
    with pytest.raises(PrivateBankCsvBlocked):
        project(raw,proof)

def test_source_proof_and_hmac_are_required():
    data=private_fixture()
    proof=reconcile_private_bank_csv(data)
    with pytest.raises(PrivateBankCsvBlocked):
        project(data,{**proof,"all_running_balances_reconciled":False})
    with pytest.raises(PrivateBankCsvBlocked):
        project_reconciled_bank_csv_transactions(
            data,report=proof,source_hmac="INVALID",
            expected_source_sha256=hashlib.sha256(data).hexdigest(),hmac_index=synthetic_hash)
    with pytest.raises(PrivateBankCsvBlocked):
        project_reconciled_bank_csv_transactions(
            data,report=proof,source_hmac=SOURCE,
            expected_source_sha256=hashlib.sha256(data).hexdigest(),
            hmac_index=lambda a,b:"NOT-HMAC")

def test_bounded_projection_rejects_instead_of_silently_truncating():
    data=private_fixture()
    proof=reconcile_private_bank_csv(data)
    with pytest.raises(PrivateBankCsvBlocked):
        project(data,{**proof,"transaction_count":601})
