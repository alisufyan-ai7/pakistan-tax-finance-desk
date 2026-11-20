"""P6 owner-only property investment cost/profit evidence from pinned Drive XLSX.

Never runs spreadsheet macros, formulas or external workbook links; only bounded
OOXML source values and arithmetic. Results are registered cost and realized
sale profit, never inferred market values, cash proceeds or taxable gains.
"""
from __future__ import annotations

from collections.abc import Callable
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
from .private_property_inventory_reconciler import reconcile_property_inventory_xlsx,PrivatePropertyRegisterBlocked
from .private_investment_relationships import private_investment_relationships
from .private_bank_csv_reconciler import reconcile_private_bank_csv,PrivateBankCsvBlocked
from .private_investment_bank_csv_matcher import (
    PrivateBankInvestmentMatchBlocked,private_investment_bank_match_config,
    match_reconciled_bank_csv_candidates,_empty,
)

_OWNER=re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class PrivatePropertyInventoryReportBlocked(ValueError):
    """Private investment source unavailable or invalid."""


def _guard(owner):
    if (os.getenv("APP_DATA_MODE")!="synthetic"
        or type(owner) is not str or _OWNER.fullmatch(owner) is None
        or owner!=os.getenv("P1W_OWNER_REF")
        or any(os.getenv(k)!="1" for k in (
            "P6B_OWNER_INVESTMENT_RUNTIME",
            "P6B_G3_PROPERTY_REGISTER_RECONCILIATION_ACCEPTED",
            "P3A_PRIVATE_SOURCE_MEDIA_ENABLED",
            "P3A_G3_RESTRICTED_SCOPE_REVIEWED",
            "P3A_OWNER_CONTENT_CONSENT_ACCEPTED",
        ))):
        raise PrivatePropertyInventoryReportBlocked("Private property source disabled")


def get_private_property_inventory_overview(
    *, session_factory:Callable[[],Session], owner_ref:str,
    transport:Callable=_http_google, media_transport:Callable=_bounded_google_media,
)->dict:
    _guard(owner_ref)
    if not all(callable(x) for x in (session_factory,transport,media_transport)):
        raise PrivatePropertyInventoryReportBlocked("Private investment transport unavailable")
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
        choices=[f for f in files if f.name.casefold().endswith(".xlsx")]
        if len(choices)>10:raise ValueError()
        accepted=[]
        for item in choices:
            if (item.trashed or item.parent_ids!=(cfg.folder_id,)
                or item.mime_type!="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                or item.size_bytes is None or not 1<=item.size_bytes<=MAX_UPLOAD_BYTES):
                continue
            try:
                blob=read_pinned_google_source_once(
                    file_id=item.id,expected_file_hmac=_index("file",item.id),
                    expected_revision_hmac=_version(item),
                    expected_name_hmac=_index("filename",item.name),
                    access_token=access,granted_scope=GOOGLE_CONTENT_READ_SCOPE,
                    metadata_transport=transport,media_transport=media_transport)
                if blob.extension!=".xlsx":raise ValueError()
                result=reconcile_property_inventory_xlsx(blob.data)
                accepted.append({**result,
                    "source_hmac":_index("file",item.id),
                    "source_content_hmac":blob.content_hmac,
                    "source_sha256_verified":True,
                    "content_retained_on_server":False})
            except (PrivatePropertyRegisterBlocked,ValueError):
                continue
        # Same approved source inventory and one-owner OAuth grant. The CSV
        # must independently pass EVERY running balance before any candidate
        # payment may be shown. PDF bytes are never accessed on this path.
        registry=private_investment_relationships(property_verified=bool(accepted))
        mapping=private_investment_bank_match_config(groups=registry["groups"])
        candidates=_empty()
        if mapping:
            possible_csv=[f for f in files if f.name.casefold().endswith(".csv")]
            # With multiple overlapping statements, account-level deduplication
            # is not proven. Do not sum potentially duplicated sources.
            if len(possible_csv)==1:
                item=possible_csv[0]
                if (not item.trashed and item.parent_ids==(cfg.folder_id,)
                    and item.mime_type in ("text/csv","application/csv",
                                            "application/vnd.ms-excel")
                    and item.size_bytes is not None
                    and 1<=item.size_bytes<=MAX_UPLOAD_BYTES):
                    try:
                        csvblob=read_pinned_google_source_once(
                            file_id=item.id,
                            expected_file_hmac=_index("file",item.id),
                            expected_revision_hmac=_version(item),
                            expected_name_hmac=_index("filename",item.name),
                            access_token=access,granted_scope=GOOGLE_CONTENT_READ_SCOPE,
                            metadata_transport=transport,
                            media_transport=media_transport)
                        if csvblob.extension!=".csv":
                            raise ValueError()
                        proof=reconcile_private_bank_csv(csvblob.data)
                        candidates=match_reconciled_bank_csv_candidates(
                            csvblob.data,report=proof,
                            source_hmac=_index("file",item.id),
                            matching=mapping,hmac_index=_index)
                    except (ValueError,PrivateBankCsvBlocked,
                            PrivateBankInvestmentMatchBlocked):
                        pass
        # Do not aggregate unrelated or duplicated property registers.
        if len(accepted)>1:raise ValueError()
        return {
            "contract":"personal_cfo_owner_property_inventory_overview_v1",
            "reports":accepted,
            "owner_relationships":registry,
            "candidate_bank_movements":candidates,
            "property_register_sources_verified":len(accepted),
            "xlsx_sources_examined":len(choices),
            "approved_source_folder":True,"inventory_complete":True,
            "originals_modified":False,"content_retained_on_server":False,
            "current_market_values_verified":False,"owner_review_required":True,
        }
    except PrivatePropertyInventoryReportBlocked:
        raise
    except Exception:
        raise PrivatePropertyInventoryReportBlocked(
            "Owner property investment report requires source review") from None
