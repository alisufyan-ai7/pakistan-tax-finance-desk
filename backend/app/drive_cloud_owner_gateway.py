"""P1F: NON-DEPLOYED, synthetic-only owner-MFA and OAuth callback gateway.

An isolated ASGI candidate for exact-route security testing. Not imported by the
Railway preview app, not wired into Nginx, and deliberately unable to contact
Google, accept authentic tokens, or connect any real owner Drive.

In production the browser callback needs a session cookie with SameSite=Lax:
a SameSite=Strict cookie does not accompany Google's cross-site GET redirect.
The PKCE state is *also* bound to this same browser session digest and can be
claimed only once. An OAuth callback is not a substitute for an owner login.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
import os
import re
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth_mfa import (
    check_password, claim_synthetic_totp_step, csrf_for_session, session_token,
    token_digest, totp_step,
)
from .cloud_drive_oauth_vault import (
    CloudOAuthCustodyBlocked, _config, remember_fake_cloud_attempt,
    claim_fake_cloud_attempt, cloud_connection_status, disconnect_fake_cloud_grant,
)
from .drive_google_oauth import begin_google_metadata_consent
from .models import OwnerSession

# This is the owner's already-registered origin. Only the exact origin/host
# is trusted in this candidate. It is NOT a command to expose the route.
ORIGIN = "https://personal-cfo-frontend-preview-development.up.railway.app"
HOST = "personal-cfo-frontend-preview-development.up.railway.app"
COOKIE = "__Host-cfo-drive-owner"
SESSION_SECONDS = 15 * 60
FAKE_CODE_RE = re.compile(r"^SYNTHETIC_GOOGLE_CODE_[A-Za-z0-9_-]{12,120}$")
COOKIE_RE = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
CSRF_RE = re.compile(r"^[0-9a-f]{64}$")

# These are PRIVATE candidate paths; do not automatically publish /api/*.
PRIVATE_ROUTES = frozenset({
    ("POST", "/internal/drive/oauth/start"),
    ("GET", "/internal/drive/oauth/callback"),
    ("GET", "/internal/drive/oauth/status"),
    ("POST", "/internal/drive/oauth/disconnect"),
    ("POST", "/internal/drive/auth/logout"),
})


class OwnerCloudGatewayBlocked(ValueError):
    """The separately gated owner-cloud security contract is not satisfied."""


def _guard_fake(db: Session) -> None:
    if os.getenv("P1F_SYNTHETIC_OWNER_GATEWAY_ONLY") != "1":
        raise OwnerCloudGatewayBlocked("Owner cloud gateway not authorized")
    try:
        _config(db)
    except Exception:
        raise OwnerCloudGatewayBlocked("Owner cloud gateway cannot use real credentials") from None


def provision_fake_mfa_session(
    db: Session, *, username: str, password: str, totp_code: str,
    now_epoch: int | None = None,
) -> str:
    """Rehearse real password+TOTP atomic issuance, WITHOUT a public login route.

    There is NO web-accessible password attempt endpoint/rate limiter. The
    synthetic owner secret and scrypt hash must be separately injected by CI.
    A real owner provisioning service still requires a G2 threat/security gate.
    """
    _guard_fake(db)
    expected_user = "synthetic-owner"
    stored = os.getenv("P1F_FAKE_OWNER_PASSWORD_SCRYPT", "")
    secret = os.getenv("P1F_FAKE_OWNER_TOTP_SECRET", "")
    if (type(username) is not str or not hmac.compare_digest(username, expected_user)
        or type(password) is not str or not stored.startswith("scrypt-v1$")
        or not check_password(password, stored)):
        raise OwnerCloudGatewayBlocked("Synthetic owner MFA rejected")
    now = int(datetime.now(timezone.utc).timestamp()) if now_epoch is None else now_epoch
    if type(now) is not int or not 1_500_000_000 <= now <= 4_000_000_000:
        raise OwnerCloudGatewayBlocked("Invalid MFA clock")
    step = totp_step(secret, totp_code, now=now)
    if step is None or not claim_synthetic_totp_step(db, step):
        db.rollback()
        raise OwnerCloudGatewayBlocked("Synthetic owner MFA rejected")
    raw = session_token()
    created = datetime.fromtimestamp(now, timezone.utc)
    db.add(OwnerSession(
        token_sha256=token_digest(raw), csrf_sha256=token_digest(csrf_for_session(raw)),
        created_at=created, expires_at=created + timedelta(seconds=SESSION_SECONDS),
        revoked=False,
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise OwnerCloudGatewayBlocked("Synthetic MFA session could not be stored") from None
    return raw


def apply_candidate_session_cookie(response: JSONResponse, raw: str) -> None:
    """SameSite=Lax permits Google's top-level GET redirect, Strict would not.

    All writes still require exact Origin+CSRF; query state is single-use and
    bound to this cookie. No token is sent in JSON, URLs or JavaScript.
    """
    if type(raw) is not str or COOKIE_RE.fullmatch(raw) is None:
        raise OwnerCloudGatewayBlocked("Invalid private browser cookie")
    response.set_cookie(
        COOKIE, raw, max_age=SESSION_SECONDS, path="/",
        secure=True, httponly=True, samesite="lax",
    )


def _request_boundary(request: Request) -> None:
    # The deployed frontend terminates HTTPS, but this *unmounted candidate*
    # intentionally refuses internal HTTP/X-Forwarded shortcuts. A reviewed
    # future gateway needs strict trusted-proxy handling, not spoofable headers.
    if request.url.scheme != "https":
        raise HTTPException(403, "TLS boundary required")
    if (request.url.hostname != HOST or request.headers.get("host") != HOST
        or request.url.port not in (None, 443)
        or request.headers.get("x-forwarded-host") is not None
        or request.headers.get("x-forwarded-proto") is not None):
        raise HTTPException(403, "Untrusted OAuth request authority")
    if (request.method, request.url.path) not in PRIVATE_ROUTES:
        raise HTTPException(404, "Private cloud route unavailable")


def _owner(db: Session, request: Request, *, mutation: bool = False) -> str:
    _request_boundary(request)
    try:
        _guard_fake(db)
    except OwnerCloudGatewayBlocked:
        raise HTTPException(503, "Synthetic private OAuth gateway unavailable") from None
    cookie = request.cookies.get(COOKIE, "")
    if type(cookie) is not str or COOKIE_RE.fullmatch(cookie) is None:
        raise HTTPException(401, "Owner MFA session required")
    row = db.get(OwnerSession, token_digest(cookie))
    now = datetime.now(timezone.utc)
    if row is None or row.revoked:
        raise HTTPException(401, "Owner MFA session required")
    expiry = row.expires_at
    created = row.created_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    # Explicit short lifetime and no acceptance of future-issued sessions.
    if now >= expiry or created > now + timedelta(seconds=30) or (
        expiry - created > timedelta(seconds=SESSION_SECONDS)
    ):
        raise HTTPException(401, "Owner MFA session expired")
    if mutation:
        supplied = request.headers.get("x-csrf-token", "")
        if (request.headers.get("origin") != ORIGIN
            or type(supplied) is not str or CSRF_RE.fullmatch(supplied) is None
            or not hmac.compare_digest(token_digest(supplied), row.csrf_sha256)):
            raise HTTPException(403, "Origin or CSRF protection failed")
    return cookie


def create_fake_private_oauth_gateway(factory: Callable[[], Session]) -> FastAPI:
    """ONLY an explicitly imported isolated test app; never Railway's app."""
    api = FastAPI(
        title="Synthetic-only cloud OAuth owner gateway contract",
        docs_url=None, redoc_url=None, openapi_url=None,
    )

    @api.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @api.post("/internal/drive/oauth/start")
    def start(request: Request):
        with factory() as db:
            raw = _owner(db, request, mutation=True)
            if request.url.query:
                raise HTTPException(400, "Unapproved OAuth query")
            try:
                cfg, _, _ = _config(db)
                pending = begin_google_metadata_consent(cfg)
                remember_fake_cloud_attempt(
                    db, pending=pending, owner_session_digest=token_digest(raw),
                )
            except Exception:
                raise HTTPException(503, "Private fake OAuth attempt unavailable") from None
        # No actual Google URL is returned, followed or rendered.
        return {"synthetic_only": True, "fake_state": pending.state,
                "google_authorization_url": None, "google_connection_active": False}

    @api.get("/internal/drive/oauth/callback")
    def callback(request: Request):
        with factory() as db:
            raw = _owner(db, request)
            params = request.query_params
            if (set(params.keys()) != {"state", "code"}
                or len(params.getlist("state")) != 1 or len(params.getlist("code")) != 1
                or FAKE_CODE_RE.fullmatch(params.get("code", "")) is None):
                raise HTTPException(400, "Unapproved simulated consent callback")
            try:
                claimed = claim_fake_cloud_attempt(
                    db, state=params["state"], owner_session_digest=token_digest(raw),
                )
            except CloudOAuthCustodyBlocked:
                raise HTTPException(400, "Expired or unbound synthetic consent") from None
        # Fake state was consumed, but no code exchange, token, Google or Drive.
        return {"synthetic_only": True, "state_claimed_once": True,
                "verified_fake_redirect": claimed.redirect_uri.endswith("/api/drive/oauth/callback"),
                "google_connection_active": False}

    @api.get("/internal/drive/oauth/status")
    def status(request: Request):
        with factory() as db:
            raw = _owner(db, request)
            if request.url.query:
                raise HTTPException(400, "Unapproved OAuth query")
        return {**cloud_connection_status(), "synthetic_only": True,
                "csrf_token": csrf_for_session(raw)}

    @api.post("/internal/drive/oauth/disconnect")
    def disconnect(request: Request):
        with factory() as db:
            _owner(db, request, mutation=True)
            if request.url.query:
                raise HTTPException(400, "Unapproved OAuth query")
            try:
                disconnect_fake_cloud_grant(db)
            except Exception:
                raise HTTPException(503, "Synthetic disconnect unavailable") from None
        return {"synthetic_only": True, "fake_local_grant_revoked": True,
                "google_remote_grant_revoked": False}

    @api.post("/internal/drive/auth/logout")
    def logout(request: Request):
        with factory() as db:
            raw = _owner(db, request, mutation=True)
            if request.url.query:
                raise HTTPException(400, "Unapproved OAuth query")
            row = db.get(OwnerSession, token_digest(raw))
            row.revoked = True
            db.commit()
        response = JSONResponse({"synthetic_only": True, "session_revoked": True})
        response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="lax")
        return response

    return api
