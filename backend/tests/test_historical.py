"""Tests use strictly synthetic information: no FBR documents or personal data."""
import base64
import os
from pathlib import Path
import pytest
from cryptography.exceptions import InvalidTag
from app.evidence_vault import EncryptedEvidenceVault, VaultConfigurationError


def sample(year=2024, kind="wealth_statement", fields=None, **kwargs):
    return {"synthetic_fixture": True, "tax_year": year, "kind": kind,
            "filing_status": "filed_original",
            "fields": fields or {"opening_wealth_minor": 1000000, "closing_wealth_minor": 1450000},
            **kwargs}

@pytest.fixture
def vault_env(tmp_path, monkeypatch):
    key = base64.urlsafe_b64encode(bytes(range(32))).decode()
    directory = tmp_path / "encrypted-evidence"
    monkeypatch.setenv("DOCUMENT_VAULT_KEY", key)
    monkeypatch.setenv("DOCUMENT_VAULT_DIR", str(directory))
    return directory


def test_synthetic_years_file_and_encrypted_original(client, vault_env):
    payload = sample()
    response = client.post("/api/historical/synthetic-filings", json=payload)
    assert response.status_code == 201, response.text
    obj = response.json()
    assert obj["tax_year"] == 2024 and obj["revision_number"] == 0
    assert obj["not_fbr_verified"] is True
    recorded = list(vault_env.glob("*.evd"))
    assert len(recorded) == 1
    ciphertext = recorded[0].read_bytes()
    assert b"opening_wealth_minor" not in ciphertext
    vault = EncryptedEvidenceVault.from_environment()
    aad = f"historical:2024:wealth_statement:individual:{obj['id']}".encode()
    assert b'"synthetic_fixture":true' in vault.get(obj["id"], aad)
    assert client.get("/api/historical/filings?tax_year=2024").json()["filings"][0]["id"] == obj["id"]


def test_exact_replay_and_revision_lineage(client, vault_env):
    original = client.post("/api/historical/synthetic-filings", json=sample())
    assert original.status_code == 201
    replay = client.post("/api/historical/synthetic-filings", json=sample())
    assert replay.status_code == 200 and replay.json()["already_imported"] is True
    assert len(list(vault_env.glob("*.evd"))) == 1
    revised = sample(filing_status="filed_revision", revision_of_id=original.json()["id"],
                     fields={"opening_wealth_minor": 1000000, "closing_wealth_minor": 1700000})
    good = client.post("/api/historical/synthetic-filings", json=revised)
    assert good.status_code == 201 and good.json()["revision_number"] == 1
    again = sample(filing_status="filed_revision", revision_of_id=original.json()["id"],
                   fields={"closing_wealth_minor": 1800000})
    assert client.post("/api/historical/synthetic-filings", json=again).status_code == 409
    assert client.post("/api/historical/synthetic-filings", json=sample(fields={"closing_wealth_minor": 99})).status_code == 409
    assert len(client.get("/api/historical/filings?tax_year=2024").json()["filings"]) == 2


def test_invalid_synthetic_input_and_missing_vault_key(client, vault_env, monkeypatch):
    cases = [sample(year=2022), sample(kind="unsupported"),
             sample(synthetic_fixture=False), sample(fields={"made_up": 100}),
             sample(fields={"opening_wealth_minor": 1.01}),
             sample(fields={"opening_wealth_minor": True}),
             sample(filing_status="filed_revision"),
             sample(revision_of_id="not-a-uuid"),
             sample(legal_entity="company")]
    for obj in cases:
        result = client.post("/api/historical/synthetic-filings", json=obj)
        assert result.status_code == 422, (obj, result.text)
    monkeypatch.delenv("DOCUMENT_VAULT_KEY")
    assert client.post("/api/historical/synthetic-filings", json=sample()).status_code == 503
    assert client.get("/api/historical/filings?tax_year=2024").json()["filings"] == []


def test_cross_year_continuity_missing_is_not_zero(client, vault_env):
    missing = client.get("/api/historical/wealth-continuity?tax_year=2025").json()
    assert missing["status"] == "MISSING_EVIDENCE" and missing["difference_minor"] is None
    assert client.post("/api/historical/synthetic-filings", json=sample(year=2024,
        fields={"closing_wealth_minor": 1450000})).status_code == 201
    assert client.get("/api/historical/wealth-continuity?tax_year=2025").json()["status"] == "MISSING_EVIDENCE"
    assert client.post("/api/historical/synthetic-filings", json=sample(year=2025,
        fields={"opening_wealth_minor": 1500000})).status_code == 201
    diff = client.get("/api/historical/wealth-continuity?tax_year=2025").json()
    assert diff["status"] == "DISCREPANCY" and diff["difference_minor"] == 50000


def test_matching_and_explicit_zero_are_distinct(client, vault_env):
    assert client.post("/api/historical/synthetic-filings", json=sample(year=2023,
        fields={"closing_wealth_minor": 0})).status_code == 201
    assert client.post("/api/historical/synthetic-filings", json=sample(year=2024,
        fields={"opening_wealth_minor": 0})).status_code == 201
    match = client.get("/api/historical/wealth-continuity?tax_year=2024").json()
    assert match["status"] == "MATCH" and match["difference_minor"] == 0


def test_vault_tampering_and_wrong_aad_rejected(vault_env):
    vault = EncryptedEvidenceVault.from_environment()
    identifier = "a5e7c8d2-793a-40df-a341-d14168711111"
    vault.put(identifier, b"strictly synthetic", b"context")
    with pytest.raises(InvalidTag):
        vault.get(identifier, b"wrong context")
    p = Path(vault_env) / f"{identifier}.evd"
    data = bytearray(p.read_bytes()); data[-1] ^= 0x01; p.write_bytes(data)
    with pytest.raises(InvalidTag):
        vault.get(identifier, b"context")
    with pytest.raises(FileExistsError):
        vault.put(identifier, b"overwrite", b"context")
    with pytest.raises(ValueError):
        vault.put("../../path-traversal", b"payload", b"context")


def test_optimization_hints_never_claim_savings(client, account):
    from test_imports import csv_bytes, upload
    statement = csv_bytes([["2025-08-01", "Synthetic registered charity", "5000.00", "", "5000.00", "R-CHARITY"]])
    assert upload(client, account, statement, opening_balance="10000.00").status_code == 201
    rows = client.get("/api/transactions?tax_year=2026").json()["rows"]
    assert client.patch(f"/api/transactions/{rows[0]['id']}", json={"category": "donation", "note": "test review"}).status_code == 200
    response = client.get("/api/tax/opportunities?tax_year=2026")
    assert response.status_code == 200
    opportunity = response.json()["opportunities"][0]
    assert opportunity["status"] == "EVIDENCE_REQUIRED"
    assert opportunity["potential_tax_savings"] is None
    assert opportunity["legal_eligibility_verified"] is False
    assert client.get("/api/tax/opportunities?tax_year=2025").json()["opportunities"] == []
