"""Owner-only synthetic-session MFA primitives. Not authorized for real financial data.

The development gateway remains restricted to loopback. Production requires a
fully deployed TLS/session/auth audit, robust multiworker throttle and recovery.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import re
from secrets import token_bytes
from time import time

SESSION_COOKIE = '__Host-taxfin-session'
COOKIE_LIFETIME_SECONDS = 8 * 60 * 60


def password_hash(password: str, salt: bytes | None = None) -> str:
    if len(password) < 16 or len(password) > 256:
        raise ValueError('Owner password must be 16-256 characters')
    salt = salt or token_bytes(16)
    if len(salt) != 16:
        raise ValueError('Invalid salt')
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2**15, r=8, p=1, maxmem=64*1024*1024)
    return 'scrypt-v1$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(digest).decode()


def check_password(password: str, stored_hash: str) -> bool:
    try:
        prefix,salt64,digest64=stored_hash.split('$')
        if prefix != 'scrypt-v1':
            return False
        salt=base64.b64decode(salt64,altchars=b'-_',validate=True)
        expected=base64.b64decode(digest64,altchars=b'-_',validate=True)
        if len(salt)!=16 or len(expected)!=64 or len(password)>256:
            return False
        actual=hashlib.scrypt(password.encode('utf-8'),salt=salt,n=2**15,r=8,p=1,maxmem=64*1024*1024)
        return hmac.compare_digest(actual, expected)
    except (ValueError,UnicodeError):
        return False


def totp_step(secret_base32: str, code: str, now: int | None = None) -> int | None:
    """Return matching RFC6238 30-second counter (±1 step), or None."""
    if not re.fullmatch(r'\d{6}',code):
        return None
    try:
        key=base64.b32decode(secret_base32.strip().upper(),casefold=True)
    except (ValueError,UnicodeError):
        return None
    if len(key)<20 or len(key)>64:
        return None
    counter=int(now if now is not None else time())//30
    for value in (counter-1,counter,counter+1):
        if value < 0:
            continue
        mac=hmac.new(key,value.to_bytes(8,'big'),hashlib.sha1).digest()
        offset=mac[-1]&0x0F
        pin=(int.from_bytes(mac[offset:offset+4],'big')&0x7fffffff)%1_000_000
        if hmac.compare_digest(f'{pin:06d}', code):
            return value
    return None


def session_token() -> str:
    return base64.urlsafe_b64encode(token_bytes(32)).decode('ascii').rstrip('=')


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def csrf_for_session(raw_session_token: str) -> str:
    # The raw session token remains HttpOnly; the derived value can be sent to
    # same-origin JavaScript and authenticated in X-CSRF-Token for mutations.
    return hashlib.sha256(('taxfin:csrf:'+raw_session_token).encode('ascii')).hexdigest()
