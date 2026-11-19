"""P1Q: separately mounted, internal-only private owner MFA HTTP candidate.

This is NOT imported or started by app.preview_api; it has no Google, finance,
or original-file routes. Only a specifically reviewed exact-route private
Railway proxy may forward to it, protected by a distinct operator gateway key.
Real enrollment, independent key custody, source recovery, and edge log review
must be accepted separately before activation.

No login body, TOTP, cookie, CSRF token or gateway key may be logged.
"""
from __future__ import annotations

from collections.abc import Callable
import hmac
import json
import os
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, issue_private_owner_session,
    verify_private_owner_session, revoke_private_owner_session,
    renew_private_owner_session_csrf,
)

_PUBLIC = "https://personal-cfo-frontend-preview-development.up.railway.app"
_PRIVATE_HOST = "personal-cfo-api-preview.railway.internal"
_COOKIE = "__Host-personal-cfo-owner"
_GATEWAY_HEADER = "x-personal-cfo-private-gateway"
_CSRF_HEADER = "x-csrf-token"
_OWNER_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_GATEWAY_RE = re.compile(r"^[A-Za-z0-9_-]{48,256}$")
_PATHS = frozenset({
    ("POST", "/internal/drive/auth/login"),
    ("GET", "/internal/drive/auth/session"),
    ("POST", "/internal/drive/auth/logout"),
    # Only the separately instantiated P1T candidate mounts these.
    ("POST", "/internal/drive/oauth/start"),
    ("GET", "/internal/drive/oauth/callback"),
    ("GET", "/internal/drive/oauth/status"),
    ("POST", "/internal/drive/metadata/refresh"),
    # P4C separately mounted/read-only Google consent routes, never wildcard.
    ("POST", "/internal/drive/content/oauth/start"),
    ("GET", "/internal/drive/content/oauth/status"),
    ("POST", "/internal/drive/content/source/preflight"),
    # P5D owner-only encrypted evidence notes; never public wildcard.
    ("GET", "/internal/finance/review/status"),
    ("POST", "/internal/finance/review/comment"),
    ("POST", "/internal/finance/review/history"),
    ("POST", "/internal/finance/historical/bahl"),
})
_MAX_BODY = 2048


def _boundary(request: Request, *, mutation: bool,
              callback_query: bool = False) -> str:
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1Q_PRIVATE_HTTP_GATEWAY_ONLY") != "1"
        or os.getenv("P1Q_G2_PRIVATE_INGRESS_REVIEWED") != "1"):
        raise HTTPException(status_code=503, detail="Private owner gateway unavailable")

    configured = os.getenv("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", "")
    provided = request.headers.get(_GATEWAY_HEADER, "")
    if (not _GATEWAY_RE.fullmatch(configured)
        or not _GATEWAY_RE.fullmatch(provided)
        or not hmac.compare_digest(provided, configured)):
        raise HTTPException(status_code=403, detail="Private gateway request denied")

    # The real approved edge must SET these headers, not forward user-supplied
    # Forwarded/X-Forwarded-Host/IP/Real-IP. The private API has no public domain.
    if (request.headers.get("host") != _PRIVATE_HOST
        or request.headers.get("x-forwarded-proto") != "https"
        or request.headers.get("forwarded") is not None
        or request.headers.get("x-forwarded-host") is not None
        or request.headers.get("x-forwarded-for") is not None
        or request.headers.get("x-real-ip") is not None
        or (request.url.query and not (
            callback_query and request.method == "GET"
            and request.url.path == "/internal/drive/oauth/callback"))
        or (request.method, request.url.path) not in _PATHS):
        raise HTTPException(status_code=403, detail="Untrusted private owner ingress")

    if mutation and request.headers.get("origin") != _PUBLIC:
        raise HTTPException(status_code=403, detail="Invalid owner request origin")

    # Reuse the exact owner reference from the private enrollment/key escrow.
    # No second owner identity or duplicate public gateway owner variable.
    owner = os.getenv("P1W_OWNER_REF", "")
    if not _OWNER_RE.fullmatch(owner):
        raise HTTPException(status_code=503, detail="Private owner identity not configured")
    return owner


def _unique_json_pairs(pairs: list[tuple[str, object]]) -> dict:
    """Deny duplicate JSON members rather than silently choosing a password."""
    values = {}
    for key, value in pairs:
        if key in values:
            raise ValueError()
        values[key] = value
    return values


async def _login_input(request: Request) -> tuple[str, str]:
    if request.headers.get("content-type") != "application/json":
        raise HTTPException(status_code=415, detail="Strict JSON owner login required")
    try:
        header = request.headers.get("content-length")
        if header and (not header.isdecimal() or int(header) > _MAX_BODY):
            raise ValueError()
        if request.headers.get("transfer-encoding") is not None:
            raise ValueError()
        raw = await request.body()
        if len(raw) > _MAX_BODY:
            raise ValueError()
        data = json.loads(raw, object_pairs_hook=_unique_json_pairs)
        if type(data) is not dict or set(data) != {"password", "totp_code"}:
            raise ValueError()
        password, code = data["password"], data["totp_code"]
        if (type(password) is not str or not 16 <= len(password) <= 256
            or type(code) is not str or not re.fullmatch(r"[0-9]{6}", code)):
            raise ValueError()
        return password, code
    except Exception:
        raise HTTPException(status_code=400, detail="Owner login request rejected") from None


def create_private_owner_http_gateway(
    session_factory: Callable[[], Session], *, lifespan=None,
) -> FastAPI:
    """Unexposed private ASGI factory, tested with fake keys/owner only.

    No public route or private Railway runtime ever imports this factory.
    """
    app = FastAPI(
        title="Personal CFO private owner-only security boundary",
        docs_url=None, redoc_url=None, openapi_url=None,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def no_sensitive_caching(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=()"
        return response

    @app.post("/internal/drive/auth/login")
    async def login(request: Request):
        owner = _boundary(request, mutation=True)
        if request.cookies.get(_COOKIE):
            raise HTTPException(status_code=403, detail="Existing session requires logout")
        password, totp = await _login_input(request)
        try:
            with session_factory() as db:
                proof = issue_private_owner_session(
                    db, owner_ref=owner, password=password, totp_code=totp)
        except PrivateOwnerIdentityBlocked:
            raise HTTPException(status_code=401, detail="Owner MFA rejected") from None
        except Exception:
            raise HTTPException(status_code=503, detail="Owner login unavailable") from None
        response = JSONResponse({
            "authenticated": True,
            "expires_epoch": proof.expires_epoch,
            "csrf_token": proof.csrf_token,
            "google_connected": False,
            "real_financial_data_enabled": False,
        })
        response.set_cookie(
            _COOKIE, proof.cookie_token, max_age=900, path="/",
            secure=True, httponly=True, samesite="lax",
        )
        return response

    @app.get("/internal/drive/auth/session")
    def session(request: Request):
        owner = _boundary(request, mutation=False)
        token = request.cookies.get(_COOKIE, "")
        try:
            with session_factory() as db:
                proof = renew_private_owner_session_csrf(
                    db, owner_ref=owner, token=token)
        except PrivateOwnerIdentityBlocked:
            raise HTTPException(status_code=401, detail="Owner MFA session required") from None
        except Exception:
            raise HTTPException(status_code=503, detail="Owner session unavailable") from None
        return {"authenticated": True,
                "csrf_token": proof["csrf_token"],
                "google_connected": False,
                "real_financial_data_enabled": False}

    @app.post("/internal/drive/auth/logout")
    def logout(request: Request):
        owner = _boundary(request, mutation=True)
        token = request.cookies.get(_COOKIE, "")
        csrf = request.headers.get(_CSRF_HEADER, "")
        try:
            with session_factory() as db:
                revoke_private_owner_session(
                    db, owner_ref=owner, token=token, csrf=csrf)
        except PrivateOwnerIdentityBlocked:
            raise HTTPException(status_code=401, detail="Owner logout rejected") from None
        except Exception:
            raise HTTPException(status_code=503, detail="Owner logout unavailable") from None
        response = JSONResponse({
            "authenticated": False, "local_session_revoked": True,
            "google_grant_revoked": False,
        })
        response.delete_cookie(
            _COOKIE, path="/", secure=True, httponly=True, samesite="lax")
        return response

    return app
