"""A5b source-graph authenticated typed projections; synthetic only."""
from datetime import date
import pytest
from app.g1c_preflight import SOURCE_COLUMNS, analyze_source_rows, _canonical, _tag
from app.canonical_fact_parity import canonical_facts_from_sealed_mirrors, CanonicalFactsBlocked
from app.ledger_crypto import seal
from app.db import Base


def fixture():
    rows={name: [] for name in SOURCE_COLUMNS}
    def rec(name,**kwargs):
        return {k:kwargs.get(k) for k in SOURCE_COLUMNS[name]}
    rows["accounts"].append(rec("accounts",id="synthetic-account-0001",
                               legal_owner="individual",currency="PKR",
                               name=seal("fiction","accounts.name"),
                               institution=seal("fiction","accounts.institution")))
    rows["documents"].append(rec("documents",id="synthetic-document-0001",
                                 account_id="synthetic-account-0001",
                                 period_start=date(2024,7,1),
                                 period_end=date(2024,7,31),coverage_declared=True))
    rows["transactions"].append(rec("transactions",id="synthetic-tx-0001",
                     account_id="synthetic-account-0001",document_id="synthetic-document-0001",
                     posted_on=date(2024,7,3),credit_minor=40000,debit_minor=0,
                     balance_minor=40000,reviewed=False,excluded=False,
                     overlap_possible=False,overlap_resolved=False,
                     description=seal("fiction","transactions.description"),
                     category=seal("unreviewed","transactions.category")))
    report=analyze_source_rows(rows)
    blobs=[]
    for name in SOURCE_COLUMNS:
        for row in rows[name]:
            pk=[c.name for c in Base.metadata.tables[name].primary_key.columns]
            h=_tag(b"candidate-source-key",[name,[row[k] for k in pk]])
            blobs.append((h,seal(_canonical({"table":name,"source_row":row}).decode(),
                                 "canonical_source_mirrors.payload_json")))
    return report,blobs


def test_authenticated_full_source_contract_no_money_or_ids():
    src,blobs=fixture()
    result=canonical_facts_from_sealed_mirrors(blobs,src)
    assert result["typed_fact_type_counts"]=={"bank_source":1}
    assert result["typed_economic_source_fact_count"]==1
    assert result["original_source_census_matched"] is True
    assert result["unreviewed_bank_rows"]==1
    assert result["actual_tax_due_minor"] is None
    assert result["ledger_authority_switched"] is False
    assert "40000" not in str(result) and "synthetic-account" not in str(result)
    assert len(result["typed_facts_integrity_hmac"])==64


def test_source_omissions_tamper_replay_are_blocked():
    src,blobs=fixture()
    with pytest.raises(CanonicalFactsBlocked):
        canonical_facts_from_sealed_mirrors(blobs[:-1],src)
    with pytest.raises(CanonicalFactsBlocked):
        canonical_facts_from_sealed_mirrors(blobs+blobs[:1],src)
    bad=dict(src,source_integrity_hmac="0"*64)
    with pytest.raises(CanonicalFactsBlocked):
        canonical_facts_from_sealed_mirrors(blobs,bad)


def test_real_mode_denied(monkeypatch):
    src,blobs=fixture()
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(CanonicalFactsBlocked,match="Real"):
        canonical_facts_from_sealed_mirrors(blobs,src)
