"""Offline-only M2o synthetic bank transaction migration to a restored candidate.

This intentionally NEVER modifies the source database, changes app summaries,
starts from a GET request, or promotes the migrated database. A verified encrypted
backup is restored in a new location; only the restored candidate is changed.
The original loan/cash numeric schema STILL contains plaintext and real data is
prohibited. This is a migration verification tool, not a production cutover.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import sqlite3
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typing import Any
import uuid

from .models import Account, PrivateFinancialEvent, Transaction
from .private_events import PrivateEventInput, _canonical, _index_key, blind_index, tax_year_of
from .private_migration_preview import EVENT_TYPES, legacy_source_ref
from .ledger_crypto import keyring, LedgerKeyError
from .privacy_fingerprints import _key as bank_dedup_key
from .synthetic_backup import create_backup, restore_backup, _key as backup_key

MAX_SOURCE_ROWS = 20_000


class MigrationBlocked(ValueError):
    """A synthetic candidate cannot be migrated without owner review or safe inputs."""


def _require_keys_and_mode() -> None:
    if os.getenv('APP_DATA_MODE', 'synthetic') != 'synthetic':
        raise MigrationBlocked('Real financial-data migration is prohibited')
    _, aes_keys = keyring()
    keys = list(aes_keys.values()) + [_index_key(), bank_dedup_key(), backup_key()]
    if len(set(keys)) != len(keys):
        raise MigrationBlocked('Synthetic migration requires distinct encryption, HMAC and backup keys')


def _hmac_json(domain: str, payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hmac.new(_index_key(), b'taxfin:m2o:' + domain.encode() + b'\0' + encoded, hashlib.sha256).hexdigest()


def _source_inventory(db: Session) -> tuple[list[tuple[Transaction, PrivateEventInput]], str]:
    txs = db.scalars(select(Transaction).order_by(Transaction.posted_on, Transaction.id).limit(MAX_SOURCE_ROWS + 1)).all()
    if not txs:
        raise MigrationBlocked('No synthetic source transactions to migrate')
    if len(txs) > MAX_SOURCE_ROWS:
        raise MigrationBlocked('Source scan truncated: reduce scope before migration')
    accounts = {a.id: a for a in db.scalars(select(Account)).all()}
    batch = []
    signature_rows = []
    for tx in txs:
        acc = accounts.get(tx.account_id)
        if acc is None or acc.currency != 'PKR' or acc.legal_owner != 'individual':
            raise MigrationBlocked('Unsupported source ownership or currency')
        if tx.excluded or not tx.reviewed or tx.category == 'unreviewed':
            raise MigrationBlocked('Every source row requires explicit classification and inclusion review')
        if tx.overlap_possible and not tx.overlap_resolved:
            raise MigrationBlocked('Unresolved bank statement overlap')
        if tx.category not in EVENT_TYPES:
            raise MigrationBlocked('Unsupported reviewed transaction category')
        if (tx.debit_minor > 0) == (tx.credit_minor > 0):
            raise MigrationBlocked('Invalid source cash movement direction')
        posted = tx.posted_on
        if not (date(2022, 7, 1) <= posted <= date(2100, 6, 30)):
            raise MigrationBlocked('Transaction date is outside supported synthetic years')
        try:
            payload = PrivateEventInput(
                synthetic_fixture=True, legal_owner='individual', currency='PKR',
                source_ref=legacy_source_ref(tx.id), source_type='synthetic_bank',
                event_kind=EVENT_TYPES[tx.category], posted_on=posted,
                amount_minor=tx.debit_minor or tx.credit_minor, account_ref=tx.account_id,
                counterparty=None,
                evidence_note='Explicit synthetic M1 reviewed ledger source for migration preview',
                reviewed=False, direction='debit' if tx.debit_minor else 'credit',
            )
        except ValueError as exc:
            raise MigrationBlocked('Source financial event failed strict validation') from exc
        batch.append((tx, payload))
        signature_rows.append({
            'id': tx.id, 'account': tx.account_id, 'date': posted.isoformat(),
            'debit': tx.debit_minor, 'credit': tx.credit_minor,
            'balance': tx.balance_minor, 'category': tx.category,
            'reviewed': tx.reviewed, 'excluded': tx.excluded,
            'overlap_possible': tx.overlap_possible, 'overlap_resolved': tx.overlap_resolved,
            'source_document_id': tx.document_id, 'source_row': tx.row_number,
        })
    return batch, _hmac_json('source-ledger:v1', signature_rows)


def _mirror_parity(db: Session, batch: list[tuple[Transaction, PrivateEventInput]]) -> tuple[int, str]:
    """Check source -> encrypted event identity and FY/account direction+amount parity.

    The HMAC receipt hides actual monetary aggregates. Raw/source account IDs,
    dates, descriptions and amounts are never written into the receipt.
    """
    expected_by_source = {p.source_ref: p for _, p in batch}
    expected_group = defaultdict(lambda: [0, 0, 0])  # count, debit, credit
    actual_group = defaultdict(lambda: [0, 0, 0])
    for tx, p in batch:
        key = (tax_year_of(tx.posted_on), tx.account_id)
        e = expected_group[key]
        e[0] += 1; e[1] += tx.debit_minor; e[2] += tx.credit_minor

    count = 0
    seen = set()
    all_events = db.scalars(select(PrivateFinancialEvent)).all()
    for row in all_events:
        try:
            data = json.loads(row.payload_json)  # authenticated decrypt via ORM
            ref = data['source_ref']
        except (ValueError, KeyError, TypeError) as exc:
            raise MigrationBlocked('Unreadable encrypted event in candidate') from exc
        if not isinstance(ref, str) or not ref.startswith('legacy-m1:'):
            continue  # independent synthetic events, never counted as bank mirrors
        expected = expected_by_source.get(ref)
        if expected is None or ref in seen:
            raise MigrationBlocked('Unexpected or duplicated legacy mirror in candidate')
        seen.add(ref)
        if (row.source_hmac != blind_index('source', 'individual:' + ref) or
            row.owner_hmac != blind_index('owner', 'individual') or
            row.year_hmac != blind_index('year', f'individual:{tax_year_of(expected.posted_on)}') or
            row.payload_json != _canonical(expected)):
            raise MigrationBlocked('Encrypted mirror/index does not match original source')
        key = (tax_year_of(expected.posted_on), expected.account_ref)
        actual = actual_group[key]
        actual[0] += 1
        if expected.direction == 'debit':
            actual[1] += expected.amount_minor
        else:
            actual[2] += expected.amount_minor
        count += 1
    if count != len(batch) or dict(expected_group) != dict(actual_group):
        raise MigrationBlocked('Financial year/account debit-credit parity failed')
    digest_rows = [
        [tax_year, account_id, *expected_group[(tax_year, account_id)]]
        for tax_year, account_id in sorted(expected_group)
    ]
    return count, _hmac_json('year-account-parity:v1', digest_rows)


def _db_session(path: Path) -> tuple[Any, Session]:
    engine = create_engine(f'sqlite:///{path}', pool_pre_ping=True)
    return engine, Session(engine, expire_on_commit=False)


def _require_safe_paths(database: Path, evidence: Path, backup: Path, target: Path, receipt: Path | None) -> None:
    if not database.is_file() or database.is_symlink():
        raise MigrationBlocked('Offline SQLite source must be an existing regular file')
    with database.open('rb') as stream:
        if stream.read(16) != b'SQLite format 3\x00':
            raise MigrationBlocked('Source is not an SQLite database')
    if backup.exists() or target.exists() or (receipt is not None and receipt.exists()):
        raise MigrationBlocked('Backup, candidate and optional audit receipt paths must be new')
    paths = [database.resolve(), backup.resolve(), target.resolve()]
    if len(set(paths)) != len(paths) or target == database.parent or database.is_relative_to(target):
        raise MigrationBlocked('Migration output paths overlap with source database')
    if evidence.exists() and evidence.is_symlink():
        raise MigrationBlocked('Unsafe evidence path')
    if target.is_relative_to(evidence) and evidence.exists():
        raise MigrationBlocked('Candidate must not live inside evidence vault')
    if receipt is not None and (receipt.resolve() in paths or receipt.is_relative_to(target)):
        raise MigrationBlocked('Audit receipt output overlaps migration artifacts')


def _write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(receipt, stream, sort_keys=True, separators=(',', ':'))
            stream.write('\n')
            stream.flush(); os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def migrate_restored_synthetic_candidate(
    database: str | Path, evidence_dir: str | Path, backup_file: str | Path,
    candidate_directory: str | Path, *, receipt_file: str | Path | None = None,
    inject_failure_after: int | None = None,
) -> dict:
    """Verified, explicit synthetic-only *candidate* copy, never live promotion.

    No API endpoint invokes this method. On an error the new candidate is removed;
    the encrypted backup and original source remain intact for investigation.
    """
    _require_keys_and_mode()
    if Path(database).is_symlink():
        raise MigrationBlocked('Synthetic source database symlink not permitted')
    source, evidence = Path(database).resolve(), Path(evidence_dir).resolve()
    backup, target = Path(backup_file).resolve(), Path(candidate_directory).resolve()
    receipt = Path(receipt_file).resolve() if receipt_file is not None else None
    _require_safe_paths(source, evidence, backup, target, receipt)

    original_engine, original_db = _db_session(source)
    try:
        source_batch, source_hmac = _source_inventory(original_db)
        original_db.rollback()
    finally:
        original_db.close(); original_engine.dispose()

    backup_meta = create_backup(source, evidence, backup)
    restored = False
    try:
        restore_meta = restore_backup(backup, target)
        restored = True
        working = target / 'finance.db'
        candidate_engine, db = _db_session(working)
        try:
            batch, candidate_hmac = _source_inventory(db)
            if candidate_hmac != source_hmac or len(batch) != len(source_batch):
                raise MigrationBlocked('Backup-restore candidate and original source differ')
            existing = db.scalars(select(PrivateFinancialEvent)).all()
            index = {row.source_hmac: row for row in existing}
            created = 0
            for tx, payload in batch:
                tag = blind_index('source', 'individual:' + payload.source_ref)
                canonical = _canonical(payload)
                old = index.get(tag)
                if old is not None:
                    if old.payload_json != canonical:
                        raise MigrationBlocked('Existing private mirror contradicts original source')
                    continue
                row = PrivateFinancialEvent(
                    id=str(uuid.uuid4()),
                    owner_hmac=blind_index('owner', 'individual'),
                    year_hmac=blind_index('year', f'individual:{tax_year_of(payload.posted_on)}'),
                    source_hmac=tag, payload_json=canonical,
                )
                db.add(row)
                index[tag] = row
                created += 1
                if inject_failure_after is not None and created >= inject_failure_after:
                    raise MigrationBlocked('Injected synthetic failure before transaction commit')
            db.flush()
            confirmed, parity_hmac = _mirror_parity(db, batch)
            db.commit()
            # Re-check committed ciphertext and HMAC equality, not only in-memory rows.
            confirmed_after, parity_after = _mirror_parity(db, batch)
            if confirmed_after != confirmed or parity_after != parity_hmac:
                raise MigrationBlocked('Committed candidate parity differs from precommit verification')
            db.rollback()
        finally:
            db.close(); candidate_engine.dispose()

        with sqlite3.connect(f'file:{working}?mode=ro', uri=True) as physical:
            if physical.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise MigrationBlocked('Post-migration candidate SQLite integrity failure')

        fresh_engine, fresh_db = _db_session(source)
        try:
            _, latest_hmac = _source_inventory(fresh_db)
            if latest_hmac != source_hmac:
                raise MigrationBlocked('Original source changed during offline candidate construction')
        finally:
            fresh_db.close(); fresh_engine.dispose()

        receipt_data = {
            'schema': 'synthetic-private-migration-candidate-v1',
            'synthetic_only': True,
            'candidate_verified': True,
            'migration_promoted': False,
            'old_ledger_authoritative': True,
            'original_retained': True,
            'verified_restored_backup': restore_meta['sqlite_integrity_check'] == 'ok',
            'source_count': len(batch),
            'mirrors_verified': confirmed,
            'new_private_event_mirrors': created,
            'source_hmac': source_hmac,
            'year_account_parity_hmac': parity_hmac,
            'encrypted_backup_sha256': backup_meta['ciphertext_sha256'],
            'candidate_contains_plaintext_legacy_tables': True,
            'complete_wealth_or_tax_reconciliation': False,
            'tax_due_minor': None,
        }
        if receipt is not None:
            _write_receipt(receipt, receipt_data)
        return receipt_data
    except BaseException:
        if restored:
            # Only our freshly-created restore directory is removed. Never the
            # source database or persistent encrypted recovery backup.
            shutil.rmtree(target)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description='OFFLINE synthetic-only restored-candidate migrator; never promotes source')
    parser.add_argument('--sqlite-db', required=True)
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--encrypted-backup', required=True)
    parser.add_argument('--candidate-dir', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    result = migrate_restored_synthetic_candidate(
        args.sqlite_db, args.evidence_dir, args.encrypted_backup,
        args.candidate_dir, receipt_file=args.receipt,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()