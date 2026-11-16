"""G1 A8: fail-closed reversible cutover readiness matrix, NEVER a migrator.

This is a safety gate for OFFLINE synthetic rehearsal reports. No SQL DDL,
roles/keys/backup deletion, real owner records, runtime authority toggle or
plaintext retirement occurs here, even if all purported evidence is positive.

A 'pass' claimed by a caller is not independent attestation. Genuine release
requires checked offsite restore, G2/G3 acceptance and owner-scoped permission.
"""
from __future__ import annotations

import os
from typing import Any


class CutoverBlocked(ValueError):
    """Unsafe or unapproved authoritative ledger cutover attempt."""


REQUIRED = (
    "original_source_complete",
    "encrypted_canonical_source_parity",
    "no_double_counted_movements",
    "full_cash_loan_investment_asset_tax_year_parity",
    "approved_owner_fbr_claim_mapping",
    "encrypted_backup_independent_restore",
    "offsite_recovery_drill",
    "ledger_and_index_key_rotation_rehearsal",
    "restricted_runtime_database_roles",
    "audited_owner_mfa_recovery",
    "protected_original_document_vault",
    "versioned_real_format_acceptance",
    "rollback_replay_and_failure_injection",
    "legacy_plaintext_retirement_rehearsal",
    "privacy_review_and_owner_authorization",
)


def inspect_synthetic_cutover_readiness(
    *, source_report: dict[str, Any], graph_report: dict[str, Any],
    backup_report: dict[str, Any], restore_report: dict[str, Any],
    independent_acceptance: dict[str, bool] | None = None,
) -> dict:
    """No write side. Never switches authority, not even with all 'True' flags.

    Strict trusted receipt shapes still cannot establish genuine release: the
    independently authorized owner cutover mechanism is intentionally absent.
    """
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise CutoverBlocked("Real mode cannot perform a synthetic cutover")
    if any(type(x) is not dict for x in (
        source_report, graph_report, backup_report, restore_report
    )):
        raise CutoverBlocked("Required independently generated rehearsal receipts missing")
    if not (
        source_report.get("read_only") is True
        and source_report.get("source_graph_consistent") is True
        and source_report.get("migration_performed") is False
        and isinstance(source_report.get("source_integrity_hmac"), str)
        and len(source_report["source_integrity_hmac"]) == 64
        and graph_report.get("synthetic_only") is True
        and graph_report.get("read_only") is True
        and graph_report.get("cross_domain_movements_double_counted") is False
        and graph_report.get("authority_cutover") is False
        and backup_report.get("encrypted") is True
        and backup_report.get("verified_read_snapshot") is True
        and backup_report.get("source_untouched") is True
        and restore_report.get("independent_target") is True
        and restore_report.get("full_row_parity_verified") is True
        and restore_report.get("source_untouched") is True
    ):
        raise CutoverBlocked("Source backup/independent restore or graph proof incomplete")
    acceptance = independent_acceptance or {}
    if not isinstance(acceptance, dict) or any(
        key not in REQUIRED or type(value) is not bool
        for key, value in acceptance.items()
    ):
        raise CutoverBlocked("Unknown or unverified cutover acceptance fields")
    # The graph currently never attests complete financial source/owner scope.
    # Caller-provided flags cannot override that internal source gap.
    positive = {
        "original_source_complete": True,
        "no_double_counted_movements": True,
        "encrypted_backup_independent_restore": True,
    }
    if graph_report.get("financial_scope_complete") is not True:
        positive["full_cash_loan_investment_asset_tax_year_parity"] = False
    if graph_report.get("fbr_acknowledgment_verified") is not True:
        positive["approved_owner_fbr_claim_mapping"] = False
    missing = tuple(
        name for name in REQUIRED
        if acceptance.get(name) is not True or positive.get(name) is False
    )
    return {
        "synthetic_only": True,
        "read_only": True,
        "cutover_policy_version": "a8_synthetic_preflight_v1",
        "declared_acceptance_count": len(REQUIRED) - len(missing),
        "missing_acceptance": missing,
        "policy_checks_not_external_audits": True,
        "reversible_cutover_rehearsal_certified": False,
        "live_owner_cutover_authorized": False,
        "ledger_authority_switched": False,
        "legacy_plaintext_retired": False,
        "backup_deleted": False,
        "real_data_authorized": False,
        "tax_due_minor": None,
    }


def refuse_authoritative_cutover(*_args, **_kwargs) -> None:
    """No 'dry run' parameter that can accidentally become a destructive switch."""
    raise CutoverBlocked(
        "Authoritative migration/cutover is not implemented or authorized; "
        "independent private evidence, explicit approval and rollback are required"
    )
