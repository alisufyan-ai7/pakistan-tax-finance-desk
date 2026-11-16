"""A5b: independently authenticated, typed synthetic financial source projections.

Derived from complete AES-GCM sealed G1-c source mirror. No SQL legacy reads or
active finance writes. No account names/dates/money/source IDs in output.
NOT a tax engine, account balance certification or cutover.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json
import os

from .db import Base
from .g1c_preflight import SOURCE_COLUMNS, MAX_ROWS, analyze_source_rows, _tag
from .g1c_projection import verify_sealed_candidate_rows, _cast_value
from .ledger_crypto import unseal
from .private_events import tax_year_of


class CanonicalFactsBlocked(ValueError):
    """Missing, altered or unverified financial source graph."""


def _guard() -> None:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise CanonicalFactsBlocked("Real finance data is not authorized")


def _facts(rows: dict, independent_receipt: dict) -> dict:
    _guard()
    if not isinstance(independent_receipt, dict) or independent_receipt.get("read_only") is not True:
        raise CanonicalFactsBlocked("An independent read-only source census is required")
    try:
        census = analyze_source_rows(rows)
    except Exception:
        raise CanonicalFactsBlocked("Complete canonical source graph invalid") from None
    if (not census["source_graph_consistent"] or
        census["source_integrity_hmac"] != independent_receipt.get("source_integrity_hmac") or
        census["year_owner_account_direction_hmac"] !=
            independent_receipt.get("year_owner_account_direction_hmac") or
        census["table_counts"] != independent_receipt.get("table_counts") or
        census["migration_performed"] is not False):
        raise CanonicalFactsBlocked("Canonical facts disagree with independent original source")

    accounts = {a["id"]: a for a in rows["accounts"]}
    transactions = {t["id"]: t for t in rows["transactions"]}
    loans = {a["id"]: a for a in rows["loan_accounts"]}
    cash = {a["id"]: a for a in rows["cash_holdings"]}
    facts = []
    kind_counts = Counter()
    # Each source transaction gets EXACTLY one typed bank fact including
    # inactive/excluded/unreviewed rows: never silently net into taxable income.
    for t in rows["transactions"]:
        a = accounts[t["account_id"]]
        if type(t["debit_minor"]) is not int or type(t["credit_minor"]) is not int:
            raise CanonicalFactsBlocked("Invalid integer bank movement")
        if not isinstance(t["posted_on"], date):
            raise CanonicalFactsBlocked("Invalid source fiscal date")
        facts.append(("bank_source", a["legal_owner"], a["currency"], t["account_id"],
                      tax_year_of(t["posted_on"]), t["id"], t["debit_minor"],
                      t["credit_minor"], t["balance_minor"], t["reviewed"],
                      t["excluded"], t["overlap_possible"], t["overlap_resolved"]))
        kind_counts["bank_source"] += 1

    for link in rows["transfer_confirmations"]:
        debit = transactions[link["debit_transaction_id"]]
        credit = transactions[link["credit_transaction_id"]]
        a = accounts[debit["account_id"]]
        facts.append(("own_transfer_link", a["legal_owner"], a["currency"],
                      link["id"], debit["id"], credit["id"],
                      debit["debit_minor"], credit["credit_minor"], link["active"]))
        kind_counts["own_transfer_link"] += 1

    for item in rows["loan_allocations"]:
        loan = loans[item["loan_id"]]
        tx = transactions[item["transaction_id"]]
        facts.append(("loan_allocation", loan["legal_owner"], loan["currency"],
                      item["id"], loan["id"], tx["id"], item["event_kind"],
                      item["principal_minor"], item["markup_minor"], item["active"]))
        kind_counts["loan_allocation"] += 1

    for item in rows["cash_movements"]:
        holding = cash[item["cash_id"]]
        facts.append(("cash_movement", holding["legal_owner"], holding["currency"],
                      item["id"], item["cash_id"], item["transaction_id"],
                      item["kind"], item["amount_minor"], item["posted_on"], item["active"]))
        kind_counts["cash_movement"] += 1

    for item in rows["historical_filings"]:
        # This is merely a FILED *claim* in a source record, not authenticated IRIS proof.
        facts.append(("filing_source_claim", item["legal_entity"], item["tax_year"],
                      item["id"], item["kind"], item["filing_status"],
                      item["revision_number"], item["revision_of_id"],
                      item["fields_json"]))
        kind_counts["filing_source_claim"] += 1

    for table, kind in (("loan_allocation_reversals", "loan_reversal"),
                        ("transfer_revocations", "transfer_revocation"),
                        ("cash_movement_reversals", "cash_reversal")):
        for row in rows[table]:
            facts.append((kind, *[row[column] for column in SOURCE_COLUMNS[table]]))
            kind_counts[kind] += 1

    for table, kind in (("loan_accounts", "loan_opening"),
                        ("cash_holdings", "cash_opening"),
                        ("asset_snapshots", "asset_source_snapshot")):
        for row in rows[table]:
            facts.append((kind, *[row[column] for column in SOURCE_COLUMNS[table]]))
            kind_counts[kind] += 1
    # The complete table HMAC covers all remaining evidence, audit/auth, and
    # encrypted source fields even where no typed economic interpretation exists.
    count = sum(kind_counts.values())
    return {
        "synthetic_only": True,
        "read_only": True,
        "typed_economic_source_fact_count": count,
        "typed_fact_type_counts": dict(sorted(kind_counts.items())),
        "typed_facts_integrity_hmac": _tag(b"typed-canonical-facts:v1",
                                           sorted(facts, key=lambda f: json.dumps(f, default=str))),
        "complete_source_integrity_hmac": census["source_integrity_hmac"],
        "bank_year_direction_hmac": census["year_owner_account_direction_hmac"],
        "original_source_census_matched": True,
        "unreviewed_bank_rows": census["review_needed_transactions"],
        "source_claims_not_certified_filings": True,
        "cash_loan_asset_balance_reconciled": False,
        "ledger_authority_switched": False,
        "plaintext_legacy_tables_retired": False,
        "actual_tax_due_minor": None,
        "real_data_authorized": False,
    }


def canonical_facts_from_sealed_mirrors(
    encrypted_mirrors: list[tuple[str, str]], independent_receipt: dict,
) -> dict:
    """Authenticated candidate-only read: replay every source field before typing."""
    _guard()
    if not isinstance(encrypted_mirrors, list) or not 1 <= len(encrypted_mirrors) <= MAX_ROWS:
        raise CanonicalFactsBlocked("Missing or unbounded candidate graph")
    try:
        verify_sealed_candidate_rows(encrypted_mirrors, independent_receipt)
        rows = {name: [] for name in SOURCE_COLUMNS}
        for _, token in encrypted_mirrors:
            decoded = json.loads(unseal(token, "canonical_source_mirrors.payload_json"))
            table = decoded["table"]
            # verify_sealed_candidate_rows above already checks identity/shape,
            # exact source HMAC and AES-GCM authentication.
            rows[table].append({
                col: _cast_value(table, col, val)
                for col, val in decoded["source_row"].items()
            })
        return _facts(rows, independent_receipt)
    except CanonicalFactsBlocked:
        raise
    except Exception:
        raise CanonicalFactsBlocked("Candidate typed financial parity failed closed") from None
