"""P2C: safe synthetic-only bank statement evidence bridge from actual BYTES.

Independent building block for future approved private Drive read+encrypted
ledger: raw file SHA-256, strict CSV/XLSX preflight, exact Decimal paisa,
opening/running balance validation, provenance counts. Unmounted; no real
Google scopes, owner/source downloads, financial SQL changes or public API.

G1/G3 real financial authority remains disallowed. This never infers a bank,
account, tax classification, investment return or complete source coverage
from a filename or from this isolated one-file candidate.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import os

from .document_preflight import MAX_UPLOAD_BYTES
from .drive_inbox_planner import _index, DriveInboxBlocked
from .importer import ImportErrorDetail, parse_statement


class PrivateStatementPreflightBlocked(ValueError):
    """Source candidate cannot safely be analyzed or promoted."""


def assess_synthetic_source_bytes(
    *, content: bytes, extension: str, date_format: str,
    opening_balance: str | None, approved_synthetic_fixture: bool,
) -> dict:
    """Validate a bounded fake statement and return evidence, never import.

    Independent source SHA-256 = digest of exact raw bytes before parsing;
    Google MD5/provider modifiedTime never substitutes for this digest.
    The digest and blinded index are for a future private encrypted store,
    NOT a client financial-status endpoint.
    """
    if (
        os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or approved_synthetic_fixture is not True
        or type(content) is not bytes or not content
        or len(content) > MAX_UPLOAD_BYTES
        or extension not in (".csv", ".xlsx")
        or date_format not in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y")
        or (opening_balance is not None and (
            type(opening_balance) is not str or len(opening_balance) > 60
        ))
    ):
        raise PrivateStatementPreflightBlocked(
            "Unsupported or unauthorized source evidence"
        )
    try:
        byte_digest = sha256(content).hexdigest()
        blind_digest = _index("source-sha256", byte_digest)
        rows, status, warnings = parse_statement(
            content, extension, date_format, opening_balance
        )
        if not rows or len(rows) > 5000:
            raise ValueError()
        amounts_accepted = status == "opening_and_running_verified"
        # An internal calculation candidate, never a verified actual account.
        # Missing opening balance => amounts remain UNKNOWN, not zero.
        total_in_minor = sum(row.credit_minor for row in rows) if amounts_accepted else None
        total_out_minor = sum(row.debit_minor for row in rows) if amounts_accepted else None
        last_balance_minor = (
            rows[-1].balance_minor if amounts_accepted else None
        )
        return {
            "contract": "personal_cfo_synthetic_statement_evidence_v1",
            "synthetic_only": True,
            "file_sha256": byte_digest,
            "source_sha256_hmac": blind_digest,
            "byte_count": len(content),
            "format": extension[1:],
            "parser_contract": "strict_normalized_tabular_v1",
            "source_row_count": len(rows),
            "period_start": min(row.posted_on for row in rows).isoformat(),
            "period_end": max(row.posted_on for row in rows).isoformat(),
            "balance_check": status,
            "opening_balance_verified": amounts_accepted,
            "synthetic_candidate_credit_minor": total_in_minor,
            "synthetic_candidate_debit_minor": total_out_minor,
            "synthetic_candidate_closing_minor": last_balance_minor,
            "warnings_count": len(warnings),
            "cross_document_overlap_reconciled": False,
            "bank_or_owner_identity_verified": False,
            "financial_ledger_mutated": False,
            "source_original_modified": False,
            "content_hash_from_actual_bytes": True,
            "google_drive_content_access_enabled": False,
            "real_financial_data_enabled": False,
        }
    except (ImportErrorDetail, ValueError, DriveInboxBlocked, OverflowError):
        # No original lines, descriptions, account number, bank name,
        # parsing error or source content reaches caller/error logs.
        raise PrivateStatementPreflightBlocked(
            "Statement evidence requires isolated format review"
        ) from None
