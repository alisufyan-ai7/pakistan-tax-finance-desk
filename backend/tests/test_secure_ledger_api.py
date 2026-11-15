"""Local synthetic-only integration checks for protected ledger fields."""
import sqlite3
from test_imports import csv_bytes, upload
from app.ledger_crypto import PREFIX


def test_account_transaction_and_audit_text_never_plaintext(client, account, tmp_path):
    raw=csv_bytes([["2024-07-05", "Synth charity to sample nonprofit", "10.00", "", "90.00", "secret-ref-8"]])
    assert upload(client, account, raw, opening_balance="100.00").status_code==201
    tx=client.get('/api/transactions?tax_year=2025').json()['rows'][0]
    assert tx['description']=="Synth charity to sample nonprofit"
    assert client.patch(f"/api/transactions/{tx['id']}",json={"category":"donation","note":"verified-synthetic-donation"}).status_code==200
    dbpath=tmp_path/'test.db'
    with sqlite3.connect(dbpath) as db:
        account_fields=db.execute("SELECT name,institution FROM accounts").fetchone()
        tx_fields=db.execute("SELECT description,reference,category FROM transactions").fetchone()
        audit_fields=db.execute("SELECT old_category,new_category,note FROM audit_events").fetchone()
        assert all(value.startswith(PREFIX) for value in (*account_fields,*tx_fields,*audit_fields))
        dump="".join(db.iterdump())
        for needle in ["Synthetic Account","Example Bank","Synth charity","secret-ref-8", "verified-synthetic-donation", "unreviewed"]:
            assert needle not in dump
    assert client.get('/api/summary?tax_year=2025').json()['classified_totals']=={'donation':'10.00'}


def test_random_ciphertext_does_not_break_weak_overlap_detection(client,account):
    a=csv_bytes([["2025-08-01","same synthetic tea","7.00","","",""]])
    b=csv_bytes([["2025-08-01","same synthetic tea","7.00","","", ""],
                 ["2025-08-02","another synthetic tea","2.00","","",""]])
    assert upload(client,account,a).json()['accepted']==1
    assert upload(client,account,b).json()['potential_overlaps']==1
    assert client.get('/api/summary?tax_year=2026').json()['possible_overlaps_pending']==1


def test_old_unsealed_ledger_fails_before_serving(tmp_path,monkeypatch):
    from sqlalchemy import create_engine
    from app.db import Base
    from app.main import create_app
    from app.models import Account
    path=tmp_path/'legacy.db'
    e=create_engine(f'sqlite:///{path}')
    Base.metadata.create_all(e)
    with e.begin() as con:
        con.exec_driver_sql("INSERT INTO accounts(id,name,institution,currency,legal_owner,created_at) VALUES (?,?,?,?,?,?)",
                            ('synthetic','LEGACY_PLAINTEXT','bank','PKR','individual','2026-11-15 00:00:00'))
    e.dispose()
    monkeypatch.setenv('OWNER_PASSWORD','synthetic-owner-password-long')
    try:
        create_app(f'sqlite:///{path}')
        assert False, 'Legacy plaintext row should fail startup'
    except RuntimeError as exc:
        assert 'unsealed' in str(exc).lower()