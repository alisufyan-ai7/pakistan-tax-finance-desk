"""P3B: provenance-aware statement candidate review (synthetic fixtures ONLY).

Composes existing bounded CSV/XLSX signature preflight, normalization and exact
integer minor-unit reconciliation, while keeping source account/period evidence
independent from filename and first/last transaction dates.

This does NOT certify a genuine bank layout, classify transfers/income,
authorize owner source bytes, write financial rows or infer completed months.
The private isolated parser must later supply independently verified account,
calendar period and approved profile before any real finance release.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from hashlib import sha256
import os
import re

from .bank_profiles import normalize_synthetic_csv
from .document_preflight import MAX_UPLOAD_BYTES, PreflightError, preflight_tabular
from .drive_inbox_planner import _index
from .importer import ImportErrorDetail, parse_statement

_HEX = re.compile(r"^[0-9a-f]{64}$")
_PROFILE = ("normalized", "synthetic_split", "synthetic_direction")
_DATE = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y")


class StatementCandidateReviewBlocked(ValueError):
    """Source cannot safely enter the statement-review pipeline."""


def _date(value: str) -> date:
    if type(value) is not str or len(value) != 10:
        raise ValueError()
    dt = date.fromisoformat(value)
    if not date(2022, 7, 1) <= dt <= date(2100, 6, 30):
        raise ValueError()
    return dt


def review_synthetic_statement_candidate(
    *, original_bytes: bytes, extension: str, layout: str,
    date_format: str, opening_balance: str | None,
    account_ref_hmac: str | None,
    declared_period: tuple[str, str] | None,
    independent_account_verified: bool,
    independent_period_verified: bool,
    approved_synthetic_fixture: bool,
) -> dict:
    """Analyze one file without treating bank movements as taxable facts.

    A genuine import should require an independently verified original
    file SHA-256, bank/account identity, format-version golden tests and PDF
    sandbox. This synthetic contract cannot grant that release by passing
    positive booleans.
    """
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or approved_synthetic_fixture is not True
        or type(original_bytes) is not bytes
        or not 0 < len(original_bytes) <= MAX_UPLOAD_BYTES
        or extension not in (".csv", ".xlsx")
        or layout not in _PROFILE
        or date_format not in _DATE
        or type(independent_account_verified) is not bool
        or type(independent_period_verified) is not bool
        or (opening_balance is not None
            and (type(opening_balance) is not str or len(opening_balance) > 60))):
        raise StatementCandidateReviewBlocked(
            "Approved bounded synthetic statement and parsing profile required"
        )
    try:
        # Reject malformed container, active spreadsheet parts and fake HTML
        # before CSV normalization; import parser revalidates normalized bytes.
        preflight_tabular(original_bytes, extension)
        if extension == ".xlsx" and layout != "normalized":
            raise ValueError()
        normalized, explicit_date = normalize_synthetic_csv(
            original_bytes, layout, extension,
        )
        if explicit_date is not None and date_format != explicit_date:
            raise ValueError()
        rows, status, warnings = parse_statement(
            normalized, extension, date_format, opening_balance,
        )
        if not 1 <= len(rows) <= 5000:
            raise ValueError()
        digest = sha256(original_bytes).hexdigest()
        hmac_digest = _index("source-sha256", digest)
        # A transaction date span NEVER proves bank statement calendar span.
        first,last=min(x.posted_on for x in rows),max(x.posted_on for x in rows)
        period=None
        if declared_period is not None:
            if type(declared_period) is not tuple or len(declared_period)!=2:
                raise ValueError()
            period=(_date(declared_period[0]),_date(declared_period[1]))
            if (period[0]>period[1] or (period[1]-period[0]).days>366
                or first<period[0] or last>period[1]):
                raise ValueError()
        if (type(account_ref_hmac) is not str
            or _HEX.fullmatch(account_ref_hmac) is None):
            # No file filename -> bank/account identity guess allowed.
            independent_account_verified=False
            account_ref_hmac=None
        if period is None:
            independent_period_verified=False
        # Independent account/period assertions are an additional input, NOT
        # independently trusted data. Never claim real-format certification.
        fully_checked = (
            status == "opening_and_running_verified"
            and independent_account_verified
            and independent_period_verified
            and period is not None
        )
        # These are GROSS synthetic bank movements, not income or spending.
        credits=sum(x.credit_minor for x in rows) if fully_checked else None
        debits=sum(x.debit_minor for x in rows) if fully_checked else None
        closing=rows[-1].balance_minor if fully_checked else None
        refs=[x.reference.casefold() for x in rows if x.reference]
        repeated_refs=sum(v-1 for v in Counter(refs).values() if v>1)
        flags=[]
        if not independent_account_verified:
            flags.append("ACCOUNT_IDENTITY_NOT_INDEPENDENTLY_VERIFIED")
        if not independent_period_verified:
            flags.append("STATEMENT_PERIOD_NOT_INDEPENDENTLY_VERIFIED")
        if status != "opening_and_running_verified":
            flags.append("OPENING_OR_RUNNING_BALANCE_UNVERIFIED")
        if repeated_refs:
            flags.append("REPEATED_TRANSACTION_REFERENCES_REQUIRE_REVIEW")
        if not fully_checked:
            flags.append("BANK_MOVEMENTS_WITHHELD_PENDING_EVIDENCE")
        return {
            "contract":"personal_cfo_synthetic_statement_review_v1",
            "synthetic_only":True,
            "content_sha256_hmac":hmac_digest,
            "content_sha256_independently_from_bytes":True,
            "file_format":extension[1:],
            "layout_candidate":layout,
            "profile_certified_for_real_bank":False,
            "source_row_count":len(rows),
            "observed_first_transaction":first.isoformat(),
            "observed_last_transaction":last.isoformat(),
            "declared_statement_start":period[0].isoformat() if period else None,
            "declared_statement_end":period[1].isoformat() if period else None,
            "account_ref_hmac":account_ref_hmac,
            "balance_check":status,
            "independent_owner_account_evidence_declared":independent_account_verified,
            "independent_period_evidence_declared":independent_period_verified,
            "synthetic_candidate_bank_credits_minor":credits,
            "synthetic_candidate_bank_debits_minor":debits,
            "synthetic_candidate_closing_minor":closing,
            "warnings_count":len(warnings),
            "repeated_reference_candidates":repeated_refs,
            "review_flags":flags,
            "source_status":"SYNTHETIC_REVIEW_CANDIDATE"
                if fully_checked else "EVIDENCE_INCOMPLETE",
            "account_month_completeness_proven":False,
            "cross_statement_overlap_reconciled":False,
            "own_transfers_classified":False,
            "actual_income_minor":None,
            "actual_expense_minor":None,
            "real_financial_data_enabled":False,
            "originals_modified":False,
            "ledger_mutated":False,
        }
    except (PreflightError, ImportErrorDetail, ValueError, OverflowError):
        raise StatementCandidateReviewBlocked(
            "Statement source requires isolated parsing and provenance review"
        ) from None
