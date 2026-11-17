"""P1P: private owner MFA recovery one-time challenge and account lockdown.

Separate from synthetic G2 recovery fixtures. Recovery does NOT log the owner
in, reset TOTP, generate a fresh session or establish Google OAuth. It may
only be invoked in an operator-reviewed PRIVATE backend after separate owner
identity proof. No public route mounts this module, no secrets in CI.
"""
from __future__ import annotations

import base64
import hmac
from hashlib import sha256
import json
import os
import re
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import (
    OwnerPrivateIdentity, OwnerPrivateSession,
    OwnerPrivateRecoveryState, OwnerPrivateRecoveryAudit,
)
from .auth_mfa import check_password
from .private_owner_identity import (
    _keys as owner_keys, _owner, _lock, _row, _verify_identity,
    _session, _now, PrivateOwnerIdentityBlocked,
)

_CODE=re.compile(r"^[A-Z2-7]{4}(?:-[A-Z2-7]{4}){7}$")
_HEX=re.compile(r"^[0-9a-f]{64}$")
_PREFIX="P1P1:"
_DEFAULT_CODES=8
_TTL=365*86400


class PrivateOwnerRecoveryBlocked(ValueError):
    """Private owner one-time recovery chain or identity proof was rejected."""


def _key(name: str) -> bytes:
    try:
        key=base64.b64decode(os.environ.get(name,""),
                             altchars=b"-_",validate=True)
    except (UnicodeError,ValueError):
        raise PrivateOwnerRecoveryBlocked("Owner recovery custody unavailable") from None
    if len(key)!=32:
        raise PrivateOwnerRecoveryBlocked("Owner recovery custody unavailable")
    return key


def _config(db: Session) -> tuple[bytes,bytes,bytes,bytes,bytes]:
    if (os.getenv("APP_DATA_MODE")!="synthetic"
        or os.getenv("P1P_PRIVATE_RECOVERY_ONLY")!="1"
        or os.getenv("P1P_G2_RECOVERY_REVIEWED")!="1"):
        raise PrivateOwnerRecoveryBlocked("Owner recovery not authorized")
    try:
        owner_enc,owner_mac,session_mac=owner_keys(db)
        rec_enc=_key("P1P_OWNER_RECOVERY_ENCRYPTION_KEY")
        rec_mac=_key("P1P_OWNER_RECOVERY_HMAC_KEY")
        if len({owner_enc,owner_mac,session_mac,rec_enc,rec_mac})!=5:
            raise ValueError()
        return owner_enc,owner_mac,session_mac,rec_enc,rec_mac
    except (ValueError,PrivateOwnerIdentityBlocked):
        raise PrivateOwnerRecoveryBlocked("Independently keyed owner recovery required") from None


def _tag(mac: bytes, domain: str, content: str) -> str:
    return hmac.new(mac,
        ("personal-cfo:p1p:"+domain+"\0"+content).encode("ascii"),
        sha256).hexdigest()


def _serialize(value: dict) -> str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True)


def _row_mac(mac: bytes, row: OwnerPrivateRecoveryState) -> str:
    return _tag(mac,"row",_serialize({
        "owner":row.owner_hmac,"revision":row.revision,
        "issued":row.issued_epoch,"expires":row.expires_epoch,
        "ciphertext":row.ciphertext,"pending":row.pending,
    }))


def _audit_tag(mac: bytes,owner: str,rev: int,action: str,
               prev: str,row_mac: str,epoch: int) -> str:
    return _tag(mac,"audit",_serialize({
        "owner":owner,"revision":rev,"action":action,
        "previous":prev,"row":row_mac,"epoch":epoch,
    }))


def _seal(key: bytes, owner: str, value: dict) -> str:
    nonce=secrets.token_bytes(12)
    c=AESGCM(key).encrypt(nonce,_serialize(value).encode("ascii"),
                         ("personal-cfo:p1p:recovery:"+owner).encode("ascii"))
    return _PREFIX+base64.urlsafe_b64encode(nonce+c).decode("ascii")


def _open(key: bytes, row: OwnerPrivateRecoveryState) -> dict:
    try:
        if (not row.ciphertext.startswith(_PREFIX)
            or len(row.ciphertext)>7000):
            raise ValueError()
        blob=base64.b64decode(row.ciphertext[len(_PREFIX):],
                              altchars=b"-_",validate=True)
        result=json.loads(AESGCM(key).decrypt(
            blob[:12],blob[12:],
            ("personal-cfo:p1p:recovery:"+row.owner_hmac).encode("ascii")))
        if (type(result) is not dict
            or set(result)!={"issued","code_hmacs","used_hmacs"}
            or result["issued"]!=row.issued_epoch
            or type(result["code_hmacs"]) is not list
            or not 4<=len(result["code_hmacs"])<=12
            or len(set(result["code_hmacs"]))!=len(result["code_hmacs"])
            or type(result["used_hmacs"]) is not list
            or not set(result["used_hmacs"])<=set(result["code_hmacs"])
            or any(type(x) is not str or _HEX.fullmatch(x) is None
                   for x in result["code_hmacs"]+result["used_hmacs"])):
            raise ValueError()
        return result
    except Exception:
        raise PrivateOwnerRecoveryBlocked("Owner recovery bundle not authenticated") from None


def _verify(db: Session,row: OwnerPrivateRecoveryState,
            mac: bytes,enc: bytes) -> tuple[dict,str]:
    if (row.revision<1 or row.expires_epoch-row.issued_epoch!=_TTL
        or type(row.row_hmac) is not str
        or not hmac.compare_digest(row.row_hmac,_row_mac(mac,row))):
        raise PrivateOwnerRecoveryBlocked("Owner recovery audit mismatch")
    records=db.scalars(select(OwnerPrivateRecoveryAudit).where(
        OwnerPrivateRecoveryAudit.owner_hmac==row.owner_hmac
    ).order_by(OwnerPrivateRecoveryAudit.revision)).all()
    if len(records)!=row.revision:
        raise PrivateOwnerRecoveryBlocked("Owner recovery audit incomplete")
    last="0"*64
    for index,event in enumerate(records,1):
        if (event.revision!=index or event.previous_hmac!=last
            or event.action not in ("ISSUED","REDEEMED")
            or type(event.row_hmac) is not str
            or type(event.event_hmac) is not str
            or not hmac.compare_digest(event.event_hmac,
                _audit_tag(mac,row.owner_hmac,index,event.action,
                           last,event.row_hmac,event.epoch))):
            raise PrivateOwnerRecoveryBlocked("Owner recovery audit chain tampered")
        last=event.event_hmac
    if records[-1].row_hmac!=row.row_hmac:
        raise PrivateOwnerRecoveryBlocked("Owner recovery state and audit differ")
    return _open(enc,row),last


def _append(db: Session,mac: bytes,row: OwnerPrivateRecoveryState,
            action: str,prev: str,epoch: int) -> None:
    event=OwnerPrivateRecoveryAudit(
        owner_hmac=row.owner_hmac,revision=row.revision,action=action,
        previous_hmac=prev,row_hmac=row.row_hmac,epoch=epoch,
        event_hmac=_audit_tag(mac,row.owner_hmac,row.revision,
                             action,prev,row.row_hmac,epoch),
    )
    db.add(event)


def private_recovery_hold_active(db: Session, *, owner_hmac: str) -> bool:
    """Identity/session validators call this ONLY if a recovery row exists.

    Missing recovery keys or any corrupt/challenged state must block access,
    rather than allow a tampered pending flag to re-enable sessions.
    """
    _,_,_,enc,mac=_config(db)
    row=db.get(OwnerPrivateRecoveryState,owner_hmac)
    if row is None:
        return False
    _verify(db,row,mac,enc)
    return row.pending


def issue_private_owner_recovery_codes(
    db: Session, *, owner_ref: str, token: str, csrf: str,
    password: str, now_epoch: int | None=None,
) -> tuple[dict,tuple[str,...]]:
    """Only a currently valid owner MFA session+CSRF+password may issue codes.

    Plain recovery codes are returned once, never kept in SQL/response logs.
    Caller must separately verify TLS/Origin/reauth before any owner UI.
    """
    _,owner_mac,session_mac,enc,mac=_config(db)
    owner=_owner(owner_mac,owner_ref)
    now=_now(now_epoch)
    try:
        _lock(db)
        current=_row(db)
        if current is None or current.owner_hmac!=owner:
            raise PrivateOwnerRecoveryBlocked("Owner recovery identity unavailable")
        _verify_identity(owner_mac,current)
        _session(db,owner,session_mac,token,now,csrf=csrf,
                 mutation=True,for_update=True)
        if (type(password) is not str or len(password)>256
            or not check_password(password,current.password_scrypt)):
            raise PrivateOwnerRecoveryBlocked("Owner recovery reauthentication failed")
        row=db.get(OwnerPrivateRecoveryState,owner)
        if row is None:
            prev="0"*64
            rev=1
        else:
            _,prev=_verify(db,row,mac,enc)
            if row.pending:
                raise PrivateOwnerRecoveryBlocked("Owner recovery is pending")
            rev=row.revision+1
        raw=[base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
             for _ in range(_DEFAULT_CODES)]
        codes=tuple("-".join(v[i:i+4] for i in range(0,32,4)) for v in raw)
        tags=[_tag(mac,"code",owner+":"+v) for v in raw]
        if len(set(tags))!=len(tags):
            raise PrivateOwnerRecoveryBlocked("Private owner recovery collision")
        cipher=_seal(enc,owner,{
            "issued":now,"code_hmacs":tags,"used_hmacs":[]})
        if row is None:
            row=OwnerPrivateRecoveryState(owner_hmac=owner,revision=rev,
                issued_epoch=now,expires_epoch=now+_TTL,ciphertext=cipher,
                pending=False,row_hmac="")
            db.add(row)
        else:
            row.revision=rev
            row.issued_epoch=now
            row.expires_epoch=now+_TTL
            row.ciphertext=cipher
        row.row_hmac=_row_mac(mac,row)
        _append(db,mac,row,"ISSUED",prev,now)
        db.commit()
        return ({
            "recovery_codes_issued":len(codes),
            "raw_codes_persisted":False,
            "old_recovery_codes_invalidated":True,
            "owner_mfa_reset_approved":False,
            "provider_google_consent_established":False,
        },codes)
    except (PrivateOwnerRecoveryBlocked,PrivateOwnerIdentityBlocked):
        db.rollback()
        raise PrivateOwnerRecoveryBlocked("Owner recovery issuance denied") from None
    except Exception:
        db.rollback()
        raise PrivateOwnerRecoveryBlocked("Owner recovery issuance failed") from None


def redeem_private_owner_recovery_code(
    db: Session, *, owner_ref: str, password: str,
    recovery_code: str, now_epoch: int | None=None,
    independently_verified_offline_owner: bool=False,
) -> dict:
    """One-time code + password + offline identity review: quarantine account.

    Redemption atomically revokes every owner session and sets a durable
    recovery-pending hold. It CANNOT create a new session or reset TOTP.
    """
    _,owner_mac,_,enc,mac=_config(db)
    owner=_owner(owner_mac,owner_ref)
    now=_now(now_epoch)
    if (independently_verified_offline_owner is not True
        or type(password) is not str
        or type(recovery_code) is not str
        or _CODE.fullmatch(recovery_code) is None):
        raise PrivateOwnerRecoveryBlocked("Independent owner recovery verification required")
    try:
        _lock(db)
        current=_row(db)
        if current is None or current.owner_hmac!=owner:
            raise PrivateOwnerRecoveryBlocked("Owner recovery identity unavailable")
        _verify_identity(owner_mac,current)
        if not check_password(password,current.password_scrypt):
            raise PrivateOwnerRecoveryBlocked("Owner password verification failed")
        row=db.scalar(select(OwnerPrivateRecoveryState).where(
            OwnerPrivateRecoveryState.owner_hmac==owner
        ).with_for_update())
        if row is None or row.pending or now>row.expires_epoch:
            raise PrivateOwnerRecoveryBlocked("Recovery code unavailable")
        bundle,prev=_verify(db,row,mac,enc)
        flattened=recovery_code.replace("-","")
        candidate=_tag(mac,"code",owner+":"+flattened)
        found=False
        for hashed in bundle["code_hmacs"]:
            found=hmac.compare_digest(candidate,hashed) or found
        if not found or candidate in bundle["used_hmacs"]:
            raise PrivateOwnerRecoveryBlocked("Recovery code already used")
        bundle["used_hmacs"].append(candidate)
        row.revision+=1
        row.pending=True
        row.ciphertext=_seal(enc,owner,bundle)
        row.row_hmac=_row_mac(mac,row)
        _append(db,mac,row,"REDEEMED",prev,now)
        affected=db.execute(update(OwnerPrivateSession).where(
            OwnerPrivateSession.owner_hmac==owner,
            OwnerPrivateSession.revoked.is_(False),
        ).values(revoked=True)).rowcount
        db.commit()
        return {
            "one_time_recovery_code_consumed":True,
            "owner_sessions_revoked":affected,
            "account_recovery_hold_active":True,
            "new_session_issued":False,
            "totp_reset_performed":False,
            "real_google_consent_authorized":False,
        }
    except (PrivateOwnerRecoveryBlocked,PrivateOwnerIdentityBlocked):
        db.rollback()
        raise PrivateOwnerRecoveryBlocked("Owner recovery redemption denied") from None
    except Exception:
        db.rollback()
        raise PrivateOwnerRecoveryBlocked("Owner recovery redemption failed") from None
