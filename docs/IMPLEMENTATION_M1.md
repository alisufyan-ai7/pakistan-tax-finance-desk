# M1 implementation — local synthetic ledger vertical slice

Status: implemented in code; production financial-data acceptance **NOT** achieved.

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -e '.[dev]'
# Set OWNER_PASSWORD to unique >=16-character password in current shell. Do not commit it.
export OWNER_PASSWORD='CHOOSE_A_UNIQUE_RANDOM_PASSWORD_LONGER_THAN_16'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000, authenticate using username `owner` and your configured password, add account, then upload `samples/synthetic_bank_normalized.csv` with opening balance `50000.00`, date format `YYYY-MM-DD`, period July 1–31 2023.

No real financial files; the backing SQLite file is unencrypted. Docker/cloud/production deployment are **not** approved by this release. The service rejects non-loopback clients, uses Basic authentication only for local testing, and has no user signup.

## Import format and guarantees

Normalized headers: `date,description,debit,credit,balance,reference`; debit/credit exclusive; PKR minor units; chosen date format; rows sorted ascending; at most 4 MiB/5000 rows. CSV UTF-8 BOM supported, XLSX single-sheet supported. Original uploaded bytes are hashed in memory, not retained. Strong cross-document dedup requires balance or reference. Exact re-upload is idempotent. Weak overlap candidates remain in review. The first balance requires an owner-supplied opening balance to achieve stronger reconciliation. Imported amounts are **unreviewed**, not automatically taxable income.

The classification API can mark loan, donation, tax payment, cash withdrawal, investment purchase, personal expense, own transfer and more. It records an audit event on every correction. Tax Year 2023+ July–June periods are supported with explicitly incomplete coverage. **No FBR tax rates, tax due, capital gains or verified investment holdings yet.**

## Security and remaining gates before genuine records

1. Owner MFA, hardened session, TLS, CSRF protections and auth failure throttling.
2. Storage encryption with key lifecycle, PII/minimized logs, and encrypted private originals / backup-restore proof.
3. Structured PostgreSQL migrations, controlled deployment and production DB role segregation.
4. Bank-specific PDF parsers with synthetic fixtures and strict security sandboxing.
5. Full historical accounting for transfers, loans, legal-entity distinctions and cash; no unsupported deductions.
6. FBR year-specific rule citations/test vectors, independently validated withholding and wealth statement evidence.

## Check

```bash
cd backend && python -m pip install -e '.[dev]' && pytest -q
```

The tests cover authentication, exact duplicate, cross-document overlap, same-day same-amount distinct rows, running balance mismatch, FBR tax year windowing, classification, XLSX parsing and explicit refusal of unsupported PDF and malformed files.
