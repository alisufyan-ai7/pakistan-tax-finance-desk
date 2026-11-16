"""G3 genuine-format acceptance registry: requirements, NOT real document parsing.

Public repo can declare explicit candidate layout obligations without
recording source account numbers, tax identifiers, real bank statement
examples, credentials, original file bytes, or claiming certified support.

Every proposed Pakistani bank/FBR layout is quarantined until independent
PRIVATE samples and production-grade parser security are accepted. A caller
cannot self-certify a real adapter by passing arbitrary booleans.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Literal


class GenuineFormatBlocked(ValueError):
    """No private owner evidence or genuine-format release approval."""


@dataclass(frozen=True)
class CandidateLayout:
    key: str
    kind: Literal["bank_statement", "iris_income_return", "iris_wealth_statement"]
    extensions: tuple[str, ...]
    required_private_evidence: tuple[str, ...]
    real_source_certified: Literal[False] = False


_COMMON = (
    "os_network_filesystem_isolation_attested",
    "encrypted_immutable_original_vault_verified",
    "source_page_row_traceability_verified",
    "bounded_size_and_malware_checks",
    "authorized_owner_private_sample_acceptance",
)
BANK = CandidateLayout(
    key="pk_bank_structured_candidate_v0", kind="bank_statement",
    extensions=(".csv", ".xlsx", ".pdf"),
    required_private_evidence=_COMMON + (
        "bank_layout_version_and_account_verified",
        "opening_running_closing_balances_exact",
        "debit_credit_direction_and_reversals_verified",
        "duplicate_overlap_and_transfer_dedup_verified",
        "statement_calendar_coverage_verified",
    ),
)
IRIS_INCOME = CandidateLayout(
    key="pk_iris_income_candidate_v0", kind="iris_income_return",
    extensions=(".pdf",),
    required_private_evidence=_COMMON + (
        "tax_year_and_legal_owner_verified",
        "filed_or_draft_provenance_reviewed",
        "official_fbr_acknowledgment_independently_verified",
        "withholding_income_schedule_links_reviewed",
    ),
)
IRIS_WEALTH = CandidateLayout(
    key="pk_iris_wealth_candidate_v0", kind="iris_wealth_statement",
    extensions=(".pdf",),
    required_private_evidence=_COMMON + (
        "tax_year_and_legal_owner_verified",
        "filed_or_draft_provenance_reviewed",
        "official_fbr_acknowledgment_independently_verified",
        "assets_liabilities_cash_and_wealth_rollforward_verified",
    ),
)
_BY_KEY = {v.key: v for v in (BANK, IRIS_INCOME, IRIS_WEALTH)}
assert len(_BY_KEY) == 3 and all(not x.real_source_certified for x in _BY_KEY.values())


def genuine_format_candidate_manifest() -> dict:
    """Static privacy-safe public roadmap. Not proof of accepted bank formats."""
    return {
        "candidate_only": True,
        "genuine_owner_document_ingestion_enabled": False,
        "certified_real_adapters": 0,
        "candidate_layouts": [
            {"key": v.key, "kind": v.kind, "extensions": v.extensions,
             "real_source_certified": False,
             "required_private_evidence": v.required_private_evidence}
            for v in _BY_KEY.values()
        ],
    }


def inspect_candidate_evidence(
    *, key: str, kind: str, extension: str,
    synthetic_fixture: bool, declared_steps: tuple[str, ...] = (),
) -> dict:
    """Inspect asserted milestone names only, never source bytes or PII.

    Even complete public declaration is NOT independent certificate. Only
    private offline review can later produce a separately signed acceptance.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic" or synthetic_fixture is not True:
        raise GenuineFormatBlocked("Real source parsing not authorized")
    if not isinstance(key, str) or key not in _BY_KEY:
        raise GenuineFormatBlocked("Unknown genuine-layout candidate")
    profile = _BY_KEY[key]
    if kind != profile.kind or extension not in profile.extensions:
        raise GenuineFormatBlocked("Declared real-source format profile mismatch")
    if (not isinstance(declared_steps, tuple) or
        not all(isinstance(v, str) for v in declared_steps) or
        len(set(declared_steps)) != len(declared_steps) or
        not set(declared_steps) <= set(profile.required_private_evidence)):
        raise GenuineFormatBlocked("Unreviewed private acceptance steps")
    unmet = [v for v in profile.required_private_evidence if v not in declared_steps]
    return {
        "candidate_only": True,
        "candidate_key": profile.key,
        "document_kind": profile.kind,
        "format": extension,
        "declared_step_count": len(declared_steps),
        "missing_private_acceptance_steps": unmet,
        "private_evidence_independently_verified": False,
        "certified_real_adapter": False,
        "genuine_source_bytes_processed": False,
        "actual_bank_or_fbr_data_imported": False,
        "real_data_authorized": False,
    }
