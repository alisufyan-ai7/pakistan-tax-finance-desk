"""P1G-next: unmounted, synthetic-only owner login HTTP contract for G2 review.

No import in app.preview_api, no deployed proxy, genuine credential, owner
enrollment, recovery authority, or OAuth grant. Uses the atomic persistent
throttle from P1G and the same short-lifetime cookie contract as P1F.
The future REAL web gateway needs a separate G2 trusted-proxy/key/role audit.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
import hmac
import os
import re
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import update
from sqlalchemy.orm import Session

from .auth_mfa import csrf_for_session, session_token, token_digest
from .drive_cloud_owner_gateway import (
    HOST, ORIGIN, COOKIE, SESSION_SECONDS, COOKIE_RE, CSRF_RE,
    apply_candidate_session_cookie,
)
from .models import OwnerSession
from .owner_login_throttle import (
    OwnerThrottleBlocked, fake_throttle_health,
    issue_throttled_fake_owner_session,
)

_ROUTES = frozenset({
    ("POST", "/internal/drive/auth/login"),
    ("GET", "/internal/drive/auth/session"),
    ("POST", "/internal/drive/auth/rotate"),
    ("POST", "/internal/drive/auth/logout"),
})


def _boundary(request: Request, *, mutation: bool = False) -> None:
    if ((request.method, request.url.path) not in _ROUTES
        or request.url.scheme != "https"
        or request.url.hostname != HOST
        or request.url.port not in (None, 443)
        or request.headers.get("host") != HOST
        or request.headers.get("x-forwarded-host") is not None
        or request.headers.get("x-forwarded-proto") is not None
        or request.url.query):
        raise HTTPException(403, "Private owner authentication unavailable")
    if mutation and request.headers.get("origin") != ORIGIN:
        raise HTTPException(403, "Untrusted owner login origin")
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1G_FAKE_LOGIN_THROTTLE_ONLY") != "1"
        or os.getenv("P1G_FAKE_LOGIN_HTTP_CONTRACT_ONLY") != "1"):
        raise HTTPException(503, "Owner login gateway disabled")


async def _credentials(request: Request) -> tuple[str, str, str]:
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "Expected private JSON request")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 1024:
            raise HTTPException(413, "Owner login request too large")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(400, "Invalid owner login request") from None
    if (type(value) is not dict or set(value) != {"username", "password", "totp_code"}
        or any(type(value[key]) is not str for key in value)
        or len(value["username"]) > 128 or len(value["password"]) > 256
        or len(value["totp_code"]) != 6
        or re.fullmatch(r"[0-9]{6}", value["totp_code"]) is None):
        raise HTTPException(400, "Invalid owner login request")
    return value["username"], value["password"], value["totp_code"]


def _session(db: Session, request: Request, *, mutation: bool = False) -> tuple[OwnerSession, str]:
    raw = request.cookies.get(COOKIE, "")
    if type(raw) is not str or COOKIE_RE.fullmatch(raw) is None:
        raise HTTPException(401, "MFA session required")
    row = db.get(OwnerSession, token_digest(raw))
    if row is None or row.revoked:
        raise HTTPException(401, "MFA session required")
    now = datetime.now(timezone.utc)
    created = row.created_at
    expires = row.expires_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if (expires <= now or created > now + timedelta(seconds=30)
        or expires - created > timedelta(seconds=SESSION_SECONDS)):
        raise HTTPException(401, "MFA session expired")
    if mutation:
        supplied = request.headers.get("x-csrf-token", "")
        if (CSRF_RE.fullmatch(supplied) is None
            or not hmac.compare_digest(row.csrf_sha256, token_digest(supplied))):
            raise HTTPException(403, "Owner CSRF denied")
    return row, raw


def create_fake_owner_login_http(factory: Callable[[], Session]) -> FastAPI:
    """Explicitly constructed only in disposable tests; NO public route."""
    app = FastAPI(title="Nondeployed synthetic MFA HTTP contract",
                  docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def protections(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        return resp

    @app.post("/internal/drive/auth/login")
    async def login(request: Request):
        _boundary(request, mutation=True)
        username, password, code = await _credentials(request)
        with factory() as db:
            try:
                fake_throttle_health(db)
                raw = issue_throttled_fake_owner_session(
                    db, username=username, password=password, totp_code=code)
            except OwnerThrottleBlocked:
                raise HTTPException(401, "Owner authentication denied") from None
        response = JSONResponse({
            "synthetic_only": True, "mfa_session_issued": True,
            "google_drive_connected": False, "real_data_authorized": False,
        })
        apply_candidate_session_cookie(response, raw)
        return response

    @app.get("/internal/drive/auth/session")
    def status(request: Request):
        _boundary(request)
        with factory() as db:
            try:
                fake_throttle_health(db)
            except OwnerThrottleBlocked:
                raise HTTPException(503, "Private owner auth unavailable") from None
            _, raw = _session(db, request)
        return {"synthetic_only": True, "csrf_token": csrf_for_session(raw),
                "google_drive_connected": False,
                "real_data_authorized": False}

    @app.post("/internal/drive/auth/rotate")
    def rotate(request: Request):
        _boundary(request, mutation=True)
        with factory() as db:
            row, raw = _session(db, request, mutation=True)
            # A conditional revoke prevents two browser tabs from minting
            # simultaneous replacement sessions from the same old cookie.
            result = db.execute(update(OwnerSession).where(
                OwnerSession.token_sha256 == row.token_sha256,
                OwnerSession.revoked.is_(False),
            ).values(revoked=True))
            if result.rowcount != 1:
                db.rollback()
                raise HTTPException(401, "Owner MFA session already rotated")
            new_token = session_token()
            now = datetime.now(timezone.utc)
            db.add(OwnerSession(
                token_sha256=token_digest(new_token),
                csrf_sha256=token_digest(csrf_for_session(new_token)),
                created_at=now, expires_at=now+timedelta(seconds=SESSION_SECONDS),
                revoked=False,
            ))
            db.commit()
        response = JSONResponse({"synthetic_only": True,
                                 "session_rotated": True,
                                 "real_data_authorized": False})
        apply_candidate_session_cookie(response, new_token)
        return response

    @app.post("/internal/drive/auth/logout")
    def logout(request: Request):
        _boundary(request, mutation=True)
        with factory() as db:
            row, _ = _session(db, request, mutation=True)
            row.revoked = True
            db.commit()
        response = JSONResponse({"synthetic_only": True, "session_revoked": True})
        response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="lax")
        return response

    return app
