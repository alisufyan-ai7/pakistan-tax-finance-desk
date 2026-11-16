"""G1 source-backed neutral ledger: zero guessed income, atomic batch rollback."""
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa
from app.confidential_bank import ConfidentialBankInput, record_confidential_bank_source
from app.canonical_journal import (
    CanonicalJournalBlocked, JournalEvent,
    record_synthetic_journal, inspect_synthetic_journal,
)
from app.canonical_bank_posting import accept_recorded_synthetic_bank, _events


ACCOUNT = "SYNTHETIC-BANK-ACCOUNT-01"
SOURCE = "SYNTHETIC-RECORDED-STATEMENT-01"


def source():
    return ConfidentialBankInput.model_validate({
        "synthetic_fixture": True, "legal_owner":"individual", "currency":"PKR",
        "account_ref": ACCOUNT, "institution":"SYNTHETIC BANK",
        "source_ref": SOURCE, "period_start":"2025-07-01", "period_end":"2025-07-31",
        "opening_balance_minor": 10000, "closing_balance_minor": 10500,
        "rows":[
            {"row_number":1,"posted_on":"2025-07-02","description":"fictional credit",
             "debit_minor":0,"credit_minor":700,"balance_minor":10700},
            {"row_number":2,"posted_on":"2025-07-03","description":"fictional debit",
             "debit_minor":200,"credit_minor":0,"balance_minor":10500},
        ],
    })


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    engine=create_engine(f"sqlite:///{tmp_path / 'synthetic-canonical-source.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_confidential_source_to_atomic_encrypted_ledger_without_income_claim(engine):
    with Session(engine) as db:
        record_confidential_bank_source(db, source())
        result=accept_recorded_synthetic_bank(db, source_ref=SOURCE)
        assert result["inserted"] == 2
        assert result["source_event_count"] == 2
        assert result["bank_running_balances_reconciled_in_fixture"]
        assert result["non_earnings_classification"] == "UNCLASSIFIED_CLEARING"
        assert result["actual_income_or_tax_minor"] is None
        again=accept_recorded_synthetic_bank(db, source_ref=SOURCE)
        assert again["inserted"] == 0 and again["already_recorded"] == 2
        summary=inspect_synthetic_journal(db,primary_account_ref=ACCOUNT,tax_year=2026)
        assert summary["source_event_count"] == 2 and summary["account_balance_minor"] is None
    with engine.connect() as c:
        raw=[v[0] for v in c.execute(text("SELECT payload_json FROM canonical_journal_entries"))]
        assert len(raw) == 2 and all(v.startswith("TFLE1:") for v in raw)
        for text_value in (SOURCE, ACCOUNT, "10700", "10500", "fictional debit"):
            assert all(text_value not in v for v in raw)
        assert c.execute(text("SELECT COUNT(*) FROM transactions")).scalar_one() == 0


def test_source_not_accepted_until_protected_and_balance_verified(engine):
    with Session(engine) as db:
        with pytest.raises(CanonicalJournalBlocked):
            accept_recorded_synthetic_bank(db,source_ref=SOURCE)
    corrupt=source().model_dump(mode="json")
    corrupt["closing_balance_minor"] += 1
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ConfidentialBankInput.model_validate(corrupt)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM canonical_journal_entries")).scalar_one() == 0


def test_batch_conflict_rolls_back_new_entries(engine):
    with Session(engine) as db:
        record_confidential_bank_source(db,source())
        events=_events(source())
        # Install a conflicting posting for the LAST row; the first row must
        # never persist when the full batch is rejected.
        rival=JournalEvent.model_validate({
            **events[1].model_dump(mode="json"),
            "event_kind":"owner_opening_assertion",
        })
        record_synthetic_journal(db,rival)
        with pytest.raises(CanonicalJournalBlocked,match="Conflicting"):
            accept_recorded_synthetic_bank(db,source_ref=SOURCE)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM canonical_journal_entries")).scalar_one() == 1


def test_real_mode_never_imports_private_statement(engine, monkeypatch):
    with Session(engine) as db:
        record_confidential_bank_source(db,source())
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with Session(engine) as db:
        with pytest.raises(CanonicalJournalBlocked):
            accept_recorded_synthetic_bank(db,source_ref=SOURCE)
