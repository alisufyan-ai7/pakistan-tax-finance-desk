"""Encrypted, integrity-checked, *synthetic-only* SQLite + evidence backups.

Never deploy this to production: it deliberately does not support PostgreSQL,
production key rotation, external object storage or disaster-recovery scheduling.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from secrets import token_bytes
import shutil
import zipfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b'TFBK1'
MAX_ARCHIVE = 40 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_EVIDENCE_FILES = 500
EVIDENCE_NAME = re.compile(r'^evidence/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.evd$')

class BackupError(ValueError):
    pass

def _key() -> bytes:
    encoded = os.environ.get('BACKUP_KEY', '')
    try:
        key = base64.b64decode(encoded.encode('ascii'), altchars=b'-_', validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise BackupError('BACKUP_KEY must be valid urlsafe base64') from exc
    if len(key) != 32:
        raise BackupError('BACKUP_KEY must represent exactly 32 bytes')
    return key

def _assert_synthetic():
    if os.getenv('APP_DATA_MODE', 'synthetic') != 'synthetic':
        raise BackupError('This backup tool permits synthetic demo data only')

def create_backup(sqlite_path: str | Path, evidence_dir: str | Path, output: str | Path) -> dict:
    """Use SQLite's snapshot API so WAL/active transactions are not lost."""
    _assert_synthetic()
    key = _key()
    db_path, ev_dir, output = Path(sqlite_path), Path(evidence_dir), Path(output)
    if not db_path.is_file() or db_path.is_symlink():
        raise BackupError('Synthetic SQLite database is missing or unsafe')
    if output.exists():
        raise FileExistsError('Backup already exists; never overwrite')
    if output.parent.resolve() == ev_dir.resolve():
        raise BackupError('Backup output must not be inside evidence directory')
    files: dict[str,bytes] = {}
    with tempfile.TemporaryDirectory() as temp:
        snap = Path(temp) / 'snapshot.db'
        with sqlite3.connect(f'file:{db_path}?mode=ro', uri=True) as source, sqlite3.connect(snap) as dest:
            source.backup(dest)
        db_bytes = snap.read_bytes()
        if not db_bytes.startswith(b'SQLite format 3\x00'):
            raise BackupError('Source is not a SQLite database')
        files['finance.db'] = db_bytes
    if ev_dir.is_symlink():
        raise BackupError("Evidence directory symlink is unsafe")
    if ev_dir.exists():
        for p in sorted(ev_dir.iterdir()):
            if p.is_symlink() or not p.is_file() or not EVIDENCE_NAME.fullmatch('evidence/' + p.name):
                raise BackupError('Evidence directory has an unexpected entry')
            if len(files) > MAX_EVIDENCE_FILES:
                raise BackupError('Too many evidence files')
            files['evidence/' + p.name] = p.read_bytes()
    if sum(len(v) for v in files.values()) > MAX_TOTAL:
        raise BackupError('Synthetic data size exceeds encrypted backup limit')
    manifest = {'version':1, 'kind':'synthetic-finance-snapshot',
                'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                'files': {k: {'sha256':sha256(v).hexdigest(),'bytes':len(v)} for k,v in files.items()}}
    memory = BytesIO()
    with zipfile.ZipFile(memory, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, payload in sorted(files.items()):
            archive.writestr(name, payload)
        archive.writestr('manifest.json', json.dumps(manifest, sort_keys=True, separators=(',',':')))
    body = memory.getvalue()
    if len(body) > MAX_ARCHIVE:
        raise BackupError('Backup too large')
    blob = MAGIC + (nonce := token_bytes(12)) + AESGCM(key).encrypt(nonce, body, MAGIC)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return {'file_count':len(files),'ciphertext_sha256':sha256(blob).hexdigest(),
            'encryption':'AES-256-GCM','synthetic_only':True,'backup_file':str(output)}

def restore_backup(backup_file: str | Path, target_directory: str | Path) -> dict:
    """Restore ONLY to a NEW directory; validates all names/digests before writing."""
    _assert_synthetic()
    key = _key()
    backup_file, target = Path(backup_file), Path(target_directory)
    if target.exists():
        raise FileExistsError('Restore target exists; never overwrite or merge financial data')
    blob = backup_file.read_bytes()
    if not blob.startswith(MAGIC) or len(blob) < 5 + 12 + 16 or len(blob) > MAX_ARCHIVE + 64:
        raise BackupError('Invalid encrypted backup envelope')
    # InvalidTag is intentional for wrong key, tampering, and authentication failure.
    data = AESGCM(key).decrypt(blob[5:17], blob[17:], MAGIC)
    files = {}
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or 'manifest.json' not in names or 'finance.db' not in names:
                raise BackupError('Missing or duplicate archive members')
            if len(names) > MAX_EVIDENCE_FILES + 2:
                raise BackupError('Too many archive entries')
            if any(n not in {'manifest.json','finance.db'} and not EVIDENCE_NAME.fullmatch(n) for n in names):
                raise BackupError('Unexpected archive filename')
            if sum(i.file_size for i in archive.infolist()) > MAX_TOTAL + 100_000:
                raise BackupError('Inflated archive exceeds size limit')
            # Never call extractall; reject links and read constrained data only.
            for item in archive.infolist():
                if item.is_dir() or ((item.external_attr >> 16) & 0o170000) == 0o120000:
                    raise BackupError('Directories and symbolic links are not supported')
            manifest = json.loads(archive.read('manifest.json'))
            if manifest.get('version') != 1 or manifest.get('kind') != 'synthetic-finance-snapshot':
                raise BackupError('Unsupported manifest')
            if set(manifest['files']) != set(names) - {'manifest.json'}:
                raise BackupError('Manifest and file list disagree')
            for name,meta in manifest['files'].items():
                payload = archive.read(name)
                if len(payload) != meta['bytes'] or sha256(payload).hexdigest() != meta['sha256']:
                    raise BackupError('Backup manifest hash mismatch')
                files[name]=payload
    except (zipfile.BadZipFile, KeyError, TypeError, IndexError, UnicodeDecodeError) as exc:
        raise BackupError('Archive invalid or malformed') from exc
    if not files['finance.db'].startswith(b'SQLite format 3\x00'):
        raise BackupError('Restored database is not SQLite')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.restore-tmp-', dir=target.parent) as tmp:
        staging = Path(tmp) / 'snapshot'
        staging.mkdir(mode=0o700)
        for name, raw in files.items():
            dest = staging / name
            dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
        # Must be a healthy database before it becomes a restored directory.
        with sqlite3.connect(f'file:{staging / "finance.db"}?mode=ro', uri=True) as conn:
            check = conn.execute('PRAGMA integrity_check').fetchone()
            if check != ('ok',):
                raise BackupError('SQLite integrity check failed')
        if target.exists():
            raise FileExistsError('Restore target appeared during verification')
        staging.rename(target)
    return {'restored_files':len(files),'target':str(target),'synthetic_only':True,
            'sqlite_integrity_check':'ok'}

def main():
    import argparse
    parser=argparse.ArgumentParser(description='Synthetic-only encrypted finance demo backup')
    sub=parser.add_subparsers(dest='action', required=True)
    create=sub.add_parser('create')
    create.add_argument('--db',required=True);create.add_argument('--evidence-dir',required=True);create.add_argument('--output',required=True)
    restore=sub.add_parser('restore')
    restore.add_argument('--backup',required=True);restore.add_argument('--target',required=True)
    args=parser.parse_args()
    result=(create_backup(args.db,args.evidence_dir,args.output)
            if args.action=='create' else restore_backup(args.backup,args.target))
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':
    main()
