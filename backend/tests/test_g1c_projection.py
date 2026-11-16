"""A5a encrypted candidate source-only read-side parity, fabricated records."""
from datetime import date
import base64
import json
import pytest
from app.g1c_preflight import SOURCE_COLUMNS, analyze_source_rows, _tag, _canonical
from app.g1c_projection import (
    SealedProjectionBlocked, verify_sealed_candidate_rows, inspect_restored_sealed_candidate,
)
from app.ledger_crypto import seal


def _rows():
    rows={name: [] for name in SOURCE_COLUMNS}
    def blank(t, **overrides):
        return {c: overrides.get(c) for c in SOURCE_COLUMNS[t]}
    account="synthetic-account-001"
    doc="synthetic-document-001"
    rows["accounts"].append(blank("accounts",
        id=account,name=seal("fictional", "accounts.name"),
        institution=seal("fictional bank", "accounts.institution"),
        currency="PKR",legal_owner="individual"))
    rows["documents"].append(blank("documents",id=doc,account_id=account,
        period_start=date(2024,7,1),period_end=date(2024,7,31),
        coverage_declared=True))
    rows["transactions"].append(blank("transactions",
        id="synthetic-tx-001", account_id=account, document_id=doc,
        row_number=1, posted_on=date(2024,7,3),
        debit_minor=0,credit_minor=50000,balance_minor=50000,
        description=seal("synthetic credit", "transactions.description"),
        category=seal("unreviewed", "transactions.category"),
        reviewed=False,overlap_possible=False,overlap_resolved=False,excluded=False))
    return rows


def _mirrors(rows):
    result=[]
    for table, items in rows.items():
        if table=="canonical_source_mirrors":
            continue
        for row in items:
            from app.db import Base
            pk=[c.name for c in Base.metadata.tables[table].primary_key.columns]
            index=_tag(b"candidate-source-key",[table,[row[c] for c in pk]])
            payload=_canonical({"table":table,"source_row":row}).decode()
            result.append((index,seal(payload,"canonical_source_mirrors.payload_json")))
    return result


def test_reconstructed_graph_matches_original_receipt_and_hides_money():
    src=_rows()
    reference=analyze_source_rows(src)
    out=verify_sealed_candidate_rows(_mirrors(src),reference)
    assert out["authenticated_mirror_count"]==3
    assert out["full_source_row_parity_verified"]
    assert out["active_ledger_cutover"] is False
    assert out["legacy_plaintext_still_present"] is True
    assert "50000" not in str(out) and "synthetic-account-001" not in str(out)
    assert out["tax_due_minor"] is None


def test_missing_mirror_and_duplicate_replay_rejected():
    src=_rows()
    original=analyze_source_rows(src)
    mirrors=_mirrors(src)
    with pytest.raises(SealedProjectionBlocked,match="parity"):
        verify_sealed_candidate_rows(mirrors[:-1],original)
    with pytest.raises(SealedProjectionBlocked,match="Duplicate"):
        verify_sealed_candidate_rows(mirrors+mirrors[:1],original)


def test_wrong_key_or_tampered_token_fail_closed(monkeypatch):
    src=_rows()
    mirrors=_mirrors(src)
    first,token=mirrors[0]
    marker,kid,encoded=token.split(":",2)
    damaged=bytearray(base64.urlsafe_b64decode(encoded))
    damaged[-1] ^= 1
    bad=":".join((marker,kid,base64.urlsafe_b64encode(damaged).decode()))
    with pytest.raises(SealedProjectionBlocked,match="authentication"):
        verify_sealed_candidate_rows([(first,bad),*mirrors[1:]],analyze_source_rows(src))


def test_source_index_conflict_and_unknown_table_rejected():
    src=_rows()
    mirrors=_mirrors(src)
    with pytest.raises(SealedProjectionBlocked,match="HMAC"):
        verify_sealed_candidate_rows([("a"*64,mirrors[0][1]),*mirrors[1:]],analyze_source_rows(src))
    token=seal(json.dumps({"table":"unexpected_table","source_row":{}},sort_keys=True),
               "canonical_source_mirrors.payload_json")
    with pytest.raises(SealedProjectionBlocked,match="Unknown"):
        verify_sealed_candidate_rows([("a"*64,token)],analyze_source_rows(src))


def test_real_mode_denied_before_postgres_query(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(SealedProjectionBlocked,match="Real"):
        inspect_restored_sealed_candidate()
    with pytest.raises(SealedProjectionBlocked,match="Real"):
        verify_sealed_candidate_rows([],{})


def test_candidate_missing_original_receipt_denied():
    with pytest.raises(SealedProjectionBlocked,match="receipt"):
        verify_sealed_candidate_rows([("a"*64,"fake")],{})
