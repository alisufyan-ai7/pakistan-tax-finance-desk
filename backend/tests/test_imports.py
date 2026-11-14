from io import BytesIO
import csv
from openpyxl import Workbook

def csv_bytes(rows):
    import io
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow(["date", "description", "debit", "credit", "balance", "reference"])
    w.writerows(rows)
    return f.getvalue().encode()

def upload(client, account, raw, suffix="csv", **kwargs):
    return client.post("/api/statements", data={"account_id": account, **kwargs},
         files={"file": ("synthetic." + suffix, raw, "text/csv" if suffix == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})

def test_authorization_and_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/accounts", auth=None).status_code == 401
    assert client.get("/api/health", auth=("owner", "wrong")).status_code == 401
    assert client.get("/api/health").json()["data_safety"] == "synthetic_only"

def test_upload_idempotent_and_years(client, account):
    raw = csv_bytes([
        ["2023-10-01", "salary October", "", "125000.00", "225000.00", "S-1"],
        ["2023-10-04", "groceries", "5000.00", "", "220000.00", "P-1"],
    ])
    first = upload(client, account, raw, opening_balance="100000.00", period_start="2023-10-01", period_end="2023-10-31")
    assert first.status_code == 201, first.text
    assert first.json()["reconciliation"] == "opening_and_running_verified"
    again = upload(client, account, raw)
    assert again.status_code == 200 and again.json()["file_duplicate"] is True
    tx = client.get("/api/transactions?tax_year=2024").json()["rows"]
    assert len(tx) == 2
    assert len(client.get("/api/transactions?tax_year=2027").json()["rows"]) == 0
    summary = client.get("/api/summary?tax_year=2024").json()
    assert summary["unreviewed_inflows"] == "125000.00"
    assert summary["unreviewed_outflows"] == "5000.00"
    assert summary["tax_due"] is None
    coverage = client.get("/api/coverage?tax_year=2024").json()["accounts"][0]["months"]
    assert next(x for x in coverage if x["month"] == "2023-10")["status"] == "observed"
    assert next(x for x in coverage if x["month"] == "2023-11")["status"] == "missing"

def test_overlapping_ref_transaction_is_deduped(client, account):
    a = csv_bytes([["2024-01-01", "salary", "", "200.00", "1200.00", "unique-ref"]])
    b = csv_bytes([["2024-01-01", "salary", "", "200.00", "1200.00", "unique-ref"],
                   ["2024-01-02", "purchase", "100.00", "", "1100.00", "unique-2"]])
    assert upload(client, account, a).json()["accepted"] == 1
    result = upload(client, account, b).json()
    assert result["accepted"] == 1 and result["duplicate_rows"] == 1
    assert len(client.get("/api/transactions?tax_year=2024").json()["rows"]) == 2

def test_same_day_same_amount_without_reference_preserved(client, account):
    raw = csv_bytes([["2024-04-01", "tea", "150.00", "", "", ""],
                     ["2024-04-01", "tea", "150.00", "", "", ""]])
    assert upload(client, account, raw).json()["accepted"] == 2
    other = csv_bytes([["2024-04-01", "tea", "150.00", "", "", ""],
                       ["2024-04-02", "market", "50.00", "", "", ""]])
    receipt = upload(client, account, other).json()
    assert receipt["potential_overlaps"] == 1
    assert len(client.get("/api/transactions?tax_year=2024").json()["rows"]) == 4
    assert client.get("/api/summary?tax_year=2024").json()["possible_overlaps_pending"] == 1

def test_balance_mismatch_fails_without_partial_records(client, account):
    raw = csv_bytes([["2025-08-01", "deposit", "", "100.00", "100.00", "r1"],
                     ["2025-08-02", "withdrawal", "50.00", "", "99.00", "r2"]])
    response = upload(client, account, raw)
    assert response.status_code == 422 and "mismatch" in response.text
    assert client.get("/api/summary?tax_year=2026").json()["record_count"] == 0

def test_classification_audit_and_non_income_loan(client, account):
    raw = csv_bytes([["2026-07-01", "loan from friend", "", "50000.00", "50000.00", "L1"],
                     ["2026-07-02", "charity", "2000.00", "", "48000.00", "C1"]])
    assert upload(client, account, raw).status_code == 201
    txs = client.get("/api/transactions?tax_year=2027").json()["rows"]
    loan = next(t for t in txs if t["credit"] == "50000.00")
    charity = next(t for t in txs if t["debit"] == "2000.00")
    assert client.patch(f"/api/transactions/{loan['id']}", json={"category": "personal_expense"}).status_code == 422
    assert client.patch(f"/api/transactions/{loan['id']}", json={"category": "loan_received"}).status_code == 200
    assert client.patch(f"/api/transactions/{charity['id']}", json={"category": "donation"}).status_code == 200
    summary = client.get("/api/summary?tax_year=2027").json()
    assert summary["classified_totals"] == {"donation": "2000.00", "loan_received": "50000.00"}
    assert summary["tax_due"] is None

def test_xlsx_support_and_reject_pdf(client, account):
    wb = Workbook()
    ws = wb.active
    ws.append(["date", "description", "debit", "credit", "balance", "reference"])
    ws.append(["2024-01-01", "synthetic salary", "", "1000.00", "1000.00", "x1"])
    content = BytesIO()
    wb.save(content)
    assert upload(client, account, content.getvalue(), "xlsx").status_code == 201
    assert upload(client, account, b"%PDF-1.7", "pdf").status_code == 415

def test_malformed_and_unsafe_input(client, account):
    assert upload(client, account, b"date,description,debit,credit\n01/02/2025,one,,5\n").status_code == 422
    assert upload(client, account, b"date,description,debit,credit\n2025-01-01,one,=2+2,\n").status_code == 422
    assert upload(client, account, b"date,description,debit,credit\n2025-01-01,one,0.001,\n").status_code == 422
    assert upload(client, account, b"date,description,debit,credit\n2025-01-01,one,,5\n", period_start="2025-01-02", period_end="2025-01-31").status_code == 422


def test_reference_dedup_across_bank_export_variants(client, account):
    with_balance = csv_bytes([["2026-01-03", "synthetic deposit", "", "100.00", "100.00", "R-BOTH"]])
    without_balance = csv_bytes([["2026-01-03", "synthetic deposit", "", "100.00", "", "R-BOTH"]])
    assert upload(client, account, with_balance).json()["accepted"] == 1
    result = upload(client, account, without_balance).json()
    assert result["accepted"] == 0 and result["duplicate_rows"] == 1


def test_weak_overlap_must_be_explicitly_resolved(client, account):
    assert upload(client, account, csv_bytes([["2025-10-01", "same weak item", "40", "", "", ""]])).status_code == 201
    response = upload(client, account, csv_bytes([["2025-10-01", "same weak item", "40", "", "", ""],
                                                   ["2025-10-02", "new item", "10", "", "", ""]]))
    assert response.json()["potential_overlaps"] == 1
    rows = client.get("/api/transactions?tax_year=2026").json()["rows"]
    weak = next(x for x in rows if x["overlap_possible"])
    assert client.patch(f"/api/transactions/{weak['id']}", json={"category": "personal_expense", "confirm_unique": True}).status_code == 422
    ok = client.patch(f"/api/transactions/{weak['id']}", json={"category": "personal_expense", "confirm_unique": True, "note": "Two independent purchases verified"})
    assert ok.status_code == 200, ok.text
    summary = client.get("/api/summary?tax_year=2026").json()
    assert summary["classified_totals"]["personal_expense"] == "40.00"
    assert summary["possible_overlaps_pending"] == 0


def test_fails_closed_without_configured_owner_password(tmp_path, monkeypatch):
    from app.main import create_app
    from fastapi.testclient import TestClient
    monkeypatch.delenv("OWNER_PASSWORD", raising=False)
    with TestClient(create_app(f"sqlite:///{tmp_path / 'blank.db'}")) as c:
        assert c.get("/api/health").status_code == 503
