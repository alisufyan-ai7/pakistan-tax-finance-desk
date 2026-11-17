from __future__ import annotations
from datetime import date, datetime, timezone
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
from .ledger_crypto import EncryptedText

def utcnow():
    return datetime.now(timezone.utc)

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(EncryptedText("accounts.name"), nullable=False)
    institution: Mapped[str] = mapped_column(EncryptedText("accounts.institution"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="PKR", nullable=False)
    legal_owner: Mapped[str] = mapped_column(String(32), default="individual", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("account_id", "sha256", name="uq_document_content_per_account"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    digest_scheme: Mapped[str] = mapped_column(String(24), nullable=False, default='hmac_sha256_v1', server_default='legacy_sha256')
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
    description: Mapped[str] = mapped_column(EncryptedText("transactions.description"), nullable=False)
    reference: Mapped[str | None] = mapped_column(EncryptedText("transactions.reference"))
    debit_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance_minor: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(EncryptedText("transactions.category"), default="unreviewed", nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    overlap_possible: Mapped[bool] = mapped_column(Boolean, default=False)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    overlap_resolved: Mapped[bool] = mapped_column(Boolean, default=False)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    old_category: Mapped[str] = mapped_column(EncryptedText("audit_events.old_category"), nullable=False)
    new_category: Mapped[str] = mapped_column(EncryptedText("audit_events.new_category"), nullable=False)
    old_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    old_overlap_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_overlap_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[str] = mapped_column(EncryptedText("audit_events.note"), default="", nullable=False)
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

class OwnerAuthState(Base):
    """Replay-protected RFC6238 counter for the single synthetic owner."""
    __tablename__ = "owner_auth_state"
    owner_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_totp_step: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)

class OwnerSession(Base):
    """Hashed session token only; never store the HttpOnly cookie itself."""
    __tablename__ = "owner_sessions"
    token_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    csrf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class LoanAccount(Base):
    """Owner-declared synthetic opening balance, not independently verified."""
    __tablename__ = "loan_accounts"
    __table_args__ = (CheckConstraint("opening_principal_minor >= 0", name="ck_loan_opening_nonnegative"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    legal_owner: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    direction: Mapped[str] = mapped_column(String(12), nullable=False)
    counterparty_label: Mapped[str] = mapped_column(EncryptedText("loan_accounts.counterparty_label"), nullable=False)
    opening_as_of: Mapped[date] = mapped_column(Date, nullable=False)
    opening_principal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    opening_basis: Mapped[str] = mapped_column(EncryptedText("loan_accounts.opening_basis"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LoanAllocation(Base):
    """Append-only, bank-transaction-backed disbursement or principal/markup split."""
    __tablename__ = "loan_allocations"
    __table_args__ = (
        Index("uq_active_loan_allocation_transaction", "transaction_id", unique=True, postgresql_where=text("active IS TRUE"), sqlite_where=text("active = 1")),
        CheckConstraint("principal_minor >= 0", name="ck_loan_principal_nonnegative"),
        CheckConstraint("markup_minor >= 0", name="ck_loan_markup_nonnegative"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loan_accounts.id"), index=True, nullable=False)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    event_kind: Mapped[str] = mapped_column(String(12), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    principal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    markup_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    evidence_note: Mapped[str] = mapped_column(EncryptedText("loan_allocations.evidence_note"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TransferConfirmation(Base):
    """Immutable owner-confirmed linkage, never a certified legal/tax conclusion."""
    __tablename__ = "transfer_confirmations"
    __table_args__ = (
        Index("uq_active_transfer_debit", "debit_transaction_id", unique=True, postgresql_where=text("active IS TRUE"), sqlite_where=text("active = 1")),
        Index("uq_active_transfer_credit", "credit_transaction_id", unique=True, postgresql_where=text("active IS TRUE"), sqlite_where=text("active = 1")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    debit_transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    credit_transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    evidence_note: Mapped[str] = mapped_column(EncryptedText("transfer_confirmations.evidence_note"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class LoanAllocationReversal(Base):
    """Append-only reason for invalidating a synthetic allocation; source preserved."""
    __tablename__ = "loan_allocation_reversals"
    __table_args__ = (UniqueConstraint("allocation_id", name="uq_loan_allocation_reversal"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    allocation_id: Mapped[str] = mapped_column(ForeignKey("loan_allocations.id"), nullable=False)
    reason: Mapped[str] = mapped_column(EncryptedText("loan_allocation_reversals.reason"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TransferRevocation(Base):
    """Append-only reason for revoking an owner-confirmed synthetic transfer."""
    __tablename__ = "transfer_revocations"
    __table_args__ = (UniqueConstraint("confirmation_id", name="uq_transfer_revocation"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    confirmation_id: Mapped[str] = mapped_column(ForeignKey("transfer_confirmations.id"), nullable=False)
    reason: Mapped[str] = mapped_column(EncryptedText("transfer_revocations.reason"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class CashHolding(Base):
    """Synthetic owner-declared PKR cash-in-hand opening, not FBR verified."""
    __tablename__ = "cash_holdings"
    __table_args__ = (CheckConstraint("opening_minor >= 0", name="ck_cash_opening_nonnegative"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    label: Mapped[str] = mapped_column(EncryptedText("cash_holdings.label"), nullable=False)
    legal_owner: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    opening_as_of: Mapped[date] = mapped_column(Date, nullable=False)
    opening_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    evidence_basis: Mapped[str] = mapped_column(EncryptedText("cash_holdings.evidence_basis"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CashMovement(Base):
    """Cash movement with reviewed bank source OR explicit manual unverified entry."""
    __tablename__ = "cash_movements"
    __table_args__ = (
        Index("uq_active_cash_bank_transaction", "transaction_id", unique=True,
              postgresql_where=text("active IS TRUE AND transaction_id IS NOT NULL"),
              sqlite_where=text("active = 1 AND transaction_id IS NOT NULL")),
        CheckConstraint("amount_minor > 0", name="ck_cash_movement_positive"),
        CheckConstraint("kind IN ('bank_withdrawal','bank_deposit','manual_receipt','manual_spend')", name="ck_cash_kind_supported"),
        CheckConstraint("(kind IN ('bank_withdrawal','bank_deposit') AND transaction_id IS NOT NULL) OR (kind IN ('manual_receipt','manual_spend') AND transaction_id IS NULL)", name="ck_cash_source_kind"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cash_id: Mapped[str] = mapped_column(ForeignKey("cash_holdings.id"), nullable=False, index=True)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    posted_on: Mapped[date] = mapped_column(Date, nullable=False)
    evidence_note: Mapped[str] = mapped_column(EncryptedText("cash_movements.evidence_note"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CashMovementReversal(Base):
    """Append-only encrypted reason, preserving inactive cash movement source."""
    __tablename__ = "cash_movement_reversals"
    __table_args__ = (UniqueConstraint("movement_id", name="uq_cash_movement_reversal"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    movement_id: Mapped[str] = mapped_column(ForeignKey("cash_movements.id"), nullable=False)
    reason: Mapped[str] = mapped_column(EncryptedText("cash_movement_reversals.reason"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AssetSnapshot(Base):
    """Only random id/time public; all position/valuation details encrypted in JSON."""
    __tablename__ = "asset_snapshots"
    id: Mapped[str] = mapped_column(String(36),primary_key=True)
    payload_json: Mapped[str] = mapped_column(EncryptedText("asset_snapshots.payload_json"),nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow,nullable=False)


class PrivateFinancialEvent(Base):
    """Sensitive event fields are sealed; only HMAC indexes/UUID/timestamp visible."""
    __tablename__ = "private_financial_events"
    __table_args__ = (
        Index("uq_private_financial_events_source_hmac", "source_hmac", unique=True),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_hmac: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    year_hmac: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(EncryptedText("private_financial_events.payload_json"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class ConfidentialBankKeyState(Base):
    """HMAC-key continuity + encrypted-key sentinel for the active synthetic source."""
    __tablename__ = "confidential_bank_key_state"
    id: Mapped[str] = mapped_column(String(8), primary_key=True)
    verifier_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    sentinel: Mapped[str] = mapped_column(EncryptedText("confidential_bank_key_state.sentinel"), nullable=False)


class ConfidentialBankBatch(Base):
    """Active encrypted operational source; not an M1 transaction or tax projection.

    Source identity, bank name, account, money, statement dates, raw row refs,
    descriptions and checked balances all live INSIDE the authenticated payload.
    No unsafe, plaintext foreign keys to the legacy finance graph.
    """
    __tablename__ = "confidential_bank_batches"
    __table_args__ = (Index("uq_confidential_bank_source_hmac", "source_hmac", unique=True),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_hmac: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_hmac: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(EncryptedText("confidential_bank_batches.payload_json"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CanonicalSourceMirror(Base):
    """G1-c RESTORED-CANDIDATE ONLY: encrypted complete legacy source row.

    No live API reads this table, no plaintext money/date/account foreign keys;
    exact source identity is HMAC-blinded. Not a cutover or production ledger.
    """
    __tablename__ = "canonical_source_mirrors"
    __table_args__ = (Index("uq_canonical_source_mirrors_source_hmac", "source_hmac", unique=True),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(EncryptedText("canonical_source_mirrors.payload_json"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CanonicalJournalKeyState(Base):
    """Distinct HMAC anchor and AES-GCM key verification; synthetic A6 only."""
    __tablename__ = "canonical_journal_key_state"
    id: Mapped[str] = mapped_column(String(8), primary_key=True)
    verifier_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    sentinel: Mapped[str] = mapped_column(
        EncryptedText("canonical_journal_key_state.sentinel"), nullable=False)


class CanonicalJournalEntry(Base):
    """Active encrypted balanced posting; isolated from legacy plaintext financial SQL.

    All economic values, date, account identifiers and source identity are only
    inside the protected payload; SQL columns are random id and blind indexes.
    """
    __tablename__ = "canonical_journal_entries"
    __table_args__ = (
        Index("uq_canonical_journal_source_hmac", "source_hmac", unique=True),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_hmac: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    year_hmac: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_hmac: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(
        EncryptedText("canonical_journal_entries.payload_json"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False)

class OwnerRecoveryState(Base):
    """G2 synthetic encrypted one-time recovery state; no owner login integration."""
    __tablename__ = "owner_recovery_states"
    owner_hmac: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_json: Mapped[str] = mapped_column(
        EncryptedText("owner_recovery_states.bundle_json"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class OwnerRecoveryAudit(Base):
    """Append-only source-authenticated recovery issuance/consumption audit."""
    __tablename__ = "owner_recovery_audit"
    __table_args__ = (
        UniqueConstraint("owner_hmac", "revision", name="uq_owner_recovery_audit_revision"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_hmac: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(12), nullable=False)
    previous_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    detail_json: Mapped[str] = mapped_column(
        EncryptedText("owner_recovery_audit.detail_json"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False)

class DriveInboxCheckpoint(Base):
    """P1: synthetic one-folder completeness and keyed inventory state anchor.

    Only HMACs and a scan counter are SQL-visible. No Drive IDs, filenames,
    bank accounts, document bytes, OAuth tokens or financial values.
    """
    __tablename__ = "drive_inbox_checkpoints"
    folder_hmac: Mapped[str] = mapped_column(String(64), primary_key=True)
    scan_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_snapshot_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    state_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class DriveInboxItem(Base):
    """P1 synthetic review row; all per-source state sealed as AES-GCM JSON."""
    __tablename__ = "drive_inbox_items"
    __table_args__ = (
        UniqueConstraint("file_hmac", name="uq_drive_inbox_file_hmac"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    folder_hmac: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    file_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(
        EncryptedText("drive_inbox_items.payload_json"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
