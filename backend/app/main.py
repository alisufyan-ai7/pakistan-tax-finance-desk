"""Local-only first milestone: private synthetic import and a reconciled review ledger.

No real documents until MFA, encryption at rest and backup/restore are certified.
"""
from datetime import date
from hashlib import sha256
from decimal import Decimal
from pathlib import Path
import os
import secrets
import uuid
from typing import Annotated
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy import and_, select, func
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .db import Base, build_engine, session_factory
from .models import Account, Document, Transaction, AuditEvent, HistoricalFiling
from .historical import SyntheticFilingInput, register_filing, _as_public, wealth_continuity
from .evidence_vault import EncryptedEvidenceVault, VaultConfigurationError
from .importer import ImportErrorDetail, MAX_BYTES, PARSER_VERSION, fingerprint, fingerprint_base, parse_statement
from .bank_profiles import normalize_synthetic_csv, PROFILES

CREDIT = {"salary", "business_income", "investment_income", "rental_income", "other_income", "loan_received", "loan_repayment_received", "gift_received", "refund", "own_transfer"}
DEBIT = {"personal_expense", "business_expense", "donation", "zakat", "investment_purchase", "loan_given", "debt_principal_paid", "tax_paid", "atm_cash", "own_transfer", "other_outflow"}
CATEGORIES = {"unreviewed"} | CREDIT | DEBIT
security = HTTPBasic(auto_error=False)

class AccountInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    institution: str = Field(min_length=1, max_length=80)
    currency: str = "PKR"
    legal_owner: str = "individual"

class ClassificationInput(BaseModel):
    category: str
    excluded: bool = False
    confirm_unique: bool = False
    note: str = Field(default="", max_length=500)

def cash(minor: int | None):
    return None if minor is None else f"{Decimal(minor) / Decimal(100):.2f}"

def as_transaction(tx: Transaction):
    return {"id": tx.id, "date": tx.posted_on.isoformat(), "description": tx.description,
            "debit": cash(tx.debit_minor), "credit": cash(tx.credit_minor), "balance": cash(tx.balance_minor),
            "category": tx.category, "reviewed": tx.reviewed, "overlap_possible": tx.overlap_possible,
            "excluded": tx.excluded, "overlap_resolved": tx.overlap_resolved, "account_id": tx.account_id, "source_row": tx.row_number}

def create_app(database_url: str | None = None):
    app = FastAPI(title="Pakistan Tax & Wealth Desk — synthetic local demo", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    engine = build_engine(database_url)
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise RuntimeError("Real-data mode is not implemented; refusing to run")
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)  # Legacy local synthetic demo convenience only.
    else:
        # PostgreSQL requires explicit Alembic migration: never silently mutate production schema.
        from sqlalchemy import inspect
        with engine.connect() as connection:
            if not inspect(connection).has_table("alembic_version") or connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one_or_none() != "0001_initial":
                raise RuntimeError("Database must be upgraded with Alembic before starting")
    sessions = session_factory(engine)

    def authenticate(request: Request, credentials: Annotated[HTTPBasicCredentials | None, Depends(security)]):
        password = os.getenv("OWNER_PASSWORD", "")
        user = os.getenv("OWNER_USERNAME", "owner")
        if not password or len(password) < 16:
            raise HTTPException(status_code=503, detail="Configure OWNER_PASSWORD with 16+ characters")
        # Fail closed even if someone binds the service beyond loopback.
        if not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            raise HTTPException(status_code=403, detail="Local-only development service")
        if not credentials or not (secrets.compare_digest(credentials.username.encode(), user.encode()) and secrets.compare_digest(credentials.password.encode(), password.encode())):
            raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": 'Basic realm="Private finance desk"'})

    def db_session():
        with sessions() as db:
            yield db

    def _configured_vault():
        try:
            return EncryptedEvidenceVault.from_environment()
        except VaultConfigurationError as exc:
            raise HTTPException(503, str(exc)) from None

    Auth = Annotated[None, Depends(authenticate)]
    DB = Annotated[Session, Depends(db_session)]

    @app.get("/", include_in_schema=False)
    def homepage(_: Auth):
        return FileResponse(Path(__file__).resolve().parents[2] / "frontend" / "index.html", media_type="text/html", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'", "Referrer-Policy": "no-referrer"})

    @app.get("/api/health")
    def health(_: Auth):
        return {"status": "ok", "data_safety": "synthetic_only", "tax_engine": "not_implemented"}

    @app.post("/api/accounts", status_code=201)
    def add_account(request: AccountInput, _: Auth, db: DB):
        if request.currency != "PKR" or request.legal_owner != "individual":
            raise HTTPException(422, "MVP supports only individual-owned PKR accounts; never merge legal entities")
        acc = Account(id=str(uuid.uuid4()), name=request.name.strip(), institution=request.institution.strip(), currency="PKR", legal_owner="individual")
        if not acc.name or not acc.institution:
            raise HTTPException(422, "Name and institution required")
        db.add(acc)
        db.commit()
        return {"id": acc.id, "name": acc.name, "institution": acc.institution, "currency": acc.currency}

    @app.get("/api/accounts")
    def list_accounts(_: Auth, db: DB):
        return [{"id": a.id, "name": a.name, "institution": a.institution, "currency": a.currency} for a in db.scalars(select(Account).order_by(Account.name)).all()]

    @app.post("/api/statements", status_code=201)
    async def import_statement(_: Auth, db: DB, account_id: Annotated[str, Form()], file: Annotated[UploadFile, File()],
                               date_format: Annotated[str, Form()] = "%Y-%m-%d", opening_balance: Annotated[str | None, Form()] = None,
                               profile: Annotated[str, Form()] = "normalized",
                               period_start: Annotated[date | None, Form()] = None, period_end: Annotated[date | None, Form()] = None):
        account = db.get(Account, account_id)
        if not account:
            raise HTTPException(404, "Unknown account")
        ext = Path(file.filename or "").suffix.lower()
        if ext not in {".csv", ".xlsx"}:
            raise HTTPException(415, "Only normalized CSV and XLSX supported; bank-specific PDF parsers are not ready")
        raw = await file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise HTTPException(413, "Maximum file size is 4 MiB")
        digest = sha256(raw).hexdigest()
        prior_document = db.scalar(select(Document).where(Document.account_id == account_id, Document.sha256 == digest))
        if prior_document:
            previously_accepted = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.document_id == prior_document.id))
            return JSONResponse(status_code=200, content={"file_duplicate": True, "accepted": 0, "duplicate_rows": previously_accepted, "potential_overlaps": 0,
                    "document_id": prior_document.id, "reconciliation": "already_imported", "warnings": ["Exact file already imported; economic ledger unchanged"]})
        try:
            normalized, profile_date_format = normalize_synthetic_csv(raw, profile, ext)
            rows, reconciliation, warnings = parse_statement(normalized, ext, profile_date_format or date_format, opening_balance)
        except ImportErrorDetail as error:
            raise HTTPException(422, detail=str(error)) from None
        if bool(period_start) != bool(period_end):
            raise HTTPException(422, "Supply both statement period dates or neither")
        if period_start and (period_start > rows[0].posted_on or period_end < rows[-1].posted_on or period_start > period_end):
            raise HTTPException(422, "Declared statement period must cover every imported transaction")
        doc = Document(id=str(uuid.uuid4()), account_id=account_id, sha256=digest, file_format=ext,
                       parser_version=PARSER_VERSION if profile == "normalized" else f"{PARSER_VERSION}:{profile}", period_start=period_start or rows[0].posted_on,
                       period_end=period_end or rows[-1].posted_on, coverage_declared=bool(period_start))
        db.add(doc)
        accepted = duplicated = overlap = 0
        occurrences: dict[str, int] = {}
        for row in rows:
            base = fingerprint_base(row)
            occurrences[base] = occurrences.get(base, 0) + 1
            fp = fingerprint(account_id, row, digest, occurrences[base])
            existing = db.scalar(select(Transaction.id).where(Transaction.account_id == account_id, Transaction.fingerprint == fp))
            if existing:
                duplicated += 1
                continue
            weak = row.balance_minor is None and not row.reference
            possible = False
            if weak:
                possible = db.scalar(select(Transaction.id).where(and_(Transaction.account_id == account_id, Transaction.document_id != doc.id,
                    Transaction.posted_on == row.posted_on, Transaction.debit_minor == row.debit_minor,
                    Transaction.credit_minor == row.credit_minor, Transaction.description == row.description)).limit(1)) is not None
            overlap += int(possible)
            db.add(Transaction(id=str(uuid.uuid4()), account_id=account_id, document_id=doc.id,
                row_number=row.row_number, fingerprint=fp, posted_on=row.posted_on, description=row.description,
                reference=row.reference, debit_minor=row.debit_minor, credit_minor=row.credit_minor,
                balance_minor=row.balance_minor, category="unreviewed", overlap_possible=possible))
            accepted += 1
        if overlap:
            warnings.append(f"{overlap} potential cross-document overlaps require explicit review before totals are trusted")
        db.commit()
        return {"file_duplicate": False, "document_id": doc.id, "accepted": accepted,
                "duplicate_rows": duplicated, "potential_overlaps": overlap, "reconciliation": reconciliation,
                "coverage_declared": doc.coverage_declared, "first_date": rows[0].posted_on.isoformat(),
                "last_date": rows[-1].posted_on.isoformat(), "warnings": warnings}

    @app.post("/api/historical/synthetic-filings", status_code=201)
    def add_synthetic_filing(payload: SyntheticFilingInput, _: Auth, db: DB):
        """Synthetic fixtures ONLY. Real historical FBR documents are not supported."""
        try:
            vault = EncryptedEvidenceVault.from_environment()
        except VaultConfigurationError as exc:
            raise HTTPException(503, str(exc)) from None
        created, duplicate = register_filing(db, payload, vault)
        if duplicate:
            return JSONResponse(status_code=200, content={**created, "already_imported": True})
        return {**created, "already_imported": False}

    @app.get("/api/historical/filings")
    def list_synthetic_filings(_: Auth, db: DB, tax_year: int = 2027):
        fiscal_bounds(tax_year)
        filings = db.scalars(select(HistoricalFiling).where(
            HistoricalFiling.tax_year == tax_year
        ).order_by(HistoricalFiling.kind, HistoricalFiling.revision_number)).all()
        return {"tax_year": tax_year, "synthetic_only": True,
                "filings": [_as_public(x, _configured_vault()) for x in filings],
                "note": "Synthetic normalized fixtures, not verified or ingested FBR documents"}

    @app.get("/api/historical/wealth-continuity")
    def year_wealth_continuity(_: Auth, db: DB, tax_year: int = 2027):
        fiscal_bounds(tax_year)
        return wealth_continuity(db, tax_year, _configured_vault())

    @app.get("/api/tax/opportunities")
    def tax_opportunity_candidates(_: Auth, db: DB, tax_year: int = 2027):
        """Evidence requests only; no legal eligibility or tax saving is asserted."""
        start, end = fiscal_bounds(tax_year)
        rows = db.scalars(select(Transaction).where(Transaction.posted_on.between(start, end))).all()
        hints = {
            "donation": ("charitable_credit_review", "Recipient eligibility, donation receipt, relevant year provisions"),
            "zakat": ("zakat_treatment_review", "Zakat evidence and correct statutory tax-year treatment"),
            "business_expense": ("business_deduction_review", "Business-purpose support, allowable expense rules, legal entity"),
            "tax_paid": ("withholding_or_advance_tax_review", "Payment type, CPR/withholding certificate, final vs adjustable treatment"),
        }
        output = []
        for category, (type_name, required) in hints.items():
            matched = [t for t in rows if t.category == category and t.reviewed and
                       not t.excluded and (not t.overlap_possible or t.overlap_resolved)]
            if matched:
                output.append({"tax_year": tax_year, "opportunity_type": type_name,
                               "status": "EVIDENCE_REQUIRED", "evidence_needed": required,
                               "supporting_transaction_ids": [t.id for t in matched],
                               "candidate_recorded_amount": cash(sum(t.debit_minor + t.credit_minor for t in matched)),
                               "potential_tax_savings": None, "legal_eligibility_verified": False,
                               "requires_review": True, "not_filing_advice": True})
        return {"tax_year": tax_year, "opportunities": output,
                "note": "Heuristic candidates only. No tax laws verified or tax benefit established."}

    @app.get("/api/transactions")
    def list_transactions(_: Auth, db: DB, tax_year: int = 2027, limit: int = 200):
        start, end = fiscal_bounds(tax_year)
        if not (1 <= limit <= 500):
            raise HTTPException(422, "limit out of range")
        rows = db.scalars(select(Transaction).where(Transaction.posted_on.between(start, end)).order_by(Transaction.posted_on.desc(), Transaction.id).limit(limit)).all()
        return {"tax_year": tax_year, "rows": [as_transaction(x) for x in rows], "limit": limit,
                "note": "All amounts are factual imports, not certified income-tax figures"}

    @app.patch("/api/transactions/{transaction_id}")
    def set_classification(transaction_id: str, payload: ClassificationInput, _: Auth, db: DB):
        tx = db.get(Transaction, transaction_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")
        if payload.category not in CATEGORIES:
            raise HTTPException(422, "Unknown category")
        allowed = CREDIT if tx.credit_minor else DEBIT
        if payload.category not in allowed and payload.category != "unreviewed":
            raise HTTPException(422, "Category is incompatible with transaction direction")
        if (payload.excluded or payload.confirm_unique) and not payload.note.strip():
            raise HTTPException(422, "A reason is mandatory before excluding or resolving a transaction")
        if payload.confirm_unique and not tx.overlap_possible:
            raise HTTPException(422, "This transaction has no ambiguous overlap to resolve")
        if payload.confirm_unique and payload.excluded:
            raise HTTPException(422, "Cannot both exclude and confirm a transaction is unique")
        db.add(AuditEvent(id=str(uuid.uuid4()), transaction_id=tx.id, old_category=tx.category,
                          new_category=payload.category, old_excluded=tx.excluded,
                          new_excluded=payload.excluded, old_overlap_resolved=tx.overlap_resolved,
                          new_overlap_resolved=payload.confirm_unique or (tx.overlap_resolved and not payload.excluded),
                          note=payload.note.strip()))
        tx.category = payload.category
        tx.reviewed = payload.category != "unreviewed" or payload.excluded
        tx.excluded = payload.excluded
        tx.overlap_resolved = payload.confirm_unique or (tx.overlap_resolved and not payload.excluded)
        db.commit()
        return as_transaction(tx)

    @app.get("/api/summary")
    def year_summary(_: Auth, db: DB, tax_year: int = 2027):
        start, end = fiscal_bounds(tax_year)
        rows = db.scalars(select(Transaction).where(Transaction.posted_on.between(start, end))).all()
        totals: dict[str, int] = {}
        unreviewed_in = unreviewed_out = review_overlap = 0
        for tx in rows:
            if tx.excluded:
                continue
            if tx.category == "unreviewed" or not tx.reviewed or (tx.overlap_possible and not tx.overlap_resolved):
                unreviewed_in += tx.credit_minor
                unreviewed_out += tx.debit_minor
                review_overlap += int(tx.overlap_possible and not tx.overlap_resolved)
            else:
                totals[tx.category] = totals.get(tx.category, 0) + tx.credit_minor + tx.debit_minor
        start_iso, end_iso = start.isoformat(), end.isoformat()
        return {"tax_year": tax_year, "period_start": start_iso, "period_end": end_iso,
                "record_count": len(rows), "classified_totals": {k: cash(v) for k, v in sorted(totals.items())},
                "unreviewed_inflows": cash(unreviewed_in), "unreviewed_outflows": cash(unreviewed_out),
                "possible_overlaps_pending": review_overlap,
                "tax_due": None, "projected_annual_tax": None, "fbr_ready": False,
                "reason": "FBR year-specific rules and withholding evidence have not been verified; no tax estimate is available"}

    @app.get("/api/coverage")
    def coverage(_: Auth, db: DB, tax_year: int = 2027):
        start, end = fiscal_bounds(tax_year)
        docs = db.scalars(select(Document).where(Document.period_end >= start, Document.period_start <= end)).all()
        accounts = db.scalars(select(Account)).all()
        report = []
        for acc in accounts:
            account_docs = [d for d in docs if d.account_id == acc.id]
            months = []
            for i in range(12):
                year = start.year + (start.month - 1 + i) // 12
                month = (start.month - 1 + i) % 12 + 1
                mstart = date(year, month, 1)
                mend = date(year + (month == 12), (month % 12) + 1, 1)
                relevant = [d for d in account_docs if d.period_start < mend and d.period_end >= mstart]
                months.append({"month": mstart.isoformat()[:7], "status": "observed" if relevant else "missing",
                               "declared_source_period": any(d.coverage_declared for d in relevant)})
            report.append({"account_id": acc.id, "name": acc.name, "months": months})
        return {"tax_year": tax_year, "accounts": report,
                "warning": "Observed months are not necessarily fully covered; missing statements may materially change totals"}

    return app

def fiscal_bounds(tax_year: int):
    if not 2023 <= tax_year <= 2100:
        raise HTTPException(422, "Supported tax year starts at 2023")
    return date(tax_year - 1, 7, 1), date(tax_year, 6, 30)

app = create_app()
