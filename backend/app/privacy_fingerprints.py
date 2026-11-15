"""Synthetic-only keyed identifiers for bank upload deduplication.

Metadata still contains readable amounts/dates/row positions in the existing
schema. This module limits offline guessing of transaction descriptions and
transaction amounts from exposed SHA-256 database fingerprints. It is NOT full
field encryption and changing the key requires an offline explicit reimport.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import os

class FingerprintKeyError(ValueError):
    pass


def _key() -> bytes:
    encoded = os.getenv('LEDGER_DEDUP_HMAC_KEY', '')
    if not encoded:
        raise FingerprintKeyError('Dedicated bank dedup HMAC key is not configured')
    try:
        result = base64.b64decode(encoded, altchars=b'-_', validate=True)
    except (ValueError, UnicodeError) as exc:
        raise FingerprintKeyError('Malformed dedicated HMAC key') from exc
    if len(result) != 32:
        raise FingerprintKeyError('Dedup HMAC key must decode to exactly 32 bytes')
    return result


def require_dedup_key() -> None:
    _key()


def document_digest(payload: bytes) -> str:
    """Content-hiding keyed ID; not a verifiable public SHA-256 checksum."""
    if not payload or len(payload) > 4 * 1024 * 1024:
        raise ValueError('Document must be nonempty and at most 4 MiB')
    return hmac.new(_key(), b'taxfin:document:v1\0' + payload, hashlib.sha256).hexdigest()


def transaction_digest(previous_fingerprint: str) -> str:
    """HMAC old canonical fingerprint, preserving idempotency and occurrence logic.

    Old synthetic database hashes must be rebuilt, NOT automatically re-keyed.
    """
    if (not isinstance(previous_fingerprint, str) or
        len(previous_fingerprint) != 64 or
        any(ch not in '0123456789abcdef' for ch in previous_fingerprint)):
        raise ValueError('Canonical fingerprint must be lowercase SHA-256 hex')
    return hmac.new(_key(), b'taxfin:transaction:v1\0' + bytes.fromhex(previous_fingerprint), hashlib.sha256).hexdigest()