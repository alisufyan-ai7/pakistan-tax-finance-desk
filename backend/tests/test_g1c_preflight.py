"""G1-c phase-1 contract and redacted inventory safety; synthetic fixtures only."""
from datetime import date

import pytest

from app.g1c_preflight import (
    SOURCE_COLUMNS, MAX_ROWS, G1CPreflightBlocked, _contract,
    _verified_envelopes, analyze_source_rows, preflight_postgres_source,
)
from app.ledger_crypto import seal


def _empty_graph():
    return {table: [] for table in SOURCE_COLUMNS}


def _row(table, **overrides):
    return {key: overrides.get(key) for key in SOURCE_COLUMNS[table]}


def _bank_graph(*, reviewed=False):
    rows = _empty_graph()
    rows["accounts"].append(_row("accounts", id="synthetic-account",
        name="encrypted-placeholder", institution="encrypted-placeholder",
        currency="PKR", legal_owner="individual"))
    rows["documents"].append(_row("documents", id="synthetic-document",
        account_id="synthetic-account", period_start=date(2024, 7, 1),
        period_end=date(2024, 7, 31), coverage_declared=True))
    rows["transactions"].append(_row("transactions",
        id="synthetic-transaction", account_id="synthetic-account",
        document_id="synthetic-document", row_number=1,
        posted_on=date(2024, 7, 10), debit_minor=0, credit_minor=14200,
        balance_minor=14200, category="unreviewed", reviewed=reviewed,
        overlap_possible=False, overlap_resolved=False, excluded=False))
    return rows


def test_complete_known_contract_and_all_source_tables_covered():
    _contract()
    report = analyze_source_rows(_empty_graph())
    assert report["source_tables"] == len(SOURCE_COLUMNS) == 22
    assert report["source_rows"] == 0
    assert report["source_graph_consistent"]
    assert report["migration_performed"] is False
    assert report["cutover_authorized"] is False
    assert report["backup_verified"] is False
    assert report["actual_private_canonical_ledger_ready"] is False


def test_keyed_parity_receipt_all_rows_including_unreviewed():
    rows = _bank_graph()
    report = analyze_source_rows(rows)
    assert report["source_graph_consistent"], report["blocking_issues"]
    assert report["source_rows"] == 3
    assert report["financial_group_count"] == 1
    assert report["review_needed_transactions"] == 1
    assert len(report["source_integrity_hmac"]) == 64
    assert len(report["year_owner_account_direction_hmac"]) == 64
    serialized = str(report)
    assert "synthetic-account" not in serialized
    assert "14200" not in serialized
    assert "2024-07-10" not in serialized
    other = _bank_graph()
    other["transactions"][0]["credit_minor"] += 1
    assert (analyze_source_rows(other)["source_integrity_hmac"] !=
            report["source_integrity_hmac"])
    assert (analyze_source_rows(other)["year_owner_account_direction_hmac"] !=
            report["year_owner_account_direction_hmac"])


@pytest.mark.parametrize("change,expected", [
    (lambda g: g["transactions"][0].update({"credit_minor": 0}), "INVALID_DIRECTION"),
    (lambda g: g["transactions"][0].update({"document_id": "unknown"}), "BROKEN_SOURCE_LINK"),
    (lambda g: g["transactions"][0].update({"account_id": "wrong"}), "BROKEN_SOURCE_LINK"),
    (lambda g: g["transactions"][0].update({"posted_on": date(2024, 8, 1)}), "OUTSIDE_DECLARED_PERIOD"),
    (lambda g: g["accounts"][0].update({"currency": "USD"}), "OWNER_OR_CURRENCY_REQUIRES_PLAN"),
    (lambda g: g["documents"][0].update({"period_end": date(2024, 6, 1)}), "INVALID_SOURCE_PERIOD"),
])
def test_preflight_reports_anomalies_without_values_or_changes(change, expected):
    graph = _bank_graph()
    original = {table: [r.copy() for r in records] for table, records in graph.items()}
    change(graph)
    after = {table: [r.copy() for r in records] for table, records in graph.items()}
    report = analyze_source_rows(graph)
    assert not report["source_graph_consistent"]
    assert expected in {item["code"] for item in report["blocking_issues"]}
    assert graph == after  # pure no-write preflight
    assert original["transactions"][0]["credit_minor"] == 14200
    assert "synthetic-transaction" not in str(report)


def test_reject_unknown_or_missing_source_table_column_and_duplicate_primary_key():
    graph = _bank_graph()
    del graph["cash_movements"]
    with pytest.raises(G1CPreflightBlocked, match="tables"):
        analyze_source_rows(graph)
    graph = _bank_graph()
    graph["transactions"][0]["unreviewed_new_field"] = 1
    with pytest.raises(G1CPreflightBlocked, match="shape"):
        analyze_source_rows(graph)
    graph = _bank_graph()
    graph["transactions"].append(graph["transactions"][0].copy())
    with pytest.raises(G1CPreflightBlocked, match="primary key"):
        analyze_source_rows(graph)


def test_encrypted_source_fields_verified_with_authenticated_decrypt():
    graph = _bank_graph()
    graph["accounts"][0]["name"] = seal("fictional", "accounts.name")
    graph["accounts"][0]["institution"] = seal("fictional-bank", "accounts.institution")
    graph["transactions"][0]["description"] = seal("synthetic only", "transactions.description")
    graph["transactions"][0]["category"] = seal("unreviewed", "transactions.category")
    _verified_envelopes(graph)
    graph["transactions"][0]["description"] = "unsealed sensitive value"
    with pytest.raises(G1CPreflightBlocked, match="Plaintext"):
        _verified_envelopes(graph)
    graph["transactions"][0]["description"] = seal("fictional", "transactions.reference")
    with pytest.raises(G1CPreflightBlocked, match="authentication"):
        _verified_envelopes(graph)


def test_real_mode_and_missing_dsn_block_before_any_postgres_access(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(G1CPreflightBlocked, match="real data"):
        preflight_postgres_source()
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.delenv("PG_G1C_SOURCE_DSN", raising=False)
    with pytest.raises(ValueError, match="provided"):
        preflight_postgres_source()


def test_strict_upper_bound_rejects_truncated_graph():
    rows = _empty_graph()
    rows["owner_auth_state"] = [_row("owner_auth_state", owner_id=str(i))
                                for i in range(MAX_ROWS + 1)]
    with pytest.raises(G1CPreflightBlocked, match="limit"):
        analyze_source_rows(rows)
