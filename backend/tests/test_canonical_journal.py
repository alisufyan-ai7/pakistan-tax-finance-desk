"""A6 synthetic active encrypted canonical double-entry journal safety tests."""
import json
import base64

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa
from app.canonical_journal import (
    JournalEvent, CanonicalJournalBlocked, record_synthetic_journal,
    inspect_synthetic_journal, _blind,
)


ACCOUNT = "SYNTHETIC-ACCT-00001"
SOURCE = "SYNTHETIC-STMT-ROW-0001"


def event(**overrides):
    payload = {
        "synthetic_fixture": True,
        "legal_owner": "individual",
        "currency": "PKR",
        "source_ref": SOURCE,
        "primary_account_ref": ACCOUNT,
        "posted_on": "2025-07-15",
        "event_kind": "bank_receipt",
        "legs": [
            {"account_ref": ACCOUNT, "account_kind": "bank", "signed_minor": 123456},
            {"account_ref": "SYNTHETIC-INCOME-1", "account_kind": "income", "signed_minor": -123456},
        ],
    }
    payload.update(overrides)
    return JournalEvent.model_validate(payload)


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    db = create_engine(f"sqlite:///{tmp_path / 'sealed-journal.db'}")
    Base.metadata.create_all(db)
    yield db
    db.dispose()


def test_balanced_insert_replay_and_internally_authenticated_read(engine):
    with Session(engine) as db:
        receipt, replay = record_synthetic_journal(db, event())
        assert not replay and receipt["balanced_to_zero"]
        assert receipt["active_within_separate_journal"] is True
        assert receipt["legacy_ledger_cutover"] is False
        second, replayed = record_synthetic_journal(db, event())
        assert replayed and second["id"] == receipt["id"]
        listed = inspect_synthetic_journal(db, primary_account_ref=ACCOUNT, tax_year=2026)
        assert listed["source_event_count"] == 1
        assert listed["account_balance_minor"] is None
        assert listed["fbr_filed_confirmed"] is False
        assert inspect_synthetic_journal(db, primary_account_ref=ACCOUNT, tax_year=2025)["source_event_count"] == 0
    with engine.connect() as conn:
        raw = conn.execute(text("SELECT payload_json FROM canonical_journal_entries")).scalar_one()
        anchor = conn.execute(text("SELECT sentinel FROM canonical_journal_key_state")).scalar_one()
        assert raw.startswith("TFLE1:") and anchor.startswith("TFLE1:")
        for secret in (SOURCE, ACCOUNT, "123456", "2025-07-15"):
            assert secret not in raw
        assert conn.execute(text("SELECT count(*) FROM transactions")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM canonical_journal_entries")).scalar_one() == 1


@pytest.mark.parametrize("overrides", [
    {"legs": [
        {"account_ref": ACCOUNT, "account_kind": "bank", "signed_minor": 12},
        {"account_ref": "SYNTHETIC-INCOME-1", "account_kind": "income", "signed_minor": -11},
    ]},
    {"legs": [
        {"account_ref": ACCOUNT, "account_kind": "bank", "signed_minor": 12},
        {"account_ref": ACCOUNT, "account_kind": "bank", "signed_minor": -12},
    ]},
    {"legs": [
        {"account_ref": ACCOUNT, "account_kind": "bank", "signed_minor": 0},
        {"account_ref": "SYNTHETIC-INCOME-1", "account_kind": "income", "signed_minor": 0},
    ]},
    {"official_fbr_verified": True},
    {"synthetic_fixture": False},
    {"primary_account_ref": "UNLINKED-ACCOUNT"},
])
def test_unbalanced_duplicate_or_unverified_claims_fail_schema(overrides):
    with pytest.raises(ValidationError):
        event(**overrides)


def test_conflicting_replay_never_overwrites(engine):
    with Session(engine) as db:
        record_synthetic_journal(db, event())
        changed = event(posted_on="2025-07-16")
        with pytest.raises(CanonicalJournalBlocked, match="Conflicting"):
            record_synthetic_journal(db, changed)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM canonical_journal_entries")).scalar_one() == 1


def test_key_change_detected_before_read_or_write(engine, monkeypatch):
    with Session(engine) as db:
        record_synthetic_journal(db, event())
    monkeypatch.setenv("CANONICAL_JOURNAL_HMAC_KEY", base64.urlsafe_b64encode(b"Z"*32).decode())
    with Session(engine) as db:
        with pytest.raises(CanonicalJournalBlocked, match="key mismatch"):
            inspect_synthetic_journal(db, primary_account_ref=ACCOUNT, tax_year=2026)
    monkeypatch.setenv("CANONICAL_JOURNAL_HMAC_KEY", base64.urlsafe_b64encode(b"S"*32).decode())
    with Session(engine) as db:
        with pytest.raises(CanonicalJournalBlocked, match="Independent"):
            inspect_synthetic_journal(db, primary_account_ref=ACCOUNT, tax_year=2026)


def test_index_payload_tampering_rejected(engine):
    with Session(engine) as db:
        record_synthetic_journal(db, event())
    with engine.begin() as c:
        c.execute(text("UPDATE canonical_journal_entries SET account_hmac = :wrong"), {"wrong": "0"*64})
    with Session(engine) as db:
        with pytest.raises(CanonicalJournalBlocked, match="index"):
            inspect_synthetic_journal(db, primary_account_ref=ACCOUNT, tax_year=2026)
        # Account lookup on the tampered index returns no rows: full SQL
        # row parity is a separate G1-c/A7 cutover precondition, not done here.
    # Direct decrypt+verification rejects physical tampering.
    from app.canonical_journal import _verify_record
    with Session(engine) as db:
        row = db.query(models.CanonicalJournalEntry).one()
        with pytest.raises(CanonicalJournalBlocked):
            _verify_record(row)


def test_real_mode_and_missing_crypto_configuration_fail_closed(engine, monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with Session(engine) as db:
        with pytest.raises(CanonicalJournalBlocked, match="Real"):
            record_synthetic_journal(db, event())
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.delenv("CANONICAL_JOURNAL_HMAC_KEY", raising=False)
    with Session(engine) as db:
        with pytest.raises(CanonicalJournalBlocked):
            record_synthetic_journal(db, event())
