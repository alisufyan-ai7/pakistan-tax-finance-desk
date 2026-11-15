"""M2r: synthetic-only, encrypted-only SQLite finance archive (not a live database).

A deliberately explicit offline operation: creates an encrypted backup of the
source, independently restores it to a temporary protected directory, and seals
*every* recognized application table and row into a new archive containing only
ciphertext and HMAC blind IDs. Verifies full content parity and in-memory schema
reconstruction; never replaces, deletes or rewrites the source database.

The separate legacy SQL database and its old plaintext fields remain unchanged.
This is a small bounded synthetic engineering tool, NOT a real-data migrator.
"""
from __future__ import annotations

import argparse
import base64
import hmac
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import tempfile
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .db import Base
from . import models  # register all expected application tables
from .ledger_crypto import keyring
from .private_events import _index_key
from .privacy_fingerprints import _key as dedup_key
from .synthetic_backup import create_backup, restore_backup, _key as backup_key

FORMAT = 'TFPA1'
MAX_ROWS = 30_000
MAX_SERIALIZED_BYTES = 32 * 1024 * 1024
_TABLE_NAME = re.compile(r'^[a-z][a-z0-9_]{0,63}$')


class ArchiveBlocked(ValueError):
    """Source or output cannot be proven safe or complete."""


def _env_key(name: str) -> bytes:
    encoded = os.getenv(name, '')
    try:
        value = base64.b64decode(encoded, altchars=b'-_', validate=True)
    except (ValueError, UnicodeError) as exc:
        raise ArchiveBlocked(f'{name} must be base64 encoded') from exc
    if len(value) != 32:
        raise ArchiveBlocked(f'{name} must be a unique 32-byte key')
    return value


def _keys() -> tuple[bytes, bytes]:
    if os.getenv('APP_DATA_MODE', 'synthetic') != 'synthetic':
        raise ArchiveBlocked('Real financial records are prohibited')
    archive = _env_key('CONFIDENTIAL_ARCHIVE_KEY')
    idx = _env_key('CONFIDENTIAL_ARCHIVE_INDEX_KEY')
    _, ring = keyring()
    all_keys = [archive, idx, *ring.values(), _index_key(), dedup_key(), backup_key()]
    if len(set(all_keys)) != len(all_keys):
        raise ArchiveBlocked('Archive, ledger, blind-index and backup keys must all differ')
    return archive, idx


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _q(name: str) -> str:
    if not _TABLE_NAME.fullmatch(name) and name != 'alembic_version':
        raise ArchiveBlocked('Unexpected SQL identifier in source')
    return '"' + name + '"'


def _encoded_cell(v: Any) -> list[Any]:
    if v is None:
        return ['null', None]
    if isinstance(v, int):
        return ['integer', str(v)]
    if isinstance(v, float):
        return ['real', repr(v)]
    if isinstance(v, str):
        return ['text', v]
    if isinstance(v, bytes):
        return ['blob', base64.b64encode(v).decode('ascii')]
    raise ArchiveBlocked('Unsupported source SQLite value type')


def _decoded_cell(v: list[Any]) -> Any:
    if not isinstance(v, list) or len(v) != 2:
        raise ArchiveBlocked('Invalid sealed cell format')
    kind, value = v
    if kind == 'null' and value is None: return None
    if kind == 'integer': return int(value)
    if kind == 'real': return float(value)
    if kind == 'text' and isinstance(value, str): return value
    if kind == 'blob': return base64.b64decode(value, validate=True)
    raise ArchiveBlocked('Unexpected sealed cell format')


def _inventory(path: Path, index_key: bytes) -> tuple[dict, list[tuple[str, str, bytes]], str]:
    if not path.is_file() or path.is_symlink():
        raise ArchiveBlocked('A regular synthetic SQLite source is required')
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise ArchiveBlocked('Source SQLite integrity check failed')
        tables = {row[0]: row[1] for row in conn.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        expected = set(Base.metadata.tables)
        if tables.keys() - (expected | {'alembic_version'}) or expected - tables.keys():
            raise ArchiveBlocked('Unrecognized or missing financial table; refuse incomplete export')
        schema: dict[str, dict] = {}
        rows: list[tuple[str, str, bytes]] = []
        digest = hmac.new(index_key, b'taxfin:m2r:inventory:v1\0', hashlib.sha256)
        bytes_seen = 0
        for table in sorted(tables):
            fields = list(conn.execute(f'PRAGMA table_info({_q(table)})'))
            column_names = [row[1] for row in fields]
            pks = [v[1] for v in sorted((x for x in fields if x[5] > 0), key=lambda x: x[5])]
            if not pks or not tables[table] or not column_names:
                raise ArchiveBlocked('Missing source primary key, schema or columns')
            schema[table] = {'ddl': tables[table], 'columns': column_names, 'pk': pks, 'count': 0}
            pk_indices = [column_names.index(p) for p in pks]
            for value_row in conn.execute(f'SELECT * FROM {_q(table)} ORDER BY ' + ','.join(_q(p) for p in pks)):
                if len(value_row) != len(column_names):
                    raise ArchiveBlocked('Source row/schema mismatch')
                encoded = [_encoded_cell(v) for v in value_row]
                source_pk = _json_bytes([encoded[i] for i in pk_indices])
                row_hmac = hmac.new(index_key, b'taxfin:m2r:row-index:v1\0' + table.encode() + b'\0' + source_pk, hashlib.sha256).hexdigest()
                payload = _json_bytes({'table':table,'values':encoded,'format':FORMAT})
                bytes_seen += len(payload)
                if bytes_seen > MAX_SERIALIZED_BYTES or len(rows) >= MAX_ROWS:
                    raise ArchiveBlocked('Unbounded source size: offline synthetic limit exceeded')
                digest.update(_json_bytes([table, row_hmac, payload.decode('ascii')]) + b'\n')
                rows.append((table, row_hmac, payload))
                schema[table]['count'] += 1
        return schema, rows, digest.hexdigest()


def _aad(kind: str, name: str = '') -> bytes:
    return ('taxfin:m2r:aesgcm:v1:' + kind + ':' + name).encode('ascii')


def _seal(key: bytes, payload: bytes, kind: str, name: str = '') -> bytes:
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, payload, _aad(kind, name))


def _unseal(key: bytes, payload: bytes, kind: str, name: str = '') -> bytes:
    if len(payload) < 28:
        raise ArchiveBlocked('Truncated sealed archive row')
    return AESGCM(key).decrypt(payload[:12], payload[12:], _aad(kind, name))


def _create_archive(path: Path, key: bytes, schema: dict, rows: list[tuple[str, str, bytes]], source_hmac: str) -> None:
    # Only sealed payloads / keyed identifiers / fixed domain labels are stored.
    with sqlite3.connect(path) as conn:
        conn.execute('PRAGMA journal_mode=DELETE')
        conn.execute('CREATE TABLE sealed_manifest (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL)')
        conn.execute('CREATE TABLE sealed_records (kind TEXT NOT NULL, blind_id TEXT PRIMARY KEY, payload BLOB NOT NULL)')
        header = _json_bytes({'version':FORMAT, 'schema':schema, 'source_hmac':source_hmac,
                              'total_rows':len(rows)})
        conn.execute('INSERT INTO sealed_manifest VALUES (1,?)', (_seal(key, header, 'manifest'),))
        conn.executemany('INSERT INTO sealed_records VALUES (?,?,?)', (
            (kind, blind, _seal(key, payload, 'row:'+kind, blind)) for kind, blind, payload in rows
        ))
        conn.commit()


def verify_sealed_archive(path: str | Path, *, expected_source_hmac: str | None = None) -> dict:
    """Verify every encrypted row and rebuild the source tables in RAM only."""
    key, index = _keys()
    file = Path(path)
    if not file.is_file() or file.is_symlink():
        raise ArchiveBlocked('Sealed archive does not exist')
    with sqlite3.connect(f'file:{file}?mode=ro', uri=True) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise ArchiveBlocked('Sealed archive integrity check failed')
        actual_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if actual_tables != {'sealed_manifest','sealed_records'}:
            raise ArchiveBlocked('Archive includes unexpected plaintext tables')
        item = conn.execute('SELECT payload FROM sealed_manifest WHERE id=1').fetchone()
        if not item or conn.execute('SELECT count(*) FROM sealed_manifest').fetchone()[0] != 1:
            raise ArchiveBlocked('Archive manifest is missing or duplicated')
        manifest = json.loads(_unseal(key, item[0], 'manifest'))
        if manifest.get('version') != FORMAT or not isinstance(manifest.get('schema'),dict):
            raise ArchiveBlocked('Unsupported private archive manifest')
        source_hmac = manifest['source_hmac']
        if expected_source_hmac is not None and not hmac.compare_digest(source_hmac,expected_source_hmac):
            raise ArchiveBlocked('Source digest differs from independently verified backup')
        with sqlite3.connect(':memory:') as rebuild:
            rebuild.execute('PRAGMA foreign_keys=OFF')
            # Recreate in memory, including original dated/amount fields, never on disk.
            schema = manifest['schema']
            if set(schema) - (set(Base.metadata.tables)|{'alembic_version'}) or set(Base.metadata.tables) - set(schema):
                raise ArchiveBlocked('Archive schema is incomplete or contains unknown tables')
            for table in sorted(schema):
                if not _TABLE_NAME.fullmatch(table) or not isinstance(schema[table]['ddl'],str):
                    raise ArchiveBlocked('Invalid archive schema')
                rebuild.execute(schema[table]['ddl'])
            counts = {table:0 for table in schema}
            digest = hmac.new(index, b'taxfin:m2r:inventory:v1\0', hashlib.sha256)
            records = list(conn.execute('SELECT kind,blind_id,payload FROM sealed_records ORDER BY kind,blind_id'))
            if len(records) != manifest['total_rows'] or len(records) > MAX_ROWS:
                raise ArchiveBlocked('Archive records missing or excessive')
            # Recover canonical source sort order using sealed primary keys.
            decoded=[]
            for kind, blind, ciphertext in records:
                if kind not in schema or not isinstance(blind,str) or len(blind)!=64:
                    raise ArchiveBlocked('Unexpected archive record metadata')
                decoded_value = _unseal(key,ciphertext,'row:'+kind,blind)
                value = json.loads(decoded_value)
                if value.get('table')!=kind or value.get('format')!=FORMAT:
                    raise ArchiveBlocked('Archive row authentication mismatch')
                cols=schema[kind]['columns']
                cells=value['values']
                if len(cells)!=len(cols):
                    raise ArchiveBlocked('Sealed data and schema disagree')
                pk_indices=[cols.index(k) for k in schema[kind]['pk']]
                pk=_json_bytes([cells[i] for i in pk_indices])
                check=hmac.new(index,b'taxfin:m2r:row-index:v1\0'+kind.encode()+b'\0'+pk,hashlib.sha256).hexdigest()
                if not hmac.compare_digest(check,blind):
                    raise ArchiveBlocked('Blind index does not match authenticated row')
                decoded.append((kind, pk, blind, decoded_value, [_decoded_cell(c) for c in cells]))
                counts[kind]+=1
            for kind,pk,blind,raw,vals in sorted(decoded,key=lambda r:(r[0],r[1])):
                digest.update(_json_bytes([kind,blind,raw.decode('ascii')])+b'\n')
                q=','.join('?' for _ in vals)
                rebuild.execute(f'INSERT INTO {_q(kind)} VALUES ({q})',vals)
            if counts!={t:schema[t]['count'] for t in schema} or not hmac.compare_digest(digest.hexdigest(),source_hmac):
                raise ArchiveBlocked('Source counts or HMAC parity mismatch')
            if rebuild.execute('PRAGMA foreign_key_check').fetchone():
                raise ArchiveBlocked('In-memory source foreign-key constraints failed')
            if rebuild.execute('PRAGMA integrity_check').fetchone()!=('ok',):
                raise ArchiveBlocked('In-memory source reconstruction failed')
        return {'synthetic_only':True,'sealed_only':True,'verified':True,
                'source_rows':sum(counts.values()),'source_tables':len(counts),
                'source_hmac':source_hmac,'plaintext_legacy_tables_present':False,
                'active_financial_database':False,'tax_due_minor':None}


def _safe_paths(source: Path, evidence: Path, backup: Path, output: Path, receipt: Path | None) -> None:
    if not source.is_file() or source.is_symlink():
        raise ArchiveBlocked('Existing regular synthetic SQLite source required')
    with source.open('rb') as f:
        if f.read(16) != b'SQLite format 3\x00':
            raise ArchiveBlocked('Invalid SQLite source header')
    destinations=[backup,output]+([receipt] if receipt is not None else [])
    if len({v.resolve() for v in [source,*destinations]}) != len(destinations)+1:
        raise ArchiveBlocked('Source and encrypted outputs must not overlap')
    if any(p.exists() or p.is_symlink() for p in destinations):
        raise ArchiveBlocked('Never overwrite an archive, backup or receipt')
    if evidence.is_symlink() or any(p.resolve().is_relative_to(evidence.resolve()) for p in destinations):
        raise ArchiveBlocked('Do not place encrypted outputs inside evidence vault')


def _receipt(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(result,f,sort_keys=True,separators=(',',':'))
            f.write('\n');f.flush();os.fsync(f.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def export_synthetic_archive(source: str | Path, evidence_dir: str | Path,
                             encrypted_backup: str | Path, archive_file: str | Path,
                             *, receipt_file: str | Path | None = None,
                             inject_failure_after_backup: bool = False) -> dict:
    """Create a recoverable sealed artifact without altering original SQLite."""
    key,index=_keys()
    source=Path(source).absolute();evidence=Path(evidence_dir).absolute()
    backup=Path(encrypted_backup).absolute();output=Path(archive_file).absolute()
    receipt=Path(receipt_file).absolute() if receipt_file is not None else None
    _safe_paths(source,evidence,backup,output,receipt)
    before_schema,before_rows,before_hmac=_inventory(source,index)
    backup_meta=create_backup(source,evidence,backup)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.archive-verify-',dir=output.parent) as scratch:
        restored=Path(scratch)/'restore'
        restore_backup(backup,restored)
        if inject_failure_after_backup:
            raise ArchiveBlocked('Injected failure after backup; source remains untouched')
        restored_schema,restored_rows,restored_hmac=_inventory(restored/'finance.db',index)
        if before_hmac!=restored_hmac or before_schema!=restored_schema:
            raise ArchiveBlocked('Independent restore differs from source')
        temp=Path(scratch)/'sealed-finance.db'
        _create_archive(temp,key,restored_schema,restored_rows,restored_hmac)
        check=verify_sealed_archive(temp,expected_source_hmac=before_hmac)
        final_schema,final_rows,final_hmac=_inventory(source,index)
        if final_hmac!=before_hmac or final_schema!=before_schema:
            raise ArchiveBlocked('Source changed during offline archive construction')
        output.parent.mkdir(parents=True,exist_ok=True)
        os.chmod(temp,0o600)
        # Link atomically without overwriting any pre-existing target.
        os.link(temp,output)
        try:
            final=verify_sealed_archive(output,expected_source_hmac=before_hmac)
        except BaseException:
            output.unlink(missing_ok=True)
            raise
    result={**check,'archive_verified_after_publish':final['verified'],
            'original_source_retained':True,'original_source_plaintext_still_present':True,
            'encrypted_backup_sha256':backup_meta['ciphertext_sha256'],
            'archive_format':FORMAT,'promoted_to_live':False,'real_data_approved':False}
    if receipt is not None:
        try:
            _receipt(receipt,result)
        except BaseException:
            # Do not leave a published candidate with an incomplete audit.
            output.unlink(missing_ok=True)
            raise
    return result


def main():
    parser=argparse.ArgumentParser(description='OFFLINE synthetic-only sealed legacy archive; NO production switch')
    parser.add_argument('--sqlite-db',required=True)
    parser.add_argument('--evidence-dir',required=True)
    parser.add_argument('--encrypted-backup',required=True)
    parser.add_argument('--sealed-archive',required=True)
    parser.add_argument('--receipt',required=True)
    args=parser.parse_args()
    print(json.dumps(export_synthetic_archive(args.sqlite_db,args.evidence_dir,args.encrypted_backup,
        args.sealed_archive,receipt_file=args.receipt),sort_keys=True))

if __name__=='__main__': main()