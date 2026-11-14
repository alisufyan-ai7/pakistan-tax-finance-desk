from __future__ import annotations
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def utcnow():
    return datetime.now(timezone.utc)

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    institution: Mapped[str] = mapped_column(String(80), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="PKR", nullable=False)
    legal_owner: Mapped[str] = mapped_column(String(32), default="individual", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("account_id", "sha256", name="uq_document_content_per_account"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_format: Mapped[str] = mapped_column(String(8), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(24), nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    coverage_declared: Mapped[bool] = mapped_column(Boolean, default=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "fingerprint", name="uq_account_fingerprint"),
        UniqueConstraint("document_id", "row_number", name="uq_document_row"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    posted_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    debit_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance_minor: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(48), default="unreviewed", nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    overlap_possible: Mapped[bool] = mapped_column(Boolean, default=False)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    overlap_resolved: Mapped[bool] = mapped_column(Boolean, default=False)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    old_category: Mapped[str] = mapped_column(String(48), nullable=False)
    new_category: Mapped[str] = mapped_column(String(48), nullable=False)
    old_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    old_overlap_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_overlap_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class HistoricalFiling(Base):
    """Immutable synthetic-only historic filed-return metadata / normalized test values.

    No original taxpayer document may enter this model until the full private
    ingestion/MFA/Postgres/key-management/backup security gate is certified.
    """
    __tablename__ = "historical_filings"
    __table_args__ = (
        UniqueConstraint("tax_year", "kind", "source_sha256", name="uq_historical_filing_digest"),
        UniqueConstraint("tax_year", "kind", "revision_number", name="uq_historical_filing_revision"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    legal_entity: Mapped[str] = mapped_column(String(32), default="individual", nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    filing_status: Mapped[str] = mapped_column(String(24), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_of_id: Mapped[str | None] = mapped_column(ForeignKey("historical_filings.id"), nullable=True)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # ONLY synthetic numerical fixtures in this stage; no actual filed figures or identifiers.
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
