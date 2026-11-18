"""P1Z: create an encrypted, owner-controlled local key escrow on the Mac.

Commands (run locally, NEVER in GitHub Actions or Railway):
  python -m app.private_owner_key_custody create "$HOME/personal-cfo-owner-keys.enc"
  python -m app.private_owner_key_custody verify "$HOME/personal-cfo-owner-keys.enc"
  python -m app.private_owner_key_custody reveal "$HOME/personal-cfo-owner-keys.enc" P1N_OWNER_ENCRYPTION_KEY

The file contains five distinct random 256-bit runtime encryption/HMAC keys
and one opaque single-owner reference. It is encrypted under a separately
chosen owner-controlled passphrase, with scrypt + AES-256-GCM.

Never send the escrow, passphrase, or revealed values to ChatGPT, GitHub,
Railway logs, email or another human. In the Railway Variables UI, manually
configure the revealed values on the approved PRIVATE API only, after separate
operator review and before an attended authenticated enrollment.

The owner must keep independent encrypted copies before live enrollment.
The operator Ed25519 private key belongs in a SEPARATE file already created;
this tool never creates or stores that signing key or a database password.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
from urllib.parse import quote

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

_FORMAT = "personal-cfo-owner-local-key-escrow-v1"
_ASSOCIATED = _FORMAT.encode("ascii")
_SECRET_NAMES = (
    "P1N_OWNER_ENCRYPTION_KEY",
    "P1N_OWNER_IDENTITY_HMAC_KEY",
    "P1N_OWNER_SESSION_HMAC_KEY",
    "P1P_OWNER_RECOVERY_ENCRYPTION_KEY",
    "P1P_OWNER_RECOVERY_HMAC_KEY",
)
_OWNER_NAME = "P1W_OWNER_REF"
_ALL = frozenset((*_SECRET_NAMES, _OWNER_NAME))
_OWNER_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_MIN_LENGTH = 20
_MAX_LENGTH = 256
_MAX_FILE = 5000
_N = 2**15


class LocalOwnerKeyCustodyBlocked(ValueError):
    """Local encrypted owner key escrow failed closed."""


def _tty() -> None:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise LocalOwnerKeyCustodyBlocked("Private interactive terminal required")


def _path(value: str) -> Path:
    path = Path(value)
    if (not path.is_absolute() or path.is_symlink()
        or any(part in (".git", "backend", "frontend", "public", "site-packages")
               for part in path.parts) or not path.parent.is_dir()):
        raise LocalOwnerKeyCustodyBlocked("Use a private absolute path outside the repository")
    return path


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode(value: str) -> bytes:
    try:
        return base64.b64decode(value, altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        raise LocalOwnerKeyCustodyBlocked("Local encrypted key bundle invalid") from None


def _key(passphrase: str, salt: bytes) -> bytes:
    if not _MIN_LENGTH <= len(passphrase) <= _MAX_LENGTH or len(salt) != 16:
        raise LocalOwnerKeyCustodyBlocked("Private escrow passphrase rejected")
    return Scrypt(salt=salt, length=32, n=_N, r=8, p=1).derive(
        passphrase.encode("utf-8"))


def _validate(payload: object) -> dict:
    if (type(payload) is not dict or set(payload) != _ALL
        or any(type(value) is not str for value in payload.values())
        or _OWNER_RE.fullmatch(payload[_OWNER_NAME]) is None):
        raise LocalOwnerKeyCustodyBlocked("Local escrow inventory invalid")
    keys = [_decode(payload[name]) for name in _SECRET_NAMES]
    if any(len(key) != 32 for key in keys) or len(set(keys)) != 5:
        raise LocalOwnerKeyCustodyBlocked("Local escrow key domains invalid")
    return payload


def _password(*, new: bool) -> str:
    first = getpass.getpass(
        "New local escrow passphrase (minimum 20 characters): "
        if new else "Local escrow passphrase: ")
    if type(first) is not str or not _MIN_LENGTH <= len(first) <= _MAX_LENGTH:
        raise LocalOwnerKeyCustodyBlocked("Local escrow passphrase rejected")
    if new:
        second = getpass.getpass("Confirm local escrow passphrase: ")
        if not hmac.compare_digest(first, second):
            raise LocalOwnerKeyCustodyBlocked("Local escrow passphrase mismatch")
    return first


def create(value: str) -> dict:
    _tty()
    path = _path(value)
    if path.exists():
        raise LocalOwnerKeyCustodyBlocked("Local escrow exists; never overwrite")
    payload = {name: _encode(secrets.token_bytes(32)) for name in _SECRET_NAMES}
    payload[_OWNER_NAME] = secrets.token_urlsafe(24)
    _validate(payload)
    passphrase = _password(new=True)
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    cipher = AESGCM(_key(passphrase, salt)).encrypt(
        nonce, json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii"),
        _ASSOCIATED)
    envelope = json.dumps({
        "format": _FORMAT, "salt": _encode(salt), "nonce": _encode(nonce),
        "ciphertext": _encode(cipher),
    }, sort_keys=True, separators=(",", ":")).encode("ascii")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(path), flags, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(envelope)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        raise LocalOwnerKeyCustodyBlocked(
            "Private escrow could not be written safely") from None
    return {
        "encrypted_file_created": True,
        "distinct_owner_runtime_keys": 5,
        "opaque_single_owner_reference": True,
        "operator_offline_private_signing_key_included": False,
        "database_password_included": False,
        "recovery_backups_verified": False,
        "railway_variables_configured": False,
    }


def _open(value: str) -> dict:
    _tty()
    path = _path(value)
    try:
        status = path.stat()
    except OSError:
        raise LocalOwnerKeyCustodyBlocked("Local escrow missing or invalid") from None
    if (not path.is_file() or status.st_size > _MAX_FILE
        or (status.st_mode & 0o777) != 0o600):
        raise LocalOwnerKeyCustodyBlocked("Local escrow missing or unsafe file permissions")
    try:
        envelope = json.loads(path.read_text("ascii"))
        if type(envelope) is not dict or set(envelope) != {
            "format", "salt", "nonce", "ciphertext"
        } or envelope["format"] != _FORMAT:
            raise ValueError()
        salt, nonce, ciphertext = (
            _decode(envelope[name]) for name in ("salt", "nonce", "ciphertext"))
        if len(nonce) != 12 or not 32 <= len(ciphertext) <= 3000:
            raise ValueError()
        password = _password(new=False)
        raw = AESGCM(_key(password, salt)).decrypt(
            nonce, ciphertext, _ASSOCIATED)
        return _validate(json.loads(raw))
    except (InvalidTag, ValueError, OSError, UnicodeError, KeyError, TypeError):
        raise LocalOwnerKeyCustodyBlocked(
            "Local escrow decryption or integrity check failed") from None


def verify(value: str) -> dict:
    _open(value)
    return {
        "authenticated_decryption": True,
        "distinct_runtime_keys": 5,
        "valid_owner_reference": True,
        "no_secrets_printed": True,
        "railway_activation": False,
    }


def reveal(value: str, name: str) -> str:
    if name not in _ALL:
        raise LocalOwnerKeyCustodyBlocked("Variable not part of owner escrow")
    return _open(value)[name]


def build_isolated_credential_dsn() -> str:
    """Use an attended prompt to construct a TLS internal restricted-role URL.

    Caller must copy this directly into a PRIVATE Railway variable. The
    password is not saved to the local escrow or command-line arguments.
    """
    _tty()
    password = getpass.getpass("Existing restricted PostgreSQL role password: ")
    if not 24 <= len(password) <= 256:
        raise LocalOwnerKeyCustodyBlocked("Restricted role password length rejected")
    return (
        "postgresql+psycopg://personal_cfo_owner_credentials:"
        + quote(password, safe="")
        + "@postgres.railway.internal:5432/personal_cfo_owner_auth"
        + "?sslmode=require"
    )


def configure_private_railway_without_deploy(
    value: str, *, backed_up_independently: bool = False,
) -> dict:
    """Owner-authenticated Railway CLI only; never put secrets in argv/logs.

    This writes only the seven private owner variables (five distinct keys,
    opaque owner ref and restricted role URL) to the existing development API.
    It does not set any G2 review switches, start MFA enrollment, redeploy
    the API, apply the staged Google secret or import a financial document.
    """
    _tty()
    if backed_up_independently is not True:
        raise LocalOwnerKeyCustodyBlocked(
            "Independently backed-up escrow must be confirmed first")
    if not shutil.which("railway"):
        raise LocalOwnerKeyCustodyBlocked("Railway CLI is not installed")
    payload = _open(value)
    dsn = build_isolated_credential_dsn()
    approved = input(
        "Type CONFIGURE PRIVATE API WITHOUT DEPLOY to proceed: ").strip()
    if approved != "CONFIGURE PRIVATE API WITHOUT DEPLOY":
        raise LocalOwnerKeyCustodyBlocked("Owner did not authorize upload")
    variables = {name: payload[name] for name in (*_SECRET_NAMES, _OWNER_NAME)}
    variables["P1W_OWNER_CREDENTIAL_DATABASE_URL"] = dsn
    configured = 0
    for name, secret in variables.items():
        command = [
            "railway", "variable", "set", name, "--stdin",
            "--project", "7021b227-f704-43d6-bcff-debdb7255b81",
            "--environment", "development",
            "--service", "personal-cfo-api-preview",
            "--skip-deploys",
        ]
        try:
            result = subprocess.run(
                command, input=secret, capture_output=True,
                text=True, timeout=45, check=False,
            )
            if result.returncode != 0:
                raise RuntimeError()
        except Exception:
            raise LocalOwnerKeyCustodyBlocked(
                "Private Railway configuration stopped; check variables by NAME only, "
                "do not paste CLI output into chat") from None
        configured += 1
    return {
        "private_railway_variables_written": configured,
        "redeployment_triggered_by_this_command": False,
        "google_secret_touched": False,
        "owner_enrollment_activated": False,
        "g2_approved_by_this_command": False,
        "restricted_database_url_value_printed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Owner-side encrypted runtime key escrow, never run in CI or Railway")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "verify", "reveal"):
        entry = sub.add_parser(command)
        entry.add_argument("absolute_encrypted_file")
        if command == "reveal":
            entry.add_argument("variable_name", choices=sorted(_ALL))
    sub.add_parser("dsn", help="Build a restricted private Railway URL from a hidden password prompt")
    upload = sub.add_parser("configure-private-railway", help="Write escrowed secrets only to the reviewed private API without redeployment")
    upload.add_argument("absolute_encrypted_file")
    upload.add_argument("--confirmed-independent-backup", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "configure-private-railway":
            print(json.dumps(
                configure_private_railway_without_deploy(
                    args.absolute_encrypted_file,
                    backed_up_independently=args.confirmed_independent_backup),
                sort_keys=True))
        elif args.command == "dsn":
            print("SECRET — copy only into the private Railway variable P1W_OWNER_CREDENTIAL_DATABASE_URL; never into chat:", file=sys.stderr)
            print(build_isolated_credential_dsn())
        elif args.command == "create":
            print(json.dumps(create(args.absolute_encrypted_file), sort_keys=True))
        elif args.command == "verify":
            print(json.dumps(verify(args.absolute_encrypted_file), sort_keys=True))
        else:
            print("SECRET — do not paste into chat, screenshots or source control:",
                  file=sys.stderr)
            print(reveal(args.absolute_encrypted_file, args.variable_name))
        return 0
    except LocalOwnerKeyCustodyBlocked as exc:
        print("Owner key escrow unavailable: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
