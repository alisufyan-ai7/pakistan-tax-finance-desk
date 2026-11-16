"""G3 private-adapter release boundary: declarations cannot certify owner originals.

The actual private approval package, secure document vault, vetted image, and
genuine bank/FBR sample provenance do not exist in public CI. This module
makes private approval requirements explicit and remains blocked regardless
of caller-supplied positive checkboxes. Only synthetic manifest metadata.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .private_adapter_registry import _BY_KEY, genuine_format_candidate_manifest


class PrivateFormatCertificationBlocked(ValueError):
    """Cannot elevate public fixture parsing into real bank/FBR certification."""


_RELEASE_CONTROLS = (
    "owner_approved_private_intake_and_environment",
    "independent_isolated_worker_attestation",
    "pinned_vulnerability_reviewed_worker_image",
    "malware_scan_and_file_type_quarantine",
    "immutable_aes_gcm_original_vault_and_independent_restore",
    "private_sample_owner_account_tax_year_provenance",
    "layout_version_and_negative_golden_test_set",
    "page_row_provenance_and_completeness",
    "duplicate_overlap_and_reversal_reconciliation",
    "two_person_sample_review_with_filing_provenance",
    "private_mfa_session_and_least_privilege_data_access",
    "independent_owner_authorized_release",
)


def inspect_private_format_release_gap(
    *, candidate_key: str, declared_controls: tuple[str, ...] = (),
) -> dict:
    """Return a redacted gap list, never a genuine-format certificate.

    A self-declared completed control cannot establish external independence:
    even if all supplied, proof and owner authorization remain unavailable.
    No uploaded bytes, account numbers, filenames or tax results are accepted.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise PrivateFormatCertificationBlocked("Real-format intake is not authorized")
    if not isinstance(candidate_key, str) or candidate_key not in _BY_KEY:
        raise PrivateFormatCertificationBlocked("Unknown bank/IRIS candidate profile")
    if (type(declared_controls) is not tuple
        or len(declared_controls) > len(_RELEASE_CONTROLS)
        or any(type(item) is not str for item in declared_controls)
        or len(set(declared_controls)) != len(declared_controls)
        or not set(declared_controls) <= set(_RELEASE_CONTROLS)):
        raise PrivateFormatCertificationBlocked("Unreviewed acceptance claim rejected")
    missing = tuple(item for item in _RELEASE_CONTROLS if item not in declared_controls)
    profile = _BY_KEY[candidate_key]
    return {
        "synthetic_only": True,
        "candidate_key": profile.key,
        "document_kind": profile.kind,
        "self_declared_control_count": len(declared_controls),
        "missing_private_controls": missing,
        "public_fixture_parser_certified_for_real_sources": False,
        "private_environment_independently_verified": False,
        "genuine_bank_or_fbr_sources_certified": False,
        "owner_source_data_imported": False,
        "real_data_mode_enabled": False,
        "release_blocked": True,
    }


def refuse_genuine_format_release(*_args, **_kwargs) -> None:
    """This public application cannot create a genuine-source certification."""
    raise PrivateFormatCertificationBlocked(
        "Real bank/FBR format certification requires independent owner-approved "
        "private isolation, encrypted originals, accepted samples and reviewer proof"
    )
