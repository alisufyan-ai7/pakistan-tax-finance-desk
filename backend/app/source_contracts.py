"""G3 synthetic-only explicit source adapter capability registry.

Catalogued capabilities are promises about *test fixture parsing*, not certifications
for Pakistani bank exports or real FBR/IRIS filings. No auto-detection of a real
institution, no disk write, no production ingestion.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Literal

from .bank_profiles import PROFILES, normalize_synthetic_csv
from .document_preflight import PreflightError, preflight_tabular
from .synthetic_pdf_adapters import (
    SYNTHETIC_BANK_MARKER, SYNTHETIC_IRIS_MARKER, SyntheticPdfError,
    preview_synthetic_bank, preview_synthetic_fbr,
)


class SourceContractBlocked(ValueError):
    """Source is unsupported or not explicitly synthetic."""


@dataclass(frozen=True)
class AdapterCapability:
    key: str
    revision: int
    kind: Literal["bank_statement", "iris_income_return", "iris_wealth_statement"]
    extension: Literal[".csv", ".pdf"]
    profile: str | None
    requires_explicit_layout: bool = True
    real_source_certified: bool = False


CAPABILITIES: tuple[AdapterCapability, ...] = (
    AdapterCapability("synthetic_normalized_bank_csv_v1", 1, "bank_statement", ".csv", "normalized"),
    AdapterCapability("synthetic_split_bank_csv_v1", 1, "bank_statement", ".csv", "synthetic_split"),
    AdapterCapability("synthetic_direction_bank_csv_v1", 1, "bank_statement", ".csv", "synthetic_direction"),
    AdapterCapability("synthetic_bank_pdf_v1", 1, "bank_statement", ".pdf", None),
    AdapterCapability("synthetic_iris_income_pdf_v1", 1, "iris_income_return", ".pdf", None),
    AdapterCapability("synthetic_iris_wealth_pdf_v1", 1, "iris_wealth_statement", ".pdf", None),
)
_BY_KEY = {item.key: item for item in CAPABILITIES}
assert len(_BY_KEY) == len(CAPABILITIES)
assert all(not item.real_source_certified for item in CAPABILITIES)


def capability_manifest() -> dict:
    """Static non-sensitive contract listing; never inferred from uploaded bytes."""
    return {
        "synthetic_only": True,
        "real_source_certified": False,
        "auto_detect_real_bank": False,
        "supported_layouts": [
            {"key": item.key, "revision": item.revision,
             "kind": item.kind, "extension": item.extension,
             "requires_explicit_layout": item.requires_explicit_layout,
             "real_source_certified": item.real_source_certified}
            for item in CAPABILITIES
        ],
    }


def inspect_synthetic_source(
    raw: bytes, *, adapter_key: str, extension: str, kind: str,
    synthetic_fixture: bool, tax_year: int | None = None,
) -> dict:
    """Explicit preflight/preview only; never persists, infers filed status or tax.

    A caller MUST pin a reviewed adapter contract, kind and format. Unknown
    layouts are rejected, not guessed. PDF preview uses in-process synthetic
    fixture tooling only; an isolated parser remains necessary for real input.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic" or synthetic_fixture is not True:
        raise SourceContractBlocked("Only explicit synthetic input is allowed")
    if not isinstance(adapter_key, str) or adapter_key not in _BY_KEY:
        raise SourceContractBlocked("Unknown or unapproved adapter contract")
    spec = _BY_KEY[adapter_key]
    if extension != spec.extension or kind != spec.kind:
        raise SourceContractBlocked("Declared source kind/extension does not match adapter")
    if tax_year is not None and (type(tax_year) is not int or not 2023 <= tax_year <= 2100):
        raise SourceContractBlocked("Invalid synthetic tax-year request")
    if not isinstance(raw, bytes) or not raw:
        raise SourceContractBlocked("Empty or invalid source bytes")

    try:
        if spec.extension == ".csv":
            preflight_tabular(raw, ".csv")
            if spec.profile not in PROFILES:
                raise SourceContractBlocked("Unreviewed synthetic CSV adapter profile")
            normalized, _ = normalize_synthetic_csv(raw, spec.profile, ".csv")
            # For normalized schema as well: require precisely the pinned header.
            first = normalized.decode("utf-8-sig").splitlines()[0].strip().lower()
            if first != PROFILES["normalized"]:
                raise SourceContractBlocked("Synthetic CSV header does not match pinned adapter")
            result = {"preview_rows": None, "balance_validated": False,
                      "needs_opening_balance": True,
                      "source_marker_verified": False}
        elif spec.kind == "bank_statement":
            preview = preview_synthetic_bank(raw)
            result = {"preview_rows": preview["rows"],
                      "balance_validated": preview["reconciliation"] == "opening_and_running_verified",
                      "needs_opening_balance": False,
                      "source_marker_verified": True}
        else:
            expected = "income_return" if spec.kind == "iris_income_return" else "wealth_statement"
            preview = preview_synthetic_fbr(raw, expected)
            if tax_year is not None and preview["tax_year"] != tax_year:
                raise SourceContractBlocked("Tax-year mismatch in synthetic source")
            result = {"preview_rows": None, "balance_validated": False,
                      "needs_opening_balance": False,
                      "source_marker_verified": True,
                      "claimed_tax_year": preview["tax_year"],
                      "filing_acknowledgement_verified": False}
    except (PreflightError, SyntheticPdfError, UnicodeError, ValueError) as exc:
        if isinstance(exc, SourceContractBlocked):
            raise
        raise SourceContractBlocked("Source does not meet strict synthetic adapter contract") from None

    return {
        "synthetic_only": True,
        "adapter": spec.key,
        "adapter_revision": spec.revision,
        "document_kind": spec.kind,
        "format": spec.extension,
        "import_performed": False,
        "owner_source_data_ingested": False,
        "real_source_certified": False,
        "fbr_ready": False,
        "tax_due_minor": None,
        **result,
    }
