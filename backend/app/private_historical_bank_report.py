"""P5E private historical BAHL statement reports, never current account balance.

Composes scope-isolated Google read-only grant, one complete pinned Drive
inventory, SHA-256 checked raw bytes, and bounded separate-process PDF reader.
Returns a source-backed historical financial observation to an authenticated
owner; no original writes, no SQL financial mutation, no public route here.
"""
from __future__ import annotations

from collections.abc import Callable
import hmac
import os
import re
from sqlalchemy.orm import Session

from .drive_inbox_planner import _index, _version
from .document_preflight import MAX_UPLOAD_BYTES
from .private_content_grant_custody import read_private_content_grant,store_private_content_grant
from .private_drive_google_http import _http_google,_guard_network
from .private_google_content_consent import GOOGLE_CONTENT_READ_SCOPE,refresh_google_content_token
from .private_original_source_preflight import _inventory
from .private_owner_google_media_read import read_pinned_google_source_once,_bounded_google_media
from .private_bahl_pdf_worker import inspect_private_bahl_pdf

_HEX=re.compile(r"^[0-9a-f]{64}$")
_OWNER=re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_BANK_FILE=re.compile(r"^SI-[0-9]{9} BAH eStatement\([0-9]{8}\)\.pdf$")


class PrivateHistoricalBankReportBlocked(ValueError):
    """Owner bank observation cannot safely be computed."""


def _gate(owner: str, subject: str, password: str | None):
    # The alternative guest VM must have its OWN independent Python+pypdf
    # containment acceptance. The standard service's bwrap still cannot boot.
    os_jail_accepted = os.getenv("P5C_BAHL_OS_JAIL_ENFORCED") == "1"
    vm_jail_accepted = (
        os.getenv("P5H_REMOTE_VM_WORKER_ACTIVE") == "1"
        and os.getenv("P5H_REMOTE_VM_G3_REVIEWED") == "1"
    )
    if (os.getenv("APP_DATA_MODE")!="synthetic"
        or type(owner) is not str or _OWNER.fullmatch(owner) is None
        or owner!=os.getenv("P1W_OWNER_REF")
        or type(subject) is not str or _HEX.fullmatch(subject) is None
        or (password is not None and (type(password) is not str
            or not 1<=len(password)<=128
            or any(ord(ch)<33 or ord(ch)>126 for ch in password)))
        or any(os.getenv(k)!="1" for k in (
            "P5E_OWNER_HISTORICAL_REPORT_PILOT",
            "P5E_G3_ISOLATED_BANK_READER_REVIEWED",
            "P5A_ORIGINAL_HASH_PILOT",
            "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
        ))
        or not (os_jail_accepted or vm_jail_accepted)):
        raise PrivateHistoricalBankReportBlocked("Private historical report disabled")


def analyze_pinned_bahl_historical_report(
    *,session_factory:Callable[[],Session],owner_ref:str,source_hmac:str,
    password:str|None=None,transport:Callable=_http_google,
    media_transport:Callable=_bounded_google_media,
)->dict:
    """Server independently resolves a blinded file from complete source inventory."""
    _gate(owner_ref,source_hmac,password)
    if not all(callable(x) for x in (session_factory,transport,media_transport)):
        raise PrivateHistoricalBankReportBlocked("Private source transport invalid")
    try:
        cfg=_guard_network()
        with session_factory() as db:
            refresh=read_private_content_grant(
                db,owner_ref=owner_ref,folder_id=cfg.folder_id,client_id=cfg.client_id)
        access,rotated=refresh_google_content_token(
            refresh_token=refresh,config=cfg,transport=transport)
        if rotated and rotated!=refresh:
            with session_factory() as db:
                store_private_content_grant(
                    db,owner_ref=owner_ref,folder_id=cfg.folder_id,
                    client_id=cfg.client_id,refresh_token=rotated,
                    verified_granted_scope=GOOGLE_CONTENT_READ_SCOPE)
        files=_inventory(access,config=cfg,transport=transport)
        matches=[file for file in files if hmac.compare_digest(
            _index("file",file.id),source_hmac)]
        if len(matches)!=1:raise ValueError()
        item=matches[0]
        if (item.trashed or item.parent_ids!=(cfg.folder_id,)
            or item.mime_type!="application/pdf"
            or _BANK_FILE.fullmatch(item.name) is None
            or item.size_bytes is None
            or not 80<=item.size_bytes<=MAX_UPLOAD_BYTES):raise ValueError()
        blob=read_pinned_google_source_once(
            file_id=item.id,expected_file_hmac=source_hmac,
            expected_revision_hmac=_version(item),
            expected_name_hmac=_index("filename",item.name),
            access_token=access,granted_scope=GOOGLE_CONTENT_READ_SCOPE,
            metadata_transport=transport,media_transport=media_transport)
        result=inspect_private_bahl_pdf(
            raw_pdf=blob.data,password=password,approved_isolated_read=True)
        common={
            "contract":"personal_cfo_owner_historical_bahl_report_v1",
            "source_hmac":source_hmac,"source_content_hmac":blob.content_hmac,
            "source_name":item.name,
            "original_source_modified":False,
            "content_retained_on_server":False,
            "income_minor":None,"expenses_minor":None,
            "current_available_balance_minor":None,
            "financial_values_verified":False,
        }
        if result.get("status") in ("PASSWORD_REQUIRED","PASSWORD_REJECTED"):
            return {**common,"status":result["status"]}
        if (result.get("status")!="SOURCE_STATEMENT_RECONCILED"
            or result.get("contract")!="personal_cfo_bahl_reconciled_statement_v1"
            or result.get("printed_closing_matches_transactions") is not True
            or result.get("printed_gross_totals_match_transactions") is not True
            or result.get("transaction_running_balances_match") is not True
            or result.get("financial_values_verified") is not False
            or result.get("income_minor") is not None
            or result.get("expenses_minor") is not None
            or result.get("current_available_balance_minor") is not None):raise ValueError()
        return {**common,
            "status":"SOURCE_STATEMENT_RECONCILED",
            "statement_start":result["statement_start"],
            "statement_end":result["statement_end"],
            "historical_opening_minor":result["opening_minor"],
            "historical_closing_minor":result["closing_minor"],
            "gross_bank_debits_minor":result["gross_bank_debits_minor"],
            "gross_bank_credits_minor":result["gross_bank_credits_minor"],
            "transaction_count":result["transaction_count"],
            "source_sha256_verified":True,
            "printed_gross_totals_match_transactions":True,
            "running_balance_reconciled":True,
            "historical_only":True,"owner_review_required":True,
            "transfers_excluded":False,"all_account_coverage_verified":False,
            "ledger_mutated":False,
        }
    except Exception:
        raise PrivateHistoricalBankReportBlocked(
            "Private historical bank statement requires password or source review"
        ) from None
