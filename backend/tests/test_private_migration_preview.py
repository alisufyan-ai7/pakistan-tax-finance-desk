"""Review-only migration preflight; synthetic financial records exclusively."""
from test_imports import csv_bytes, upload


def make_reviewed(client, account):
    raw = csv_bytes([
        ["2024-06-30", "synthetic salary receipt", "", "200.00", "200.00", "P-01"],
        ["2024-07-01", "synthetic cash purchase", "30.00", "", "170.00", "P-02"],
    ])
    receipt = upload(client, account, raw)
    assert receipt.status_code == 201, receipt.text
    for year in (2024, 2025):
        for row in client.get(f"/api/transactions?tax_year={year}").json()["rows"]:
            kind = "salary" if row["credit"] == "200.00" else "personal_expense"
            result = client.patch(f"/api/transactions/{row['id']}", json={"category": kind, "note": "Reviewed original synthetic statement"})
            assert result.status_code == 200, result.text


def test_read_only_legacy_preflight_year_scopes(client, account):
    make_reviewed(client, account)
    v24 = client.get('/api/finance/private-events/migration-preview?tax_year=2024')
    v25 = client.get('/api/finance/private-events/migration-preview?tax_year=2025')
    assert v24.status_code == v25.status_code == 200
    assert v24.json()["status_counts"] == {"READY_FOR_EXPLICIT_MIGRATION": 1}
    assert v25.json()["status_counts"] == {"READY_FOR_EXPLICIT_MIGRATION": 1}
    assert v24.json()["read_only"] and not v24.json()["migration_performed"]
    assert client.get('/api/finance/private-events?tax_year=2024').json()["count"] == 0
    assert client.get('/api/finance/private-events?tax_year=2025').json()["count"] == 0


def test_pending_review_is_not_migratable(client, account):
    raw = csv_bytes([["2023-09-01", "synthetic unreviewed purchase", "20.00", "", "80.00", "UNR-01"]])
    assert upload(client, account, raw).status_code == 201
    view = client.get('/api/finance/private-events/migration-preview?tax_year=2024').json()
    assert view["status_counts"] == {"REVIEW_REQUIRED": 1}
    assert view["tax_due_minor"] is None


def test_detects_existing_matching_synthetic_mirror(client, account):
    make_reviewed(client, account)
    tx = client.get('/api/transactions?tax_year=2024').json()['rows'][0]
    mirror = {
        "synthetic_fixture": True,
        "source_ref": f"legacy-m1:{tx['id']}",
        "source_type": "synthetic_bank", "event_kind": "income",
        "posted_on": "2024-06-30", "amount_minor": 20000,
        "account_ref": account,
        "counterparty": None,
        "evidence_note": "Explicit synthetic M1 reviewed ledger source for migration preview",
        "direction": "credit",
    }
    assert client.post('/api/finance/private-events', json=mirror).status_code == 201
    view = client.get('/api/finance/private-events/migration-preview?tax_year=2024').json()
    assert view["status_counts"] == {"ALREADY_MIRRORED_UNVERIFIED": 1}
    # The old ledger is still the only source of business summary, never double counted.
    assert client.get('/api/summary?tax_year=2024').json()["record_count"] == 1


def test_detects_conflicting_existing_source(client, account):
    make_reviewed(client, account)
    tx = client.get('/api/transactions?tax_year=2024').json()['rows'][0]
    changed = {
        "synthetic_fixture": True, "source_ref": f"legacy-m1:{tx['id']}",
        "source_type": "synthetic_bank", "event_kind": "income",
        "posted_on": "2024-06-30", "amount_minor": 12345,
        "account_ref": account, "direction": "credit",
        "evidence_note": "Different synthetic value, not matched to bank",
    }
    assert client.post('/api/finance/private-events', json=changed).status_code == 201
    view = client.get('/api/finance/private-events/migration-preview?tax_year=2024').json()
    assert view["status_counts"] == {"SOURCE_CONTENT_CONFLICT": 1}


def test_preview_requires_auth(client):
    assert client.get('/api/finance/private-events/migration-preview?tax_year=2024', auth=None).status_code == 401
    assert client.get('/api/finance/private-events/migration-preview?tax_year=2022').status_code == 422
    assert client.get('/api/finance/private-events/migration-preview?tax_year=2024&limit=0').status_code == 422