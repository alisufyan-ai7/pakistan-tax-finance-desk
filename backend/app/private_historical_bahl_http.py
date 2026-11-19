"""P5G private MFA-only historical BAHL statement route mount candidate.

No global app or public listener. Requires an independently reviewed exact
Nginx ingress, owner MFA session+CSRF, pinned original file HMAC and separately
accepted P5E isolation. All password strings enter only this bounded private
JSON body and the private PDF child's stdin, NEVER logs, SQL or Drive.

No consumer can use this controller to view current balance, income, expenses,
investment returns, unrelated Drive files or change an original.
"""
from __future__ import annotations

from collections.abc import Callable
import json
import os
import re

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .private_owner_http_gateway import _boundary, _COOKIE, _CSRF_HEADER
from .private_owner_identity import verify_private_owner_session, PrivateOwnerIdentityBlocked
from .private_historical_bank_report import (
    analyze_pinned_bahl_historical_report, PrivateHistoricalBankReportBlocked,
)
from .private_drive_google_http import _http_google

_HEX = re.compile(r"^[a-f0-9]{64}$")
_MAX_BYTES = 768
_MAX_MINOR = 10**15


class PrivateHistoricalHttpBlocked(ValueError):
    """Historical bank route not approved for real owner access."""


def _reject_duplicate_fields(pairs):
    value={}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate private request key")
        value[key]=item
    return value


def _strict_body(raw: bytes) -> tuple[str,str | None]:
    """Only source HMAC and OPTIONAL short transient PDF password."""
    try:
        if type(raw) is not bytes or not 2 <= len(raw) <= _MAX_BYTES:
            raise ValueError()
        payload=json.loads(raw,object_pairs_hook=_reject_duplicate_fields)
        if (type(payload) is not dict
            or set(payload) not in ({"source_hmac"},{"source_hmac","password"})
            or type(payload["source_hmac"]) is not str
            or _HEX.fullmatch(payload["source_hmac"]) is None):
            raise ValueError()
        pw=payload.get("password")
        if (pw is not None and (type(pw) is not str
            or not 1<=len(pw)<=128
            or any(ord(c)<33 or ord(c)>126 for c in pw))):
            raise ValueError()
        return payload["source_hmac"],pw
    except Exception:
        raise PrivateHistoricalHttpBlocked("Historical source request invalid") from None


def _validate_report(result: dict, source_hmac: str) -> dict:
    """Never expose a partial or economically misclassified source response."""
    if (type(result) is not dict
        or result.get("contract")!="personal_cfo_owner_historical_bahl_report_v1"
        or result.get("source_hmac")!=source_hmac
        or _HEX.fullmatch(str(result.get("source_content_hmac",""))) is None
        or type(result.get("source_name")) is not str
        or len(result["source_name"])>512
        or result.get("original_source_modified") is not False
        or result.get("content_retained_on_server") is not False
        or result.get("financial_values_verified") is not False
        or result.get("income_minor") is not None
        or result.get("expenses_minor") is not None
        or result.get("current_available_balance_minor") is not None):
        raise PrivateHistoricalHttpBlocked("Historical bank response failed evidence contract")
    status=result.get("status")
    common={
        "contract":"personal_cfo_private_historical_bahl_http_v1",
        "source_hmac":source_hmac,
        "source_name":result["source_name"],
        "source_content_hmac":result["source_content_hmac"],
        "status":status,
        "historical_only":True,
        "income_minor":None,"expenses_minor":None,
        "current_available_balance_minor":None,
        "original_source_modified":False,
        "content_retained_on_server":False,
        "financial_values_verified":False,
    }
    if status in ("PASSWORD_REQUIRED","PASSWORD_REJECTED"):
        return common
    if (status!="SOURCE_STATEMENT_RECONCILED"
        or result.get("source_sha256_verified") is not True
        or result.get("running_balance_reconciled") is not True
        or result.get("printed_gross_totals_match_transactions") is not True
        or result.get("historical_only") is not True
        or result.get("owner_review_required") is not True
        or result.get("transfers_excluded") is not False
        or result.get("all_account_coverage_verified") is not False
        or result.get("ledger_mutated") is not False):
        raise PrivateHistoricalHttpBlocked("Historical statement not fully reconciled")
    for key in (
        "historical_opening_minor","historical_closing_minor",
        "gross_bank_debits_minor","gross_bank_credits_minor","transaction_count",
    ):
        v=result.get(key)
        if type(v) is not int or not 0<=v<=_MAX_MINOR:
            raise PrivateHistoricalHttpBlocked("Unbounded bank source amount")
    start,end=result.get("statement_start"),result.get("statement_end")
    if not (type(start) is str and type(end) is str
        and re.fullmatch(r"20\d\d-\d\d-\d\d",start)
        and re.fullmatch(r"20\d\d-\d\d-\d\d",end)
        and start<=end):
        raise PrivateHistoricalHttpBlocked("Untrusted bank statement period")
    return {**common,
        "statement_start":start,"statement_end":end,
        "historical_opening_minor":result["historical_opening_minor"],
        "historical_closing_minor":result["historical_closing_minor"],
        "gross_bank_debits_minor":result["gross_bank_debits_minor"],
        "gross_bank_credits_minor":result["gross_bank_credits_minor"],
        "transaction_count":result["transaction_count"],
        "source_sha256_verified":True,
        "running_balance_reconciled":True,
        "printed_gross_totals_match_transactions":True,
        "owner_review_required":True,
        "transfers_excluded":False,
        "all_account_coverage_verified":False,
        "ledger_mutated":False,
    }


def mount_private_historical_bahl_http(
    app:FastAPI,*,session_factory:Callable[[],Session],
    transport:Callable=_http_google,
    report_callback:Callable=analyze_pinned_bahl_historical_report,
) -> None:
    """Register ONE exact POST route in a separately approved private app."""
    if (os.getenv("APP_DATA_MODE")!="synthetic"
        or os.getenv("P5G_OWNER_HISTORICAL_HTTP_RUNTIME")!="1"
        or os.getenv("P5G_G2_HISTORICAL_EXACT_INGRESS_REVIEWED")!="1"
        or os.getenv("P5G_G3_PASSWORD_AND_SOURCE_ISOLATION_ACCEPTED")!="1"
        or os.getenv("P4C_CONTENT_OAUTH_RUNTIME")!="1"
        or not isinstance(app,FastAPI)
        or not callable(session_factory) or not callable(transport)
        or not callable(report_callback)):
        raise PrivateHistoricalHttpBlocked("Historical statement service not accepted")

    @app.post("/internal/finance/historical/bahl")
    async def historical_bahl(request:Request):
        owner=_boundary(request,mutation=True)
        if (request.headers.get("transfer-encoding") is not None
            or request.headers.get("content-type","").lower()!="application/json"):
            raise HTTPException(400,"Invalid historical statement request")
        try:
            raw=await request.body()
            subject,pw=_strict_body(raw)
        except PrivateHistoricalHttpBlocked:
            raise HTTPException(400,"Invalid historical statement request") from None
        try:
            with session_factory() as db:
                verify_private_owner_session(
                    db,owner_ref=owner,
                    token=request.cookies.get(_COOKIE,""),
                    csrf=request.headers.get(_CSRF_HEADER,""),
                    mutation=True,
                )
        except PrivateOwnerIdentityBlocked:
            raise HTTPException(401,"Owner MFA/CSRF required") from None
        except Exception:
            raise HTTPException(503,"Private owner session unavailable") from None
        try:
            data=report_callback(
                session_factory=session_factory,owner_ref=owner,
                source_hmac=subject,password=pw,
                transport=transport,
            )
            safe=_validate_report(data,subject)
        except (PrivateHistoricalBankReportBlocked,PrivateHistoricalHttpBlocked):
            raise HTTPException(503,"Historical statement requires private review") from None
        except Exception:
            raise HTTPException(503,"Historical statement unavailable") from None
        finally:
            # Strings are immutable in Python; don't retain the password in
            # SQL, session cookies, JSON output, exceptions or log arguments.
            pw=None
        return JSONResponse(safe,headers={
            "Cache-Control":"no-store, private",
            "Pragma":"no-cache",
            "Referrer-Policy":"no-referrer",
            "X-Content-Type-Options":"nosniff",
        })
