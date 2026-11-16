"""A5c owner-account-year source receipts never leak actual amounts or confer cutover."""
from datetime import date
import pytest

from app.g1c_preflight import SOURCE_COLUMNS, analyze_source_rows
from app.g1c_balance_parity import EconomicParityBlocked, proof_from_source_rows, proof_from_sealed_candidate


def row(table, **overrides):
    return {col: overrides.get(col) for col in SOURCE_COLUMNS[table]}


def source_graph():
    data = {name: [] for name in SOURCE_COLUMNS}
    data["accounts"] = [row("accounts", id="fake-account-id", legal_owner="individual", currency="PKR")]
    data["documents"] = [row("documents", id="fake-document-id", account_id="fake-account-id",
                             period_start=date(2025, 7, 1), period_end=date(2025, 7, 31),
                             coverage_declared=True)]
    data["transactions"] = [
        row("transactions", id="fake-credit", account_id="fake-account-id",
            document_id="fake-document-id", row_number=1,
            posted_on=date(2025, 7, 2), debit_minor=0, credit_minor=15555,
            balance_minor=15555, category="unreviewed", reviewed=False,
            excluded=False, overlap_possible=False, overlap_resolved=False),
        row("transactions", id="fake-debit", account_id="fake-account-id",
            document_id="fake-document-id", row_number=2,
            posted_on=date(2025, 7, 3), debit_minor=2555, credit_minor=0,
            balance_minor=13000, category="unreviewed", reviewed=False,
            excluded=False, overlap_possible=False, overlap_resolved=False),
    ]
    return data


def original_receipt(data):
    report = analyze_source_rows(data)
    assert report["source_graph_consistent"], report["blocking_issues"]
    assert report["read_only"] is True
    return report


def test_account_tax_year_direction_proof_is_keyed_and_source_bounded(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    rows = source_graph()
    proof = proof_from_source_rows(rows, original_receipt(rows))
    assert proof["bank_year_direction_groups"] == 2
    assert proof["unreviewed_bank_rows"] == 2
    assert proof["active_canonical_write_authority"] is False
    assert proof["real_data_authorized"] is False
    assert proof["loan_cash_asset_balances_certified"] is False
    assert "15555" not in str(proof)
    assert "fake-credit" not in str(proof)
    assert len(proof["bank_year_direction_proof_hmac"]) == 64
    # Same source receipt and content replay is deterministic.
    assert proof == proof_from_source_rows(rows, original_receipt(rows))


def test_altered_amount_or_missing_source_cannot_be_reconciled(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    rows = source_graph()
    receipt = original_receipt(rows)
    rows["transactions"][0]["credit_minor"] += 1
    with pytest.raises(EconomicParityBlocked):
        proof_from_source_rows(rows, receipt)
    rows = source_graph()
    del rows["documents"]
    with pytest.raises(EconomicParityBlocked):
        proof_from_source_rows(rows, receipt)


def test_real_mode_and_unverified_or_empty_candidate_rejected(monkeypatch):
    rows = source_graph()
    receipt = original_receipt(rows)
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(EconomicParityBlocked, match="synthetic"):
        proof_from_source_rows(rows, receipt)
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    with pytest.raises(EconomicParityBlocked):
        proof_from_source_rows(rows, {**receipt, "read_only": False})
    with pytest.raises(EconomicParityBlocked):
        proof_from_sealed_candidate([], receipt)
