"""Local encrypted evidence vault; synthetic-only until full production controls exist.

No keys or plaintext documents belong in version control. This primitive is not a
substitute for MFA, audit, key rotation, database encryption or backup/restore.
"""
from __future__ import annotations
import base64
import os
from pathlib import Path
from secrets import token_bytes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"EVD1"

class VaultConfigurationError(Exception):
    pass

class EncryptedEvidenceVault:
    def __init__(self, root: str | Path, key_base64: str):
        try:
            raw = base64.urlsafe_b64decode(key_base64.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise VaultConfigurationError("DOCUMENT_VAULT_KEY must be valid URL-safe base64") from exc
        if len(raw) != 32:
            raise VaultConfigurationError("DOCUMENT_VAULT_KEY must encode exactly 32 bytes")
        self.key = raw
        self.root = Path(root)

    @classmethod
    def from_environment(cls):
        key = os.getenv("DOCUMENT_VAULT_KEY", "")
        if not key:
            raise VaultConfigurationError("Missing DOCUMENT_VAULT_KEY; encrypted storage is disabled")
        return cls(os.getenv("DOCUMENT_VAULT_DIR", "./data/evidence"), key)

    def _target(self, identifier: str):
        import uuid
        try:
            identifier = str(uuid.UUID(identifier))
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid evidence identifier") from exc
        return self.root / f"{identifier}.evd"

    def put(self, identifier: str, plaintext: bytes, associated_data: bytes):
        if not plaintext or len(plaintext) > 1024 * 1024:
            raise ValueError("Evidence is empty or exceeds 1 MiB synthetic limit")
        target = self._target(identifier)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "posix":
            self.root.chmod(0o700)
        nonce = token_bytes(12)
        cipher = AESGCM(self.key).encrypt(nonce, plaintext, associated_data)
        blob = MAGIC + nonce + cipher
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(blob)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return str(target)

    def get(self, identifier: str, associated_data: bytes):
        blob = self._target(identifier).read_bytes()
        if not blob.startswith(MAGIC) or len(blob) < len(MAGIC) + 12 + 16:
            raise ValueError("Invalid encrypted evidence envelope")
        return AESGCM(self.key).decrypt(blob[4:16], blob[16:], associated_data)

    def discard(self, identifier: str):
        self._target(identifier).unlink(missing_ok=True)
