"""Authenticated encryption for *synthetic* structured filing fields.

This is not yet a complete encrypted database: M1 bank transactions and audit
notes remain plaintext in SQLite. App MUST NOT be used for personal records.
"""
from __future__ import annotations
import base64
import json
from secrets import token_bytes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .evidence_vault import EncryptedEvidenceVault

PREFIX = 'TFJF1:'

def protect_fields(vault: EncryptedEvidenceVault, filing_id: str, tax_year: int, kind: str, fields: dict) -> str:
    raw = json.dumps(fields, sort_keys=True, separators=(',', ':')).encode('utf-8')
    nonce = token_bytes(12)
    aad = f'taxfinance:structured:v1:{filing_id}:{tax_year}:{kind}'.encode()
    encrypted = AESGCM(vault.key).encrypt(nonce, raw, aad)
    return PREFIX + base64.urlsafe_b64encode(nonce + encrypted).decode('ascii')

def reveal_fields(vault: EncryptedEvidenceVault, filing_id: str, tax_year: int, kind: str, sealed: str) -> dict:
    if not sealed.startswith(PREFIX):
        raise ValueError('Legacy plaintext historical row; migrate or discard synthetic demo database')
    raw = base64.b64decode(sealed[len(PREFIX):].encode('ascii'), altchars=b'-_', validate=True)
    if len(raw) < 28:
        raise ValueError('Corrupt structured-data envelope')
    aad = f'taxfinance:structured:v1:{filing_id}:{tax_year}:{kind}'.encode()
    result = json.loads(AESGCM(vault.key).decrypt(raw[:12], raw[12:], aad))
    if not isinstance(result, dict):
        raise ValueError('Unexpected decrypted structured data')
    return result
