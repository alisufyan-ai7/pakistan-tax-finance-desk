"""A5c precursor: protected owner/account/tax-year economic source parity proof.

This NEVER changes legacy or canonical SQL. It independently validates a
complete restored-candidate source graph and makes separate keyed receipts for
bank direction, loan principal/markup, cash changes and filed-source claims.
These are *source assertions*, NOT a certified account balance, realized yield,
taxable income, verified IRIS filing or active authority cutover.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
import json
import os

from .g1c_preflight import SOURCE_COLUMNS, MAX_ROWS, _tag, analyze_source_rows
from .g1c_projection import verify_sealed_candidate_rows, _cast_value
from .ledger_crypto import unseal
from .private_events import tax_year_of


class EconomicParityBlocked(ValueError):
    """Unbounded, altered or non-authoritative financial source graph."""


def _guard():
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise EconomicParityBlocked("G1 source reconciliation is synthetic-only")


def proof_from_source_rows(rows: dict, independent_receipt: dict) -> dict:
    """Cross-domain, exact-minor-unit and source-separated parity HMACs.

    Requires a freshly generated READ-ONLY original-source receipt. Values are
    never emitted: each aggregate key and amount is included ONLY in HMAC input.
    For loan/cash movement, sums remain independent of the linked bank row.
    """
    _guard()
    if (not isinstance(independent_receipt, dict)
        or independent_receipt.get("read_only") is not True
        or independent_receipt.get("migration_performed") is not False):
        raise EconomicParityBlocked("Independent original-source preflight required")
    try:
        census = analyze_source_rows(rows)
    except Exception:
        raise EconomicParityBlocked("Unknown, partial or inconsistent source graph") from None
    if (not census["source_graph_consistent"]
        or census["source_integrity_hmac"] != independent_receipt.get("source_integrity_hmac")
        or census["year_owner_account_direction_hmac"] != independent_receipt.get("year_owner_account_direction_hmac")
        or census["table_counts"] != independent_receipt.get("table_counts")):
        raise EconomicParityBlocked("Full source graph or original keyed receipt changed")

    accounts = {r["id"]: r for r in rows["accounts"]}
    transactions = {r["id"]: r for r in rows["transactions"]}
    loans = {r["id"]: r for r in rows["loan_accounts"]}
    cash_holdings = {r["id"]: r for r in rows["cash_holdings"]}
    bank = defaultdict(lambda: [0, 0, 0])
    loan = defaultdict(lambda: [0, 0, 0])
    cash = defaultdict(lambda: [0, 0])
    filings = defaultdict(int)

    for tx in rows["transactions"]:
        account = accounts[tx["account_id"]]
        if not isinstance(tx["posted_on"], date):
            raise EconomicParityBlocked("Untyped bank source date")
        debit, credit = tx["debit_minor"], tx["credit_minor"]
        if type(debit) is not int or type(credit) is not int or (debit > 0) == (credit > 0):
            raise EconomicParityBlocked("Invalid bank source direction")
        direction = "DEBIT" if debit else "CREDIT"
        key = (account["legal_owner"], account["currency"], account["id"],
               tax_year_of(tx["posted_on"]), direction)
        value = bank[key]
        value[0] += debit
        value[1] += credit
        value[2] += 1

    for alloc in rows["loan_allocations"]:
        owner = loans[alloc["loan_id"]]
        tx = transactions[alloc["transaction_id"]]
        if not isinstance(tx["posted_on"], date):
            raise EconomicParityBlocked("Unverifiable linked loan fiscal period")
        principal, markup = alloc["principal_minor"], alloc["markup_minor"]
        if type(principal) is not int or type(markup) is not int or min(principal, markup) < 0:
            raise EconomicParityBlocked("Invalid loan economic source claim")
        key = (owner["legal_owner"], owner["currency"], owner["id"],
               tax_year_of(tx["posted_on"]), alloc["event_kind"], bool(alloc["active"]))
        value = loan[key]
        value[0] += principal
        value[1] += markup
        value[2] += 1

    for movement in rows["cash_movements"]:
        holding = cash_holdings[movement["cash_id"]]
        when = movement["posted_on"]
        amount = movement["amount_minor"]
        if not isinstance(when, date) or type(amount) is not int or amount <= 0:
            raise EconomicParityBlocked("Invalid source cash movement")
        key = (holding["legal_owner"], holding["currency"], holding["id"],
               tax_year_of(when), movement["kind"], bool(movement["active"]))
        value = cash[key]
        value[0] += amount
        value[1] += 1

    for filing in rows["historical_filings"]:
        # A claimed FILED record is NEVER proof of an IRIS acknowledgment.
        key = (filing["legal_entity"], filing["tax_year"], filing["kind"],
               filing["filing_status"], filing["revision_number"])
        filings[key] += 1

    def digest(domain, grouped):
        return _tag(domain, sorted(
            [(list(key), list(value) if isinstance(value, list) else value)
             for key, value in grouped.items()],
            key=lambda item: json.dumps(item[0], default=str, sort_keys=True)
        ))

    return {
        "synthetic_only": True,
        "read_only": True,
        "complete_source_graph_matched": True,
        "bank_year_direction_groups": len(bank),
        "bank_year_direction_proof_hmac": digest(b"a5c-bank-owner-account-year-direction-v1", bank),
        "loan_year_principal_markup_groups": len(loan),
        "loan_source_proof_hmac": digest(b"a5c-loan-year-allocation-v1", loan),
        "cash_year_movement_groups": len(cash),
        "cash_source_proof_hmac": digest(b"a5c-cash-year-movement-v1", cash),
        "filing_source_claim_groups": len(filings),
        "filing_source_claim_hmac": digest(b"a5c-fbr-claim-v1", filings),
        "asset_snapshot_count": len(rows["asset_snapshots"]),
        "asset_payloads_in_complete_source_hmac": True,
        "unreviewed_bank_rows": census["review_needed_transactions"],
        "all_sources_integrity_hmac": census["source_integrity_hmac"],
        "fbr_acknowledgment_verified": False,
        "loan_cash_asset_balances_certified": False,
        "active_canonical_write_authority": False,
        "legacy_plaintext_retired": False,
        "real_data_authorized": False,
    }


def proof_from_sealed_candidate(mirrors: list[tuple[str, str]], original_receipt: dict) -> dict:
    """Verify all authenticated AES-GCM row mirrors against original before proof."""
    _guard()
    if not isinstance(mirrors, list) or not 1 <= len(mirrors) <= MAX_ROWS:
        raise EconomicParityBlocked("Unbounded or missing sealed candidate")
    try:
        verify_sealed_candidate_rows(mirrors, original_receipt)
        rows = {name: [] for name in SOURCE_COLUMNS}
        for _, token in mirrors:
            item = json.loads(unseal(token, "canonical_source_mirrors.payload_json"))
            table = item["table"]
            if table not in rows:
                raise EconomicParityBlocked("Unrecognized canonical source")
            rows[table].append({
                key: _cast_value(table, key, value)
                for key, value in item["source_row"].items()
            })
        return proof_from_source_rows(rows, original_receipt)
    except EconomicParityBlocked:
        raise
    except Exception:
        raise EconomicParityBlocked("Protected candidate reconciliation failed closed") from None
