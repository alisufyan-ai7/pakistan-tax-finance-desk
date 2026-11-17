"""G1-b: offline encrypted PostgreSQL DATA snapshot and independent recovery.

Synthetic-only, bounded prototype. Captures a repeatable-read snapshot of ALL
known application tables into in-memory CSV, seals it with AES-256-GCM BEFORE
writing any disk artifact, restores into an EMPTY separately Alembic-migrated
PostgreSQL database, and checks every table's row count + full row-byte parity.

No live user credentials, production authority, automatic deletion or cutover.
Plaintext legacy M1 finance tables persist on source AND restored target: this
does NOT make the active legacy database confidential or complete release G1.
"""
from __future__ import annotations

import base64
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .db import Base
from . import models  # noqa: F401 register all known tables
from .ledger_crypto import keyring

MAGIC = b"TFPG1"
MAX_PLAIN = 24 * 1024 * 1024
MAX_FILE = 26 * 1024 * 1024
SCHEMA_REVISION = "0014_drive_inbox"
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,60}$")


class PgRecoveryBlocked(ValueError):
    """A snapshot/recovery boundary failed; no certified source copy."""


def _guard() -> bytes:
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise PgRecoveryBlocked("PostgreSQL recovery prototype is synthetic-only")
    encoded = os.getenv("PG_SNAPSHOT_KEY", "")
    try:
        key = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise PgRecoveryBlocked("Independent PG_SNAPSHOT_KEY must be base64") from exc
    if len(key) != 32:
        raise PgRecoveryBlocked("PG_SNAPSHOT_KEY must contain exactly 32 bytes")
    _, ring = keyring()
    if key in ring.values():
        raise PgRecoveryBlocked("PostgreSQL backup and ledger field keys must differ")
    return key


def _connection_config(env_name: str, *, restore: bool) -> tuple[str, str]:
    # DSNs are environment-only, never passed as CLI args or written to receipts.
    dsn = os.getenv(env_name, "")
    if not dsn or "\x00" in dsn:
        raise PgRecoveryBlocked(f"{env_name} must be provided outside source control")
    try:
        from psycopg.conninfo import conninfo_to_dict
        parts = conninfo_to_dict(dsn)
    except Exception:
        raise PgRecoveryBlocked("PostgreSQL connection settings invalid") from None
    name = parts.get("dbname", "")
    required_prefix = "synthetic_restore_" if restore else "synthetic_"
    if not _NAME.fullmatch(name) or not name.startswith(required_prefix):
        raise PgRecoveryBlocked("Only explicitly named synthetic source/restore databases allowed")
    return dsn, name


def _table_names(conn) -> list[str]:
    actual = {row[0] for row in conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    )}
    expected = set(Base.metadata.tables) | {"alembic_version"}
    if actual != expected:
        raise PgRecoveryBlocked("PostgreSQL schema has missing/unknown financial tables")
    version = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    if version != (SCHEMA_REVISION,):
        raise PgRecoveryBlocked("Schema revision mismatch; explicit Alembic upgrade required")
    return [table.name for table in Base.metadata.sorted_tables]


def _ordered_copy(conn, table: str) -> bytes:
    from psycopg import sql
    if table not in Base.metadata.tables:
        raise PgRecoveryBlocked("Unknown application table")
    pks = [col.name for col in Base.metadata.tables[table].primary_key.columns]
    if not pks:
        raise PgRecoveryBlocked("Application source has no stable primary key")
    query = sql.SQL("COPY (SELECT * FROM {} ORDER BY {}) TO STDOUT WITH (FORMAT CSV)").format(
        sql.Identifier(table), sql.SQL(",").join(sql.Identifier(v) for v in pks)
    )
    chunks = bytearray()
    with conn.cursor() as cur:
        with cur.copy(query) as copy:
            for item in copy:
                chunks.extend(item)
                if len(chunks) > MAX_PLAIN:
                    raise PgRecoveryBlocked("PostgreSQL source table exceeds bounded snapshot limit")
    return bytes(chunks)


def _read_all(conn) -> tuple[list[dict[str, Any]], int]:
    names = _table_names(conn)
    items: list[dict[str, Any]] = []
    total = 0
    conn.execute("SET TIME ZONE 'UTC'")
    conn.execute("SET DateStyle = 'ISO, YMD'")
    for name in names:
        raw = _ordered_copy(conn, name)
        total += len(raw)
        if total > MAX_PLAIN:
            raise PgRecoveryBlocked("PostgreSQL snapshot exceeds in-memory size limit")
        count = conn.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0]
        items.append({
            "table": name,
            "count": count,
            "sha256": sha256(raw).hexdigest(),
            "csv_b64": base64.b64encode(raw).decode("ascii"),
        })
    return items, total


def _decode(blob: bytes, key: bytes) -> dict[str, Any]:
    if not isinstance(blob, bytes) or not blob.startswith(MAGIC) or not 33 <= len(blob) <= MAX_FILE:
        raise PgRecoveryBlocked("Invalid encrypted PostgreSQL snapshot envelope")
    try:
        text = AESGCM(key).decrypt(blob[len(MAGIC):len(MAGIC)+12], blob[len(MAGIC)+12:], MAGIC)
        manifest = json.loads(text)
    except Exception:
        raise PgRecoveryBlocked("Encrypted PostgreSQL snapshot authentication failed") from None
    if (not isinstance(manifest, dict) or manifest.get("format") != "TFPG1" or
        manifest.get("schema_revision") != SCHEMA_REVISION or
        not isinstance(manifest.get("tables"), list)):
        raise PgRecoveryBlocked("Encrypted PostgreSQL snapshot manifest invalid")
    expected = set(Base.metadata.tables)
    found: set[str] = set()
    total = 0
    for item in manifest["tables"]:
        if not isinstance(item, dict) or set(item) != {"table","count","sha256","csv_b64"}:
            raise PgRecoveryBlocked("Invalid PostgreSQL table snapshot entry")
        name = item["table"]
        if name not in expected or name in found or not isinstance(item["count"],int) or item["count"] < 0:
            raise PgRecoveryBlocked("Unexpected PostgreSQL snapshot table")
        found.add(name)
        try:
            raw = base64.b64decode(item["csv_b64"], validate=True)
        except Exception:
            raise PgRecoveryBlocked("Malformed encrypted snapshot rows") from None
        total += len(raw)
        if total > MAX_PLAIN or sha256(raw).hexdigest() != item["sha256"]:
            raise PgRecoveryBlocked("PostgreSQL snapshot row digest/size check failed")
    if found != expected:
        raise PgRecoveryBlocked("Incomplete PostgreSQL snapshot table inventory")
    if not isinstance(manifest.get("source_database"),str) or not manifest["source_database"].startswith("synthetic_"):
        raise PgRecoveryBlocked("Invalid synthetic source identity")
    return manifest


def create_pg_snapshot(output_file: str | Path) -> dict[str, Any]:
    """Read-only consistent snapshot; encrypt all bytes before writing to disk."""
    key = _guard()
    dsn, database = _connection_config("PG_SNAPSHOT_SOURCE_DSN", restore=False)
    output = Path(output_file)
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise PgRecoveryBlocked("Snapshot target must be new and inside an existing directory")
    try:
        import psycopg
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                items, total = _read_all(conn)
        plain = json.dumps({"format":"TFPG1","schema_revision":SCHEMA_REVISION,
                            "source_database":database,"tables":items},
                           sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii")
        if len(plain) > MAX_PLAIN:
            raise PgRecoveryBlocked("PostgreSQL snapshot metadata exceeds limit")
        nonce = secrets.token_bytes(12)
        sealed = MAGIC + nonce + AESGCM(key).encrypt(nonce, plain, MAGIC)
        if len(sealed) > MAX_FILE:
            raise PgRecoveryBlocked("Encrypted snapshot exceeds size limit")
    except PgRecoveryBlocked:
        raise
    except Exception:
        raise PgRecoveryBlocked("Source PostgreSQL data snapshot could not be verified") from None
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(sealed)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return {"synthetic_only":True, "encrypted":True,"format":"TFPG1",
            "table_count":len(items),"verified_read_snapshot":True,
            "ciphertext_sha256":sha256(sealed).hexdigest(),
            "source_untouched":True,"production_backup":False}


def restore_pg_snapshot(backup_file: str | Path, *, inject_failure_after_tables: int | None = None) -> dict[str, Any]:
    """Restore to EMPTY, pre-migrated synthetic_restore_* database; no destructive SQL.

    On any error the PostgreSQL transaction is rolled back, so partial tables
    cannot be left behind. Does not create a database or perform DDL automatically.
    """
    key = _guard()
    dsn, target_database = _connection_config("PG_SNAPSHOT_RESTORE_DSN", restore=True)
    backup = Path(backup_file)
    if not backup.is_file() or backup.is_symlink() or backup.stat().st_size > MAX_FILE:
        raise PgRecoveryBlocked("Encrypted snapshot must be an existing bounded regular file")
    manifest = _decode(backup.read_bytes(), key)
    if target_database == manifest["source_database"]:
        raise PgRecoveryBlocked("Original database cannot be overwritten by recovery")
    tables = {entry["table"]:entry for entry in manifest["tables"]}
    try:
        import psycopg
        from psycopg import sql
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.transaction():
                conn.execute("SET LOCAL lock_timeout = '4s'")
                conn.execute("SET TIME ZONE 'UTC'")
                conn.execute("SET DateStyle = 'ISO, YMD'")
                names = _table_names(conn)
                # PostgreSQL foreign-key dependency order; a separate *already
                # migrated* empty target is essential to any safe restoration.
                for name in names:
                    conn.execute(sql.SQL("LOCK TABLE {} IN ACCESS EXCLUSIVE MODE").format(sql.Identifier(name)))
                    count = conn.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(name))).fetchone()[0]
                    if count:
                        raise PgRecoveryBlocked("Restore target contains existing data; refusing overwrite")
                count = 0
                for name in names:
                    item = tables[name]
                    raw = base64.b64decode(item["csv_b64"], validate=True)
                    with conn.cursor() as cur:
                        with cur.copy(sql.SQL("COPY {} FROM STDIN WITH (FORMAT CSV)").format(sql.Identifier(name))) as copy:
                            copy.write(raw)
                    count += 1
                    if inject_failure_after_tables == count:
                        raise PgRecoveryBlocked("Injected transactional restore failure")
                for name in names:
                    restored = _ordered_copy(conn, name)
                    item = tables[name]
                    count_found = conn.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(name))).fetchone()[0]
                    if count_found != item["count"] or sha256(restored).hexdigest() != item["sha256"]:
                        raise PgRecoveryBlocked("Restored PostgreSQL data parity mismatch")
        return {"synthetic_only":True,"independent_target":True,"encrypted_source":True,
                "source_untouched":True,"restored_tables":len(names),
                "full_row_parity_verified":True,"transactional_rollback":True,
                "production_recovery_approved":False}
    except PgRecoveryBlocked:
        raise
    except Exception:
        raise PgRecoveryBlocked("Independent PostgreSQL restore could not be verified") from None
