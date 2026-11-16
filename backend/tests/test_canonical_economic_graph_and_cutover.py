"""G1 A7/A8 synthetic source graph and irreversible authority protection."""
from datetime import date
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa
from app.confidential_bank import ConfidentialBankInput, record_confidential_bank_source
from app.canonical_bank_posting import accept_recorded_synthetic_bank
from app.canonical_journal import JournalEvent, record_synthetic_journal, _blind
from app.canonical_economic_graph import (
    EconomicSourceClaim, CanonicalGraphBlocked, analyze_synthetic_economic_graph,
)
from app.canonical_cutover_policy import (
    CutoverBlocked, inspect_synthetic_cutover_readiness, refuse_authoritative_cutover, REQUIRED,
)
from app.g1c_preflight import SOURCE_COLUMNS, analyze_source_rows


BANK="SYNTHETIC-G1-BANK-0001"
STMT="SYNTHETIC-G1-STMT-0001"
CASH="SYNTHETIC-G1-CASH-001"
LOAN="SYNTHETIC-G1-LOAN-001"


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    engine=create_engine(f"sqlite:///{tmp_path / 'a7-source-graph.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def bank_payload():
    return ConfidentialBankInput.model_validate({
        "synthetic_fixture":True,"legal_owner":"individual","currency":"PKR",
        "account_ref":BANK,"institution":"FICTIONAL BANK","source_ref":STMT,
        "period_start":"2025-07-01","period_end":"2025-07-31",
        "opening_balance_minor":1200,"closing_balance_minor":1250,
        "rows":[
            {"row_number":1,"posted_on":"2025-07-02",
             "description":"fictional sample credit","debit_minor":0,
             "credit_minor":150,"balance_minor":1350},
            {"row_number":2,"posted_on":"2025-07-03",
             "description":"fictional sample debit","debit_minor":100,
             "credit_minor":0,"balance_minor":1250},
        ],
    })


def post_extra(db, ref, kind, account, domain, minor):
    entry=JournalEvent.model_validate({
        "synthetic_fixture":True,"legal_owner":"individual","currency":"PKR",
        "source_ref":ref,"primary_account_ref":account,
        "posted_on":"2025-07-05","event_kind":kind,
        "legs":[
            {"account_ref":account,"account_kind":domain,"signed_minor":minor},
            {"account_ref":"SYNTHETIC-CLEARING-A7","account_kind":"transfer_clearing","signed_minor":-minor},
        ],
    })
    record_synthetic_journal(db, entry)


def sample_claim(ref,domain,account,movement=None,amount=None,**kwargs):
    return EconomicSourceClaim.model_validate({
        "synthetic_fixture":True,"source_ref":ref,"source_domain":domain,
        "posted_on":"2025-07-05","account_ref":account,
        "movement_source_ref":movement, "amount_minor":amount, **kwargs,
    })


def seeded(db):
    record_confidential_bank_source(db,bank_payload())
    accept_recorded_synthetic_bank(db,source_ref=STMT)
    post_extra(db, "SYNTHETIC-A7-CASH-ENTRY","cash_transfer",CASH,"cash",200)
    post_extra(db, "SYNTHETIC-A7-LOAN-ENTRY","loan_principal",LOAN,"loan_receivable",300)


def test_verified_bank_and_distinct_cash_loan_claims_are_not_added_to_income(db):
    seeded(db)
    claims=(
        sample_claim("SYNTHETIC-A7-CLAIM-CASH","cash_movement",CASH,
                     "SYNTHETIC-A7-CASH-ENTRY",200),
        sample_claim("SYNTHETIC-A7-CLAIM-LOAN","loan_principal",LOAN,
                     "SYNTHETIC-A7-LOAN-ENTRY",300),
        sample_claim("SYNTHETIC-A7-CLAIM-ASSET","asset_valuation_claim",
                     "SYNTHETIC-A7-ASSET-001",status="OWNER_DECLARED",amount_minor=400),
        sample_claim("SYNTHETIC-A7-CLAIM-FBR","fbr_wealth_claim",
                     "SYNTHETIC-A7-FBR-WEALTH",status="DRAFT_CLAIM",amount_minor=900),
    )
    report=analyze_synthetic_economic_graph(db,claims=claims)
    assert report["bank_source_rows_verified"]==2
    assert report["neutral_postings_verified"]==2
    assert report["other_canonical_postings"]==2
    assert report["economic_claim_count"]==4
    assert report["domain_claim_counts"]["loan_principal"]==1
    assert report["source_receipt_hmac"] and len(report["source_receipt_hmac"])==64
    assert report["cross_domain_movements_double_counted"] is False
    assert report["net_worth_minor"] is None and report["tax_due_minor"] is None
    assert not report["fbr_acknowledgment_verified"]
    assert not report["authority_cutover"]
    assert "900" not in str(report) and CASH not in str(report)
    assert analyze_synthetic_economic_graph(db,claims=claims)==report


def test_missing_bank_posting_or_surplus_posting_rejected(db):
    record_confidential_bank_source(db, bank_payload())
    with pytest.raises(CanonicalGraphBlocked,match="Missing"):
        analyze_synthetic_economic_graph(db)
    accept_recorded_synthetic_bank(db,source_ref=STMT)
    with db.bind.begin() as connection:
        connection.execute(text("DELETE FROM canonical_journal_entries WHERE id = "
                                "(SELECT id FROM canonical_journal_entries LIMIT 1)"))
    db.expire_all()
    with pytest.raises(CanonicalGraphBlocked,match="Missing"):
        analyze_synthetic_economic_graph(db)


def test_cross_domain_duplicate_claim_ref_or_movement_ref_rejected(db):
    seeded(db)
    cash_claim=sample_claim("SYNTHETIC-CLAIM-DUP-001","cash_movement",CASH,
                            "SYNTHETIC-A7-CASH-ENTRY",200)
    with pytest.raises(CanonicalGraphBlocked,match="Duplicate"):
        analyze_synthetic_economic_graph(db,claims=(cash_claim,cash_claim))
    loan_claim=sample_claim("SYNTHETIC-CLAIM-DUP-002","loan_principal",LOAN,
                            "SYNTHETIC-A7-CASH-ENTRY",200)
    with pytest.raises(CanonicalGraphBlocked,match="multiple claims"):
        analyze_synthetic_economic_graph(db,claims=(cash_claim,loan_claim))


def test_unclassified_bank_receipt_cannot_be_called_income_or_cash(db):
    seeded(db)
    from app.canonical_bank_posting import _events
    bank_ref=_events(bank_payload())[0].source_ref
    bad=sample_claim("SYNTHETIC-A7-CASH-MISCLAIM","cash_movement",CASH,
                     bank_ref,150)
    with pytest.raises(CanonicalGraphBlocked,match="not classified"):
        analyze_synthetic_economic_graph(db,claims=(bad,))


@pytest.mark.parametrize("change", [
    {"status":"FILED_CLAIM"},
    {"source_domain":"fbr_wealth_claim","movement_source_ref":"SYNTHETIC-A7-CASH-ENTRY"},
    {"source_domain":"loan_principal","amount_minor":0},
    {"source_domain":"investment_cost","movement_source_ref":None},
    {"synthetic_fixture":False},
])
def test_unverified_claims_cannot_elevate_accounting_status(change):
    obj={
        "synthetic_fixture":True,"source_ref":"SYNTHETIC-CANDIDATE-1",
        "source_domain":"cash_movement","posted_on":"2025-07-05",
        "account_ref":CASH,"movement_source_ref":"SYNTHETIC-A7-CASH-ENTRY",
        "amount_minor":200,
    }
    obj.update(change)
    with pytest.raises(ValidationError):
        EconomicSourceClaim.model_validate(obj)


def readiness(source, graph, **changes):
    receipt={
        "source_report":source,
        "graph_report":graph,
        "backup_report":{"encrypted":True,"verified_read_snapshot":True,"source_untouched":True},
        "restore_report":{"independent_target":True,"full_row_parity_verified":True,
                          "source_untouched":True},
    }
    receipt.update(changes)
    return inspect_synthetic_cutover_readiness(**receipt)


def test_cutover_controller_is_non_executable_even_all_yes(db):
    seeded(db)
    graph=analyze_synthetic_economic_graph(db)
    source=analyze_source_rows({k: [] for k in SOURCE_COLUMNS})
    affirm={item:True for item in REQUIRED}
    report=readiness(source,graph,independent_acceptance=affirm)
    assert report["missing_acceptance"]
    assert "full_cash_loan_investment_asset_tax_year_parity" in report["missing_acceptance"]
    assert "approved_owner_fbr_claim_mapping" in report["missing_acceptance"]
    assert report["ledger_authority_switched"] is False
    assert report["legacy_plaintext_retired"] is False
    assert report["real_data_authorized"] is False
    with pytest.raises(CutoverBlocked,match="not implemented"):
        refuse_authoritative_cutover(owner_approved=True,source_proof=affirm)


def test_changed_backup_or_source_receipts_refuse_readiness(db):
    seeded(db)
    graph=analyze_synthetic_economic_graph(db)
    source=analyze_source_rows({k: [] for k in SOURCE_COLUMNS})
    with pytest.raises(CutoverBlocked):
        readiness(source,graph,backup_report={"encrypted":False})
    with pytest.raises(CutoverBlocked):
        readiness(source,graph,restore_report={"independent_target":False})
    with pytest.raises(CutoverBlocked):
        readiness(source,graph,independent_acceptance={"unknown_override":True})


def test_real_mode_cannot_reconcile_or_simulate_cutover(db,monkeypatch):
    seeded(db)
    graph=analyze_synthetic_economic_graph(db)
    source=analyze_source_rows({k: [] for k in SOURCE_COLUMNS})
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(CanonicalGraphBlocked):
        analyze_synthetic_economic_graph(db)
    with pytest.raises(CutoverBlocked):
        readiness(source,graph)
    with pytest.raises(CutoverBlocked):
        refuse_authoritative_cutover()
