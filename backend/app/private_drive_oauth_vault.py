"""P1C owner-only encrypted Google OAuth custody (separate local private vault).

Only explicit loopback, synthetic data mode and user-controlled private host.
No real secrets, folder IDs, account details or owner source contents are
stored in public GitHub or Railway. The OAuth refresh grant lives in an
independent private SQLite file, AES-256-GCM protected with a dedicated
externally supplied key. Owner handles private backup/key recovery separately.

A pending OAuth state is cryptographically random, domain-separated HMAC
indexed and consumed atomically BEFORE any Google code exchange: failed
callbacks cannot replay. A second worker cannot claim the same attempt.
This is NOT permission to ingest real bank/FBR bytes or enable real mode.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .drive_google_oauth import (
    DriveOAuthConfig, PendingGoogleConsent, PrivateDriveOAuthBlocked,
    GOOGLE_METADATA_SCOPE, private_google_configuration,
)

_PREFIX = "DCF1:"
_MAX_ATTEMPTS = 12
_STATE_TTL = 600
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class PrivateDriveVaultBlocked(ValueError):
    """Refuse untrusted vault, replayed authorization or unreadable ciphertext."""


@dataclass(frozen=True)
class ClaimedGoogleAttempt:
    pkce_verifier: str
    client_id: str
    redirect_uri: str
    folder_hmac: str


def _b64_key() -> bytes:
    raw = os.getenv("P1C_OAUTH_VAULT_KEY", "")
    try:
        key = base64.b64decode(raw, altchars=b"-_", validate=True)
    except (ValueError, UnicodeError):
        raise PrivateDriveVaultBlocked("Private OAuth vault key is unavailable") from None
    if len(key) != 32:
        raise PrivateDriveVaultBlocked("Private OAuth vault key is unavailable")
    return key


def _tag(key: bytes, label: str, text_value: str) -> str:
    return hmac.new(key, ("personal-cfo:private-drive-oauth:v1:"+label+":"+text_value).encode(), sha256).hexdigest()


def _seal(key: bytes, domain: str, value: dict) -> str:
    nonce = secrets.token_bytes(12)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sealed = AESGCM(key).encrypt(nonce, raw, b"personal-cfo:drive-vault:v1:"+domain.encode())
    return _PREFIX + base64.urlsafe_b64encode(nonce+sealed).decode("ascii")


def _open(key: bytes, domain: str, ciphertext: str) -> dict:
    try:
        if not isinstance(ciphertext, str) or not ciphertext.startswith(_PREFIX):
            raise ValueError()
        blob=base64.b64decode(ciphertext[len(_PREFIX):], altchars=b"-_", validate=True)
        if len(blob)<28:
            raise ValueError()
        decoded=AESGCM(key).decrypt(blob[:12],blob[12:],b"personal-cfo:drive-vault:v1:"+domain.encode())
        result=json.loads(decoded)
        if type(result) is not dict:
            raise ValueError()
        return result
    except Exception:
        raise PrivateDriveVaultBlocked("Private Google consent state could not be authenticated") from None


def _path() -> Path:
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY") != "1"
        or os.getenv("P1C_LOCAL_OAUTH_VAULT_ENABLED") != "1"):
        raise PrivateDriveVaultBlocked("Private OAuth vault disabled")
    raw = os.getenv("P1C_OAUTH_VAULT_PATH", "")
    if not raw or not os.path.isabs(raw):
        raise PrivateDriveVaultBlocked("Private OAuth vault must have an absolute path")
    path=Path(raw)
    if path.suffix != ".sqlite3" or path.name.startswith("."):
        raise PrivateDriveVaultBlocked("Private OAuth vault path rejected")
    if Path.cwd() == path.parent or Path.cwd() in path.parents or path.parent == Path("/"):
        raise PrivateDriveVaultBlocked("Private OAuth vault cannot be inside repository")
    parent=path.parent
    if not parent.exists() or parent.is_symlink():
        raise PrivateDriveVaultBlocked("Vault directory must be created privately")
    mode=parent.stat().st_mode
    if not stat.S_ISDIR(mode) or (mode & 0o077) != 0 or parent.stat().st_uid != os.getuid():
        raise PrivateDriveVaultBlocked("Private OAuth vault directory must be owned and mode 0700")
    if path.is_symlink():
        raise PrivateDriveVaultBlocked("Private OAuth vault symlink refused")
    if path.exists():
        st=path.stat()
        if not stat.S_ISREG(st.st_mode) or (st.st_mode & 0o077) or st.st_uid != os.getuid():
            raise PrivateDriveVaultBlocked("OAuth vault file must be owner-only")
    return path


class PrivateGoogleOAuthVault:
    """Caller owns all Google API/network and private authentication decisions."""

    def __init__(self):
        self.key=_b64_key()
        self.path=_path()
        # O_EXCL ensures new vault is created by its owner with exact mode.
        if not self.path.exists():
            try:
                fd=os.open(str(self.path), os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
            except OSError:
                raise PrivateDriveVaultBlocked("Cannot initialize private OAuth vault") from None
        _path()  # Verify new file owner, type and access bits.
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS oauth_attempts(
                  state_hmac TEXT PRIMARY KEY, payload_cipher TEXT NOT NULL,
                  created_unix INTEGER NOT NULL, expires_unix INTEGER NOT NULL,
                  status TEXT NOT NULL CHECK(status IN ('pending','claimed'))
                );
                CREATE TABLE IF NOT EXISTS oauth_grants(
                  folder_hmac TEXT PRIMARY KEY, payload_cipher TEXT NOT NULL,
                  granted_unix INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
                );
                """)

    def _connect(self):
        _path()
        db=sqlite3.connect(str(self.path),timeout=5,isolation_level=None)
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA secure_delete=ON")
        db.execute("PRAGMA busy_timeout=5000")
        return db

    def remember_attempt(self, pending: PendingGoogleConsent, *,
                         current: DriveOAuthConfig, now_unix: int|None=None) -> None:
        if (not isinstance(pending,PendingGoogleConsent)
            or not isinstance(current,DriveOAuthConfig)
            or current != private_google_configuration()
            or not re.fullmatch(r"[A-Za-z0-9_-]{40,128}", pending.state)
            or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", pending.pkce_verifier)
            or not hmac.compare_digest(current.folder_hmac,pending.folder_hmac)):
            raise PrivateDriveVaultBlocked("Unverified private consent attempt")
        now=int(time.time()) if now_unix is None else now_unix
        if type(now) is not int or now<1_500_000_000:
            raise PrivateDriveVaultBlocked("Invalid OAuth clock")
        sid=_tag(self.key,"state",pending.state)
        record={
            "verifier":pending.pkce_verifier,"client_id":current.client_id,
            "redirect_uri":current.redirect_uri,"folder_hmac":current.folder_hmac,
        }
        sealed=_seal(self.key,"attempt:"+sid,record)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("DELETE FROM oauth_attempts WHERE expires_unix < ?",(now,))
                count=db.execute("SELECT COUNT(*) FROM oauth_attempts WHERE status='pending'").fetchone()[0]
                if count>=_MAX_ATTEMPTS:
                    raise PrivateDriveVaultBlocked("Too many pending private OAuth attempts")
                db.execute(
                    "INSERT INTO oauth_attempts(state_hmac,payload_cipher,created_unix,expires_unix,status) "
                    "VALUES(?,?,?,?, 'pending')",
                    (sid,sealed,now,now+_STATE_TTL))
                db.commit()
        except sqlite3.Error:
            raise PrivateDriveVaultBlocked("Private OAuth attempt could not be stored") from None

    def consume_attempt(self, state: str, *, now_unix: int|None=None) -> ClaimedGoogleAttempt:
        if not isinstance(state,str) or not re.fullmatch(r"[A-Za-z0-9_-]{40,128}",state):
            raise PrivateDriveVaultBlocked("OAuth state invalid, expired or already consumed")
        current=private_google_configuration()
        now=int(time.time()) if now_unix is None else now_unix
        sid=_tag(self.key,"state",state)
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row=db.execute("SELECT payload_cipher,expires_unix,status FROM oauth_attempts WHERE state_hmac=?",
                               (sid,)).fetchone()
                if row is None or row[2]!="pending" or now>=row[1]:
                    raise PrivateDriveVaultBlocked("OAuth state invalid, expired or already consumed")
                payload=_open(self.key,"attempt:"+sid,row[0])
                if (set(payload)!={"verifier","client_id","redirect_uri","folder_hmac"}
                    or payload["client_id"]!=current.client_id
                    or payload["redirect_uri"]!=current.redirect_uri
                    or not hmac.compare_digest(payload["folder_hmac"],current.folder_hmac)):
                    raise PrivateDriveVaultBlocked("OAuth attempt is bound to a different client or folder")
                updated=db.execute(
                    "UPDATE oauth_attempts SET status='claimed',payload_cipher=? "
                    "WHERE state_hmac=? AND status='pending'",
                    (_seal(self.key,"attempt:"+sid,{"claimed":True}),sid))
                if updated.rowcount!=1:
                    raise PrivateDriveVaultBlocked("OAuth state already consumed")
                db.commit()
                return ClaimedGoogleAttempt(
                    pkce_verifier=payload["verifier"], client_id=current.client_id,
                    redirect_uri=current.redirect_uri, folder_hmac=current.folder_hmac)
            except sqlite3.Error:
                db.rollback()
                raise PrivateDriveVaultBlocked("OAuth state could not be consumed") from None

    def store_grant(self, *, folder_hmac: str, client_id: str,
                    refresh_token: str, scope: str, now_unix: int|None=None):
        current=private_google_configuration()
        if (not isinstance(folder_hmac,str) or not _HEX64.fullmatch(folder_hmac)
            or not hmac.compare_digest(current.folder_hmac,folder_hmac)
            or current.client_id!=client_id or scope!=GOOGLE_METADATA_SCOPE
            or not isinstance(refresh_token,str) or not 24<=len(refresh_token)<=4096
            or any(c in refresh_token for c in "\r\n\x00")):
            raise PrivateDriveVaultBlocked("Invalid restricted Google consent grant")
        now=int(time.time()) if now_unix is None else now_unix
        record={"client_id":client_id,"folder_hmac":folder_hmac,
                "scope":scope,"refresh_token":refresh_token}
        cipher=_seal(self.key,"grant:"+folder_hmac,record)
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "INSERT INTO oauth_grants(folder_hmac,payload_cipher,granted_unix,revoked) "
                    "VALUES(?,?,?,0) ON CONFLICT(folder_hmac) DO UPDATE "
                    "SET payload_cipher=excluded.payload_cipher,granted_unix=excluded.granted_unix,revoked=0",
                    (folder_hmac,cipher,now))
                db.commit()
            except sqlite3.Error:
                db.rollback()
                raise PrivateDriveVaultBlocked("Google refresh grant could not be sealed") from None

    def load_grant(self) -> dict:
        current=private_google_configuration()
        with self._connect() as db:
            row=db.execute(
                "SELECT payload_cipher FROM oauth_grants WHERE folder_hmac=? AND revoked=0",
                (current.folder_hmac,)).fetchone()
        if row is None:
            raise PrivateDriveVaultBlocked("No approved local Google metadata grant")
        payload=_open(self.key,"grant:"+current.folder_hmac,row[0])
        if (set(payload)!={"client_id","folder_hmac","scope","refresh_token"}
            or payload["client_id"]!=current.client_id
            or payload["folder_hmac"]!=current.folder_hmac
            or payload["scope"]!=GOOGLE_METADATA_SCOPE
            or not isinstance(payload["refresh_token"],str)
            or not 24<=len(payload["refresh_token"])<=4096):
            raise PrivateDriveVaultBlocked("Stored metadata grant is invalid")
        return payload

    def local_disconnect(self) -> None:
        """Local revocation only. Remote Google revocation must be done separately."""
        current=private_google_configuration()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM oauth_grants WHERE folder_hmac=?",(current.folder_hmac,))
            db.execute("DELETE FROM oauth_attempts")
            db.commit()

    def redacted_status(self) -> dict:
        current=private_google_configuration()
        with self._connect() as db:
            present=db.execute(
                "SELECT 1 FROM oauth_grants WHERE folder_hmac=? AND revoked=0",
                (current.folder_hmac,)).fetchone() is not None
        return {
            "private_local_grant_sealed":present,
            "source_scope":"DRIVE_METADATA_ONLY",
            "source_folder":"OWNER_APPROVED_ONE_FOLDER",
            "live_owner_sync_verified":False,
            "financial_source_parsed":False,
            "real_finance_authorized":False,
        }
