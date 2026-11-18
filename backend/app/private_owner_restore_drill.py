"""P1AG: owner-Mac-only isolated PostgreSQL18 credential restore rehearsal.

Owner-controlled local encrypted snapshot + five-key escrow are read only in
attended Terminal. Authenticated owner/recovery rows are reconstructed in a
one-use PostgreSQL18 Docker container with --network none and a RAM-only
PGDATA tmpfs. No host ports, Railway, Google, financial tables or source writes.

Never print decrypted identity, TOTP, recovery hashes, SQL, environment keys,
PostgreSQL errors or Docker stderr. The Docker client must already be trusted.
A successful drill tests snapshot restoration only; it does not authorize G2
public login or prove that offline Ed25519 signer backup itself is recoverable.
"""
from __future__ import annotations

import argparse
import csv
import getpass
import hmac
import io
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import models
from . import private_owner_auth_schema as schema
from . import private_owner_credential_snapshot as snapshot
from . import private_owner_key_custody as custody
from .private_owner_identity import _owner, _unseal, _verify_identity
from .private_owner_recovery import _open as open_recovery, _row_mac, _audit_tag

_TABLES = {
    name: models.Base.metadata.tables[name]
    for name in snapshot._FIELDS
}
_IMAGE = "postgres:18"
_EXPECTED_COUNTS = (1, 0, 1, 1, 0, 0)
_MAX_SQL = 2_000_000


class PrivateOwnerRestoreDrillBlocked(ValueError):
    """Private credential recovery exercise unavailable or denied."""


def _local_payload(value: str) -> dict:
    snapshot._tty()
    path = snapshot._local_path(value)
    try:
        status = path.stat()
        if (not path.is_file() or status.st_mode & 0o777 != 0o600
            or not 0 < status.st_size <= snapshot._MAX * 2):
            raise ValueError()
        envelope = json.loads(path.read_text("ascii"))
        if (type(envelope) is not dict or set(envelope) != {
            "contract", "salt", "nonce", "ciphertext"
        } or envelope["contract"] != snapshot._FMT):
            raise ValueError()
        salt, nonce, body = (snapshot._raw(envelope[k]) for k in (
            "salt", "nonce", "ciphertext"
        ))
        if len(nonce) != 12 or not 32 <= len(body) <= snapshot._MAX + 2000:
            raise ValueError()
        password = getpass.getpass("Encrypted owner snapshot passphrase: ")
        payload = json.loads(AESGCM(
            snapshot._key(password, salt)
        ).decrypt(nonce, body, snapshot._AAD))
        return snapshot._validate_snapshot(payload)
    except Exception:
        raise PrivateOwnerRestoreDrillBlocked(
            "Encrypted local snapshot invalid or unavailable"
        ) from None


def _crypto_rehearsal(payload: dict, escrow: dict) -> dict:
    try:
        owner_enc, owner_mac, session_mac, recovery_enc, recovery_mac = (
            custody._decode(escrow[name]) for name in custody._SECRET_NAMES
        )
        if len({owner_enc, owner_mac, session_mac,
                recovery_enc, recovery_mac}) != 5:
            raise ValueError()
        identity = models.OwnerPrivateIdentity(
            **payload["tables"]["owner_private_identities"][0]
        )
        state = models.OwnerPrivateRecoveryState(
            **payload["tables"]["owner_private_recovery_states"][0]
        )
        audit = models.OwnerPrivateRecoveryAudit(
            **payload["tables"]["owner_private_recovery_audit"][0]
        )
        owner = _owner(owner_mac, escrow[custody._OWNER_NAME])
        if not hmac.compare_digest(identity.owner_hmac, owner):
            raise ValueError()
        _verify_identity(owner_mac, identity)
        if not _unseal(owner_enc, identity):
            raise ValueError()
        if (state.owner_hmac != owner or state.pending is not False
            or state.revision != 1 or audit.revision != 1
            or audit.owner_hmac != owner or audit.action != "ISSUED"
            or audit.previous_hmac != "0" * 64
            or audit.row_hmac != state.row_hmac
            or not hmac.compare_digest(state.row_hmac,
                                       _row_mac(recovery_mac, state))
            or not hmac.compare_digest(audit.event_hmac, _audit_tag(
                recovery_mac, owner, 1, "ISSUED",
                audit.previous_hmac, audit.row_hmac, audit.epoch,
            ))):
            raise ValueError()
        bundle = open_recovery(recovery_enc, state)
        if (bundle["issued"] != state.issued_epoch
            or len(bundle["code_hmacs"]) != 8
            or bundle["used_hmacs"]):
            raise ValueError()
        return {
            "snapshot_owner_row_hmac_verified": True,
            "encrypted_totp_decryption_verified": True,
            "recovery_ciphertext_and_audit_verified": True,
            "eight_issued_recovery_code_hashes_present": True,
            "raw_recovery_codes_exposed": False,
        }
    except Exception:
        raise PrivateOwnerRestoreDrillBlocked(
            "Owner/recovery cryptographic integrity check denied"
        ) from None


def _column_csv(value: object) -> str:
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        if not -(2**63) <= value < 2**63:
            raise PrivateOwnerRestoreDrillBlocked("Credential field invalid")
        return str(value)
    if (type(value) is str and len(value) <= 16000
        and value.isascii()
        and not any(char in value for char in ("\x00", "\n", "\r", "\\"))):
        return value
    raise PrivateOwnerRestoreDrillBlocked("Credential field invalid")


def _copy_sql(payload: dict) -> str:
    """Source-pinned COPY statements; values are RFC 4180 escaped CSV only."""
    chunks = ["SET log_min_error_statement = 'panic';",
              "BEGIN;", "SET LOCAL search_path = public, pg_catalog;"]
    for name in snapshot._FIELDS:
        table = _TABLES[name]
        columns = tuple(col.name for col in table.columns)
        rows = payload["tables"][name]
        if len(rows) > 100:
            raise PrivateOwnerRestoreDrillBlocked("Too many private records")
        if not rows:
            continue
        header = (
            "\\copy public." + name + " (" + ", ".join(columns) +
            ") FROM STDIN WITH (FORMAT csv, HEADER false)"
        )
        chunks.append(header)
        for row in rows:
            if type(row) is not dict or set(row) != set(columns):
                raise PrivateOwnerRestoreDrillBlocked("Credential column layout mismatch")
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n",
                                quoting=csv.QUOTE_ALL)
            writer.writerow([_column_csv(row[column]) for column in columns])
            chunks.append(buffer.getvalue().rstrip("\n"))
        chunks.append("\\.")
    chunks.append("COMMIT;")
    sql = "\n".join(chunks) + "\n"
    if len(sql) > _MAX_SQL:
        raise PrivateOwnerRestoreDrillBlocked("Private restore SQL too large")
    return sql


def _run(args: list[str], *, content: str | None = None,
         timeout: int = 40) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            args, input=content, text=True, capture_output=True,
            timeout=timeout, check=False,
        )
        if result.returncode != 0:
            raise ValueError()
        return result
    except Exception:
        # In particular, never surface psql's SQL/CONTEXT messages or stdout.
        raise PrivateOwnerRestoreDrillBlocked(
            "Disposable PostgreSQL operation unavailable"
        ) from None


def _inside(container: str, *, database: str, sql: str) -> str:
    return _run([
        "docker", "exec", "-i", container, "psql",
        "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1",
        "-U", "postgres", "-d", database,
    ], content=sql, timeout=40).stdout.strip()


def _docker_rehearsal(payload: dict) -> dict:
    """No live DB contact: one-use RAM disk, isolated Docker network only."""
    if not shutil.which("docker"):
        raise PrivateOwnerRestoreDrillBlocked(
            "Local Docker required for disposable PostgreSQL restore drill"
        )
    container = "personal-cfo-owner-drill-" + secrets.token_hex(6)
    created = False
    cleaned = False
    result = {}
    try:
        _run([
            "docker", "run", "--rm", "-d", "--network", "none",
            "--name", container,
            "--tmpfs", "/var/lib/postgresql:rw,nosuid,nodev,size=512m",
            "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
            _IMAGE,
        ], timeout=70)
        created = True
        for _ in range(40):
            check = subprocess.run(
                ["docker", "exec", container, "pg_isready",
                 "-U", "postgres", "-d", "postgres"],
                text=True, capture_output=True, timeout=5, check=False,
            )
            if check.returncode == 0:
                break
            time.sleep(0.25)
        else:
            raise PrivateOwnerRestoreDrillBlocked("Disposable PostgreSQL not ready")
        _inside(container, database="postgres",
                sql="CREATE DATABASE personal_cfo_owner_auth;\n")
        _inside(container, database="personal_cfo_owner_auth",
                sql=schema.review_only_sql())
        _inside(container, database="personal_cfo_owner_auth",
                sql=_copy_sql(payload))
        query = "SELECT " + ", ".join(
            f"(SELECT count(*) FROM public.{name})"
            for name in snapshot._FIELDS
        ) + ";\n"
        counts = _inside(container, database="personal_cfo_owner_auth", sql=query)
        if tuple(int(n) for n in counts.split("|")) != _EXPECTED_COUNTS:
            raise PrivateOwnerRestoreDrillBlocked("Restored owner row counts mismatched")
        receipt = _inside(
            container, database="personal_cfo_owner_auth",
            sql="SELECT revision || '|' || model_signature "
                "FROM public.owner_auth_schema_version;\n"
        )
        if receipt != schema.OWNER_AUTH_SCHEMA_REV + "|" + schema.schema_signature():
            raise PrivateOwnerRestoreDrillBlocked("Restored schema receipt mismatch")
        result = {
            "disposable_postgresql18_schema_recreated": True,
            "six_owner_security_tables_restored_and_verified": True,
            "owner_identity_count": 1,
            "recovery_state_count": 1,
            "recovery_audit_count": 1,
            "financial_tables_restored": False,
            "private_network_connection_used": False,
            "google_consent_activated": False,
            "source_credential_database_modified": False,
        }
    finally:
        if created:
            try:
                stop = subprocess.run(
                    ["docker", "rm", "-f", container],
                    capture_output=True, text=True, timeout=20, check=False,
                )
                cleaned = stop.returncode == 0
            except Exception:
                cleaned = False
    if not cleaned:
        raise PrivateOwnerRestoreDrillBlocked(
            "Disposable restore container cleanup not verified"
        )
    result["disposable_container_removed"] = True
    result["production_g2_authorized"] = False
    return result


def drill(snapshot_path: str, escrow_path: str) -> dict:
    snapshot._tty()
    if Path(snapshot_path).resolve() == Path(escrow_path).resolve():
        raise PrivateOwnerRestoreDrillBlocked("Separate encrypted backups required")
    payload = _local_payload(snapshot_path)
    escrow = custody._open(escrow_path)
    crypto = _crypto_rehearsal(payload, escrow)
    restored = _docker_rehearsal(payload)
    return {
        "contract": "personal_cfo_owner_local_credential_restore_drill_v1",
        **crypto, **restored,
        "independent_off_device_backup_verified": False,
        "offline_ed25519_private_signer_backup_verified": False,
        "full_financial_disaster_recovery_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Owner Mac ONLY: private offline ephemeral credential PostgreSQL18 restore"
    )
    parser.add_argument("encrypted_credential_snapshot")
    parser.add_argument("encrypted_runtime_key_escrow")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(drill(
            args.encrypted_credential_snapshot,
            args.encrypted_runtime_key_escrow,
        ), sort_keys=True))
        return 0
    except PrivateOwnerRestoreDrillBlocked:
        print("Private credential restore drill unavailable or denied",
              file=sys.stderr)
        return 1
    except Exception:
        print("Private credential restore drill failed closed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
