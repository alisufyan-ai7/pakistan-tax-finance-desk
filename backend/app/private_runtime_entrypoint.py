"""P1AJ: reviewed single-process ASGI switch for existing private preview service.

Default mode is *exactly* app.preview_api:create_preview_app() and never
imports or mounts owner routes. Explicit opt-in mode serves only three
internal one-owner MFA routes alongside the existing preview. It does not
change the frontend Nginx and cannot enable public Google consent, document
bytes, real financial mode or other endpoints.

Must be launched with --no-access-log and without debug/reload; the separately
reviewed edge must suppress path/query/body/cookie/error request-target logs.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from .preview_api import create_preview_app

_OWNER_ROUTES = frozenset({
    "/internal/drive/auth/login",
    "/internal/drive/auth/session",
    "/internal/drive/auth/logout",
})
_GOOGLE_ROUTES = frozenset({
    "/internal/drive/oauth/start",
    "/internal/drive/oauth/callback",
    "/internal/drive/oauth/status",
    "/internal/drive/metadata/refresh",
})


_GOOGLE_CONTENT_ROUTES = frozenset({
    "/internal/drive/content/oauth/start",
    "/internal/drive/content/oauth/status",
})

class PrivateRuntimeSwitchBlocked(ValueError):
    """Owner route exposure not authorized by exact private release gates."""


class _PrivatePreviewComposite:
    """Route by exact canonical path, never wildcard-prefix proxy."""

    def __init__(self, preview: FastAPI, owner: FastAPI, *,
                 google_metadata: bool = False, google_content: bool = False):
        self.preview = preview
        self.owner = owner
        self.owner_routes = (_OWNER_ROUTES
            | (_GOOGLE_ROUTES if google_metadata else frozenset())
            | (_GOOGLE_CONTENT_ROUTES if google_content else frozenset()))

        @asynccontextmanager
        async def lifespan(_app):
            # Do not serve ANY requests if either independent startup fails.
            async with preview.router.lifespan_context(preview):
                async with owner.router.lifespan_context(owner):
                    yield

        self._lifecycle = FastAPI(
            title="Personal CFO private lifespan coordinator",
            docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan,
        )

    async def __call__(self, scope, receive, send):
        kind = scope.get("type")
        if kind == "lifespan":
            await self._lifecycle(scope, receive, send)
        elif kind == "http" and scope.get("path") in self.owner_routes:
            # Method mismatch reaches FastAPI to return 405. The P1Q
            # boundary separately requires a trusted gateway proof.
            await self.owner(scope, receive, send)
        else:
            # Missing, query-manipulated or unexpected owner paths are
            # never routed to any private identity/OAuth/finance handler.
            await self.preview(scope, receive, send)


def create_private_runtime_entrypoint():
    mode = os.getenv("P1AJ_OWNER_LOGIN_RUNTIME", "")
    if not mode:
        return create_preview_app()
    if mode != "1":
        raise PrivateRuntimeSwitchBlocked("Private runtime mode rejected")
    # Read and enforce the same concrete private login release controls,
    # including the exact approved Railway project/service, existing escrowed
    # key domains, one owner and restricted SQL role. The startup attests
    # actual read-only owner/recovery rows before accepting any request.
    from .private_owner_login_service import (
        _reviewed_private_configuration,
        create_review_only_private_owner_login_service,
    )
    if (
        os.getenv("P1AJ_G2_EXACT_INGRESS_REVIEWED") != "1"
        or os.getenv("P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED") != "1"
        or os.getenv("APP_DATA_MODE") != "synthetic"
    ):
        raise PrivateRuntimeSwitchBlocked("Private runtime ingress not approved")
    google_mode = os.getenv("P1AN_GOOGLE_METADATA_RUNTIME", "")
    if google_mode not in ("", "0", "1"):
        raise PrivateRuntimeSwitchBlocked("Private Google mode invalid")
    google_on = google_mode == "1"
    content_mode = os.getenv("P4C_CONTENT_OAUTH_RUNTIME", "")
    if content_mode not in ("", "0", "1"):
        raise PrivateRuntimeSwitchBlocked("Private content OAuth mode invalid")
    content_on = content_mode == "1"
    if content_on and not google_on:
        raise PrivateRuntimeSwitchBlocked("Content OAuth cannot run without existing Google metadata")
    if google_on:
        if (
            os.getenv("P1AN_G2_GOOGLE_CALLBACK_INGRESS_REVIEWED") != "1"
            or os.getenv("P1AN_METADATA_ONLY_HTTP_ACCEPTED") != "1"
            or os.getenv("P1C_GOOGLE_NETWORK_ENABLED") != "1"
        ):
            raise PrivateRuntimeSwitchBlocked(
                "Private real Google ingress acceptance absent"
            )
    elif os.getenv("P1C_GOOGLE_NETWORK_ENABLED") == "1":
        # Never enable an outbound Google network mode without also
        # mounting its separately approved session-bound controller.
        raise PrivateRuntimeSwitchBlocked("Unbound Google network denied")
    try:
        _reviewed_private_configuration()
        if google_on:
            from .private_owner_real_google_http import _reviewed_google_http
            _reviewed_google_http()
            if content_on:
                from .private_owner_real_google_http import _reviewed_content_http
                _reviewed_content_http()
    except Exception:
        raise PrivateRuntimeSwitchBlocked(
            "Private runtime credential/metadata authority not accepted"
        ) from None
    owner = (
        create_review_only_private_owner_login_service(
            google_metadata=True, google_content=True)
        if content_on else
        create_review_only_private_owner_login_service(google_metadata=True)
        if google_on else create_review_only_private_owner_login_service()
    )
    return _PrivatePreviewComposite(
        create_preview_app(), owner, google_metadata=google_on,
        google_content=content_on,
    )


# Deliberately keep the image harmless when no P1AJ flags are configured.
app = create_private_runtime_entrypoint()
