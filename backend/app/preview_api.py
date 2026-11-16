"""Railway-only private synthetic preview API.

Never import the legacy finance API, never expose raw financial tables,
never authorize real owner documents, and never publish a public Railway domain.
PostgreSQL is a private *connectivity demonstration* until G1/G2/G3 pass.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from .owner_workspace_status import build_owner_workspace_status, OwnerWorkspaceBlocked


class PreviewConfigurationError(RuntimeError):
    """An untrusted or incomplete private preview deployment configuration."""


def _configuration() -> tuple[str, str, bool]:
    if os.getenv("APP_DATA_MODE") != "synthetic":
        raise PreviewConfigurationError("Real financial mode is prohibited")
    if os.getenv("PERSONAL_CFO_PRIVATE_PREVIEW") != "enabled":
        raise PreviewConfigurationError("Private preview mode is disabled")
    token = os.getenv("PREVIEW_INTERNAL_TOKEN", "")
    if len(token) < 40 or len(token) > 256 or token.isspace():
        raise PreviewConfigurationError("Private service-to-service authentication is required")
    raw = os.getenv("DATABASE_URL", "")
    try:
        url = make_url(raw)
    except Exception:
        raise PreviewConfigurationError("Private PostgreSQL connection is required") from None
    if url.drivername not in ("postgresql", "postgresql+psycopg"):
        raise PreviewConfigurationError("Only PostgreSQL is supported")
    if not url.host or not url.host.endswith(".railway.internal") or url.port not in (None, 5432):
        raise PreviewConfigurationError("Only Railway project-private PostgreSQL is allowed")
    require_tls = os.getenv("PREVIEW_DB_TLS", "require") == "require"
    if os.getenv("PREVIEW_DB_TLS", "require") not in ("require", "disable_for_ci"):
        raise PreviewConfigurationError("Unsupported PostgreSQL transport setting")
    if not require_tls and os.getenv("PREVIEW_TEST_ONLY") != "1":
        raise PreviewConfigurationError("Disabling DB TLS outside isolated CI is forbidden")
    return str(url.set(drivername="postgresql+psycopg")), token, require_tls


def _engine(database_url: str, tls: bool) -> Engine:
    opts = {
        "options": "-c default_transaction_read_only=on -c statement_timeout=3500",
        "connect_timeout": 5,
        "application_name": "personal-cfo-synthetic-private-preview",
    }
    if tls:
        opts["sslmode"] = "require"
    return create_engine(database_url, pool_pre_ping=True, pool_size=2,
                         max_overflow=0, pool_timeout=5, connect_args=opts)


def _check_database(engine: Engine) -> bool:
    # Does not introspect genuine economic tables, perform migrations or writes.
    with engine.connect() as conn:
        return conn.scalar(text("SELECT 1")) == 1


def create_preview_app() -> FastAPI:
    @asynccontextmanager
    async def lifetime(application: FastAPI):
        url, token, tls = _configuration()
        engine = _engine(url, tls)
        try:
            if not _check_database(engine):
                raise PreviewConfigurationError("Private PostgreSQL unavailable")
            application.state.engine = engine
            application.state.token = token
            yield
        finally:
            engine.dispose()
            application.state.engine = None
            application.state.token = None

    api = FastAPI(title="Personal CFO — private synthetic connectivity", docs_url=None,
                  redoc_url=None, openapi_url=None, lifespan=lifetime)

    @api.get("/healthz")
    def health():
        try:
            if not _check_database(api.state.engine):
                raise RuntimeError("PostgreSQL unavailable")
        except Exception:
            raise HTTPException(503, "Private preview dependency unavailable") from None
        return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})

    @api.get("/internal/preview/status")
    def status(tax_year: int = Query(default=2027, ge=2023, le=2027),
               internal_token: str | None = Header(None, alias="X-Personal-CFO-Preview-Key")):
        expected = api.state.token
        supplied = internal_token or ""
        if len(supplied) > 512 or not hmac.compare_digest(supplied, expected):
            raise HTTPException(401, "Preview service authentication required")
        try:
            if not _check_database(api.state.engine):
                raise RuntimeError("PostgreSQL unavailable")
            data = build_owner_workspace_status(tax_year, legal_owner="individual")
        except (OwnerWorkspaceBlocked, RuntimeError, Exception):
            # Do not report DB names, DSNs, internal service names, money or
            # application tracebacks across the public frontend proxy.
            raise HTTPException(503, "Synthetic preview unavailable") from None
        return JSONResponse({
            "contract": "personal_cfo_private_preview_status_v1",
            "synthetic_only": True,
            "backend": "connected",
            "postgresql": "private_connected",
            "canonical_finance_schema": "NOT_CERTIFIED",
            "real_data_authorized": False,
            "owner_workspace": data,
        }, headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        })

    return api


app = create_preview_app()
