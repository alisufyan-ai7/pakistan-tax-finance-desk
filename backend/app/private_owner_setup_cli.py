"""P1W: attended one-owner setup and off-device recovery-key generation.

Commands:
  python -m app.private_owner_setup_cli keygen /safe/local/offline-key.pem
  python -m app.private_owner_setup_cli enroll

KEYGEN must run on the owner's trusted local machine, NEVER Railway: its
private key must remain outside the Personal CFO server and GitHub.
ENROLL must run in a *reviewed private Railway administrative terminal*,
with a restricted credential DB role, separate strong env encryption keys,
offline operator public key, and genuine one-owner admin identity verified.

No passwords/seeds/codes are accepted as CLI arguments, environment values,
HTTP requests or repo files. Terminal output of the QR enrollment URI and
one-time recovery codes is itself sensitive: avoid captured/shared terminals.
No web service imports or mounts this module.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hmac
import os
from pathlib import Path
import re
import secrets
import sys
from urllib.parse import quote

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption, Encoding, PrivateFormat, PublicFormat,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .private_owner_bootstrap import (
    PrivateOwnerBootstrapBlocked, enroll_single_owner_with_recovery,
)
from .private_credential_role_policy import (
    PrivateCredentialRoleBlocked, attest_private_credential_role,
)

_REF = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_ALLOWED_PHRASE = "ENROLL MY ONE OWNER ACCOUNT"


class PrivateOwnerSetupBlocked(ValueError):
    """The owner setup ceremony could not be safely conducted."""


def _require_tty() -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PrivateOwnerSetupBlocked("An attended, private terminal is required")


def _password_twice(*, label: str, min_length: int = 16) -> str:
    value = getpass.getpass(label + ": ")
    confirmation = getpass.getpass("Confirm " + label.lower() + ": ")
    if (type(value) is not str or not min_length <= len(value) <= 256
        or not hmac.compare_digest(value, confirmation)):
        raise PrivateOwnerSetupBlocked("Secure password confirmation failed")
    return value


def create_offline_recovery_signing_key(path: str) -> str:
    """Generate an encrypted Ed25519 recovery private key on the OWNER device.

    The returned URL-safe base64 public key is safe to configure separately
    in Railway. The private file is opened O_EXCL mode 0600, never overwritten.
    """
    _require_tty()
    if not path or not Path(path).is_absolute():
        raise PrivateOwnerSetupBlocked("Use an absolute path outside the project")
    target = Path(path)
    if target.is_symlink() or target.exists() or not target.parent.is_dir():
        raise PrivateOwnerSetupBlocked("Recovery key file must be a new local file")
    if any(part in ("site-packages", ".git", "public", "frontend")
           for part in target.parts):
        raise PrivateOwnerSetupBlocked("Recovery key location cannot be web or source")
    passphrase = _password_twice(label="Offline recovery-key passphrase",
                                 min_length=20)
    key = Ed25519PrivateKey.generate()
    encrypted = key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8,
        BestAvailableEncryption(passphrase.encode("utf-8")))
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(target), flags, 0o600)
        with os.fdopen(fd, "wb") as file:
            file.write(encrypted)
            file.flush()
            os.fsync(file.fileno())
    except OSError:
        raise PrivateOwnerSetupBlocked(
            "Offline recovery key could not be saved securely") from None
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    # No private key material returned, logged or exposed by this operation.
    return base64.urlsafe_b64encode(public).decode("ascii")


def _operator_database_url() -> str:
    url = os.getenv("P1W_OWNER_CREDENTIAL_DATABASE_URL", "")
    if (not (url.startswith("postgresql://")
             or url.startswith("postgresql+psycopg://"))
        or not 24 <= len(url) <= 2048
        or url == os.getenv("DATABASE_URL", "")):
        raise PrivateOwnerSetupBlocked(
            "An independent restricted PostgreSQL credential role is required")
    return url


def bootstrap_with_private_terminal() -> dict:
    """Private Railway terminal step; no app/server public route is started."""
    _require_tty()
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1W_G2_TERMINAL_CUSTODY_REVIEWED") != "1"
        or os.getenv("P1W_ATOMIC_OWNER_BOOTSTRAP_ONLY") != "1"):
        raise PrivateOwnerSetupBlocked("Owner setup release gate is not approved")
    ref = os.getenv("P1W_OWNER_REF", "")
    if _REF.fullmatch(ref) is None:
        raise PrivateOwnerSetupBlocked("A private one-owner reference is required")
    db_url = _operator_database_url()
    print("This is an administrative, one-owner, private-only enrollment.")
    print("Do not record, paste, share or screenshot this terminal.")
    agreed = input("Type the exact approval phrase: ").strip()
    if agreed != _ALLOWED_PHRASE:
        raise PrivateOwnerSetupBlocked("Owner approval not confirmed")

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            attest_private_credential_role(connection)
        password = _password_twice(label="New Personal CFO owner password")
        secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii")
        uri = ("otpauth://totp/" + quote("Personal CFO:Owner", safe="")
               + "?secret=" + quote(secret)
               + "&issuer=" + quote("Personal CFO", safe="")
               + "&digits=6&period=30")
        print("\nOne-time authenticator enrollment URI. Do NOT save this in chat or logs:")
        print(uri)
        proof = getpass.getpass(
            "\nEnter the current six-digit code from your authenticator: ")
        with Session(engine) as db:
            outcome, codes = enroll_single_owner_with_recovery(
                db, owner_ref=ref, password=password,
                totp_secret_base32=secret, confirmed_totp_code=proof,
                independently_verified_admin_session=True)
        print("\nOne-time owner recovery codes (store OFF-device, offline):")
        for code in codes:
            print(code)
        print("\nOwner enrolled and recovery codes issued atomically.")
        print("No Google authorization or public owner login was activated.")
        return outcome
    except (PrivateCredentialRoleBlocked, PrivateOwnerBootstrapBlocked):
        raise PrivateOwnerSetupBlocked(
            "Private owner setup denied; database not modified unless success was confirmed") from None
    except PrivateOwnerSetupBlocked:
        raise
    except Exception:
        raise PrivateOwnerSetupBlocked("Private owner setup failed") from None
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="personal-cfo-owner-setup",
        description="Attended private owner credential and off-device recovery setup")
    sub = parser.add_subparsers(dest="command", required=True)
    keygen = sub.add_parser("keygen", help="Generate offline key on owner's own device")
    keygen.add_argument("absolute_file")
    sub.add_parser("enroll", help="Enroll owner in private restricted-role Railway terminal")
    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            public = create_offline_recovery_signing_key(args.absolute_file)
            print("Store the encrypted key file outside Railway/GitHub.")
            print("Configure this public key as P1Q_OPERATOR_PUBLIC_KEY:")
            print(public)
        else:
            bootstrap_with_private_terminal()
        return 0
    except PrivateOwnerSetupBlocked as error:
        print("Setup not completed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
