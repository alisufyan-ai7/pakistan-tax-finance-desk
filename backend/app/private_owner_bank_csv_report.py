"""P6: real, readonly, single-owner bank CSV evidence from pinned Google Drive.

No bank identities, raw CSV contents, credentials or account numbers are
logged or persisted. Optional P7 rows contain masked owner-only descriptions
through existing MFA/private no-store JSON, never public logs or GitHub.
A bank movement is NOT automatically personal income or spending.
"""
from __future__ import annotations

from collections.abc import Callable
import os
import re
from sqlalchemy.orm import Session

from .drive_inbox_planner import _index, _version
from .document_preflight import MAX_UPLOAD_BYTES
from .private_content_grant_custody import read_private_content_grant, store_private_content_grant
from .private_drive_google_http import _http_google, _guard_network
from .private_google_content_consent import GOOGLE_CONTENT_READ_SCOPE, refresh_google_content_token
from .private_original_source_preflight import _inventory
from .private_owner_google_media_read import read_pinned_google_source_once, _bounded_google_media
from .private_bank_csv_reconciler import reconcile_private_bank_csv, PrivateBankCsvBlocked
from .private_bank_csv_transaction_classifier import classify_reconciled_private_bank_csv
from .private_owner_bank_csv_transaction_rows import project_reconciled_bank_csv_transactions
from .private_offline_bank_pdf_receipts import (verify_pinned_offline_receipts, PrivateOfflineBahlBlocked)

_OWNER = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_MAX_SOURCE_CSV = 10


class PrivateBankCsvReportBlocked(ValueError):
    """Source-backed monthly historical account observation unavailable."""


def _guard(owner: str):
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or type(owner) is not str or _OWNER.fullmatch(owner) is None
        or owner != os.getenv("P1W_OWNER_REF")
        or any(os.getenv(key) != "1" for key in (
            "P6A_OWNER_BANK_CSV_RUNTIME",
            "P6A_G3_BANK_CSV_RECONCILIATION_ACCEPTED",
            "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
            "P3A_G3_RESTRICTED_SCOPE_REVIEWED",
            "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
        ))):
        raise PrivateBankCsvReportBlocked("Private bank CSV report not enabled")


def get_private_bank_csv_overview(
    *, session_factory: Callable[[], Session], owner_ref: str,
    transport: Callable = _http_google,
    media_transport: Callable = _bounded_google_media,
) -> dict:
    """Independently list approved folder, pin whole CSV bytes and reconcile each.

    No user-selected file ID, arbitrary external file URL, or filename enters
    the API request. A bank CSV is never sufficient to assert all-account
    coverage or personal spending. Other source formats need independent review.
    """
    _guard(owner_ref)
    if not all(callable(x) for x in (session_factory, transport, media_transport)):
        raise PrivateBankCsvReportBlocked("Private bank CSV report transport invalid")
    try:
        cfg = _guard_network()
        with session_factory() as db:
            refresh = read_private_content_grant(
                db, owner_ref=owner_ref, folder_id=cfg.folder_id, client_id=cfg.client_id)
        access, rotated = refresh_google_content_token(
            refresh_token=refresh, config=cfg, transport=transport)
        if rotated and rotated != refresh:
            with session_factory() as db:
                store_private_content_grant(
                    db, owner_ref=owner_ref, folder_id=cfg.folder_id,
                    client_id=cfg.client_id, refresh_token=rotated,
                    verified_granted_scope=GOOGLE_CONTENT_READ_SCOPE)
        files = _inventory(access, config=cfg, transport=transport)
        csvs = [item for item in files if item.name.casefold().endswith(".csv")]
        if len(csvs) > _MAX_SOURCE_CSV:
            raise ValueError()
        reports = []
        needs_review_count = 0
        for item in csvs:
            if (item.trashed or item.parent_ids != (cfg.folder_id,)
                or item.mime_type not in ("text/csv", "application/csv", "application/vnd.ms-excel")
                or item.size_bytes is None
                or not 1 <= item.size_bytes <= MAX_UPLOAD_BYTES):
                needs_review_count += 1
                continue
            try:
                blob = read_pinned_google_source_once(
                    file_id=item.id,
                    expected_file_hmac=_index("file", item.id),
                    expected_revision_hmac=_version(item),
                    expected_name_hmac=_index("filename", item.name),
                    access_token=access, granted_scope=GOOGLE_CONTENT_READ_SCOPE,
                    metadata_transport=transport, media_transport=media_transport)
                if blob.extension != ".csv":
                    raise ValueError()
                parsed = reconcile_private_bank_csv(blob.data)
                classification = classify_reconciled_private_bank_csv(blob.data, report=parsed)
                transactions = None
                if os.getenv("P7_OWNER_TRANSACTION_ROWS_ENABLED") == "1":
                    # This owner-only projection never changes the already
                    # accepted statement summary. 600+ lines need reviewed
                    # pagination, not silently truncated or guessed.
                    try:
                        transactions = project_reconciled_bank_csv_transactions(
                            blob.data,report=parsed,
                            source_hmac=_index("file",item.id),hmac_index=_index)
                    except PrivateBankCsvBlocked:
                        transactions = None
            except (PrivateBankCsvBlocked, ValueError, Exception):
                needs_review_count += 1
                continue
            reports.append({
                **parsed,
                "classification":classification,
                "source_hmac": _index("file", item.id),
                "source_content_hmac": blob.content_hmac,
                "source_name": item.name,
                "source_sha256_verified": True,
                "content_retained_on_server": False,
                **({"transactions": transactions} if transactions is not None else {}),
            })
        # P6D is optional, separately attested offline evidence. A stale
        # or invalid PDF receipt NEVER blocks an already reconciled CSV and
        # NEVER causes any PDF parser to run in the Railway API container.
        offline_pdf = {
            "contract":"personal_cfo_p6d_offline_pdf_overview_v1",
            "reports":[], "sources_configured":0, "sources_requiring_review":0,
            "all_account_coverage_verified":False,
            "current_available_balance_minor":None,
            "personal_income_minor":None, "personal_expenses_minor":None,
        }
        try:
            offline_pdf=verify_pinned_offline_receipts(
                files=files,folder_id=cfg.folder_id,access_token=access,
                metadata_transport=transport,media_transport=media_transport)
        except PrivateOfflineBahlBlocked:
            pass
        return {
            "contract": "personal_cfo_owner_bank_csv_overview_v1",
            "offline_pdf":offline_pdf,
            "reports": reports,
            "csv_sources_found": len(csvs),
            "csv_sources_requiring_review": needs_review_count,
            "source_inventory_complete": True,
            "approved_source_folder": True,
            "originals_modified": False,
            "content_retained_on_server": False,
            "historical_only": True,
            "all_account_coverage_verified": False,
            "personal_income_minor": None,
            "personal_expenses_minor": None,
            "current_available_balance_minor": None,
        }
    except PrivateBankCsvReportBlocked:
        raise
    except Exception:
        raise PrivateBankCsvReportBlocked(
            "Verified original bank CSV evidence requires private review") from None
