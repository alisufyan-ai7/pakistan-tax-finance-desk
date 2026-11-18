"""P1AF one-owner credential-only encrypted recovery snapshot (not finance DB).

- `capture <absolute-path>`: owner's Mac, authenticated Railway CLI, private TTY
- `verify <absolute-path>`: owner's Mac, decrypt and validate locally
- `export --recipient <public-X25519-key>`: private API via SSH ONLY

No plaintext credential rows are printed, written to disk or placed in CLI
arguments. The remote API E2E-encrypts six whitelisted credential tables to a
fresh one-use recipient public key; the local Mac decrypts directly in memory,
then re-encrypts under a separate 20+ char owner-controlled passphrase with
scrypt+AES-256-GCM. The operator must make an independent off-device copy.

No restore or live G2 readiness is certified by a successful capture. A
disposable-database restore drill and key-escrow recovery test remain required.
Never call export by hand: output is encrypted, but capture manages receipt.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from .private_owner_runtime_preflight import _inventory
from .private_owner_setup_cli import _operator_database_url
from .private_credential_role_policy import PRIVATE_TABLES, attest_private_credential_role

_FMT = "personal-cfo-owner-credential-recovery-v1"
_WIRE = "personal-cfo-owner-credential-ssh-sealed-v1"
_TAG = "PERSONAL_CFO_PRIVATE_ENCRYPTED_SNAPSHOT_V1:"
_FIELDS = (
    "owner_private_identities",
    "owner_private_sessions",
    "owner_private_recovery_states",
    "owner_private_recovery_audit",
    "owner_google_metadata_grants",
    "owner_private_oauth_attempts",
)
_AAD = _FMT.encode("ascii")
_WIRE_AAD = _WIRE.encode("ascii")
_MAX = 2_000_000


class PrivateCredentialSnapshotBlocked(ValueError):
    """Fail-closed snapshot procedure, never expose credential rows or errors."""


def _tty() -> None:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise PrivateCredentialSnapshotBlocked("Private attended Mac terminal required")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _raw(value: str) -> bytes:
    try:
        return base64.b64decode(value, altchars=b"-_", validate=True)
    except Exception:
        raise PrivateCredentialSnapshotBlocked("Encrypted snapshot integrity invalid") from None


def _key(password: str, salt: bytes) -> bytes:
    if not 20 <= len(password) <= 256 or len(salt) != 16:
        raise PrivateCredentialSnapshotBlocked("Snapshot recovery passphrase invalid")
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(
        password.encode("utf-8"))


def _local_path(value: str) -> Path:
    p = Path(value)
    if (not p.is_absolute() or p.is_symlink() or not p.parent.is_dir()
        or any(part in (".git", "backend", "frontend", "public", "site-packages")
               for part in p.parts)):
        raise PrivateCredentialSnapshotBlocked("Use a private absolute path outside the project")
    return p


def _validate_snapshot(payload: dict) -> dict:
    if (
        type(payload) is not dict
        or set(payload) != {"contract", "schema_revision", "created_epoch", "tables"}
        or payload["contract"] != _FMT
        or payload["schema_revision"] != "p1y_owner_auth_v1"
        or type(payload["created_epoch"]) is not int
        or not 1_500_000_000 <= payload["created_epoch"] <= 4_000_000_000
        or type(payload["tables"]) is not dict
        or set(payload["tables"]) != set(_FIELDS)
    ):
        raise PrivateCredentialSnapshotBlocked("Credential snapshot shape invalid")
    table = payload["tables"]
    if any(type(table[name]) is not list or
           any(type(row) is not dict for row in table[name])
           for name in _FIELDS):
        raise PrivateCredentialSnapshotBlocked("Credential row inventory invalid")
    if (len(table["owner_private_identities"]) != 1
        or table["owner_private_identities"][0].get("singleton_id") != 1
        or len(table["owner_private_recovery_states"]) != 1
        or len(table["owner_private_recovery_audit"]) != 1
        or table["owner_private_identities"][0].get("revision") != 1
        or table["owner_private_recovery_states"][0].get("revision") != 1
        or table["owner_private_recovery_audit"][0].get("revision") != 1
        or table["owner_private_recovery_audit"][0].get("action") != "ISSUED"
        or any(table[name] for name in (
            "owner_private_sessions", "owner_google_metadata_grants",
            "owner_private_oauth_attempts",
        ))):
        raise PrivateCredentialSnapshotBlocked("Initial owner recovery snapshot not acceptable")
    owner = table["owner_private_identities"][0].get("owner_hmac")
    if (type(owner) is not str or len(owner) != 64
        or table["owner_private_recovery_states"][0].get("owner_hmac") != owner
        or any(row.get("owner_hmac") != owner
               for row in table["owner_private_recovery_audit"])):
        raise PrivateCredentialSnapshotBlocked("One-owner recovery linkage invalid")
    blob = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("ascii")
    if len(blob) > _MAX:
        raise PrivateCredentialSnapshotBlocked("Owner credential snapshot exceeded private limit")
    return payload


def _derive_shared(private: X25519PrivateKey, peer: bytes, salt: bytes) -> bytes:
    if len(peer) != 32 or len(salt) != 16:
        raise PrivateCredentialSnapshotBlocked("Ephemeral snapshot envelope invalid")
    shared = private.exchange(X25519PublicKey.from_public_bytes(peer))
    return HKDF(
        algorithm=hashes.SHA256(), length=32,
        salt=salt, info=_WIRE_AAD,
    ).derive(shared)


def _seal_wire(payload: dict, recipient: str) -> dict:
    key_bytes = _raw(recipient)
    if len(key_bytes) != 32:
        raise PrivateCredentialSnapshotBlocked("Ephemeral recipient invalid")
    local = X25519PrivateKey.generate()
    local_public = local.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    key = _derive_shared(local, key_bytes, salt)
    ciphertext = AESGCM(key).encrypt(
        nonce, json.dumps(_validate_snapshot(payload), sort_keys=True,
                          ensure_ascii=True, separators=(",", ":")).encode("ascii"),
        _WIRE_AAD)
    return {
        "contract": _WIRE, "sender": _b64(local_public),
        "salt": _b64(salt), "nonce": _b64(nonce),
        "ciphertext": _b64(ciphertext),
    }


def _open_wire(envelope: dict, private: X25519PrivateKey) -> dict:
    try:
        if type(envelope) is not dict or set(envelope) != {
            "contract", "sender", "salt", "nonce", "ciphertext"
        } or envelope["contract"] != _WIRE:
            raise ValueError()
        peer, salt, nonce, cipher = (_raw(envelope[name]) for name in (
            "sender", "salt", "nonce", "ciphertext",
        ))
        if len(nonce) != 12 or not 32 <= len(cipher) <= _MAX + 2000:
            raise ValueError()
        raw = AESGCM(_derive_shared(private, peer, salt)).decrypt(
            nonce, cipher, _WIRE_AAD)
        return _validate_snapshot(json.loads(raw))
    except Exception:
        raise PrivateCredentialSnapshotBlocked("Remote snapshot authentication failed") from None


def _private_export(recipient: str) -> dict:
    # The private API must have the previously attested five keys and
    # a separately authorized one-time export switch. Never enable globally.
    if os.getenv("P1W_PRIVATE_CREDENTIAL_SNAPSHOT_EXPORT") != "1":
        raise PrivateCredentialSnapshotBlocked("Private snapshot authorization denied")
    _inventory()
    url = _operator_database_url()
    engine = create_engine(
        url, poolclass=NullPool,
        connect_args={
            "connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=3500",
        },
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            row = conn.execute(text(
                "SELECT current_database(), current_user, "
                "(SELECT ssl FROM pg_catalog.pg_stat_ssl WHERE pid=pg_backend_pid()), "
                "current_setting('transaction_read_only')"
            )).one()
            if row != ("personal_cfo_owner_auth", "personal_cfo_owner_credentials",
                       True, "on"):
                raise PrivateCredentialSnapshotBlocked("Credential SQL authority denied")
            attest_private_credential_role(conn)
            values = {}
            for name in _FIELDS:
                # Names are source-constant whitelist, not user-controlled SQL.
                values[name] = [
                    dict(row) for row in conn.execute(
                        text(f"SELECT * FROM public.{name} LIMIT 101")
                    ).mappings().all()
                ]
            payload = _validate_snapshot({
                "contract": _FMT,
                "schema_revision": "p1y_owner_auth_v1",
                "created_epoch": int(time.time()),
                "tables": values,
            })
            return _seal_wire(payload, recipient)
    finally:
        engine.dispose()


def _new_password() -> str:
    password = getpass.getpass("New credential-snapshot passphrase (20+ chars): ")
    confirm = getpass.getpass("Confirm credential-snapshot passphrase: ")
    if password != confirm:
        raise PrivateCredentialSnapshotBlocked("Snapshot passphrase confirmation failed")
    return password


def _write_local(payload: dict, value: str) -> dict:
    p = _local_path(value)
    if p.exists():
        raise PrivateCredentialSnapshotBlocked("Snapshot file already exists; never overwrite")
    password = _new_password()
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    body = json.dumps(_validate_snapshot(payload), sort_keys=True,
                      ensure_ascii=True, separators=(",", ":")).encode("ascii")
    cipher = AESGCM(_key(password, salt)).encrypt(nonce, body, _AAD)
    envelope = json.dumps({
        "contract": _FMT, "salt": _b64(salt),
        "nonce": _b64(nonce), "ciphertext": _b64(cipher),
    }, sort_keys=True, separators=(",", ":")).encode("ascii")
    fd = None
    try:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(str(p), flags, 0o600)
        with os.fdopen(fd, "wb") as out:
            fd = None
            out.write(envelope)
            out.flush()
            os.fsync(out.fileno())
    except OSError:
        if fd is not None:
            os.close(fd)
        raise PrivateCredentialSnapshotBlocked("Encrypted credential snapshot write failed") from None
    return {
        "encrypted_snapshot_created": True,
        "one_owner_and_recovery_records_included": True,
        "google_grant_included": False,
        "plaintext_database_rows_saved": False,
        "independent_off_device_copy_verified": False,
        "restore_to_disposable_database_tested": False,
        "google_consent_activated": False,
    }


def verify(value: str) -> dict:
    _tty()
    p = _local_path(value)
    try:
        stat = p.stat()
        if not p.is_file() or stat.st_size > _MAX * 2 or stat.st_mode & 0o777 != 0o600:
            raise ValueError()
        env = json.loads(p.read_text("ascii"))
        if type(env) is not dict or set(env) != {
            "contract", "salt", "nonce", "ciphertext"
        } or env["contract"] != _FMT:
            raise ValueError()
        salt, nonce, cipher = (_raw(env[key]) for key in ("salt", "nonce", "ciphertext"))
        if len(nonce) != 12 or len(cipher) > _MAX + 2000:
            raise ValueError()
        password = getpass.getpass("Credential-snapshot passphrase: ")
        payload = json.loads(AESGCM(_key(password, salt)).decrypt(
            nonce, cipher, _AAD))
        _validate_snapshot(payload)
        return {
            "authenticated_decryption": True,
            "single_owner_recovery_state_present": True,
            "encrypted_file_permissions_restricted": True,
            "independent_off_device_copy_verified": False,
            "restore_tested": False,
        }
    except Exception:
        raise PrivateCredentialSnapshotBlocked("Encrypted credential snapshot verification failed") from None


def capture(value: str) -> dict:
    _tty()
    _local_path(value)
    if not shutil.which("railway"):
        raise PrivateCredentialSnapshotBlocked("Railway CLI unavailable")
    if Path(value).exists():
        raise PrivateCredentialSnapshotBlocked("Snapshot already exists")
    recipient = X25519PrivateKey.generate()
    public = _b64(recipient.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    command = [
        "railway", "ssh",
        "--project", "7021b227-f704-43d6-bcff-debdb7255b81",
        "--environment", "development",
        "--service", "personal-cfo-api-preview",
        "--", "env", "P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1",
        "P1W_PRIVATE_CREDENTIAL_SNAPSHOT_EXPORT=1",
        "python", "-m", "app.private_owner_credential_snapshot",
        "export", "--recipient", public,
    ]
    try:
        output = subprocess.run(command, text=True, capture_output=True,
                                timeout=50, check=False)
        if output.returncode != 0 or len(output.stdout) > _MAX * 2:
            raise ValueError()
        lines = [
            line[len(_TAG):] for line in output.stdout.splitlines()
            if line.startswith(_TAG)
        ]
        if len(lines) != 1:
            raise ValueError()
        envelope = json.loads(lines[0])
        payload = _open_wire(envelope, recipient)
    except Exception:
        raise PrivateCredentialSnapshotBlocked(
            "Private credential snapshot retrieval failed; no secret output displayed") from None
    return _write_local(payload, value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One-owner private credential snapshot; never commit files to GitHub")
    commands = parser.add_subparsers(dest="command", required=True)
    for cmd in ("capture", "verify"):
        item = commands.add_parser(cmd)
        item.add_argument("absolute_encrypted_file")
    export = commands.add_parser("export")
    export.add_argument("--recipient", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            print(json.dumps(capture(args.absolute_encrypted_file), sort_keys=True))
        elif args.command == "verify":
            print(json.dumps(verify(args.absolute_encrypted_file), sort_keys=True))
        else:
            envelope = _private_export(args.recipient)
            print(_TAG + json.dumps(envelope, sort_keys=True, separators=(",", ":")))
        return 0
    except PrivateCredentialSnapshotBlocked:
        print("Owner credential recovery snapshot unavailable or denied",
              file=sys.stderr)
        return 1
    except Exception:
        print("Owner credential recovery snapshot failed closed",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
