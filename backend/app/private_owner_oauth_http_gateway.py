"""P1T: unmounted synthetic-only private MFA -> OAuth callback HTTP integration.

Never imported by the Railway preview entrypoint. This deliberately operates
ONLY on a fictional Google client/folder and does not call Google or retain
any provider code. It tests the real-compatible P1Q MFA cookie and P1R
encrypted, session-bound, single-use PKCE state across HTTP request boundaries.

The registered public callback and private Railway proxy must undergo an
independent real TLS/Host/Origin/cookie/log audit before ANY actual OAuth
endpoint, client secret, live Google grant, or original owner data is enabled.
"""
from __future__ import annotations

from collections.abc import Callable
import os

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from .private_owner_http_gateway import (
    _COOKIE, _CSRF_HEADER, _boundary, create_private_owner_http_gateway,
)
from .private_owner_google_oauth_state import (
    PrivateOAuthStateBlocked, begin_private_session_google_oauth,
    consume_private_session_google_oauth,
)
from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, verify_private_owner_session,
)

_CALLBACK = "/internal/drive/oauth/callback"
_FINISH = "/"  # Always remove Google code/state from the browser address.
_MAX_QUERY = 3072


def _synthetic_http_guard() -> None:
    # These guardrails are *in addition* to private owner MFA/CSRF and
    # the independent P1R vaulted state/security checks. They make it
    # impossible to accidentally present genuine Google consent through
    # the source-only rehearsal by setting ordinary P1B OAuth variables.
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1T_SYNTHETIC_HTTP_OAUTH_ONLY") != "1"
        or os.getenv("P1T_G2_HTTP_REHEARSAL_REVIEWED") != "1"
        or not os.getenv("P1B_GOOGLE_CLIENT_ID", "").startswith(
            "000000000000-syntheticdev.")
        or not os.getenv("P1B_GOOGLE_FOLDER_ID", "").startswith("SYNTHETIC_")
        or os.getenv("P1C_GOOGLE_NETWORK_ENABLED") == "1"):
        raise HTTPException(503, "Synthetic-only OAuth HTTP rehearsal unavailable")


def create_synthetic_private_owner_oauth_gateway(
    session_factory: Callable[[], Session],
):
    """Separately instantiated from the public preview or private owner API.

    A synthetic authorization URL can only be returned in this fictional
    test app. The callback acknowledges neither genuine Google consent nor
    a live provider connection, and emits no verifier, state, code or token.
    """
    app = create_private_owner_http_gateway(session_factory)

    @app.post("/internal/drive/oauth/start")
    async def start(request: Request):
        owner = _boundary(request, mutation=True)
        _synthetic_http_guard()
        if (request.headers.get("content-length", "0") not in ("0", "")
            or request.headers.get("transfer-encoding") is not None):
            raise HTTPException(400, "OAuth start does not accept a request body")
        cookie = request.cookies.get(_COOKIE, "")
        csrf = request.headers.get(_CSRF_HEADER, "")
        try:
            with session_factory() as db:
                url = begin_private_session_google_oauth(
                    db, owner_ref=owner, session_token=cookie, csrf_token=csrf)
        except (PrivateOAuthStateBlocked, PrivateOwnerIdentityBlocked):
            raise HTTPException(401, "Owner MFA/CSRF required") from None
        except Exception:
            raise HTTPException(503, "Synthetic OAuth start unavailable") from None
        return JSONResponse({
            "synthetic_only": True,
            "authorization_url": url,
            "google_connection_active": False,
            "google_token_exchange_performed": False,
            "original_document_access_enabled": False,
        })

    @app.get(_CALLBACK)
    def callback(request: Request):
        # ALWAYS scrub the provider URL using a fixed no-referrer redirect.
        # An unauthorized, duplicate-key, malformed or replayed callback must
        # be indistinguishable from a successful *synthetic* state claim to a
        # network observer. No body/headers include code, state, or verifier.
        try:
            owner = _boundary(request, mutation=False, callback_query=True)
            _synthetic_http_guard()
            params = request.query_params
            if (len(request.url.query) > _MAX_QUERY
                or set(params.keys()) != {"state", "code"}
                or len(params.getlist("state")) != 1
                or len(params.getlist("code")) != 1):
                raise PrivateOAuthStateBlocked("Unapproved synthetic callback shape")
            with session_factory() as db:
                # P1R itself authenticates the same live MFA cookie and consumes
                # the claim atomically before *any* network exchange.
                consume_private_session_google_oauth(
                    db, owner_ref=owner,
                    session_token=request.cookies.get(_COOKIE, ""),
                    state=params["state"], code=params["code"])
        except Exception:
            # No sensitive exception text or OAuth query in responses/logging.
            # The vault rejects corrupted or expired attempts transactionally.
            pass
        return RedirectResponse(
            url=_FINISH, status_code=303,
            headers={"Cache-Control": "no-store",
                     "Pragma": "no-cache",
                     "Referrer-Policy": "no-referrer"})

    @app.get("/internal/drive/oauth/status")
    def status(request: Request):
        owner = _boundary(request, mutation=False)
        _synthetic_http_guard()
        try:
            with session_factory() as db:
                verify_private_owner_session(
                    db, owner_ref=owner, token=request.cookies.get(_COOKIE, ""))
        except PrivateOwnerIdentityBlocked:
            raise HTTPException(401, "Owner MFA session required") from None
        except Exception:
            raise HTTPException(503, "Private OAuth status unavailable") from None
        # A valid PKCE attempt, or a consumed callback, is NOT Google consent.
        return {"synthetic_only": True, "google_drive_app_connected": False,
                "google_token_exchange_performed": False,
                "last_successful_app_sync": None,
                "real_document_import_enabled": False}

    return app
