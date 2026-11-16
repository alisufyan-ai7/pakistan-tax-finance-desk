"""G2 F3: durable synthetic owner recovery-code state and chained audit.

Offline internal service ONLY; not an owner login endpoint. No real records,
no automatic session creation or TOTP reset. The caller must authenticate
password/MFA separately; Postgres SELECT FOR UPDATE serializes consumption.
SQLite synthetic tests use BEGIN IMMEDIATE plus revision-checked updates.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import OwnerRecoveryState, OwnerRecoveryAudit
from .owner_recovery_codes import (
    RecoveryBlocked, RecoveryBundle, _tag, issue_recovery_bundle,
    redeem_recovery_code,
)


def _guard():
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise RecoveryBlocked("Real owner recovery remains disabled")


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _bundle_encode(value: RecoveryBundle) -> str:
    return _canonical({
        "owner_hmac": value.owner_hmac, "issued_epoch": value.issued_epoch,
        "code_hmacs": list(value.code_hmacs),
        "consumed_hmacs": sorted(value.consumed_hmacs),
        "synthetic_only": True,
    })


def _bundle_decode(raw: str) -> RecoveryBundle:
    try:
        item = json.loads(raw)
        if not isinstance(item, dict) or set(item) != {
            "owner_hmac", "issued_epoch", "code_hmacs", "consumed_hmacs", "synthetic_only"
        } or item["synthetic_only"] is not True:
            raise ValueError()
        if (type(item["issued_epoch"]) is not int or item["issued_epoch"] <= 0
            or not isinstance(item["owner_hmac"], str) or len(item["owner_hmac"]) != 64
            or not isinstance(item["code_hmacs"], list)
            or not 4 <= len(item["code_hmacs"]) <= 12
            or not isinstance(item["consumed_hmacs"], list)
            or len(set(item["code_hmacs"])) != len(item["code_hmacs"])
            or not set(item["consumed_hmacs"]) <= set(item["code_hmacs"])
            or any(type(v) is not str or len(v) != 64
                   for v in item["code_hmacs"] + item["consumed_hmacs"])):
            raise ValueError()
        return RecoveryBundle(
            owner_hmac=item["owner_hmac"], issued_epoch=item["issued_epoch"],
            code_hmacs=tuple(item["code_hmacs"]),
            consumed_hmacs=frozenset(item["consumed_hmacs"]),
        )
    except Exception:
        raise RecoveryBlocked("Authenticated recovery bundle malformed") from None


def _owner_ref(owner_ref: str) -> str:
    if not isinstance(owner_ref, str):
        raise RecoveryBlocked("Invalid recovery owner")
    try:
        return _tag(b"owner", owner_ref)
    except (ValueError, UnicodeError):
        raise RecoveryBlocked("Invalid recovery owner") from None


def _lock_session(db: Session) -> None:
    if db.bind is None or db.bind.dialect.name not in ("postgresql", "sqlite"):
        raise RecoveryBlocked("Supported SQL transactional recovery store required")
    if db.bind.dialect.name == "sqlite":
        # SQLite BEGIN IMMEDIATE before ANY SELECT: serializes writers. Not
        # a substitute for production PG FOR UPDATE and owner rate limits.
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def _event_tag(owner_hmac: str, version: int, action: str,
               prev_hmac: str, bundle_hmac: str) -> str:
    if action not in ("ISSUED", "REDEEMED"):
        raise RecoveryBlocked("Unknown recovery audit event")
    return _tag(b"audit", _canonical({
        "owner": owner_hmac, "revision": version, "action": action,
        "previous": prev_hmac, "bundle": bundle_hmac,
    }))


def _verify_chain(db: Session, owner_hmac: str, state: OwnerRecoveryState | None):
    rows = db.scalars(select(OwnerRecoveryAudit).where(
        OwnerRecoveryAudit.owner_hmac == owner_hmac
    ).order_by(OwnerRecoveryAudit.revision)).all()
    if (state is None and rows) or (state is not None and (
        not rows or len(rows) != state.revision
    )):
        raise RecoveryBlocked("Recovery audit sequence incomplete")
    prev = "0" * 64
    for n, row in enumerate(rows, start=1):
        if row.revision != n or row.previous_hmac != prev:
            raise RecoveryBlocked("Recovery audit sequence altered")
        if row.event_hmac != _event_tag(
            owner_hmac, n, row.action, row.previous_hmac, row.bundle_hmac
        ):
            raise RecoveryBlocked("Recovery audit authenticity failed")
        prev = row.event_hmac
    if state is not None:
        bundle = _bundle_decode(state.bundle_json)
        if bundle.owner_hmac != owner_hmac or rows[-1].bundle_hmac != _tag(
            b"bundle", _bundle_encode(bundle)
        ):
            raise RecoveryBlocked("Recovery state and audit chain disagree")
    return rows[-1].event_hmac if rows else "0" * 64


def _append_audit(db: Session, owner_hmac: str, revision: int,
                  action: str, previous: str, bundle: RecoveryBundle) -> None:
    digest = _tag(b"bundle", _bundle_encode(bundle))
    event_hmac = _event_tag(owner_hmac, revision, action, previous, digest)
    db.add(OwnerRecoveryAudit(
        id=str(uuid.uuid4()), owner_hmac=owner_hmac, revision=revision,
        action=action, previous_hmac=previous, bundle_hmac=digest,
        event_hmac=event_hmac,
        detail_json=_canonical({
            "action": action, "revision": revision,
            "code_count": len(bundle.code_hmacs),
            "consumed_count": len(bundle.consumed_hmacs),
            "synthetic_only": True,
        }),
    ))


def issue_persisted_synthetic_codes(
    db: Session, *, owner_ref: str, mfa_confirmed: bool,
    issued_epoch: int, count: int = 8,
) -> tuple[dict, tuple[str, ...]]:
    """Replace all prior codes atomically; plaintext returned only once.

    Caller must have authenticated existing owner password and MFA. No HTTP API.
    """
    _guard()
    bundle, codes = issue_recovery_bundle(
        owner_ref=owner_ref, mfa_confirmed=mfa_confirmed,
        issued_epoch=issued_epoch, count=count,
    )
    owner_hmac = _owner_ref(owner_ref)
    try:
        _lock_session(db)
        state = db.scalar(select(OwnerRecoveryState).where(
            OwnerRecoveryState.owner_hmac == owner_hmac
        ).with_for_update())
        previous = _verify_chain(db, owner_hmac, state)
        revision = 1 if state is None else state.revision + 1
        if state is None:
            db.add(OwnerRecoveryState(
                owner_hmac=owner_hmac, revision=revision,
                bundle_json=_bundle_encode(bundle),
            ))
        else:
            changed = db.execute(update(OwnerRecoveryState).where(
                OwnerRecoveryState.owner_hmac == owner_hmac,
                OwnerRecoveryState.revision == state.revision,
            ).values(revision=revision, bundle_json=_bundle_encode(bundle)))
            if changed.rowcount != 1:
                raise RecoveryBlocked("Concurrent recovery revision conflict")
        _append_audit(db, owner_hmac, revision, "ISSUED", previous, bundle)
        db.commit()
    except RecoveryBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise RecoveryBlocked("Transactional recovery issuance failed") from None
    return ({
        "synthetic_only": True, "recovery_revision": revision,
        "code_count": len(codes), "persisted_atomically": True,
        "audit_chained": True, "raw_codes_in_database": False,
        "owner_login_or_mfa_reset_authorized": False,
        "real_data_authorized": False,
    }, codes)


def consume_persisted_synthetic_code(
    db: Session, *, owner_ref: str, presented_code: str,
    password_confirmed: bool, now_epoch: int,
) -> dict:
    """Consume exactly once in SQL transaction; no session, TOTP reset or login."""
    _guard()
    if password_confirmed is not True:
        raise RecoveryBlocked("Owner password reauthentication required")
    owner_hmac = _owner_ref(owner_ref)
    try:
        _lock_session(db)
        state = db.scalar(select(OwnerRecoveryState).where(
            OwnerRecoveryState.owner_hmac == owner_hmac
        ).with_for_update())
        if state is None:
            raise RecoveryBlocked("No authenticated recovery state")
        previous = _verify_chain(db, owner_hmac, state)
        bundle = _bundle_decode(state.bundle_json)
        next_bundle = redeem_recovery_code(
            bundle=bundle, owner_ref=owner_ref, presented_code=presented_code,
            password_confirmed=True, now_epoch=now_epoch,
        )
        revision = state.revision + 1
        changed = db.execute(update(OwnerRecoveryState).where(
            OwnerRecoveryState.owner_hmac == owner_hmac,
            OwnerRecoveryState.revision == state.revision,
        ).values(revision=revision, bundle_json=_bundle_encode(next_bundle)))
        if changed.rowcount != 1:
            raise RecoveryBlocked("Concurrent recovery consumption blocked")
        _append_audit(db, owner_hmac, revision, "REDEEMED", previous, next_bundle)
        db.commit()
    except RecoveryBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise RecoveryBlocked("Transactional recovery redemption failed") from None
    return {
        "synthetic_only": True, "recovery_revision": revision,
        "consumed_once_in_transaction": True, "audit_chained": True,
        "login_session_issued": False, "totp_reset": False,
        "real_data_authorized": False,
    }


def attest_synthetic_recovery_chain(db: Session, *, owner_ref: str) -> dict:
    """Check all code state and audit rows, no plaintext or owner identifier."""
    _guard()
    owner_hmac = _owner_ref(owner_ref)
    try:
        _lock_session(db)
        state = db.scalar(select(OwnerRecoveryState).where(
            OwnerRecoveryState.owner_hmac == owner_hmac
        ).with_for_update())
        if state is None:
            raise RecoveryBlocked("No persistent recovery state")
        _verify_chain(db, owner_hmac, state)
        bundle = _bundle_decode(state.bundle_json)
        report = {
            "synthetic_only": True, "audit_revision": state.revision,
            "active_code_count": len(bundle.code_hmacs) - len(bundle.consumed_hmacs),
            "audit_chain_verified": True, "encrypted_state": True,
            "prod_owner_recovery_certified": False,
        }
        db.rollback()  # read-only and release SQLite transaction
        return report
    except RecoveryBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise RecoveryBlocked("Recovery audit read failed closed") from None
