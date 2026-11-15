"""Synthetic, privacy-focused journal regression tests. No real user data."""
import base64
import sqlite3
import pytest

BASE = {
    "synthetic_fixture": True,
    "source_ref": "SYNTHETIC-EVENT-0001",
    "source_type": "synthetic_bank",
    "event_kind": "loan_advance",
    "posted_on": "2024-06-30",
    "amount_minor": 987654321,
    "account_ref": "SYNTHETIC-ACCOUNT-SECRET",
    "counterparty": "Synthetic private counterpart",
    "evidence_note": "Explicit synthetic unverified banking event",
}


def test_entire_event_is_ciphertext_with_blind_indexes(client, tmp_path):
    r = client.post("/api/finance/private-events", json=BASE)
    assert r.status_code == 201, r.text
    with sqlite3.connect(tmp_path / "test.db") as db:
        row = db.execute("SELECT owner_hmac,year_hmac,source_hmac,payload_json FROM private_financial_events").fetchone()
    assert all(len(row[i]) == 64 for i in range(3))
    assert row[3].startswith("TFLE1:")
    for secret in ("987654321", "2024-06-30", "SYNTHETIC-ACCOUNT-SECRET", "Synthetic private counterpart", "SYNTHETIC-EVENT-0001"):
        assert secret not in "|".join(row)
    view = client.get("/api/finance/private-events?tax_year=2024").json()
    assert view["count"] == 1 and view["events"][0]["amount_minor"] == 987654321
    assert view["tax_due_minor"] is None and view["fbr_ready"] is False


def test_year_boundaries_and_no_cross_year_results(client):
    assert client.post("/api/finance/private-events", json=BASE).status_code == 201
    later = {**BASE, "source_ref": "SYNTHETIC-EVENT-0002", "posted_on": "2024-07-01"}
    assert client.post("/api/finance/private-events", json=later).status_code == 201
    assert client.get("/api/finance/private-events?tax_year=2024").json()["count"] == 1
    assert client.get("/api/finance/private-events?tax_year=2025").json()["count"] == 1


def test_replay_and_conflicting_source_are_strict(client):
    assert client.post("/api/finance/private-events", json=BASE).status_code == 201
    old = client.post("/api/finance/private-events", json=BASE)
    assert old.status_code == 200 and old.json()["already_recorded"]
    change = client.post("/api/finance/private-events", json={**BASE, "amount_minor": 1})
    assert change.status_code == 409
    assert client.get("/api/finance/private-events?tax_year=2024").json()["count"] == 1


def test_identical_economics_different_source_are_distinct(client):
    assert client.post("/api/finance/private-events", json=BASE).status_code == 201
    assert client.post("/api/finance/private-events", json={**BASE, "source_ref": "SYNTHETIC-EVENT-0003"}).status_code == 201
    assert client.get("/api/finance/private-events?tax_year=2024").json()["count"] == 2


def test_invalid_financial_data_rejected(client):
    cases = [
        {"synthetic_fixture": False},
        {"legal_owner": "company"},
        {"currency": "USD"},
        {"posted_on": "2022-06-30"},
        {"amount_minor": -1},
        {"amount_minor": True},
        {"event_kind": "verified_tax_deduction"},
        {"source_ref": "  padded-reference"},
        {"evidence_note": "   "},
    ]
    for changed in cases:
        r = client.post("/api/finance/private-events", json={**BASE, **changed})
        assert r.status_code == 422, (changed, r.text)
    assert client.get("/api/finance/private-events?tax_year=2022").status_code == 422
    assert client.get("/api/finance/private-events?tax_year=2024&limit=0").status_code == 422


def test_event_journal_does_not_modify_legacy_tax_summary(client):
    assert client.post("/api/finance/private-events", json=BASE).status_code == 201
    result = client.get("/api/summary?tax_year=2024").json()
    assert result["tax_due"] is None and not result["fbr_ready"]
    assert result["record_count"] == 0


def test_dedicated_key_is_required_and_independent(monkeypatch):
    from app.private_events import blind_index, PrivateEventKeyError
    import os
    existing = os.environ["PRIVATE_EVENT_HMAC_KEY"]
    assert blind_index("source", "individual:SYNTHETIC-EVENT-0001") != blind_index("year", "individual:SYNTHETIC-EVENT-0001")
    monkeypatch.delenv("PRIVATE_EVENT_HMAC_KEY")
    with pytest.raises(PrivateEventKeyError):
        blind_index("source", "individual:SYNTHETIC-EVENT-0001")
    monkeypatch.setenv("PRIVATE_EVENT_HMAC_KEY", existing)


def test_reject_missing_index_key_at_app_start(monkeypatch, tmp_path):
    from app.main import create_app
    monkeypatch.delenv("PRIVATE_EVENT_HMAC_KEY")
    with pytest.raises(RuntimeError, match="private.*index|HMAC"):
        create_app(f"sqlite:///{tmp_path / 'missing-key.db'}")