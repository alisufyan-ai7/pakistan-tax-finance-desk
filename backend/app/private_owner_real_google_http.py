"""P1AL: unmounted owner-session-bound REAL-compatible Google metadata OAuth.

Uses exact registered Railway callback, one-time encrypted P1R PKCE claims,
P1C's fixed TLS no-redirect Google transport, and P1M's PostgreSQL encrypted
refresh-token custody. No original document bytes, file downloads, broad
Google Drive search, tax/finance endpoints or uncontrolled redirect URL.

This is a reviewed factory only. It is NEVER mounted by the preview or P1AJ
owner-login process until separately gated P1AL G2/OAuth ingress, actual
Google client-secret custody, and owner browser consent are accepted.
"""
from __future__ import annotations

from collections.abc import Callable
import logging
import os
import re

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from .drive_google_oauth import (
    PERSONAL_CFO_RAILWAY_CALLBACK, GOOGLE_METADATA_SCOPE,
    private_google_configuration,
)
from .private_drive_google_http import (
    _http_google, exchange_google_code, verify_owner_private_folder,
)
from .private_metadata_grant_custody import (
    PrivateMetadataCustodyBlocked, read_private_metadata_grant,
    store_private_metadata_grant,
)
from .private_owner_drive_metadata_preview import (
    scan_one_owner_folder_metadata, PrivateMetadataSnapshotBlocked,
)
from .private_owner_google_oauth_state import (
    PrivateOAuthStateBlocked, begin_private_session_google_oauth,
    consume_private_session_google_oauth,
    begin_private_session_google_content_oauth,
    consume_private_session_google_content_oauth,
)
from .private_google_content_consent import (
    GOOGLE_CONTENT_READ_SCOPE, exchange_google_content_code,
)
from .private_content_grant_custody import (
    PrivateContentGrantBlocked, read_private_content_grant,
    store_private_content_grant,
)
from .private_owner_http_gateway import (
    _boundary, _COOKIE, _CSRF_HEADER,
    create_private_owner_http_gateway,
)
from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, verify_private_owner_session,
)

_MAX_QUERY = 3072
_CALLBACK = "/internal/drive/oauth/callback"
_FINISH = "/owner-login"
_CALLBACK_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,47}$")
_GOOGLE_ISSUER = "https://accounts.google.com"
# RFC 6749 §4.1.2 requires ignoring unrecognized authorization-response
# parameters, e.g. Google's hd, while authenticating code+state via PKCE.
# RFC 9207 requires verifying an optional issuer to prevent AS mix-up.
_LOG = logging.getLogger("personal_cfo.oauth_callback")


class PrivateOwnerGoogleHttpBlocked(ValueError):
    """Real Google connection is not independently accepted."""

def _reviewed_content_http() -> None:
    """Independent consent+vault+ingress gate, NEVER implied by metadata mode."""
    _reviewed_google_http()
    if any(os.getenv(name) != "1" for name in (
        "P4_CONTENT_OAUTH_CONTRACT_ONLY",
        "P4_G2_OWNER_SESSION_CONTENT_REVIEWED",
        "P4_G3_RESTRICTED_SCOPE_ACCEPTED",
        "P4B_PRIVATE_CONTENT_GRANT_CUSTODY",
        "P4B_G2_OWNER_CONTENT_GRANT_REVIEWED",
        "P4B_G3_EXACT_CONTENT_SCOPE_ATTESTED",
        "P4C_CONTENT_OAUTH_RUNTIME",
        "P4C_G2_CONTENT_OAUTH_CALLBACK_REVIEWED",
        "P4C_G3_READONLY_SOURCE_POLICY_REVIEWED",
    )):
        raise PrivateOwnerGoogleHttpBlocked(
            "Private read-only content OAuth not independently accepted"
        )



def _reviewed_google_http() -> None:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1AL_CLOUD_METADATA_NETWORK_ONLY") != "1"
        or os.getenv("P1AL_G2_EXACT_OAUTH_REVIEWED") != "1"
        or os.getenv("P1C_GOOGLE_NETWORK_ENABLED") != "1"
        or os.getenv("P1C_PRIVATE_OWNER_MFA_ACCEPTED") != "1"
        or os.getenv("P1M_PRIVATE_METADATA_CUSTODY_ONLY") != "1"
        or os.getenv("P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED") != "1"
        or os.getenv("P1R_PRIVATE_OAUTH_STATE_ONLY") != "1"
        or os.getenv("P1R_G2_SESSION_OAUTH_REVIEWED") != "1"
        or os.getenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY") != "1"
        or os.getenv("P1AJ_OWNER_LOGIN_RUNTIME") != "1"
        or os.getenv("P1AJ_G2_EXACT_INGRESS_REVIEWED") != "1"
        or os.getenv("P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED") != "1"
    ):
        raise PrivateOwnerGoogleHttpBlocked("Private Google metadata HTTP disabled")
    try:
        config = private_google_configuration()
        if config.redirect_uri != PERSONAL_CFO_RAILWAY_CALLBACK:
            raise ValueError()
        # The network adapter only reads the reviewed sealed service variable
        # during the later callback. This check does not access its plaintext.
    except Exception:
        raise PrivateOwnerGoogleHttpBlocked(
            "Registered private Google callback not accepted"
        ) from None


def create_review_only_private_google_http_gateway(
    session_factory: Callable[[], Session], *,
    transport: Callable = _http_google,
    lifespan=None,
    enable_content_oauth: bool = False,
):
    """HTTP routes exist ONLY on this separately instantiated private app.

    The caller must provide an independently attested one-owner PostgreSQL
    session_factory. This factory does not change the live ASGI entrypoint.
    """
    app = create_private_owner_http_gateway(
        session_factory, lifespan=lifespan,
    )
    if enable_content_oauth:
        _reviewed_content_http()


    @app.post("/internal/drive/oauth/start")
    async def start(request: Request):
        owner = _boundary(request, mutation=True)
        try:
            _reviewed_google_http()
        except PrivateOwnerGoogleHttpBlocked:
            raise HTTPException(503, "Private Google metadata HTTP disabled") from None
        # No JSON/form body; strict session/csrf and rate gates in P1R.
        if (request.headers.get("content-length", "0") not in ("", "0")
            or request.headers.get("transfer-encoding") is not None
            or await request.body()):
            raise HTTPException(400, "Google start requires an empty POST")
        try:
            with session_factory() as db:
                authorization_url = begin_private_session_google_oauth(
                    db, owner_ref=owner,
                    session_token=request.cookies.get(_COOKIE, ""),
                    csrf_token=request.headers.get(_CSRF_HEADER, ""),
                )
        except (PrivateOwnerIdentityBlocked, PrivateOAuthStateBlocked):
            raise HTTPException(401, "Owner MFA/CSRF required") from None
        except Exception:
            raise HTTPException(503, "Private Google start unavailable") from None
        return JSONResponse({
            "authorization_url": authorization_url,
            "google_drive_app_connected": False,
            "scope": "DRIVE_METADATA_ONLY",
            "content_download_enabled": False,
            "financial_data_enabled": False,
        })


    if enable_content_oauth:
        @app.post("/internal/drive/content/oauth/start")
        async def content_start(request: Request):
            owner = _boundary(request, mutation=True)
            try:
                _reviewed_content_http()
            except PrivateOwnerGoogleHttpBlocked:
                raise HTTPException(503, "Private content OAuth disabled") from None
            if (request.headers.get("content-length", "0") not in ("", "0")
                or request.headers.get("transfer-encoding") is not None
                or await request.body()):
                raise HTTPException(400, "Content consent requires empty POST")
            try:
                with session_factory() as db:
                    url = begin_private_session_google_content_oauth(
                        db, owner_ref=owner,
                        session_token=request.cookies.get(_COOKIE, ""),
                        csrf_token=request.headers.get(_CSRF_HEADER, ""),
                    )
            except (PrivateOwnerIdentityBlocked, PrivateOAuthStateBlocked):
                raise HTTPException(401, "Owner MFA/CSRF required") from None
            except Exception:
                raise HTTPException(503, "Read-only content consent unavailable") from None
            return JSONResponse({
                "authorization_url": url,
                "scope": "DRIVE_READONLY_CONTENT",
                "google_content_grant_stored": False,
                "source_bytes_downloaded": False,
                "financial_data_enabled": False,
            })

        @app.get("/internal/drive/content/oauth/status")
        def content_status(request: Request):
            owner = _boundary(request, mutation=False)
            try:
                _reviewed_content_http()
            except PrivateOwnerGoogleHttpBlocked:
                raise HTTPException(503, "Private content status disabled") from None
            try:
                with session_factory() as db:
                    verify_private_owner_session(
                        db, owner_ref=owner,
                        token=request.cookies.get(_COOKIE, ""),
                    )
                config = private_google_configuration()
                try:
                    with session_factory() as db:
                        # Token discarded inside private process, never in JSON.
                        read_private_content_grant(
                            db, owner_ref=owner, folder_id=config.folder_id,
                            client_id=config.client_id,
                        )
                except PrivateContentGrantBlocked:
                    stored = False
                else:
                    stored = True
            except PrivateOwnerIdentityBlocked:
                raise HTTPException(401, "Owner MFA required") from None
            except Exception:
                raise HTTPException(503, "Content grant status unavailable") from None
            return {
                "content_scope": "DRIVE_READONLY_CONTENT",
                "google_content_grant_stored": stored,
                "source_bytes_downloaded": False,
                "financial_data_enabled": False,
            }

    @app.get(_CALLBACK)
    def callback(request: Request):
        # ALWAYS return the same fixed 303, including for forged, malformed,
        # expired or replayed requests. Never echo code/state/verifier/token,
        # provider error, owner identity, folder ID or personal filenames.
        stage = "ingress_or_callback_parameters"
        try:
            owner = _boundary(request, mutation=False, callback_query=True)
            _reviewed_google_http()
            params = request.query_params
            names = set(params.keys())
            # The only authority-bearing response fields are code+state.
            # Do not let ancillary Google fields prevent legitimate consent.
            # Unknown fields are ignored per RFC 6749 §4.1.2, never used
            # for routing, identity, permissions or token exchange.
            if (len(request.url.query) > _MAX_QUERY
                or not {"state", "code"} <= names
                or "error" in names or "error_description" in names
                or "error_uri" in names
                or len(names) > 12
                or any(
                    _CALLBACK_KEY.fullmatch(name) is None
                    or len(params.getlist(name)) != 1
                    or len(params[name]) > 2048
                    or any(ord(ch) < 32 or ord(ch) == 127
                           for ch in params[name])
                    for name in names
                )
                # RFC 9207: when Google includes 'iss', validate it
                # exactly, rather than ignoring a forged/mixed issuer.
                or ("iss" in names and params["iss"] != _GOOGLE_ISSUER)):
                raise PrivateOwnerGoogleHttpBlocked(
                    "Unapproved callback parameters"
                )
            stage = "session_bound_one_use_pkce"
            # The fixed callback is already Google-registered. An independent
            # encrypted scope is bound to every one-time pending state. ONLY
            # a genuine content state can reach the content-token vault.
            claim = None
            if enable_content_oauth:
                try:
                    with session_factory() as db:
                        claim = consume_private_session_google_content_oauth(
                            db, owner_ref=owner,
                            session_token=request.cookies.get(_COOKIE, ""),
                            state=params["state"], code=params["code"],
                        )
                except PrivateOAuthStateBlocked:
                    claim = None
            if claim is None:
                with session_factory() as db:
                    claim = consume_private_session_google_oauth(
                        db, owner_ref=owner,
                        session_token=request.cookies.get(_COOKIE, ""),
                        state=params["state"], code=params["code"],
                    )
            if claim.state_consumed_before_external_exchange is not True:
                raise PrivateOwnerGoogleHttpBlocked("One-use PKCE claim rejected")
            config = private_google_configuration()
            if claim.content_readonly is True and claim.metadata_only is False:
                if not enable_content_oauth:
                    raise PrivateOwnerGoogleHttpBlocked("Content route not mounted")
                _reviewed_content_http()
                stage = "google_content_code_exchange"
                access, refresh = exchange_google_content_code(
                    code=params["code"], verifier=claim.verifier,
                    config=config, transport=transport,
                )
                stage = "approved_content_folder_verification"
                verify_owner_private_folder(
                    access_token=access, config=config, transport=transport,
                )
                stage = "encrypted_content_grant_storage"
                with session_factory() as db:
                    store_private_content_grant(
                        db, owner_ref=owner, folder_id=config.folder_id,
                        client_id=config.client_id, refresh_token=refresh,
                        verified_granted_scope=GOOGLE_CONTENT_READ_SCOPE,
                    )
            elif claim.metadata_only is True and claim.content_readonly is False:
                stage = "google_code_exchange"
                access, refresh = exchange_google_code(
                    code=params["code"], verifier=claim.verifier,
                    config=config, transport=transport,
                )
                stage = "owner_private_folder_verification"
                verify_owner_private_folder(
                    access_token=access, config=config, transport=transport,
                )
                stage = "encrypted_metadata_grant_storage"
                with session_factory() as db:
                    store_private_metadata_grant(
                        db, owner_ref=owner, folder_id=config.folder_id,
                        client_id=config.client_id, refresh_token=refresh,
                    )
            else:
                raise PrivateOwnerGoogleHttpBlocked("Content/metadata state confusion")
        except Exception:
            # Only an enumerated stage, never exception strings or secrets.
            # Response is identical for success and failure.
            _LOG.warning("owner_google_consent_failed stage=%s", stage)
        return RedirectResponse(
            _FINISH, status_code=303,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache",
                     "Referrer-Policy": "no-referrer"},
        )

    @app.get("/internal/drive/oauth/status")
    def status(request: Request):
        owner = _boundary(request, mutation=False)
        try:
            _reviewed_google_http()
        except PrivateOwnerGoogleHttpBlocked:
            raise HTTPException(503, "Private Google metadata HTTP disabled") from None
        try:
            with session_factory() as db:
                verify_private_owner_session(
                    db, owner_ref=owner,
                    token=request.cookies.get(_COOKIE, ""),
                )
            config = private_google_configuration()
            try:
                with session_factory() as db:
                    # Returned token is immediately discarded in private
                    # process; only the presence of an authenticated grant
                    # is revealed to the signed-in one-owner browser.
                    read_private_metadata_grant(
                        db, owner_ref=owner, folder_id=config.folder_id,
                        client_id=config.client_id,
                    )
            except PrivateMetadataCustodyBlocked:
                connected = False
            else:
                connected = True
        except PrivateOwnerIdentityBlocked:
            raise HTTPException(401, "Owner MFA session required") from None
        except Exception:
            raise HTTPException(503, "Private Google status unavailable") from None
        return {
            "metadata_scope": "DRIVE_METADATA_ONLY",
            "google_drive_app_connected": connected,
            "last_successful_app_sync": None,
            "original_content_import_enabled": False,
            "financial_data_enabled": False,
        }

    @app.post("/internal/drive/metadata/refresh")
    async def metadata_refresh(request: Request):
        """One complete approved-folder snapshot, no media or raw Drive IDs."""
        owner = _boundary(request, mutation=True)
        try:
            _reviewed_google_http()
        except PrivateOwnerGoogleHttpBlocked:
            raise HTTPException(503, "Private Documents unavailable") from None
        if (request.headers.get("content-length", "0") not in ("0", "")
            or request.headers.get("transfer-encoding") is not None
            or await request.body()):
            raise HTTPException(400, "Private Documents requires empty POST")
        try:
            with session_factory() as db:
                verify_private_owner_session(
                    db, owner_ref=owner,
                    token=request.cookies.get(_COOKIE, ""),
                    csrf=request.headers.get(_CSRF_HEADER, ""),
                    mutation=True,
                )
        except PrivateOwnerIdentityBlocked:
            raise HTTPException(401, "Owner MFA/CSRF required") from None
        try:
            # Reuse the independently accepted P1AP bounded, all-or-nothing,
            # private owner-only snapshot. No user-supplied folder/cursor.
            data = scan_one_owner_folder_metadata(
                session_factory=session_factory,
                owner_ref=owner, transport=transport,
            )
        except PrivateMetadataSnapshotBlocked:
            raise HTTPException(503, "Private Documents unavailable") from None
        return JSONResponse(data)


    return app
