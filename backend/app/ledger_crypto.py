"""Authenticated column encryption for synthetic financial text.

DOES NOT certify real-data storage: money amounts, dates, account identifiers,
linkage and file hashes remain queryable metadata. Real-data mode is disabled.
Every envelope carries a version/key id so key rotation is explicit and safe.
"""
from __future__ import annotations

import base64
import json
import os
import re
from secrets import token_bytes

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.types import Text, TypeDecorator

PREFIX = "TFLE1:"
_KEY_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
# Each entry must be a compile-time constant: no caller-supplied SQL/field names.
ENCRYPTED_COLUMNS = {
    "accounts": ("name", "institution"),
    "transactions": ("description", "reference", "category"),
    "audit_events": ("old_category", "new_category", "note"),
    "loan_accounts": ("counterparty_label", "opening_basis"),
    "loan_allocations": ("evidence_note",),
    "transfer_confirmations": ("evidence_note",),
    "loan_allocation_reversals": ("reason",),
    "transfer_revocations": ("reason",),
    "cash_holdings": ("label", "evidence_basis"),
    "cash_movements": ("evidence_note",),
    "cash_movement_reversals": ("reason",),
    "asset_snapshots": ("payload_json",),
    "private_financial_events": ("payload_json",),
    "confidential_bank_batches": ("payload_json",),
    "confidential_bank_key_state": ("sentinel",),
    "canonical_source_mirrors": ("payload_json",),
    "canonical_journal_entries": ("payload_json",),
    "canonical_journal_key_state": ("sentinel",),
    "owner_recovery_states": ("bundle_json",),
    "owner_recovery_audit": ("detail_json",),
}


class LedgerKeyError(ValueError):
    """Missing/invalid key, unknown key id, plaintext or unreadable ciphertext."""


def _decode_key(encoded: str) -> bytes:
    if not isinstance(encoded, str):
        raise LedgerKeyError("Ledger key must be URL-safe base64")
    try:
        decoded = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise LedgerKeyError("Invalid ledger key encoding") from exc
    if len(decoded) != 32:
        raise LedgerKeyError("Ledger encryption keys must be 32 bytes")
    return decoded


def keyring() -> tuple[str, dict[str, bytes]]:
    """Read current keys every time; deployment must inject external secrets."""
    raw = os.getenv("LEDGER_FIELD_KEYS_JSON", "")
    active = os.getenv("LEDGER_FIELD_ACTIVE_KEY", "")
    if not raw or not active:
        raise LedgerKeyError("Ledger field encryption keyring is not configured")
    try:
        spec = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LedgerKeyError("Invalid ledger keyring JSON") from exc
    if not isinstance(spec, dict) or not 1 <= len(spec) <= 16:
        raise LedgerKeyError("Ledger keyring requires 1–16 key identifiers")
    if not all(isinstance(k, str) and _KEY_ID.fullmatch(k) for k in spec):
        raise LedgerKeyError("Invalid ledger key identifier")
    keys = {kid: _decode_key(value) for kid, value in spec.items()}
    if active not in keys:
        raise LedgerKeyError("Active ledger key id is missing")
    return active, keys


def _aad(domain: str) -> bytes:
    allowed = {f"{table}.{column}" for table, columns in ENCRYPTED_COLUMNS.items() for column in columns}
    if domain not in allowed:
        raise LedgerKeyError("Unrecognized encrypted column domain")
    return b"taxfin:ledger-field:v1:" + domain.encode("ascii")


def _raw_decode(token: str) -> tuple[str, bytes, bytes]:
    if not isinstance(token, str) or not token.startswith(PREFIX):
        raise LedgerKeyError("Legacy unsealed ledger value; synthetic rebuild required")
    parts = token.split(":", 2)
    if len(parts) != 3 or not _KEY_ID.fullmatch(parts[1]):
        raise LedgerKeyError("Malformed ledger ciphertext envelope")
    try:
        blob = base64.b64decode(parts[2], altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise LedgerKeyError("Invalid ledger ciphertext encoding") from exc
    if len(blob) < 12 + 16:
        raise LedgerKeyError("Truncated ledger ciphertext")
    return parts[1], blob[:12], blob[12:]


def seal(value: str, domain: str, *, key_id: str | None = None) -> str:
    if not isinstance(value, str):
        raise TypeError("Encrypted field expects a string")
    active, keys = keyring()
    kid = key_id or active
    if kid not in keys:
        raise LedgerKeyError("Requested key id not available")
    nonce = token_bytes(12)
    ciphertext = AESGCM(keys[kid]).encrypt(nonce, value.encode("utf-8"), _aad(domain))
    return f"{PREFIX}{kid}:{base64.urlsafe_b64encode(nonce + ciphertext).decode('ascii')}"


def unseal(token: str, domain: str) -> str:
    _, keys = keyring()
    kid, nonce, ciphertext = _raw_decode(token)
    if kid not in keys:
        raise LedgerKeyError("Ledger ciphertext key id unavailable")
    plaintext = AESGCM(keys[kid]).decrypt(nonce, ciphertext, _aad(domain))
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LedgerKeyError("Ciphertext did not contain UTF-8") from exc


def envelope_key_id(token: str) -> str:
    return _raw_decode(token)[0]


class EncryptedText(TypeDecorator):
    """SQLAlchemy transparent at-rest encryption; all filtering occurs after read.

    Randomized ciphertext MUST NOT be used in equality, sorting or LIKE clauses.
    The domain is static per column, not supplied from untrusted input.
    """
    impl = Text
    cache_ok = True

    def __init__(self, domain: str):
        _aad(domain)
        self.domain = domain
        super().__init__()

    def process_bind_param(self, value, dialect):
        return None if value is None else seal(value, self.domain)

    def process_result_value(self, value, dialect):
        return None if value is None else unseal(value, self.domain)

    def copy(self, **kw):
        return EncryptedText(self.domain)


# Foreign/legacy plaintext SQL values must NEVER be automatically re-encrypted by
# the running app. No implicit migration. Explicit developer-authorized synthetic
# wipe/reimport, or offline audited migration from a verified backup, is required.


def assert_encrypted_ledger(engine) -> None:
    """Reject pre-M2d plaintext stores. Never silently rewrite an old ledger.

    Intended only for the synthetic/local demonstration. A production boot check
    will need a versioned migrator and integrity/backup procedure, not full scans.
    """
    from sqlalchemy import inspect, text
    keyring()  # No hardcoded fallback: fail when secrets are absent.
    present = set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        for table, columns in ENCRYPTED_COLUMNS.items():
            if table not in present:
                continue
            for column in columns:
                # Table/column names are constants, not user-provided.
                unsealed = connection.execute(
                    text(f"SELECT 1 FROM {table} WHERE {column} IS NOT NULL "
                         f"AND {column} NOT LIKE :envelope_prefix LIMIT 1"),
                    {"envelope_prefix": "TFLE1:%"},
                ).first()
                if unsealed:
                    raise LedgerKeyError(
                        "Existing unsealed synthetic ledger values detected; "
                        "back up and explicitly reimport synthetic fixtures"
                    )