"""G1-a operational private source tests. Everything here is fabricated."""
import base64
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from app.main import create_app
from app.confidential_bank import ConfidentialBankInput, ConfidentialBankKeyError, _blind, _key
from app.synthetic_backup import create_backup, restore_backup

BASE = {
    "synthetic_fixture": True,
    "legal_owner": "individual",
    "currency": "PKR",
    "account_ref": "SYNTHETIC-CONFIDENTIAL-ACCOUNT-902",
    "institution": "TEST-INSTITUTION-NOT-A-REAL-BANK",
    "source_ref": "SYNTHETIC-STATEMENT-SOURCE-0001",
    "period_start": "2024-06-29",
    "period_end": "2024-07-02",
    "opening_balance_minor": 25001234,
    "closing_balance_minor": 25003234,
    "rows": [
        {"row_number": 3, "posted_on": "2024-06-30", "description": "Synthetic salary credit",
         "reference": "SYN-FICTIONAL-CREDIT-1", "debit_minor": 0, "credit_minor": 4000,
         "balance_minor": 25005234},
        {"row_number": 7, "posted_on": "2024-07-01", "description": "Synthetic reviewed purchase",
         "reference": "SYN-FICTIONAL-DEBIT-2", "debit_minor": 2000, "credit_minor": 0,
         "balance_minor": 25003234},
    ],
}
URL = "/api/finance/confidential-bank/statements"


def _post(client, data=BASE):
    return client.post(URL, json=data)


def test_operational_source_is_aes_sealed_with_no_plain_economic_sql(client, tmp_path):
    result = _post(client)
    assert result.status_code == 201, result.text
    assert result.json()["row_count"] == 2
    assert result.json()["filing_ready"] is False
    with sqlite3.connect(tmp_path / "test.db") as db:
        fields = [c[1] for c in db.execute("PRAGMA table_info(confidential_bank_batches)")]
        assert fields == ["id", "owner_hmac", "account_hmac", "source_hmac", "payload_json", "created_at"]
        row = db.execute("SELECT owner_hmac,account_hmac,source_hmac,payload_json FROM confidential_bank_batches").fetchone()
        anchor = db.execute("SELECT verifier_hmac,sentinel FROM confidential_bank_key_state").fetchone()
        assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    assert all(len(row[i]) == 64 for i in range(3))
    assert row[3].startswith("TFLE1:") and anchor[1].startswith("TFLE1:")
    raw = "|".join(row + anchor)
    for sensitive in ("25001234", "25003234", "2024-06-30",
                      "SYNTHETIC-CONFIDENTIAL-ACCOUNT-902", "SYNTHETIC-STATEMENT-SOURCE-0001",
                      "TEST-INSTITUTION-NOT-A-REAL-BANK", "Synthetic salary credit",
                      "SYN-FICTIONAL-DEBIT-2"):
        assert sensitive not in raw
    assert result.json()["not_in_legacy_totals"]
    assert client.get("/api/summary?tax_year=2024").json()["record_count"] == 0
    assert client.get("/api/finance/private-events?tax_year=2024").json()["count"] == 0


def test_cross_year_source_retrieval_and_no_false_annual_totals(client):
    assert _post(client).status_code == 201
    for year in (2024, 2025):
        res = client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": year})
        assert res.status_code == 200, res.text
        obj = res.json()
        assert obj["source_count"] == 1
        assert obj["sources"][0]["reconciliation"] == "source_running_balances_verified"
        assert obj["annual_coverage_verified"] is False
        assert obj["income_or_tax_total"] is None
    response = client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2026})
    assert response.json()["source_count"] == 0


def test_exact_replay_conflict_and_independent_sources(client):
    assert _post(client).status_code == 201
    replay = _post(client)
    assert replay.status_code == 200 and replay.json()["already_recorded"]
    modified = {**BASE, "rows": [*BASE["rows"]]}
    modified["rows"][-1] = {**modified["rows"][-1], "description": "Changed synthetic expense"}
    assert _post(client, modified).status_code == 409
    separate = {**BASE, "source_ref": "SYNTHETIC-STATEMENT-SOURCE-0002"}
    assert _post(client, separate).status_code == 201
    assert client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2024}).json()["source_count"] == 2


def test_bad_balance_is_rejected_without_any_record(client, tmp_path):
    bad = {**BASE, "closing_balance_minor": BASE["closing_balance_minor"] + 1}
    response = _post(client, bad)
    assert response.status_code == 422, response.text
    assert client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2024}).json()["source_count"] == 0
    with sqlite3.connect(tmp_path / "test.db") as db:
        assert db.execute("SELECT COUNT(*) FROM confidential_bank_batches").fetchone()[0] == 0


@pytest.mark.parametrize("change", [
    {"synthetic_fixture": False}, {"legal_owner": "company"}, {"currency": "USD"},
    {"opening_balance_minor": True}, {"period_end": "2024-06-29"},
    {"period_start": "2022-06-01"}, {"source_ref": " short"}, {"source_ref": " A"},
    {"rows": []}, {"rows": BASE["rows"] * 251},
    {"rows": [{**BASE["rows"][0], "balance_minor": 25000000}, BASE["rows"][1]]},
    {"rows": [{**BASE["rows"][0], "debit_minor": 1}, BASE["rows"][1]]},
    {"rows": [BASE["rows"][1], BASE["rows"][0]]},
    {"rows": [BASE["rows"][0], {**BASE["rows"][1], "row_number": 3}]},
    {"rows": [{**BASE["rows"][0], "posted_on": "2025-08-01"}, BASE["rows"][1]]},
])
def test_strict_batch_validation_rejects_unsafe_or_unbalanced_input(client, change):
    res = _post(client, {**BASE, **change})
    assert res.status_code == 422, (change if "rows" not in change else "rows", res.text)


def test_wrong_index_key_never_silently_returns_zero(client, monkeypatch):
    assert _post(client).status_code == 201
    monkeypatch.setenv("CONFIDENTIAL_BANK_HMAC_KEY", base64.urlsafe_b64encode(b"Z" * 32).decode())
    res = client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2024})
    assert res.status_code == 503
    assert "unavailable" in res.text.lower()
    assert _post(client).status_code == 503


def test_confidential_index_key_independent_and_required(client, monkeypatch):
    assert _post(client).status_code == 201
    monkeypatch.delenv("CONFIDENTIAL_BANK_HMAC_KEY")
    assert client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2024}).status_code == 503
    monkeypatch.setenv("CONFIDENTIAL_BANK_HMAC_KEY", base64.urlsafe_b64encode(b"P"*32).decode())
    assert client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2024}).status_code == 503
    monkeypatch.setenv("CONFIDENTIAL_BANK_HMAC_KEY", base64.urlsafe_b64encode(b"S"*32).decode())
    assert _post(client).status_code == 503


def test_raw_index_tampering_is_detected(client, tmp_path):
    assert _post(client).status_code == 201
    with sqlite3.connect(tmp_path / "test.db") as db:
        db.execute("UPDATE confidential_bank_batches SET source_hmac=?",
                   ("0" * 64,))
        db.commit()
    result = client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2024})
    assert result.status_code == 409
    assert "mismatch" in result.text.lower()


def test_anchor_rejection_after_deletion_and_source_retention(client, tmp_path):
    assert _post(client).status_code == 201
    with sqlite3.connect(tmp_path / "test.db") as db:
        db.execute("DELETE FROM confidential_bank_key_state")
        db.commit()
    assert client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2024}).status_code == 503
    with sqlite3.connect(tmp_path / "test.db") as db:
        assert db.execute("SELECT COUNT(*) FROM confidential_bank_batches").fetchone()[0] == 1


def test_backup_restore_preserves_encrypted_operational_bank_and_key_anchor(client, tmp_path, monkeypatch):
    assert _post(client).status_code == 201
    monkeypatch.setenv("BACKUP_KEY", base64.urlsafe_b64encode(b"B" * 32).decode())
    blob = tmp_path / "snapshot.tfbk"
    created = create_backup(tmp_path / "test.db", tmp_path / "empty-vault", blob)
    assert created["encryption"] == "AES-256-GCM"
    assert b"25001234" not in blob.read_bytes()
    restored = restore_backup(blob, tmp_path / "fresh-restore")
    assert restored["sqlite_integrity_check"] == "ok"
    with TestClient(create_app(f"sqlite:///{tmp_path / 'fresh-restore' / 'finance.db'}")) as independent:
        independent.auth = ("owner", "local-test-password-123456")
        response = independent.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2025})
        assert response.status_code == 200, response.text
        assert response.json()["source_count"] == 1


def test_synthetic_only_and_auth_gate(client, monkeypatch, tmp_path):
    assert client.get(URL, params={"account_ref": BASE["account_ref"], "tax_year": 2024}, auth=None).status_code == 401
    assert _post(client, {**BASE, "synthetic_fixture": False}).status_code == 422
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(RuntimeError, match="Real-data"):
        create_app(f"sqlite:///{tmp_path / 'must-refuse.db'}")


def test_keyed_indexes_are_purpose_separated_and_plaintext_unavailable():
    values = [_blind(kind, "individual:SYNTHETIC-X") for kind in ("owner", "account", "source")]
    assert len(set(values)) == 3
    assert all(len(x) == 64 for x in values)


def test_migration_model_contains_no_unprotected_amount_date_or_bank_columns():
    engine = create_engine("sqlite://")
    from app.db import Base
    from app import models
    Base.metadata.create_all(engine)
    names = {c["name"] for c in inspect(engine).get_columns("confidential_bank_batches")}
    assert names == {"id","owner_hmac","account_hmac","source_hmac","payload_json","created_at"}
