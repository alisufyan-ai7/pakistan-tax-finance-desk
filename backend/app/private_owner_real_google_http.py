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
    enable_source_preflight: bool = False,
    enable_review_comments: bool = False,
    enable_historical_bahl: bool = False,
    enable_bank_csv: bool = False,
    enable_property_inventory: bool = False,
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



    if enable_property_inventory:
        if not enable_content_oauth:
            raise PrivateOwnerGoogleHttpBlocked("Private investment source requires content OAuth")
        _reviewed_content_http()
        from .private_owner_property_inventory_report import (
            PrivatePropertyInventoryReportBlocked,get_private_property_inventory_overview,
        )

        @app.get("/internal/finance/investments/overview")
        async def owner_investment_overview(request:Request):
            owner=_boundary(request,mutation=False)
            try:
                with session_factory() as db:
                    verify_private_owner_session(
                        db,owner_ref=owner,
                        token=request.cookies.get(_COOKIE,""),mutation=False)
            except PrivateOwnerIdentityBlocked:
                raise HTTPException(401,"Owner MFA required") from None
            try:
                result=get_private_property_inventory_overview(
                    session_factory=session_factory,owner_ref=owner,transport=transport)
            except PrivatePropertyInventoryReportBlocked:
                raise HTTPException(503,"Property investments require source review") from None
            return JSONResponse(result)

    if enable_bank_csv:
        if not enable_content_oauth:
            raise PrivateOwnerGoogleHttpBlocked("Owner bank CSV needs approved read-only content grant")
        _reviewed_content_http()
        from .private_owner_bank_csv_report import (
            PrivateBankCsvReportBlocked, get_private_bank_csv_overview,
        )

        @app.get("/internal/finance/bank/csv-overview")
        async def owner_bank_csv_overview(request: Request):
            owner = _boundary(request, mutation=False)
            try:
                with session_factory() as db:
                    verify_private_owner_session(
                        db, owner_ref=owner,
                        token=request.cookies.get(_COOKIE, ""),
                        mutation=False,
                    )
            except PrivateOwnerIdentityBlocked:
                raise HTTPException(401, "Owner MFA required") from None
            try:
                result = get_private_bank_csv_overview(
                    session_factory=session_factory, owner_ref=owner,
                    transport=transport,
                )
            except PrivateBankCsvReportBlocked:
                raise HTTPException(503, "Private bank source needs review") from None
            return JSONResponse(result)

    if enable_historical_bahl:
        if not enable_content_oauth or not enable_source_preflight:
            raise PrivateOwnerGoogleHttpBlocked(
                "Historical BAHL reporting requires approved content + source verification"
            )
        _reviewed_content_http()
        from .private_historical_bahl_http import mount_private_historical_bahl_http
        mount_private_historical_bahl_http(
            app, session_factory=session_factory, transport=transport,
        )

    if enable_review_comments:
        if not enable_content_oauth:
            raise PrivateOwnerGoogleHttpBlocked(
                "Private financial review requires protected content OAuth")

        from sqlalchemy import text as _sqltext
        from .private_owner_review_comments import (
            PrivateOwnerReviewBlocked, _setup as _review_setup,
            append_owner_review_comment, list_owner_review_comments,
        )
        from .private_original_source_preflight import _inventory as _source_inventory
        # Use the already imported module-level read_private_content_grant.
        # A same-name import here would shadow it in the factory closure and
        # break existing P4C content-status routes when P5D is disabled.
        from .private_google_content_consent import refresh_google_content_token
        from .drive_inbox_planner import _index as _source_hmac

        def _review_private_owner(request: Request, *, mutation: bool) -> str:
            owner = _boundary(request, mutation=mutation)
            if os.getenv("P5D_OWNER_REVIEW_HTTP_RUNTIME") != "1":
                raise HTTPException(503, "Private financial review not activated")
            try:
                _reviewed_content_http()
                with session_factory() as db:
                    verify_private_owner_session(
                        db, owner_ref=owner,
                        token=request.cookies.get(_COOKIE, ""),
                        csrf=request.headers.get(_CSRF_HEADER, "") if mutation else None,
                        mutation=mutation,
                    )
                    _review_setup(db, owner)
                    # 0024 migration is NEVER automatically applied by startup.
                    # Keep the UI disabled if the existing DB has not passed
                    # the reviewed encrypted backup/restore and migration gate.
                    db.execute(_sqltext(
                        "SELECT id FROM owner_financial_review_comments LIMIT 0"))
            except PrivateOwnerIdentityBlocked:
                raise HTTPException(401, "Owner MFA/CSRF required") from None
            except Exception:
                raise HTTPException(503, "Private review records unavailable") from None
            return owner

        async def _strict_review_body(request: Request, *, save: bool) -> dict:
            if (request.headers.get("transfer-encoding") is not None
                or len(await request.body()) > 1800):
                raise HTTPException(400, "Invalid review comment request")
            try:
                data = await request.json()
                fields = {"subject_hmac", "subject_kind", "comment"} if save else {
                    "subject_hmac", "subject_kind"}
                if (type(data) is not dict or set(data) != fields
                    or data["subject_kind"] != "document"
                    or type(data["subject_hmac"]) is not str
                    or re.fullmatch(r"[a-f0-9]{64}", data["subject_hmac"]) is None
                    or (save and (
                        type(data["comment"]) is not str
                        or not 1 <= len(data["comment"].strip()) <= 1500
                    ))):
                    raise ValueError()
                return data
            except Exception:
                raise HTTPException(400, "Private review input invalid") from None

        def _assert_source_approved(owner: str, subject_hmac: str) -> None:
            """Never attach notes to invented document IDs or account-wide files."""
            try:
                config = private_google_configuration()
                with session_factory() as db:
                    refresh = read_private_content_grant(
                        db, owner_ref=owner, folder_id=config.folder_id,
                        client_id=config.client_id)
                access, _rotated = refresh_google_content_token(
                    refresh_token=refresh, config=config, transport=transport)
                listed = _source_inventory(access, config=config, transport=transport)
                if not any(_source_hmac("file", item.id) == subject_hmac
                           for item in listed):
                    raise ValueError()
            except Exception:
                raise HTTPException(403, "Document is not in approved source folder") from None

        @app.get("/internal/finance/review/status")
        def financial_review_status(request: Request):
            _review_private_owner(request, mutation=False)
            return {
                "contract": "personal_cfo_owner_review_ready_v1",
                "review_enabled": True,
                "target_kind": "document",
                "append_only_encrypted": True,
                "auto_resolve": False,
                "financial_figures_verified": False,
            }

        @app.post("/internal/finance/review/comment")
        async def financial_review_comment(request: Request):
            owner = _review_private_owner(request, mutation=True)
            data = await _strict_review_body(request, save=True)
            _assert_source_approved(owner, data["subject_hmac"])
            try:
                with session_factory() as db:
                    result = append_owner_review_comment(
                        db, owner_ref=owner,
                        subject_kind="document",
                        subject_hmac=data["subject_hmac"],
                        comment=data["comment"],
                    )
                return JSONResponse({
                    "contract":"personal_cfo_owner_review_comment_saved_v1",
                    "saved_encrypted":result["saved_encrypted"],
                    "review_state":result["review_state"],
                    "revision":result["revision"],
                    "automatically_resolved":False,
                    "original_transaction_changed":False,
                })
            except PrivateOwnerReviewBlocked:
                raise HTTPException(503, "Private review comment unavailable") from None

        @app.post("/internal/finance/review/history")
        async def financial_review_history(request: Request):
            owner = _review_private_owner(request, mutation=True)
            data = await _strict_review_body(request, save=False)
            _assert_source_approved(owner, data["subject_hmac"])
            try:
                with session_factory() as db:
                    records = list_owner_review_comments(
                        db, owner_ref=owner,
                        subject_kind="document",
                        subject_hmac=data["subject_hmac"])
                return JSONResponse(records)
            except PrivateOwnerReviewBlocked:
                raise HTTPException(503, "Private review history unavailable") from None

    if enable_source_preflight:
        if not enable_content_oauth:
            raise PrivateOwnerGoogleHttpBlocked(
                "Source preflight requires protected content OAuth")

        @app.post("/internal/drive/content/source/preflight")
        async def original_source_preflight(request: Request):
            """Hash real originals only after MFA+CSRF, never accept file IDs."""
            from .private_original_source_preflight import (
                PrivateSourcePreflightBlocked, preflight_original_owner_batch,
            )
            owner = _boundary(request, mutation=True)
            try:
                _reviewed_content_http()
            except PrivateOwnerGoogleHttpBlocked:
                raise HTTPException(503, "Private source service disabled") from None
            if (request.headers.get("transfer-encoding") is not None
                or len(await request.body()) > 128):
                raise HTTPException(400, "Invalid private source batch request")
            try:
                payload = await request.json()
                if type(payload) is not dict or set(payload) != {"batch_index"}:
                    raise ValueError()
                batch_index = payload["batch_index"]
                if type(batch_index) is not int or not 0 <= batch_index <= 333:
                    raise ValueError()
            except Exception:
                raise HTTPException(400, "Invalid private source batch") from None
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
                result = preflight_original_owner_batch(
                    session_factory=session_factory,
                    owner_ref=owner, batch_index=batch_index,
                    transport=transport,
                )
            except PrivateSourcePreflightBlocked:
                raise HTTPException(
                    503, "Private source preflight unavailable or needs review"
                ) from None
            return JSONResponse(result)

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
