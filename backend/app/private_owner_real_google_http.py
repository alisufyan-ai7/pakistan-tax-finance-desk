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
import os
import json
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
    refresh_google_access_token, list_private_owner_folder_page,
)
from .private_metadata_grant_custody import (
    PrivateMetadataCustodyBlocked, read_private_metadata_grant,
    store_private_metadata_grant,
)
from .private_owner_google_oauth_state import (
    PrivateOAuthStateBlocked, begin_private_session_google_oauth,
    consume_private_session_google_oauth,
)
from .private_owner_http_gateway import (
    _boundary, _COOKIE, _CSRF_HEADER, _unique_json_pairs,
    create_private_owner_http_gateway,
)
from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, verify_private_owner_session,
)

_MAX_QUERY = 3072
_CALLBACK = "/internal/drive/oauth/callback"
_FINISH = "/owner-login"


class PrivateOwnerGoogleHttpBlocked(ValueError):
    """Real Google connection is not independently accepted."""


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
):
    """HTTP routes exist ONLY on this separately instantiated private app.

    The caller must provide an independently attested one-owner PostgreSQL
    session_factory. This factory does not change the live ASGI entrypoint.
    """
    app = create_private_owner_http_gateway(
        session_factory, lifespan=lifespan,
    )

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

    @app.get(_CALLBACK)
    def callback(request: Request):
        # ALWAYS return the same fixed 303, including for forged, malformed,
        # expired or replayed requests. Never echo code/state/verifier/token,
        # provider error, owner identity, folder ID or personal filenames.
        try:
            owner = _boundary(request, mutation=False, callback_query=True)
            _reviewed_google_http()
            params = request.query_params
            if (len(request.url.query) > _MAX_QUERY
                or set(params.keys()) != {"state", "code"}
                or len(params.getlist("state")) != 1
                or len(params.getlist("code")) != 1):
                raise PrivateOwnerGoogleHttpBlocked(
                    "Unapproved callback parameters"
                )
            with session_factory() as db:
                # Atomic one-use state claim + commit happens BEFORE network.
                claim = consume_private_session_google_oauth(
                    db, owner_ref=owner,
                    session_token=request.cookies.get(_COOKIE, ""),
                    state=params["state"], code=params["code"],
                )
            if (claim.metadata_only is not True
                or claim.state_consumed_before_external_exchange is not True):
                raise PrivateOwnerGoogleHttpBlocked("PKCE claim was not accepted")
            config = private_google_configuration()
            access, refresh = exchange_google_code(
                code=params["code"], verifier=claim.verifier,
                config=config, transport=transport,
            )
            verify_owner_private_folder(
                access_token=access, config=config, transport=transport,
            )
            # Never store refresh token until the folder's identity/visibility
            # and exact metadata scope have been independently authenticated.
            with session_factory() as db:
                store_private_metadata_grant(
                    db, owner_ref=owner, folder_id=config.folder_id,
                    client_id=config.client_id, refresh_token=refresh,
                )
        except Exception:
            # Safe uniform response. No access/error log of provider URL
            # may be enabled on ANY edge, ASGI proxy or Google callback.
            pass
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


    @app.post("/internal/drive/metadata/page")
    async def metadata_page(request: Request):
        """Live owner-only folder direct-children metadata, NO file bytes.

        A POST keeps provider pagination tokens OUT of request-target logs.
        Source filenames are returned only in the authenticated owner's
        no-store JSON body, never persisted in the app or added to a URL.
        """
        owner = _boundary(request, mutation=True)
        try:
            _reviewed_google_http()
        except PrivateOwnerGoogleHttpBlocked:
            raise HTTPException(503, "Private metadata page not enabled") from None
        try:
            length = request.headers.get("content-length")
            if (request.headers.get("content-type") != "application/json"
                or request.headers.get("transfer-encoding") is not None
                or length is not None
                and (not length.isdecimal() or int(length) > 1200)):
                raise ValueError()
            raw = await request.body()
            if not 1 <= len(raw) <= 1200:
                raise ValueError()
            data = json.loads(raw, object_pairs_hook=_unique_json_pairs)
            if type(data) is not dict or set(data) != {"page_token"}:
                raise ValueError()
            page_token = data["page_token"]
            if (page_token is not None
                and (type(page_token) is not str
                     or re.fullmatch(r"[A-Za-z0-9._~+/=-]{1,1024}",
                                     page_token) is None)):
                raise ValueError()
        except Exception:
            raise HTTPException(400, "Private metadata request rejected") from None
        try:
            config = private_google_configuration()
            with session_factory() as db:
                verify_private_owner_session(
                    db, owner_ref=owner,
                    token=request.cookies.get(_COOKIE, ""),
                    csrf=request.headers.get(_CSRF_HEADER, ""),
                    mutation=True,
                )
                refresh = read_private_metadata_grant(
                    db, owner_ref=owner, folder_id=config.folder_id,
                    client_id=config.client_id,
                )
            access, rotated = refresh_google_access_token(
                refresh_token=refresh, config=config, transport=transport,
            )
            # Reverify private ownership/sharing on every metadata request.
            verify_owner_private_folder(
                access_token=access, config=config, transport=transport,
            )
            page = list_private_owner_folder_page(
                access_token=access, config=config, page_token=page_token,
                transport=transport,
            )
            if rotated is not None:
                with session_factory() as db:
                    store_private_metadata_grant(
                        db, owner_ref=owner, folder_id=config.folder_id,
                        client_id=config.client_id, refresh_token=rotated,
                    )
            next_token = page.get("nextPageToken")
            if (next_token is not None and (
                type(next_token) is not str
                or re.fullmatch(r"[A-Za-z0-9._~+/=-]{1,1024}",
                                next_token) is None)):
                raise ValueError()
            items = []
            for file in page["files"]:
                name = file.get("name")
                mime = file.get("mimeType")
                modified = file.get("modifiedTime")
                size = file.get("size")
                if (type(name) is not str or not 1 <= len(name) <= 512
                    or type(mime) is not str or not 1 <= len(mime) <= 128
                    or (modified is not None
                        and (type(modified) is not str
                             or len(modified) > 80))
                    or (size is not None
                        and (type(size) is not str or not size.isdecimal()
                             or len(size) > 20))):
                    raise ValueError()
                items.append({
                    "id": file["id"], "name": name,
                    "mime_type": mime, "modified_time": modified,
                    "size_bytes": int(size) if size is not None else None,
                })
        except (PrivateOwnerIdentityBlocked, PrivateMetadataCustodyBlocked):
            # 401 only for missing owner session; missing/revoked grant
            # yields an opaque unavailable response, never its credentials.
            raise HTTPException(401, "Owner session or Google grant required") from None
        except Exception:
            raise HTTPException(503, "Private folder metadata unavailable") from None
        return {
            "contract": "personal_cfo_private_live_folder_metadata_v1",
            "metadata_only": True,
            "files": items,
            "next_page_token": next_token,
            "one_pinned_folder_only": True,
            "background_sync_active": False,
            "original_file_bytes_imported": False,
            "financial_data_enabled": False,
        }

    return app
