"""A6 synthetic confidential bank -> separate canonical journal acceptance.

Checks immutable encrypted bank batch and running-balance continuity before any
journal posting. Offset leg is UNCLASSIFIED clearing, never an income/expense/tax
claim. Atomic batch commit makes a conflicting row fail without partial writes.
Not connected to the old M1 summary, production importer or Railway preview.
"""
from __future__ import annotations

import os
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from .confidential_bank import (
    ConfidentialBankInput, ConfidentialBankBatch,
    require_confidential_bank_store, _blind as bank_index, _verified_payload,
)
from .canonical_journal import (
    CanonicalJournalBlocked, JournalEvent, JournalLeg,
    _blind as journal_index, record_synthetic_journal_batch,
)

CLEARING = "SYNTHETIC-UNCLASSIFIED-COUNTERENTRY"


def _events(source: ConfidentialBankInput) -> tuple[JournalEvent, ...]:
    """Transform already balance-reconciled fictional source into neutral postings."""
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise CanonicalJournalBlocked("Real bank posting prohibited")
    if not isinstance(source, ConfidentialBankInput):
        raise CanonicalJournalBlocked("Validated synthetic bank source required")
    # Revalidate model, including exact opening/running/closing balances, even
    # when a caller has constructed a mutable nested fixture.
    try:
        verified = ConfidentialBankInput.model_validate(source.model_dump(mode="json"))
    except Exception:
        raise CanonicalJournalBlocked("Unsupported synthetic bank source") from None
    result = []
    for row in verified.rows:
        movement = row.credit_minor - row.debit_minor
        if movement == 0:
            raise CanonicalJournalBlocked("Empty source movement")
        # Purpose-separated keyed identity, not an unkeyed digest of private
        # source IDs, descriptions or dates.
        row_ref = "BANKROW-" + journal_index("source",
            f"{verified.legal_owner}:{verified.source_ref}:{row.row_number}")[:48]
        result.append(JournalEvent(
            synthetic_fixture=True, legal_owner=verified.legal_owner,
            currency=verified.currency, posted_on=row.posted_on,
            source_ref=row_ref, primary_account_ref=verified.account_ref,
            event_kind="bank_observation_unclassified",
            legs=(
                JournalLeg(account_kind="bank", account_ref=verified.account_ref,
                           signed_minor=movement),
                JournalLeg(account_kind="transfer_clearing", account_ref=CLEARING,
                           signed_minor=-movement),
            ),
        ))
    return tuple(result)


def accept_recorded_synthetic_bank(db: Session, *, source_ref: str) -> dict:
    """Create all neutral journal rows only from an existing sealed bank batch."""
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or not isinstance(source_ref, str)
        or not re.fullmatch(r"[A-Za-z0-9_.:/-]{8,80}", source_ref)):
        raise CanonicalJournalBlocked("Unverified synthetic bank source selector")
    try:
        require_confidential_bank_store(db)
        source_hmac = bank_index("source", "individual:" + source_ref)
        sealed_source = db.scalar(select(ConfidentialBankBatch).where(
            ConfidentialBankBatch.source_hmac == source_hmac))
        if sealed_source is None:
            raise CanonicalJournalBlocked("Unregistered confidential bank source")
        source = _verified_payload(sealed_source)
        if source.legal_owner != "individual" or source.source_ref != source_ref:
            raise CanonicalJournalBlocked("Cross-owner synthetic bank source mismatch")
        events = _events(source)
        receipt = record_synthetic_journal_batch(db, events)
    except CanonicalJournalBlocked:
        raise
    except Exception:
        raise CanonicalJournalBlocked("Confidential source-to-journal acceptance failed") from None
    return {
        **receipt,
        "bank_running_balances_reconciled_in_fixture": True,
        "non_earnings_classification": "UNCLASSIFIED_CLEARING",
        "owner_source_certified": False,
        "actual_income_or_tax_minor": None,
        "bank_opening_closing_balances_certified": False,
    }
