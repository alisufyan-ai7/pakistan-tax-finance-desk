"""Optional source-hash-bound, OFFLINE-reconciled BAHL observations.

NO PDF interpreter, document parsing, passwords, owner original bytes in a
worker, or extra VM. Historical observations are provided from an independently
reviewed offline source reconciliation stored only in owner-private Railway
configuration, NOT GitHub. Every displayed observation must still match the
bytes of the CURRENT pinned, read-only Google Drive file.

This is deliberately NOT an assertion that automated PDF parser containment
or current cash/income/investments have been accepted.
"""
from __future__ import annotations

from datetime import date
import hmac
import json
import os
import re

from .drive_inbox_planner import _index, _version
from .private_google_content_consent import GOOGLE_CONTENT_READ_SCOPE
from .private_owner_google_media_read import read_pinned_google_source_once
from .document_preflight import MAX_UPLOAD_BYTES

_HEX = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^SI-[0-9]{9} BAH eStatement\([0-9]{8}\)\.pdf$")
_KEYS = frozenset((
    "name", "sha256", "period_start", "period_end", "opening_minor",
    "closing_minor", "debits_minor", "credits_minor", "transaction_count",
    "page_count",
))
_MAX_MINOR = 10**15


class PrivateOfflineBahlBlocked(ValueError):
    """A historical, privately attested source statement is not acceptable."""


def _strict_object(pairs):
    value = {}
    for key, element in pairs:
        if key in value:
            raise ValueError()
        value[key] = element
    return value


def _private_receipts():
    raw = os.getenv("P6D_PRIVATE_BAHL_OFFLINE_RECEIPTS_JSON")
    if raw is None or raw == "":
        return ()
    if (os.getenv("P6D_OWNER_OFFLINE_PDF_RECEIPTS_ENABLED") != "1"
        or len(raw) > 4096):
        raise PrivateOfflineBahlBlocked("Private historical evidence not reviewed")
    try:
        obj = json.loads(raw, object_pairs_hook=_strict_object)
        if type(obj) is not dict or set(obj) != {"contract", "receipts"} or (
            obj["contract"] != "personal_cfo_p6d_private_offline_bahl_receipts_v1"
            or type(obj["receipts"]) is not list
            or not 1 <= len(obj["receipts"]) <= 3):
            raise ValueError()
        names=set()
        result=[]
        for rec in obj["receipts"]:
            if type(rec) is not dict or set(rec) != _KEYS:
                raise ValueError()
            name = rec["name"]
            if type(name) is not str or not _NAME.fullmatch(name) or name in names:
                raise ValueError()
            names.add(name)
            if type(rec["sha256"]) is not str or not _HEX.fullmatch(rec["sha256"]):
                raise ValueError()
            for key in ("opening_minor", "closing_minor", "debits_minor", "credits_minor",
                        "transaction_count", "page_count"):
                if type(rec[key]) is not int or rec[key] < 0:
                    raise ValueError()
            for key in ("opening_minor", "closing_minor", "debits_minor", "credits_minor"):
                if rec[key] > _MAX_MINOR:
                    raise ValueError()
            if (not 1 <= rec["transaction_count"] <= 5000
                or not 1 <= rec["page_count"] <= 100
                or rec["opening_minor"] + rec["credits_minor"] -
                    rec["debits_minor"] != rec["closing_minor"]):
                raise ValueError()
            start = date.fromisoformat(rec["period_start"])
            end = date.fromisoformat(rec["period_end"])
            if (start > end or (end - start).days > 366
                or not 2020 <= start.year <= 2050):
                raise ValueError()
            result.append(rec)
        return tuple(result)
    except Exception:
        raise PrivateOfflineBahlBlocked(
            "Offline observations require private review") from None


def verify_pinned_offline_receipts(
    *, files, folder_id: str, access_token: str, metadata_transport,
    media_transport,
) -> dict:
    """Re-check exact file SHA and current version, without opening the PDF.

    Never use Google filename as sufficient evidence; compare both pinned
    metadata and the original bytes with an authenticated private receipt.
    Mismatches disappear from UI and contribute only to review count.
    """
    receipts=_private_receipts()
    accepted=[]
    pending=0
    for rec in receipts:
        choices=[item for item in files if item.name == rec["name"]]
        if len(choices) != 1:
            pending+=1
            continue
        item=choices[0]
        if (item.trashed or item.parent_ids != (folder_id,)
            or item.mime_type != "application/pdf" or item.size_bytes is None
            or not 80 <= item.size_bytes <= MAX_UPLOAD_BYTES):
            pending+=1
            continue
        try:
            blob=read_pinned_google_source_once(
                file_id=item.id,expected_file_hmac=_index("file",item.id),
                expected_revision_hmac=_version(item),
                expected_name_hmac=_index("filename",item.name),
                access_token=access_token, granted_scope=GOOGLE_CONTENT_READ_SCOPE,
                metadata_transport=metadata_transport,
                media_transport=media_transport,
            )
            # No PDF interpreter is invoked here. Reconciliation happened
            # offline and is bound to the SHA of the exact current source.
            if (blob.extension != ".pdf"
                or not hmac.compare_digest(blob.sha256, rec["sha256"])):
                raise ValueError()
        except Exception:
            pending+=1
            continue
        accepted.append({
            "contract":"personal_cfo_p6d_offline_pdf_observation_v1",
            "source_name":rec["name"],
            "source_hmac":_index("file",item.id),
            "source_content_hmac":blob.content_hmac,
            "statement_start":rec["period_start"],
            "statement_end":rec["period_end"],
            "opening_minor":rec["opening_minor"],
            "closing_minor":rec["closing_minor"],
            "gross_bank_debits_minor":rec["debits_minor"],
            "gross_bank_credits_minor":rec["credits_minor"],
            "transaction_count":rec["transaction_count"],
            "page_count":rec["page_count"],
            "source_sha256_verified":True,
            "offline_reconciliation_attested":True,
            "automatic_pdf_parsing_performed":False,
            "isolation_runtime_accepted":False,
            "historical_only":True,
            "current_available_balance_minor":None,
            "personal_income_minor":None,
            "personal_expenses_minor":None,
            "owner_review_required":True,
        })
    return {
        "contract":"personal_cfo_p6d_offline_pdf_overview_v1",
        "reports":accepted,
        "sources_configured":len(receipts),
        "sources_requiring_review":pending,
        "all_account_coverage_verified":False,
        "current_available_balance_minor":None,
        "personal_income_minor":None,
        "personal_expenses_minor":None,
    }
