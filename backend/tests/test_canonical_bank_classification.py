"""G1: synthetic-only source-backed, reversible annotation with no money duplication."""
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db import Base
from app import models
from app.confidential_bank import ConfidentialBankInput, record_confidential_bank_source
from app.canonical_bank_posting import accept_recorded_synthetic_bank
from app.canonical_bank_classification import (
    BankCandidate, ClassificationBlocked, annotate_synthetic_bank_candidate,
    reverse_synthetic_bank_candidate,
)
from app.canonical_journal import _verify_record
from app.canonical_economic_graph import analyze_synthetic_economic_graph

SOURCE="SYNTHETIC-CANDIDATE-STMT-01"
BANK="SYNTHETIC-CANDIDATE-BANK-01"


@pytest.fixture
def engine(monkeypatch,tmp_path):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    eng=create_engine(f"sqlite:///{tmp_path / 'candidate-only.db'}")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def statement():
    return ConfidentialBankInput.model_validate({
        "synthetic_fixture":True, "legal_owner":"individual", "currency":"PKR",
        "institution":"FICTIONAL BANK", "account_ref":BANK,
        "source_ref":SOURCE, "period_start":"2025-07-01", "period_end":"2025-07-31",
        "opening_balance_minor":100000, "closing_balance_minor":101200,
        "rows":[
            {"row_number":1,"posted_on":"2025-07-03","description":"fictional receipt",
             "credit_minor":2000,"debit_minor":0,"balance_minor":102000},
            {"row_number":2,"posted_on":"2025-07-04","description":"fictional withdrawal",
             "credit_minor":0,"debit_minor":800,"balance_minor":101200},
        ],
    })


def annotation(row,candidate):
    return BankCandidate.model_validate({
        "synthetic_fixture":True,"source_ref":SOURCE,"row_number":row,
        "candidate":candidate,"explicit_owner_annotation":True,
    })


def seed(db):
    record_confidential_bank_source(db,statement())
    accept_recorded_synthetic_bank(db,source_ref=SOURCE)


def test_direction_matched_annotation_and_idempotent_reversal(engine):
    with Session(engine) as db:
        seed(db)
        plus=annotate_synthetic_bank_candidate(
            db,annotation=annotation(1,"income_candidate"))
        minus=annotate_synthetic_bank_candidate(
            db,annotation=annotation(2,"expense_candidate"))
        assert plus["balanced_candidate_entry"] and not plus["candidate_replayed"]
        assert minus["balanced_candidate_entry"] and not minus["candidate_replayed"]
        replay=annotate_synthetic_bank_candidate(
            db,annotation=annotation(1,"income_candidate"))
        assert replay["candidate_replayed"] is True
        original = db.scalars(select(models.CanonicalJournalEntry)).all()
        verified = [_verify_record(x) for x in original]
        assert len(verified) == 4
        assert sum(leg.signed_minor for e in verified for leg in e.legs
                   if leg.account_kind == "bank") == 1200
        assert len([e for e in verified if e.event_kind=="classification_candidate"])==2
        assert all(not any(leg.account_kind=="bank" for leg in e.legs)
                   for e in verified if e.event_kind=="classification_candidate")
        correction=reverse_synthetic_bank_candidate(
            db,source_ref=SOURCE,row_number=1,explicit_correction=True)
        assert correction["exact_inverse_posted"] and not correction["correction_replayed"]
        repeated=reverse_synthetic_bank_candidate(
            db,source_ref=SOURCE,row_number=1,explicit_correction=True)
        assert repeated["correction_replayed"]
        verified=[_verify_record(x) for x in db.scalars(select(models.CanonicalJournalEntry)).all()]
        assert sum(leg.signed_minor for e in verified for leg in e.legs
                   if leg.account_kind=="income")==0
        assert sum(leg.signed_minor for e in verified for leg in e.legs
                   if leg.account_kind=="bank")==1200
        graph=analyze_synthetic_economic_graph(db)
        assert graph["bank_source_rows_verified"]==2
        assert graph["financial_scope_complete"] is False
        assert graph["tax_due_minor"] is None
        with pytest.raises(ClassificationBlocked,match="Reversed"):
            annotate_synthetic_bank_candidate(db,annotation=annotation(1,"income_candidate"))
    with engine.connect() as c:
        values=c.execute(text("SELECT payload_json FROM canonical_journal_entries")).scalars().all()
        assert len(values)==5
        assert all(v.startswith("TFLE1:") for v in values)
        assert all(SOURCE not in v and BANK not in v and "2000" not in v for v in values)


def test_unknown_or_mismatched_annotation_cannot_ever_post(engine):
    with Session(engine) as db:
        seed(db)
        with pytest.raises(ClassificationBlocked,match="contradicts"):
            annotate_synthetic_bank_candidate(db,annotation=annotation(1,"expense_candidate"))
        with pytest.raises(ClassificationBlocked,match="contradicts"):
            annotate_synthetic_bank_candidate(db,annotation=annotation(2,"income_candidate"))
        with pytest.raises(ClassificationBlocked,match="Unverified"):
            annotate_synthetic_bank_candidate(db,annotation=annotation(99,"income_candidate"))
        with pytest.raises(ClassificationBlocked,match="No original"):
            reverse_synthetic_bank_candidate(
                db,source_ref=SOURCE,row_number=1,explicit_correction=True)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM canonical_journal_entries")).scalar_one()==2


def test_without_sealed_source_and_neutral_posting_fails(engine):
    with Session(engine) as db:
        with pytest.raises(ClassificationBlocked):
            annotate_synthetic_bank_candidate(db,annotation=annotation(1,"income_candidate"))
        record_confidential_bank_source(db,statement())
        with pytest.raises(ClassificationBlocked,match="neutral"):
            annotate_synthetic_bank_candidate(db,annotation=annotation(1,"income_candidate"))


def test_immutable_candidate_conflict_and_unapproved_correction(engine):
    with Session(engine) as db:
        seed(db)
        annotate_synthetic_bank_candidate(db,annotation=annotation(1,"income_candidate"))
        with pytest.raises(ClassificationBlocked):
            reverse_synthetic_bank_candidate(db,source_ref=SOURCE,row_number=1,explicit_correction=False)
        with pytest.raises(ClassificationBlocked):
            annotate_synthetic_bank_candidate(db,annotation=annotation(1,"expense_candidate"))


@pytest.mark.parametrize("invalid",[
    {"synthetic_fixture":False},{"explicit_owner_annotation":False},
    {"candidate":"official_salary"},{"row_number":True},
])
def test_only_explicit_synthetic_owner_annotation_accepted(invalid):
    payload=dict(synthetic_fixture=True,source_ref=SOURCE,row_number=1,
                 candidate="income_candidate",explicit_owner_annotation=True)
    payload.update(invalid)
    with pytest.raises(ValidationError):
        BankCandidate.model_validate(payload)


def test_real_mode_forbids_annotation_and_reversal(engine,monkeypatch):
    with Session(engine) as db:
        seed(db)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with Session(engine) as db:
        with pytest.raises(ClassificationBlocked):
            annotate_synthetic_bank_candidate(db,annotation=annotation(1,"income_candidate"))
        with pytest.raises(ClassificationBlocked):
            reverse_synthetic_bank_candidate(
                db,source_ref=SOURCE,row_number=1,explicit_correction=True)
