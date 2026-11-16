"""G1 synthetic typed movement coverage without fictional owner balance claims."""
from datetime import date
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from pydantic import ValidationError
import pytest

from app.db import Base
from app import models
from app.canonical_typed_economic_postings import (
    OwnerEconomicMovement, EconomicMovementBlocked,
    build_owner_economic_proposal, record_owner_economic_proposal,
    inspect_synthetic_bank_transfer_pair,
)
from app.canonical_economic_graph import (
    EconomicSourceClaim,analyze_synthetic_economic_graph,CanonicalGraphBlocked,
)
from app.canonical_journal import _verify_record
from app.confidential_bank import ConfidentialBankInput,record_confidential_bank_source
from app.canonical_bank_posting import accept_recorded_synthetic_bank


@pytest.fixture
def engine(monkeypatch,tmp_path):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    eng=create_engine(f"sqlite:///{tmp_path/'typed-synthetic-finance.db'}")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


DOMAINS=(
    ("cash_movement","cash","cash_transfer"),
    ("loan_given_principal","loan_receivable","loan_principal"),
    ("loan_taken_principal","loan_payable","loan_principal"),
    ("investment_cost","investment_cost","investment_contribution"),
    ("withholding_candidate","withholding_candidate","withholding_candidate"),
    ("asset_cost_opening","asset_cost","owner_opening_assertion"),
)


def movement(domain,source=None,amount=1200,**kwargs):
    source = source or ("SYNTHETIC-TYPED-"+domain.upper())
    attrs={
        "synthetic_fixture": True,
        "source_ref": source,
        "account_ref":"SYNTHETIC-OWNED-ACCOUNT-"+domain.upper(),
        "posted_on":"2025-07-15",
        "movement_kind":domain,
        "amount_minor":amount,
        "direction":"increase",
        "explicit_owner_annotation":True,
    }
    attrs.update(kwargs)
    return OwnerEconomicMovement.model_validate(attrs)


def test_all_six_typed_domains_remain_encrypted_balanced_and_uncertified(engine):
    with Session(engine) as db:
        created=[]
        for domain,kind,event_kind in DOMAINS:
            item=movement(domain)
            proposal=build_owner_economic_proposal(item)
            assert proposal.event_kind==event_kind
            assert proposal.legs[0].account_kind==kind
            assert all(leg.account_kind!="bank" for leg in proposal.legs)
            result=record_owner_economic_proposal(db,movement=item)
            assert result["double_entry_balanced"]
            assert not result["idempotent_replay"]
            assert not result["independent_source_verified"]
            assert result["verified_account_balance_minor"] is None
            assert result["tax_due_minor"] is None
            assert record_owner_economic_proposal(db,movement=item)["idempotent_replay"]
            created.append((item,proposal))
        claims=[]
        for idx,(item,event) in enumerate(created):
            domain = "loan_principal" if "loan_" in item.movement_kind else item.movement_kind
            claims.append(EconomicSourceClaim.model_validate({
                "synthetic_fixture":True,
                "source_ref":"SYNTHETIC-CORROBORATING-CLAIM-"+str(idx),
                "source_domain":domain,
                "posted_on":item.posted_on,
                "account_ref":item.account_ref,
                "movement_source_ref":event.source_ref,
                "amount_minor":item.amount_minor,
            }))
        report=analyze_synthetic_economic_graph(db,claims=tuple(claims))
        assert report["economic_claim_count"]==6
        assert report["domain_claim_counts"]["loan_principal"]==2
        assert report["domain_claim_counts"]["asset_cost_opening"]==1
        assert report["financial_scope_complete"] is False
        assert report["fbr_acknowledgment_verified"] is False
        assert report["asset_valuation_is_realized_return"] is False
        assert report["net_worth_minor"] is None
        assert report["tax_due_minor"] is None
    with engine.connect() as connection:
        encrypted=connection.execute(text(
            "SELECT payload_json FROM canonical_journal_entries")).scalars().all()
        assert len(encrypted)==6 and all(s.startswith("TFLE1:") for s in encrypted)
        for private in ("SYNTHETIC-TYPED-","1200","2025-07-15"):
            assert all(private not in s for s in encrypted)
        assert connection.execute(text("SELECT COUNT(*) FROM transactions")).scalar_one()==0


def test_same_owner_source_cannot_double_book_cash_and_loan(engine):
    with Session(engine) as db:
        first=movement("cash_movement",source="SYNTHETIC-SHARED-SOURCE-01")
        next_event=movement("loan_given_principal",source="SYNTHETIC-SHARED-SOURCE-01")
        record_owner_economic_proposal(db,movement=first)
        with pytest.raises(EconomicMovementBlocked,match="Conflicting"):
            record_owner_economic_proposal(db,movement=next_event)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM canonical_journal_entries")).scalar_one()==1


@pytest.mark.parametrize("wrong",[
    {"synthetic_fixture":False},{"explicit_owner_annotation":False},
    {"independent_source_verified":True},
    {"original_document_certified":True},
    {"amount_minor":0},{"amount_minor":True},
    {"movement_kind":"real_salary"},
    {"movement_kind":"asset_cost_opening","direction":"decrease"},
])
def test_input_never_self_certifies_unreviewed_domain_claims(wrong):
    obj={
        "synthetic_fixture":True,"source_ref":"SYNTHETIC-OWNER-CLAIM-01",
        "account_ref":"SYNTHETIC-OWNER-ACCOUNT-01",
        "posted_on":"2025-07-15","movement_kind":"cash_movement",
        "amount_minor":1000,"direction":"increase",
        "explicit_owner_annotation":True,
    }
    obj.update(wrong)
    with pytest.raises(ValidationError):
        OwnerEconomicMovement.model_validate(obj)


def statement(account,source,credit,debit,opening):
    return ConfidentialBankInput.model_validate({
        "synthetic_fixture":True,"legal_owner":"individual","currency":"PKR",
        "institution":"FICTIONAL BANK","account_ref":account,
        "source_ref":source,
        "period_start":"2025-07-01","period_end":"2025-07-31",
        "opening_balance_minor":opening,
        "closing_balance_minor":opening+credit-debit,
        "rows":[{"row_number":1,"posted_on":"2025-07-15",
                 "description":"fictional synthetic pair",
                 "credit_minor":credit,"debit_minor":debit,
                 "balance_minor":opening+credit-debit}],
    })


def test_bank_transfer_pair_proposes_link_only_without_new_bank_legs(engine):
    with Session(engine) as db:
        from_account="SYNTHETIC-TRANSFER-BANK-A"
        to_account="SYNTHETIC-TRANSFER-BANK-B"
        from_source="SYNTHETIC-TRANSFER-STMT-A"
        to_source="SYNTHETIC-TRANSFER-STMT-B"
        for batch in (
            statement(from_account,from_source,0,2500,10000),
            statement(to_account,to_source,2500,0,2000),
        ):
            record_confidential_bank_source(db,batch)
            accept_recorded_synthetic_bank(db,source_ref=batch.source_ref)
        before=db.query(models.CanonicalJournalEntry).count()
        result=inspect_synthetic_bank_transfer_pair(db,
            debit_source_ref=from_source,debit_row_number=1,
            credit_source_ref=to_source,credit_row_number=1,
            explicit_owner_annotation=True)
        assert len(result["candidate_transfer_hmac"])==64
        assert result["matched_neutral_bank_rows"]==2
        assert result["additional_bank_postings_created"]==0
        assert not result["actual_same_owner_transfer_verified"]
        assert db.query(models.CanonicalJournalEntry).count()==before==2
        with pytest.raises(EconomicMovementBlocked):
            inspect_synthetic_bank_transfer_pair(db,
                debit_source_ref=to_source,debit_row_number=1,
                credit_source_ref=from_source,credit_row_number=1,
                explicit_owner_annotation=True)
        with pytest.raises(EconomicMovementBlocked):
            inspect_synthetic_bank_transfer_pair(db,
                debit_source_ref=from_source,debit_row_number=1,
                credit_source_ref=to_source,credit_row_number=1,
                explicit_owner_annotation=False)


def test_real_mode_fails_closed(engine,monkeypatch):
    item=movement("cash_movement")
    with Session(engine) as db:
        monkeypatch.setenv("APP_DATA_MODE","real")
        with pytest.raises(EconomicMovementBlocked):
            record_owner_economic_proposal(db,movement=item)
        with pytest.raises(EconomicMovementBlocked):
            inspect_synthetic_bank_transfer_pair(db,
                debit_source_ref="SYNTHETIC-TRANSFER-STMT-A",debit_row_number=1,
                credit_source_ref="SYNTHETIC-TRANSFER-STMT-B",credit_row_number=1,
                explicit_owner_annotation=True)
