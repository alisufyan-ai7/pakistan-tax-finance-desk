"""P5F: exact, unmounted authenticated BAHL historical report HTTP controller.

Install ONLY from the independently gated owner app after exact Nginx ingress
and source/report sandbox acceptance. Private PDF passwords arrive via a
short-lived HTTPS POST body and go only to private isolated stdin worker.
They are never saved, returned, logged, sent to Google or placed in a URL.
"""
from __future__ import annotations

from collections.abc import Callable
import os
import re

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .private_owner_http_gateway import _boundary,_COOKIE,_CSRF_HEADER
from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, verify_private_owner_session,
)
from .private_historical_bank_report import (
    PrivateHistoricalBankReportBlocked, analyze_pinned_bahl_historical_report,
)

_HEX=re.compile(r"^[a-f0-9]{64}$")


def _release() -> None:
    if (os.getenv("APP_DATA_MODE")!="synthetic"
        or any(os.getenv(k)!="1" for k in (
            "P5F_OWNER_BAHL_HTTP_RUNTIME",
            "P5F_G2_TRANSIENT_PASSWORD_INGRESS_REVIEWED",
            "P5F_G3_BANK_SOURCE_REPORT_REVIEWED",
            "P5E_OWNER_HISTORICAL_REPORT_PILOT",
            "P5E_G3_ISOLATED_BANK_READER_REVIEWED",
            "P5A_ORIGINAL_HASH_PILOT",
            "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
        ))):
        raise PrivateHistoricalBankReportBlocked("Private bank report is not released")


def install_owner_bahl_report_http(
    app, *, session_factory:Callable[[],Session],transport:Callable,
) -> None:
    """Call only on the exact private owner factory with closed gates."""
    _release()

    def authorize(request,mutation):
        owner=_boundary(request,mutation=mutation)
        try:
            _release()
            with session_factory() as db:
                verify_private_owner_session(
                    db,owner_ref=owner,
                    token=request.cookies.get(_COOKIE,""),
                    csrf=request.headers.get(_CSRF_HEADER,"") if mutation else None,
                    mutation=mutation,
                )
        except PrivateOwnerIdentityBlocked:
            raise HTTPException(401,"Owner MFA/CSRF required") from None
        except PrivateHistoricalBankReportBlocked:
            raise HTTPException(503,"Bank statement reader unavailable") from None
        except Exception:
            raise HTTPException(503,"Bank statement session unavailable") from None
        return owner

    @app.get("/internal/finance/bahl/status")
    def owner_bahl_status(request: Request):
        authorize(request,False)
        return JSONResponse({
            "contract":"personal_cfo_owner_historical_bahl_status_v1",
            "historical_source_reports_enabled":True,
            "requires_private_pdf_password_on_demand":True,
            "current_bank_balances_verified":False,
            "income_expenses_verified":False,
            "original_drive_writes_allowed":False,
            "financial_ledger_mutated":False,
        })

    @app.post("/internal/finance/bahl/analyze")
    async def owner_bahl_analyze(request: Request):
        owner=authorize(request,True)
        if (request.headers.get("transfer-encoding") is not None
            or len(await request.body())>480):
            raise HTTPException(400,"Invalid historical statement request")
        try:
            payload=await request.json()
            if (type(payload) is not dict
                or set(payload) not in (
                    {"source_hmac"},{"source_hmac","password"},
                )
                or type(payload["source_hmac"]) is not str
                or _HEX.fullmatch(payload["source_hmac"]) is None):
                raise ValueError()
            password=payload.get("password")
            if password is not None and (
                type(password) is not str or not 1<=len(password)<=128
                or any(ord(ch)<33 or ord(ch)>126 for ch in password)):
                raise ValueError()
        except Exception:
            raise HTTPException(400,"Private historical source request invalid") from None
        try:
            result=analyze_pinned_bahl_historical_report(
                session_factory=session_factory,
                owner_ref=owner,source_hmac=payload["source_hmac"],
                password=password,transport=transport)
            return JSONResponse(result)
        except PrivateHistoricalBankReportBlocked:
            raise HTTPException(
                503,"Historical source unavailable or requires format review"
            ) from None
