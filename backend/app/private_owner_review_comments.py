"""P5B: append-only, encrypted owner-authenticated finance review comments.

Comment text is OWNER evidence, not a bank fact, tax determination, model
instruction or automatic resolution. Supported targets are blinded source
or transaction identities emitted by trusted private financial APIs.

No account numbers, narrative text, document names or raw money amounts enter
SQL columns: an independently derived AEAD envelope holds all comment text.
No Google Drive write, no original-file mutation, no SaaS/third-party AI call.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import hmac
import json
import os
import re
import secrets
import time
from uuid import uuid4

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from .models import OwnerFinancialReviewComment
from .private_owner_identity import _keys, _owner

_HEX = re.compile(r"^[0-9a-f]{64}$")
_PREFIX = "P5B1:"
_PURPOSE = b"personal-cfo:p5b:owner-comments:v1:"
_VALID_KIND = frozenset(("document", "transaction"))
_MAX_COMMENT = 2000
_MAX_ROWS = 50


class PrivateOwnerReviewBlocked(ValueError):
    """Private owner review comment unavailable or untrusted."""


def _derive(raw: bytes, purpose: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_PURPOSE+b"salt",
        info=_PURPOSE+purpose,
    ).derive(raw)


def _setup(db: Session, owner_ref: str):
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P5B_OWNER_REVIEW_COMMENTS_ENABLED") != "1"
        or os.getenv("P5B_G2_PRIVATE_REVIEW_ENCRYPTION_ACCEPTED") != "1"
        or os.getenv("P5B_G3_FINANCIAL_REVIEW_SCHEMA_ACCEPTED") != "1"):
        raise PrivateOwnerReviewBlocked("Private review system disabled")
    try:
        cipher_root,identity_root,session_root=_keys(db)
        enc=_derive(cipher_root,b"aesgcm")
        mac=_derive(identity_root,b"row-integrity")
        if len({enc,mac,cipher_root,identity_root,session_root})!=5:
            raise ValueError()
        return _owner(identity_root,owner_ref),enc,mac
    except Exception:
        raise PrivateOwnerReviewBlocked(
            "Independent owner comment keys unavailable") from None


def _target(kind: str, source_hmac: str) -> None:
    if (type(kind) is not str or kind not in _VALID_KIND
        or type(source_hmac) is not str or _HEX.fullmatch(source_hmac) is None):
        raise PrivateOwnerReviewBlocked("Valid private financial review target required")


def _comment(value: str) -> str:
    if (type(value) is not str or not 1<=len(value.strip())<=_MAX_COMMENT
        or "\x00" in value
        or any(ord(ch)<32 and ch not in "\r\n\t" for ch in value)):
        raise PrivateOwnerReviewBlocked("Review note must be 1–2000 characters")
    return value.strip()


def _now(epoch: int | None) -> int:
    value=int(time.time()) if epoch is None else epoch
    if type(value) is not int or not 1_500_000_000<=value<=4_000_000_000:
        raise PrivateOwnerReviewBlocked("Private review clock unavailable")
    return value


def _aad(row: OwnerFinancialReviewComment) -> bytes:
    binding = (f"{row.id}:{row.owner_hmac}:{row.subject_hmac}:{row.subject_kind}:"
               f"{row.revision}:{row.created_epoch}").encode("ascii")
    return _PURPOSE + binding


def _seal(key: bytes, row: OwnerFinancialReviewComment, note: str) -> str:
    payload=json.dumps({
        "comment":note,
        "review_state":"PENDING_EVIDENCE_RECONCILIATION",
        "automatically_accepted":False,
    },ensure_ascii=False,separators=(",",":")).encode("utf-8")
    nonce=secrets.token_bytes(12)
    encrypted=AESGCM(key).encrypt(nonce,payload,_aad(row))
    return _PREFIX+base64.urlsafe_b64encode(nonce+encrypted).decode("ascii")


def _tag(key: bytes, row: OwnerFinancialReviewComment) -> str:
    packed=json.dumps({
        "id":row.id,
        "owner":row.owner_hmac,
        "target":row.subject_hmac,
        "kind":row.subject_kind,
        "revision":row.revision,
        "cipher":row.ciphertext,
        "epoch":row.created_epoch,
    },sort_keys=True,separators=(",",":")).encode("ascii")
    return hmac.new(key,_PURPOSE+b"row\0"+packed,sha256).hexdigest()


def _read(row: OwnerFinancialReviewComment,key: bytes,mac: bytes) -> dict:
    try:
        if (_HEX.fullmatch(row.row_hmac) is None
            or not hmac.compare_digest(row.row_hmac,_tag(mac,row))
            or not row.ciphertext.startswith(_PREFIX)
            or len(row.ciphertext)>14000):
            raise ValueError()
        b=base64.b64decode(row.ciphertext[len(_PREFIX):],
                           altchars=b"-_",validate=True)
        if not 28<=len(b)<=10400:
            raise ValueError()
        payload=json.loads(AESGCM(key).decrypt(b[:12],b[12:],
                                              _aad(row)).decode("utf-8"))
        if (type(payload) is not dict
            or payload.get("review_state") != "PENDING_EVIDENCE_RECONCILIATION"
            or payload.get("automatically_accepted") is not False):
            raise ValueError()
        comment=_comment(payload["comment"])
        return {
            "id":row.id,
            "subject_hmac":row.subject_hmac,
            "subject_kind":row.subject_kind,
            "revision":row.revision,
            "comment":comment,
            "review_state":"PENDING_EVIDENCE_RECONCILIATION",
            "created_epoch":row.created_epoch,
            "analysis_pending":True,
        }
    except Exception:
        raise PrivateOwnerReviewBlocked("Owner review record integrity invalid") from None


def append_owner_review_comment(
    db: Session, *, owner_ref: str, subject_kind: str,
    subject_hmac: str, comment: str, now_epoch: int | None = None,
) -> dict:
    """Append one immutable encrypted note; never rewrite bank classifications."""
    _target(subject_kind,subject_hmac)
    note=_comment(comment)
    owner,key,mac=_setup(db,owner_ref)
    now=_now(now_epoch)
    try:
        if db.bind.dialect.name=="sqlite":
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        else:
            db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock))"),
                       {"lock":owner+subject_hmac})
        q=select(OwnerFinancialReviewComment).where(
            OwnerFinancialReviewComment.owner_hmac==owner,
            OwnerFinancialReviewComment.subject_hmac==subject_hmac,
            OwnerFinancialReviewComment.subject_kind==subject_kind,
        ).order_by(OwnerFinancialReviewComment.revision.desc()).limit(1)
        previous=db.execute(q).scalars().first()
        if previous is not None:
            _read(previous,key,mac)
            if previous.revision>=_MAX_ROWS:
                raise PrivateOwnerReviewBlocked(
                    "Review history limit reached; needs owner reconciliation")
        row=OwnerFinancialReviewComment(
            id=str(uuid4()),owner_hmac=owner,subject_hmac=subject_hmac,
            subject_kind=subject_kind,
            revision=1 if previous is None else previous.revision+1,
            ciphertext="",row_hmac="",created_epoch=now,
        )
        row.ciphertext=_seal(key,row,note)
        row.row_hmac=_tag(mac,row)
        db.add(row)
        db.commit()
        result=_read(row,key,mac)
        result["saved_encrypted"]=True
        result["original_transaction_changed"]=False
        result["automatically_resolved"]=False
        return result
    except PrivateOwnerReviewBlocked:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise PrivateOwnerReviewBlocked("Owner review comment not saved") from None


def list_owner_review_comments(
    db: Session, *, owner_ref: str,
    subject_kind: str,subject_hmac: str,
) -> dict:
    """Only return note plaintext to a separately MFA-verified owner route."""
    _target(subject_kind,subject_hmac)
    owner,key,mac=_setup(db,owner_ref)
    try:
        q=select(OwnerFinancialReviewComment).where(
            OwnerFinancialReviewComment.owner_hmac==owner,
            OwnerFinancialReviewComment.subject_hmac==subject_hmac,
            OwnerFinancialReviewComment.subject_kind==subject_kind,
        ).order_by(OwnerFinancialReviewComment.revision.asc()).limit(_MAX_ROWS+1)
        rows=db.execute(q).scalars().all()
        if len(rows)>_MAX_ROWS:
            raise PrivateOwnerReviewBlocked("Review history exceeded safety bound")
        comments=[_read(row,key,mac) for row in rows]
        for n,item in enumerate(comments,1):
            if item["revision"]!=n:
                raise PrivateOwnerReviewBlocked("Owner review history discontinuity")
        return {
            "contract":"personal_cfo_owner_encrypted_review_comments_v1",
            "subject_hmac":subject_hmac,
            "subject_kind":subject_kind,
            "comments":comments,
            "comment_count":len(comments),
            "original_source_unchanged":True,
            "financial_values_changed":False,
            "automatic_resolution_performed":False,
        }
    except PrivateOwnerReviewBlocked:
        raise
    except Exception:
        raise PrivateOwnerReviewBlocked("Private review notes unavailable") from None
    finally:
        db.rollback()
