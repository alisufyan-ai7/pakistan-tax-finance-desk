"""M2d synthetic-only secure-ledger field and rotation tests."""
import base64
import json
import sqlite3
import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import Column, String, MetaData, Table, create_engine, select
from sqlalchemy.orm import Session
from app.ledger_crypto import EncryptedText, LedgerKeyError, envelope_key_id, seal, unseal, ENCRYPTED_COLUMNS
from app.rotate_ledger_keys import rotate_fields


def setup_keyring(monkeypatch):
    keys = {"v1": base64.urlsafe_b64encode(b"a" * 32).decode(),
            "v2": base64.urlsafe_b64encode(b"b" * 32).decode()}
    monkeypatch.setenv("LEDGER_FIELD_KEYS_JSON", json.dumps(keys))
    monkeypatch.setenv("LEDGER_FIELD_ACTIVE_KEY", "v1")
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    return keys


def test_randomized_ciphertext_roundtrip_and_domain_binding(monkeypatch):
    setup_keyring(monkeypatch)
    a = seal("Synthetic investment salary", "transactions.description")
    b = seal("Synthetic investment salary", "transactions.description")
    assert a != b and a.startswith("TFLE1:v1:")
    assert "Synthetic" not in a
    assert unseal(a, "transactions.description") == "Synthetic investment salary"
    with pytest.raises(InvalidTag):
        unseal(a, "accounts.name")
    with pytest.raises(LedgerKeyError):
        unseal("Synthetic investment salary", "transactions.description")
    with pytest.raises(LedgerKeyError):
        seal("unsafe", "unknown.column")
    with pytest.raises(LedgerKeyError):
        unseal("TFLE1:v3:abcd", "transactions.description")


def test_ciphertext_tampering_and_missing_key_fail_closed(monkeypatch):
    keys=setup_keyring(monkeypatch)
    encrypted = seal("Synthetic private reference", "transactions.reference")
    raw = list(encrypted)
    raw[-4] = "B" if raw[-4] != "B" else "A"
    with pytest.raises(InvalidTag):
        unseal("".join(raw), "transactions.reference")
    monkeypatch.delenv("LEDGER_FIELD_KEYS_JSON")
    with pytest.raises(LedgerKeyError):
        unseal(encrypted, "transactions.reference")
    monkeypatch.setenv("LEDGER_FIELD_KEYS_JSON", json.dumps({"v2":keys["v2"]}))
    monkeypatch.setenv("LEDGER_FIELD_ACTIVE_KEY", "v2")
    with pytest.raises(LedgerKeyError,match="unavailable"):
        unseal(encrypted, "transactions.reference")


def test_sqlalchemy_column_roundtrip_encrypted_at_rest(tmp_path,monkeypatch):
    setup_keyring(monkeypatch)
    db=tmp_path/"synthetic.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    meta=MetaData()
    accounts=Table("accounts",meta,Column("id", String, primary_key=True), Column("name",EncryptedText("accounts.name")),Column("institution",EncryptedText("accounts.institution")))
    meta.create_all(engine)
    with engine.begin() as con:
        con.execute(accounts.insert().values(id="1",name="Synthetic savings",institution="Synthetic bank"))
    with sqlite3.connect(db) as con:
        name,bank=con.execute("SELECT name,institution FROM accounts").fetchone()
        assert "Synthetic" not in name and "Synthetic" not in bank
    with Session(engine) as session:
        row=session.execute(select(accounts)).one()
        assert row.name=="Synthetic savings" and row.institution=="Synthetic bank"
    with engine.begin() as con:
        con.exec_driver_sql("UPDATE accounts SET name = 'legacy-plaintext' WHERE id = '1'")
    with pytest.raises(Exception,match="Legacy unsealed"):
        with Session(engine) as session:
            session.execute(select(accounts)).all()


def test_atomic_rotation_and_key_retirement(tmp_path,monkeypatch):
    keys=setup_keyring(monkeypatch)
    path=tmp_path/"synthetic.sqlite"
    engine=create_engine(f"sqlite:///{path}")
    with engine.begin() as con:
        con.exec_driver_sql("CREATE TABLE accounts (id TEXT PRIMARY KEY, name TEXT, institution TEXT)")
        con.exec_driver_sql("CREATE TABLE transactions (id TEXT PRIMARY KEY, description TEXT, reference TEXT, category TEXT)")
        con.exec_driver_sql("CREATE TABLE audit_events (id TEXT PRIMARY KEY, old_category TEXT, new_category TEXT, note TEXT)")
        con.exec_driver_sql("INSERT INTO accounts VALUES (?, ?, ?)", ("a",seal("savings", "accounts.name"),seal("bank", "accounts.institution")))
        con.exec_driver_sql("INSERT INTO transactions VALUES (?, ?, ?, ?)",("t",seal("salary", "transactions.description"),None,seal("unreviewed","transactions.category")))
        con.exec_driver_sql("INSERT INTO audit_events VALUES (?, ?, ?, ?)",("e",seal("unreviewed", "audit_events.old_category"),seal("salary", "audit_events.new_category"),seal("corrected", "audit_events.note")))
    before=engine.connect().exec_driver_sql("SELECT name FROM accounts").scalar_one()
    dry=rotate_fields(engine,new_key_id="v2")
    assert dry["accounts.name"]==1
    assert engine.connect().exec_driver_sql("SELECT name FROM accounts").scalar_one()==before
    changes=rotate_fields(engine,new_key_id="v2",dry_run=False)
    assert changes["audit_events.note"]==1
    after=engine.connect().exec_driver_sql("SELECT name FROM accounts").scalar_one()
    assert envelope_key_id(after)=="v2"
    assert unseal(after,"accounts.name")=="savings"
    monkeypatch.setenv("LEDGER_FIELD_KEYS_JSON",json.dumps({"v2":keys["v2"]}))
    monkeypatch.setenv("LEDGER_FIELD_ACTIVE_KEY","v2")
    assert unseal(after,"accounts.name")=="savings"
    assert rotate_fields(engine,new_key_id="v2",dry_run=True)["accounts.name"]==0


def test_rotation_rollback_on_plaintext_legacy(tmp_path,monkeypatch):
    setup_keyring(monkeypatch)
    path=tmp_path/"synthetic.sqlite"
    engine=create_engine(f"sqlite:///{path}")
    with engine.begin() as con:
        con.exec_driver_sql("CREATE TABLE accounts (id TEXT PRIMARY KEY, name TEXT, institution TEXT)")
        con.exec_driver_sql("CREATE TABLE transactions (id TEXT PRIMARY KEY, description TEXT, reference TEXT, category TEXT)")
        con.exec_driver_sql("CREATE TABLE audit_events (id TEXT PRIMARY KEY, old_category TEXT, new_category TEXT, note TEXT)")
        con.exec_driver_sql("INSERT INTO accounts VALUES (?, ?, ?)", ("a",seal("savings", "accounts.name"), "legacy plaintext bank"))
    before=engine.connect().exec_driver_sql("SELECT name FROM accounts").scalar_one()
    with pytest.raises(LedgerKeyError,match="Legacy unsealed"):
        rotate_fields(engine,new_key_id="v2",dry_run=False)
    after=engine.connect().exec_driver_sql("SELECT name FROM accounts").scalar_one()
    assert after==before # atomic rollback