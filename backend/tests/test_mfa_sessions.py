"""Synthetic-only owner MFA, session, CSRF and logout tests."""
from __future__ import annotations
import base64
import hashlib
import hmac
import sqlite3
from datetime import datetime, timezone, timedelta
from time import time
import pytest
from fastapi.testclient import TestClient
from app.auth_mfa import password_hash,check_password,totp_step,csrf_for_session,SESSION_COOKIE
from app.main import create_app


def _otp(secret: str, when: int | None = None) -> str:
    counter=int(when if when is not None else time())//30
    key=base64.b32decode(secret)
    digest=hmac.new(key,counter.to_bytes(8,'big'),hashlib.sha1).digest()
    off=digest[-1]&0xf
    return f'{((int.from_bytes(digest[off:off+4],"big")&0x7fffffff)%1_000_000):06d}'

@pytest.fixture
def mfa_settings(tmp_path,monkeypatch):
    secret=base64.b32encode(b'correct synthetic only').decode()
    password='synthetic-owner-strong-password-123'
    monkeypatch.setenv('OWNER_AUTH_MODE','totp_session')
    monkeypatch.setenv('OWNER_USERNAME','owner')
    monkeypatch.setenv('OWNER_PASSWORD_SCRYPT',password_hash(password,bytes(range(16))))
    monkeypatch.setenv('OWNER_TOTP_SECRET',secret)
    monkeypatch.setenv('APP_DATA_MODE','synthetic')
    app=create_app(f'sqlite:///{tmp_path / "sessions.db"}')
    with TestClient(app,base_url='https://testserver') as client:
        yield client,secret,password,tmp_path/'sessions.db'


def test_rfc6238_six_digit_totp_and_password_hash():
    # RFC 6238 test-key first time slot: 8-digit code 94287082 -> 6 digits 287082.
    secret=base64.b32encode(b'12345678901234567890').decode()
    assert totp_step(secret,'287082',now=59)==1
    assert totp_step(secret,'287083',now=59) is None
    h=password_hash('synthetic strong password 123')
    assert check_password('synthetic strong password 123',h)
    assert not check_password('not the password',h)
    assert not check_password('synthetic strong password 123','not-a-hash')


def test_mfa_login_cookie_csrf_replay_logout(mfa_settings):
    client,secret,password,dbpath=mfa_settings
    assert client.get('/api/health').status_code==401
    bad=client.post('/api/auth/login',json={'username':'owner','password':'wrong','totp_code':_otp(secret)})
    assert bad.status_code==401
    one_time_code=_otp(secret)
    login=client.post('/api/auth/login',json={'username':'owner','password':password,'totp_code':one_time_code})
    assert login.status_code==200,login.text
    cookie=login.headers['set-cookie']
    assert '__Host-taxfin-session=' in cookie and 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
    assert client.get('/api/health').json()['status']=='ok'
    replay=client.post('/api/auth/login',json={'username':'owner','password':password,'totp_code':one_time_code})
    assert replay.status_code==401 and 'already used' in replay.text
    session=client.get('/api/auth/session').json()
    assert session['mode']=='totp_session' and len(session['csrf_token'])==64
    assert client.post('/api/accounts',json={'name':'Synthetic','institution':'Fake bank'}).status_code==403
    assert client.post('/api/accounts',headers={'X-CSRF-Token':'0'*64},json={'name':'Synthetic','institution':'Fake bank'}).status_code==403
    assert client.post('/api/accounts',headers={'X-CSRF-Token':session['csrf_token'],'Origin':'https://attacker.invalid'},json={'name':'Synthetic','institution':'Fake bank'}).status_code==403
    accepted=client.post('/api/accounts',headers={'X-CSRF-Token':session['csrf_token'],'Origin':'https://testserver'},json={'name':'Synthetic','institution':'Fake bank'})
    assert accepted.status_code==201,accepted.text
    with sqlite3.connect(dbpath) as db:
        token_hash, csrf_hash=db.execute('SELECT token_sha256, csrf_sha256 FROM owner_sessions').fetchone()
    raw_cookie=client.cookies.get(SESSION_COOKIE)
    assert raw_cookie and raw_cookie not in (token_hash, csrf_hash)
    assert csrf_hash==hashlib.sha256(session['csrf_token'].encode()).hexdigest()
    logout=client.post('/api/auth/logout',headers={'X-CSRF-Token':session['csrf_token']})
    assert logout.status_code==200
    assert client.get('/api/health').status_code==401


def test_mfa_session_expiration_and_https_restriction(mfa_settings):
    client,secret,password,dbpath=mfa_settings
    # A second client on insecure HTTP cannot get an authenticated session.
    with TestClient(client.app,base_url='http://testserver') as insecure:
        response=insecure.post('/api/auth/login',json={'username':'owner','password':password,'totp_code':_otp(secret)})
        assert response.status_code==403
    response=client.post('/api/auth/login',json={'username':'owner','password':password,'totp_code':_otp(secret)})
    assert response.status_code==200,response.text
    with sqlite3.connect(dbpath) as db:
        db.execute('UPDATE owner_sessions SET expires_at=?',(datetime(2000,1,1,tzinfo=timezone.utc).isoformat(),))
        db.commit()
    assert client.get('/api/auth/session').status_code==401


def test_totp_invalid_values():
    secret=base64.b32encode(b'correct synthetic only').decode()
    assert totp_step(secret,'abcd12') is None
    assert totp_step('notvalid',_otp(secret)) is None
    assert totp_step(secret,'12345678') is None
