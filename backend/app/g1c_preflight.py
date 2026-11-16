"""G1-c phase 1: read-only, fail-closed synthetic PostgreSQL legacy source census.

This is NOT a migrator, a tax calculator, or an authorization to switch the
operational ledger. It inventories the entire ORM-owned graph (including
auth and encrypted source tables), checks cross-table facts, and returns only
counts, generic issue codes and domain-separated keyed HMAC receipts.

Never writes to PostgreSQL, prints source rows, or produces plain SHA digests
of financial facts. All execution is offline and explicitly invoked.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import hmac
import json
import os
from hashlib import sha256

from . import models  # noqa: F401 - load complete metadata
from .db import Base
from .ledger_crypto import ENCRYPTED_COLUMNS, PREFIX, unseal
from .pg_recovery import SCHEMA_REVISION, _connection_config, _table_names
from .private_events import _index_key, tax_year_of


class G1CPreflightBlocked(ValueError):
    """Source is incompatible, unbounded, or ineligible for inspection."""


# REVIEWED schema contract, not derived from the ORM: future model fields MUST
# be explicitly triaged here before a candidate migration can be attempted.
# Auth tables are included to avoid silent loss during future full-table restore.
SOURCE_COLUMNS = {
    "accounts": "id name institution currency legal_owner created_at",
    "documents": "id account_id sha256 digest_scheme file_format parser_version period_start period_end coverage_declared imported_at",
    "transactions": "id account_id document_id row_number fingerprint posted_on description reference debit_minor credit_minor balance_minor category reviewed overlap_possible excluded overlap_resolved",
    "audit_events": "id transaction_id old_category new_category old_excluded new_excluded old_overlap_resolved new_overlap_resolved note changed_at",
    "historical_filings": "id tax_year legal_entity kind filing_status revision_number revision_of_id source_sha256 fields_json imported_at",
    "owner_auth_state": "owner_id last_totp_step",
    "owner_sessions": "token_sha256 csrf_sha256 created_at expires_at revoked",
    "loan_accounts": "id legal_owner currency direction counterparty_label opening_as_of opening_principal_minor opening_basis created_at",
    "loan_allocations": "id loan_id transaction_id event_kind active principal_minor markup_minor evidence_note created_at",
    "transfer_confirmations": "id debit_transaction_id credit_transaction_id evidence_note active created_at",
    "loan_allocation_reversals": "id allocation_id reason created_at",
    "transfer_revocations": "id confirmation_id reason created_at",
    "cash_holdings": "id label legal_owner currency opening_as_of opening_minor evidence_basis created_at",
    "cash_movements": "id cash_id transaction_id kind amount_minor posted_on evidence_note active created_at",
    "cash_movement_reversals": "id movement_id reason created_at",
    "asset_snapshots": "id payload_json created_at",
    "private_financial_events": "id owner_hmac year_hmac source_hmac payload_json created_at",
    "confidential_bank_key_state": "id verifier_hmac sentinel",
    "confidential_bank_batches": "id owner_hmac account_hmac source_hmac payload_json created_at",
    "canonical_source_mirrors": "id source_hmac payload_json created_at",
}
SOURCE_COLUMNS = {name: tuple(value.split()) for name, value in SOURCE_COLUMNS.items()}
MAX_ROWS = 20_000
MAX_SOURCE_BYTES = 24 * 1024 * 1024
LEGACY_FINANCE_TABLES = frozenset({
    "accounts", "documents", "transactions", "audit_events",
    "historical_filings", "loan_accounts", "loan_allocations",
    "loan_allocation_reversals", "transfer_confirmations", "transfer_revocations",
    "cash_holdings", "cash_movements", "cash_movement_reversals", "asset_snapshots",
})


def _contract() -> None:
    if set(SOURCE_COLUMNS) != set(Base.metadata.tables):
        raise G1CPreflightBlocked("Unreviewed application source table inventory")
    for name, expected in SOURCE_COLUMNS.items():
        if set(expected) != set(Base.metadata.tables[name].columns.keys()):
            raise G1CPreflightBlocked("Unreviewed application source column inventory")
        if not Base.metadata.tables[name].primary_key.columns:
            raise G1CPreflightBlocked("Application source table lacks stable primary key")


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, default=str).encode("ascii")


def _tag(domain: bytes, value) -> str:
    return hmac.new(_index_key(), b"taxfin:g1c:preflight:v1:" + domain + b"\0" +
                    _canonical(value), sha256).hexdigest()


def _verified_envelopes(rows: dict[str, list[dict]]) -> None:
    """Check cryptographic authenticity, not merely the TFLE1 prefix."""
    for table, columns in ENCRYPTED_COLUMNS.items():
        if table not in rows:
            raise G1CPreflightBlocked("Encrypted table absent from source inventory")
        for row in rows[table]:
            for column in columns:
                token = row[column]
                if token is None:
                    continue
                if not isinstance(token, str) or not token.startswith(PREFIX):
                    raise G1CPreflightBlocked("Plaintext or invalid legacy encrypted column")
                try:
                    unseal(token, f"{table}.{column}")
                except Exception:
                    raise G1CPreflightBlocked("Legacy encryption authentication failed") from None


def analyze_source_rows(rows: dict[str, list[dict]]) -> dict:
    """Pure in-memory graph analysis; no source IDs, dates or money in response.

    Incomplete/ambiguous classifications are preserved as review-needed facts;
    no synthetic source record is dropped, silently rewritten or recategorized.
    """
    _contract()
    if set(rows) != set(SOURCE_COLUMNS):
        raise G1CPreflightBlocked("Source graph has missing or unknown tables")
    if sum(map(len, rows.values())) > MAX_ROWS:
        raise G1CPreflightBlocked("Source row limit exceeded; incomplete census forbidden")
    index = {}
    for table, entries in rows.items():
        if not isinstance(entries, list):
            raise G1CPreflightBlocked("Invalid source table rows")
        pk = tuple(col.name for col in Base.metadata.tables[table].primary_key.columns)
        indexed = {}
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != set(SOURCE_COLUMNS[table]):
                raise G1CPreflightBlocked("Unreviewed source row shape")
            key = tuple(entry[c] for c in pk)
            if None in key or key in indexed:
                raise G1CPreflightBlocked("Duplicate/null source primary key")
            indexed[key] = entry
        index[table] = indexed

    issues = Counter()
    def flag(table: str, code: str) -> None:
        issues[(table, code)] += 1

    # Every relationship is checked from the ORM's complete foreign-key map.
    # Precompute target indexes to avoid an O(n^2) scan of financial records.
    fk_targets = {
        (fk.column.table.name, fk.column.name)
        for table in Base.metadata.sorted_tables for fk in table.foreign_keys
    }
    fk_values = {
        (table, column): {entry[column] for entry in rows[table]}
        for table, column in fk_targets
    }
    for table in Base.metadata.sorted_tables:
        for entry in rows[table.name]:
            for fk in table.foreign_keys:
                parent_val = entry[fk.parent.name]
                if parent_val is None:
                    continue
                target = (fk.column.table.name, fk.column.name)
                if parent_val not in fk_values[target]:
                    flag(table.name, "BROKEN_SOURCE_LINK")

    accounts = {x["id"]: x for x in rows["accounts"]}
    documents = {x["id"]: x for x in rows["documents"]}
    transactions = {x["id"]: x for x in rows["transactions"]}
    loans = {x["id"]: x for x in rows["loan_accounts"]}
    cash = {x["id"]: x for x in rows["cash_holdings"]}
    unreviewed = 0
    direction_parity = defaultdict(lambda: [0, 0, 0, 0])  # all rows incl excluded/unreviewed
    for account in accounts.values():
        if account["currency"] != "PKR" or account["legal_owner"] != "individual":
            flag("accounts", "OWNER_OR_CURRENCY_REQUIRES_PLAN")

    for document in rows["documents"]:
        start, end = document["period_start"], document["period_end"]
        if (start is None) != (end is None) or (start is not None and start > end):
            flag("documents", "INVALID_SOURCE_PERIOD")
        if document["account_id"] not in accounts:
            flag("documents", "MISSING_ACCOUNT")

    for tx in rows["transactions"]:
        debit, credit = tx["debit_minor"], tx["credit_minor"]
        if (type(debit) is not int or type(credit) is not int or
            debit < 0 or credit < 0 or (debit > 0) == (credit > 0)):
            flag("transactions", "INVALID_DIRECTION")
        acc = accounts.get(tx["account_id"])
        doc = documents.get(tx["document_id"])
        if doc and doc["account_id"] != tx["account_id"]:
            flag("transactions", "DOCUMENT_ACCOUNT_MISMATCH")
        if doc and doc["coverage_declared"] and doc["period_start"] and doc["period_end"]:
            if not doc["period_start"] <= tx["posted_on"] <= doc["period_end"]:
                flag("transactions", "OUTSIDE_DECLARED_PERIOD")
        if not tx["reviewed"] or tx["overlap_possible"] and not tx["overlap_resolved"]:
            unreviewed += 1
        if acc and isinstance(tx["posted_on"], date) and type(debit) is int and type(credit) is int:
            group = direction_parity[(acc["legal_owner"], acc["currency"], tx["account_id"],
                                      tax_year_of(tx["posted_on"]))]
            group[0] += 1
            group[1] += debit
            group[2] += credit
            group[3] += int(bool(tx["excluded"]))

    for link in rows["transfer_confirmations"]:
        d = transactions.get(link["debit_transaction_id"])
        c = transactions.get(link["credit_transaction_id"])
        if d and c:
            a, b = accounts.get(d["account_id"]), accounts.get(c["account_id"])
            if (d["id"] == c["id"] or d["debit_minor"] <= 0 or c["credit_minor"] <= 0 or
                d["debit_minor"] != c["credit_minor"] or d["account_id"] == c["account_id"] or
                (a and b and (a["legal_owner"], a["currency"]) != (b["legal_owner"], b["currency"]))):
                flag("transfer_confirmations", "TRANSFER_PARITY_MISMATCH")

    for alloc in rows["loan_allocations"]:
        tx, loan = transactions.get(alloc["transaction_id"]), loans.get(alloc["loan_id"])
        if tx and loan:
            bank = accounts.get(tx["account_id"])
            if (alloc["principal_minor"] < 0 or alloc["markup_minor"] < 0 or
                alloc["principal_minor"] + alloc["markup_minor"] > max(tx["debit_minor"], tx["credit_minor"]) or
                (bank and (bank["legal_owner"], bank["currency"]) !=
                 (loan["legal_owner"], loan["currency"]))):
                flag("loan_allocations", "LOAN_SOURCE_PARITY_MISMATCH")

    for movement in rows["cash_movements"]:
        tx = transactions.get(movement["transaction_id"])
        holding = cash.get(movement["cash_id"])
        bank = accounts.get(tx["account_id"]) if tx else None
        if (movement["amount_minor"] <= 0 or
            (movement["kind"].startswith("bank_") != (movement["transaction_id"] is not None))):
            flag("cash_movements", "CASH_SOURCE_MISMATCH")
        if tx and (movement["amount_minor"] > max(tx["debit_minor"], tx["credit_minor"]) or
                   (movement["kind"] == "bank_withdrawal" and tx["debit_minor"] <= 0) or
                   (movement["kind"] == "bank_deposit" and tx["credit_minor"] <= 0) or
                   (bank and holding and (bank["legal_owner"], bank["currency"]) !=
                    (holding["legal_owner"], holding["currency"]))):
            flag("cash_movements", "CASH_BANK_PARITY_MISMATCH")

    for link_table, parent_table, parent_field in (
        ("loan_allocation_reversals", "loan_allocations", "allocation_id"),
        ("transfer_revocations", "transfer_confirmations", "confirmation_id"),
        ("cash_movement_reversals", "cash_movements", "movement_id"),
    ):
        parent = {item["id"]: item for item in rows[parent_table]}
        for reversal in rows[link_table]:
            entry = parent.get(reversal[parent_field])
            if entry and entry["active"]:
                flag(link_table, "REVERSAL_STILL_ACTIVE")

    for filing in rows["historical_filings"]:
        original = next((f for f in rows["historical_filings"] if f["id"] == filing["revision_of_id"]), None)
        if ((filing["revision_of_id"] is None) != (filing["filing_status"] == "filed_original") or
            (original and (original["tax_year"], original["kind"], original["legal_entity"]) !=
             (filing["tax_year"], filing["kind"], filing["legal_entity"]))):
            flag("historical_filings", "FILING_REVISION_INCONSISTENT")

    # A keyed fingerprint of *all* source columns, even rows marked excluded or
    # unreviewed. Values never appear in the audit receipt or public CI logs.
    fingerprint = []
    for table in sorted(SOURCE_COLUMNS):
        ordered = sorted(rows[table], key=lambda x: _canonical(
            [x[col.name] for col in Base.metadata.tables[table].primary_key.columns]))
        fingerprint.append([table, _tag(b"table", ordered)])
    parity = [[*key, *value] for key, value in sorted(direction_parity.items())]
    counts = {table: len(rows[table]) for table in sorted(SOURCE_COLUMNS)}
    return {
        "schema_revision": SCHEMA_REVISION, "synthetic_only": True,
        "read_only": True, "migration_performed": False,
        "backup_verified": False, "cutover_authorized": False,
        "source_tables": len(SOURCE_COLUMNS), "source_rows": sum(counts.values()),
        "table_counts": counts,
        "source_integrity_hmac": _tag(b"all-tables", fingerprint),
        "year_owner_account_direction_hmac": _tag(b"year-owner-account", parity),
        "financial_group_count": len(parity),
        "review_needed_transactions": unreviewed,
        "blocking_issues": [
            {"table": table, "code": code, "count": number}
            for (table, code), number in sorted(issues.items())
        ],
        "source_graph_consistent": not issues,
        "candidate_requires_verified_encrypted_backup_and_independent_restore": True,
        "actual_private_canonical_ledger_ready": False,
        "fbr_ready": False, "tax_due_minor": None,
    }


def preflight_postgres_source(*, restored_candidate: bool = False) -> dict:
    """Read-only PG18 preflight from explicit environment-only synthetic DSN."""
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise G1CPreflightBlocked("G1-c source inspection prohibited for real data")
    _contract()
    _index_key()  # No public/unkeyed aggregate financial digest fallback.
    dsn, _ = _connection_config(
        "PG_SNAPSHOT_RESTORE_DSN" if restored_candidate else "PG_G1C_SOURCE_DSN",
        restore=restored_candidate,
    )
    try:
        import psycopg
        from psycopg import sql
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                _table_names(conn)  # strict database inventory + exact Alembic revision
                rows: dict[str, list[dict]] = {}
                total = 0
                for table in sorted(SOURCE_COLUMNS):
                    actual_cols = {r[0] for r in conn.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = %s", (table,)
                    ).fetchall()}
                    if actual_cols != set(SOURCE_COLUMNS[table]):
                        raise G1CPreflightBlocked("Unreviewed PostgreSQL column inventory")
                    count = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(
                        sql.Identifier("public", table))).fetchone()[0]
                    total += count
                    if total > MAX_ROWS:
                        raise G1CPreflightBlocked("Source census exceeds hard row limit")
                    model = Base.metadata.tables[table]
                    names = [x.name for x in model.primary_key.columns]
                    query = sql.SQL("SELECT * FROM {} ORDER BY {}").format(
                        sql.Identifier("public", table),
                        sql.SQL(",").join(sql.Identifier(name) for name in names))
                    with conn.cursor() as cur:
                        cur.execute(query)
                        cols = [desc.name for desc in cur.description]
                        table_rows = [dict(zip(cols, data)) for data in cur.fetchall()]
                    rows[table] = table_rows
                if len(_canonical(rows)) > MAX_SOURCE_BYTES:
                    raise G1CPreflightBlocked("Source census exceeds hard in-memory byte limit")
                _verified_envelopes(rows)
                return analyze_source_rows(rows)
    except G1CPreflightBlocked:
        raise
    except Exception:
        # No source values, connection strings, database identifiers or keys in errors.
        raise G1CPreflightBlocked("Synthetic PostgreSQL source preflight failed closed") from None
