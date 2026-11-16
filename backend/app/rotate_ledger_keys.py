"""Offline synthetic-only, atomic rotation of encrypted ledger text.

Execution must happen during an application maintenance window, with an encrypted
backup made separately. Source and target key IDs must both be configured. No
plaintext data is ever persisted. Encrypted numeric data remains out of scope.
"""
from __future__ import annotations

import argparse
import os
from sqlalchemy import create_engine, inspect
from .ledger_crypto import ENCRYPTED_COLUMNS, LedgerKeyError, envelope_key_id, keyring, seal, unseal

# Reviewed schema exceptions: not every encrypted source table has an "id" PK.
PRIMARY_KEYS = {table: "id" for table in ENCRYPTED_COLUMNS}
PRIMARY_KEYS["owner_recovery_states"] = "owner_hmac"


def rotate_fields(engine, *, new_key_id: str, dry_run: bool = True) -> dict[str, int]:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise LedgerKeyError("Rotation helper is synthetic-only")
    _, keys = keyring()
    if new_key_id not in keys:
        raise LedgerKeyError("Target key id not present")
    count: dict[str, int] = {}
    # Atomic transaction: exceptions roll back all SQL updates.
    with engine.begin() as connection:
        present_tables = set(inspect(connection).get_table_names())
        for table, columns in ENCRYPTED_COLUMNS.items():
            # Old synthetic fixtures and older schema versions legitimately lack
            # newer tables. Never invent data or silently convert legacy values.
            if table not in present_tables:
                continue
            pk = PRIMARY_KEYS[table]
            rows = connection.exec_driver_sql(f"SELECT {pk}, {', '.join(columns)} FROM {table}").all()
            for idx, col in enumerate(columns, 1):
                key = f"{table}.{col}"
                count[key] = 0
                for row in rows:
                    old = row[idx]
                    if old is None:
                        continue
                    existing_key_id = envelope_key_id(old)  # Reject legacy plaintext.
                    if existing_key_id == new_key_id:
                        # Still verify integrity before reporting no action.
                        unseal(old, key)
                        continue
                    clear = unseal(old, key)
                    if not dry_run:
                        rotated = seal(clear, key, key_id=new_key_id)
                        connection.exec_driver_sql(
                            f"UPDATE {table} SET {col} = ? WHERE {pk} = ?" if engine.dialect.name == "sqlite" else
                            f"UPDATE {table} SET {col} = %s WHERE {pk} = %s",
                            (rotated, row[0]),
                        )
                    count[key] += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate synthetic encrypted ledger text (offline).")
    parser.add_argument("--db-url", required=True, help="Existing synthetic SQLite or PostgreSQL DSN")
    parser.add_argument("--new-key-id", required=True)
    parser.add_argument("--apply", action="store_true", help="Otherwise dry run only")
    args = parser.parse_args()
    if not args.db_url.startswith(("sqlite:///", "postgresql+psycopg://")):
        parser.error("Only SQLite or PostgreSQL+psycopg supported")
    engine = create_engine(args.db_url)
    try:
        result = rotate_fields(engine, new_key_id=args.new_key_id, dry_run=not args.apply)
        print({"dry_run": not args.apply, "encrypted_values_to_rotate": result})
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()