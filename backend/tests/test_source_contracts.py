"""Only fabricated source layouts; no actual Pakistani bank or FBR files."""
import pytest

from app.source_contracts import (
    CAPABILITIES, SourceContractBlocked,
    capability_manifest, inspect_synthetic_source,
)


def _normalized():
    return (b"date,description,debit,credit,balance,reference\n"
            b"2024-07-01,Synthetic salary,,200.00,200.00,SYN-1\n")


def _split():
    return (b"Post Date,Narration,Withdrawals,Deposits,Running Balance,Transaction Ref\n"
            b"01/07/2024,Synthetic paid,,200.00,200.00,SYN-2\n")


def test_manifest_is_explicit_synthetic_only():
    m = capability_manifest()
    assert m["synthetic_only"] and not m["real_source_certified"]
    assert len(CAPABILITIES) == 6
    assert len({p.key for p in CAPABILITIES}) == 6
    assert all(not spec["real_source_certified"] for spec in m["supported_layouts"])


@pytest.mark.parametrize("key,raw", [
    ("synthetic_normalized_bank_csv_v1", _normalized()),
    ("synthetic_split_bank_csv_v1", _split()),
])
def test_pinned_layout_is_preview_only(key, raw):
    status = inspect_synthetic_source(
        raw, adapter_key=key, kind="bank_statement", extension=".csv",
        synthetic_fixture=True,
    )
    assert status["adapter"] == key
    assert status["import_performed"] is False
    assert status["real_source_certified"] is False
    assert status["balance_validated"] is False
    assert status["needs_opening_balance"] is True
    assert status["tax_due_minor"] is None
    assert "Synthetic salary" not in str(status)


def test_explicit_direction_adapter_and_no_guessing():
    text = (b"Transaction Date,Details,Amount,Type,Closing Balance,Trace\n"
            b"01/07/2024,Synthetic debit,10.00,DR,90.00,SYN-3\n")
    assert inspect_synthetic_source(
        text, adapter_key="synthetic_direction_bank_csv_v1",
        kind="bank_statement", extension=".csv", synthetic_fixture=True
    )["adapter_revision"] == 1
    with pytest.raises(SourceContractBlocked):
        inspect_synthetic_source(text, adapter_key="synthetic_split_bank_csv_v1",
                                kind="bank_statement", extension=".csv", synthetic_fixture=True)


@pytest.mark.parametrize("kwargs", [
    {"adapter_key": "BAHL_real_2026"},
    {"extension": ".pdf"},
    {"kind": "iris_income_return"},
    {"synthetic_fixture": False},
])
def test_unknown_mismatched_or_real_source_blocked(kwargs):
    params = dict(raw=_normalized(), adapter_key="synthetic_normalized_bank_csv_v1",
                  kind="bank_statement", extension=".csv", synthetic_fixture=True)
    params.update(kwargs)
    with pytest.raises(SourceContractBlocked):
        inspect_synthetic_source(**params)


@pytest.mark.parametrize("invalid", [
    b"%PDF-1.7", b"<html>not a bank export</html>",
    b"date,description,debit,credit,balance,reference\nX\x00Y",
    b"DATE,DESCRIPTION,CREDIT,DEBIT,BALANCE,REFERENCE\n",
])
def test_masquerade_binary_and_ambiguous_header_rejected(invalid):
    with pytest.raises(SourceContractBlocked):
        inspect_synthetic_source(
            invalid, adapter_key="synthetic_normalized_bank_csv_v1",
            kind="bank_statement", extension=".csv", synthetic_fixture=True
        )


def test_real_data_mode_is_never_allowed(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(SourceContractBlocked, match="synthetic"):
        inspect_synthetic_source(
            _normalized(), adapter_key="synthetic_normalized_bank_csv_v1",
            kind="bank_statement", extension=".csv", synthetic_fixture=True
        )


def test_iris_never_assumed_filed_without_proof():
    # Without an explicit valid PDF fixture, the IRIS adapter refuses input.
    with pytest.raises(SourceContractBlocked):
        inspect_synthetic_source(
            _normalized(), adapter_key="synthetic_iris_income_pdf_v1",
            kind="iris_income_return", extension=".pdf",
            tax_year=2025, synthetic_fixture=True,
        )
