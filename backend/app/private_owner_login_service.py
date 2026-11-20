"""P1AI: unmounted source-only one-owner login ASGI runtime candidate.

Never started by the live Railway preview Dockerfile, app.preview_api or the
public frontend. All configuration gates must be explicitly reviewed in the
existing isolated Personal CFO development service before a *separate* live
deployment is considered. No Google grant, originals, finances or recovery
operator route is mounted.

Do NOT serve this app with default Uvicorn access/error request-target logging:
the actual private process, Railway ingress/log scrubbing and rate controls
require independent G2 review before deployment.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from .private_credential_role_policy import attest_private_credential_role
from .private_owner_http_gateway import (
    _GATEWAY_RE, create_private_owner_http_gateway,
)
from .private_owner_runtime_preflight import _inventory
from .private_owner_setup_cli import _operator_database_url


class PrivateOwnerLoginServiceBlocked(ValueError):
    """Private owner login runtime cannot be mounted under current controls."""


def _reviewed_private_configuration() -> None:
    # Intentionally more restrictive than app.preview_api. The two additional
    # release flags are NEVER configured by deploying this code image.
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("PERSONAL_CFO_PRIVATE_PREVIEW") != "enabled"
        or (
            os.getenv("RAILWAY_PROJECT_NAME"),
            os.getenv("RAILWAY_ENVIRONMENT_NAME"),
            os.getenv("RAILWAY_SERVICE_NAME"),
        ) != (
            "personal-cfo-dev-sandbox",
            "development",
            "personal-cfo-api-preview",
        )
        or os.getenv("P1AI_PRIVATE_OWNER_SERVICE_ONLY") != "1"
        or os.getenv("P1AI_G2_RUNTIME_INDEPENDENTLY_REVIEWED") != "1"
        or os.getenv("P1N_PRIVATE_OWNER_AUTH_ONLY") != "1"
        or os.getenv("P1N_G2_OWNER_IDENTITY_REVIEWED") != "1"
        # An enrolled recovery row is always read during MFA validation.
        # Missing these gates previously made *every* valid login HTTP 401.
        or os.getenv("P1P_PRIVATE_RECOVERY_ONLY") != "1"
        or os.getenv("P1P_G2_RECOVERY_REVIEWED") != "1"
        or os.getenv("P1Q_PRIVATE_HTTP_GATEWAY_ONLY") != "1"
        or os.getenv("P1Q_G2_PRIVATE_INGRESS_REVIEWED") != "1"
        or os.getenv("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT") != "1"
        or not _GATEWAY_RE.fullmatch(
            os.getenv("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", "")
        )
    ):
        raise PrivateOwnerLoginServiceBlocked("Private owner runtime not approved")
    # Reuse the existing five distinct keys, one P1W_OWNER_REF and offline
    # operator PUBLIC key; this check cannot read/print their values.
    try:
        _inventory()
    except Exception:
        raise PrivateOwnerLoginServiceBlocked(
            "Private owner runtime custody not approved"
        ) from None


def _new_engine():
    # The operator helper refuses the financial DATABASE_URL, administrator
    # roles, public hosts, missing TLS and all unrelated DSN query options.
    url = _operator_database_url()
    return create_engine(
        url, pool_pre_ping=True, pool_size=2, max_overflow=0,
        pool_timeout=5,
        connect_args={"connect_timeout": 5,
                      "options": "-c statement_timeout=3500"},
    )


def _attest_enrolled_owner(connection) -> None:
    """Read-only attestation; no password, owner reference, or raw row returned."""
    if connection.dialect.name != "postgresql":
        raise PrivateOwnerLoginServiceBlocked("Isolated PostgreSQL required")
    connection.execute(text("SET TRANSACTION READ ONLY"))
    info = connection.execute(text(
        "SELECT current_database(), current_user,"
        " inet_client_addr() IS NOT NULL,"
        " (SELECT ssl FROM pg_catalog.pg_stat_ssl WHERE pid=pg_backend_pid()),"
        " current_setting('transaction_read_only')"
    )).one()
    if tuple(info) != (
        "personal_cfo_owner_auth", "personal_cfo_owner_credentials",
        True, True, "on"
    ):
        raise PrivateOwnerLoginServiceBlocked(
            "Isolated owner database or TLS not approved"
        )
    attest_private_credential_role(connection)
    counts = (
        connection.execute(text(
            "SELECT count(*) FROM public.owner_private_identities"
        )).scalar_one(),
        connection.execute(text(
            "SELECT count(*) FROM public.owner_private_recovery_states"
        )).scalar_one(),
        connection.execute(text(
            "SELECT count(*) FROM public.owner_private_recovery_audit"
        )).scalar_one(),
    )
    if counts[0] != 1 or counts[1] != 1 or counts[2] < 1:
        raise PrivateOwnerLoginServiceBlocked(
            "Exactly one enrolled and recoverable owner is required"
        )


def create_review_only_private_owner_login_service(*, google_metadata: bool = False,
                                                   google_content: bool = False,
                                                   source_preflight: bool = False,
                                                   review_comments: bool = False,
                                                   historical_bahl: bool = False) -> FastAPI:
    """Factory only: deliberately NOT a module-global app or public endpoint.

    The returned ASGI service contains only the existing three MFA
    login/session/logout routes, no Google, finance, sign-up or recovery API.
    Its life-cycle gate runs before any session can be issued. No Railway
    deployment command or changed live frontend config is included.
    """
    state = {"engine": None}

    def private_session():
        if state["engine"] is None:
            raise PrivateOwnerLoginServiceBlocked("Private owner service not started")
        return Session(state["engine"])

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        engine = None
        try:
            _reviewed_private_configuration()
            engine = _new_engine()
            with engine.connect() as connection:
                _attest_enrolled_owner(connection)
        except Exception:
            if engine is not None:
                engine.dispose()
            # No SQL DSN, TLS failure, keys or owner records in startup logs.
            raise PrivateOwnerLoginServiceBlocked(
                "Private owner runtime startup denied"
            ) from None
        state["engine"] = engine
        try:
            yield
        finally:
            state["engine"] = None
            engine.dispose()

    if bank_csv and (not google_content or not source_preflight):
        raise PrivateOwnerLoginServiceBlocked("Bank CSV requires source and content approval")
    if historical_bahl and (not google_content or not source_preflight):
        raise PrivateOwnerLoginServiceBlocked("Historical banking requires content and original verification")
    if review_comments and not google_content:
        raise PrivateOwnerLoginServiceBlocked("Private review notes require protected owner content")
    if source_preflight and not google_content:
        raise PrivateOwnerLoginServiceBlocked("Original source preflight requires approved content OAuth")
    if google_content and not google_metadata:
        raise PrivateOwnerLoginServiceBlocked("Content OAuth requires metadata owner controller")
    if google_metadata:
        # Distinct from the ordinary three-route MFA service. P1AL verifies
        # all separately approved real Google/PKCE/metadata-only gates.
        from .private_owner_real_google_http import (
            _reviewed_google_http,
            create_review_only_private_google_http_gateway,
        )
        _reviewed_google_http()
        return create_review_only_private_google_http_gateway(
            private_session, lifespan=lifespan,
            enable_content_oauth=google_content,
            enable_source_preflight=source_preflight,
            enable_review_comments=review_comments,
            enable_historical_bahl=historical_bahl,
            enable_bank_csv=bank_csv,
        )
    return create_private_owner_http_gateway(
        private_session, lifespan=lifespan,
    )
