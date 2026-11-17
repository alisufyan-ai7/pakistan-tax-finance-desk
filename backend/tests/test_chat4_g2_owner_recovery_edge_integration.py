"""Chat04 integrated G2 private MFA, recovery and exact OAuth ingress isolation.

Tests synthetic fixture end-to-end *without* connecting Google, mounting owner
login, deploying nginx, using real Railway secrets or accepting financial data.
"""
import base64
import hashlib
import hmac
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.private_owner_identity import (
    enroll_private_owner,issue_private_owner_session,
    verify_private_owner_session,PrivateOwnerIdentityBlocked,
)
from app.private_owner_recovery import (
    issue_private_owner_recovery_codes,redeem_private_owner_recovery_code,
)
from app.private_metadata_grant_custody import (
    PrivateMetadataCustodyBlocked,store_private_metadata_grant,
)

OWNER="SYNTHETIC_OWNER_INTEGRATED_2026"
PASSWORD="fake-integrated-owner-password-2026"
T=1_800_045_000
SEED=base64.b32encode(b"J"*20).decode("ascii")


def otp():
    step=T//30
    mac=hmac.new(b"J"*20,step.to_bytes(8,'big'),hashlib.sha1).digest()
    off=mac[-1]&15
    return f"{(int.from_bytes(mac[off:off+4],'big')&0x7fffffff)%1000000:06d}"


def keys(monkeypatch):
    enc=lambda x:base64.urlsafe_b64encode(x*32).decode("ascii")
    for name,value in {
        "APP_DATA_MODE":"synthetic",
        "P1N_PRIVATE_OWNER_AUTH_ONLY":"1",
        "P1N_G2_OWNER_IDENTITY_REVIEWED":"1",
        "P1N_SQLITE_FAKE_TEST_ONLY":"1",
        "P1N_OWNER_ENCRYPTION_KEY":enc(b"A"),
        "P1N_OWNER_IDENTITY_HMAC_KEY":enc(b"B"),
        "P1N_OWNER_SESSION_HMAC_KEY":enc(b"C"),
        "P1P_PRIVATE_RECOVERY_ONLY":"1",
        "P1P_G2_RECOVERY_REVIEWED":"1",
        "P1P_OWNER_RECOVERY_ENCRYPTION_KEY":enc(b"D"),
        "P1P_OWNER_RECOVERY_HMAC_KEY":enc(b"E"),
    }.items():
        monkeypatch.setenv(name,value)


def test_owner_auth_then_one_use_recovery_preserves_no_oauth_access(monkeypatch,tmp_path):
    keys(monkeypatch)
    engine=create_engine("sqlite:///"+str(tmp_path/"fake-p1-integrated.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        receipt=enroll_private_owner(db,owner_ref=OWNER,password=PASSWORD,
            totp_secret_base32=SEED,now_epoch=T,verified_offline_bootstrap=True)
        assert receipt["private_metadata_owner_enrolled"]
    with Session(engine) as db:
        proof=issue_private_owner_session(db,owner_ref=OWNER,password=PASSWORD,
                                         totp_code=otp(),now_epoch=T)
    with Session(engine) as db:
        assert verify_private_owner_session(db,owner_ref=OWNER,
            token=proof.cookie_token,csrf=proof.csrf_token,
            mutation=True,now_epoch=T)["private_owner_mfa_session_valid"]
    with Session(engine) as db:
        issued,codes=issue_private_owner_recovery_codes(
            db,owner_ref=OWNER,token=proof.cookie_token,csrf=proof.csrf_token,
            password=PASSWORD,now_epoch=T+1)
        assert len(codes)==issued["recovery_codes_issued"]==8
    with Session(engine) as db:
        done=redeem_private_owner_recovery_code(
            db,owner_ref=OWNER,password=PASSWORD,
            recovery_code=codes[0],now_epoch=T+2,
            independently_verified_offline_owner=True)
        assert done["account_recovery_hold_active"]
        assert done["new_session_issued"] is False
    with Session(engine) as db:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            verify_private_owner_session(db,owner_ref=OWNER,
                token=proof.cookie_token,now_epoch=T+3)
    # Even after valid fixture MFA, the unrelated P1M Google vault is still
    # default-off, with no OAuth state/token or Google consent.
    with Session(engine) as db:
        with pytest.raises(PrivateMetadataCustodyBlocked):
            store_private_metadata_grant(
                db,owner_ref=OWNER,folder_id="SYNTHETIC_FOLDER_INTEGRATED",
                client_id="000000000000-syntheticdev.apps.googleusercontent.com",
                refresh_token="SYNTHETIC_FAKE_REFRESH_"+("X"*64),now_epoch=T)
    with engine.connect() as c:
        auth=c.execute(text("SELECT * FROM owner_private_identities")).one()
        recovery=c.execute(text("SELECT * FROM owner_private_recovery_states")).one()
        assert recovery[5] in (True,1)
        source=str(auth)+str(recovery)
        for secret in (OWNER,PASSWORD,SEED,proof.cookie_token,proof.csrf_token,*codes):
            assert secret not in source
        assert c.execute(text("SELECT count(*) FROM owner_google_metadata_grants")).scalar_one()==0
    engine.dispose()


def test_candidate_route_cannot_auto_mount_on_current_railway_private_api():
    root=Path(__file__).parents[2]
    live=(root/"frontend/nginx.railway.conf").read_text()
    candidate=(root/"ops/nginx.personal-cfo-oauth.candidate.conf").read_text()
    assert "/api/drive/oauth/callback" not in live
    assert "location = /api/drive/oauth/callback" in candidate
    assert "access_log off;" in candidate
    assert "error_log /dev/null crit;" in candidate
    from app.preview_api import create_preview_app
    paths={r.path for r in create_preview_app().routes}
    assert "/api/owner/login" not in paths
    assert "/api/owner/recover" not in paths
    assert "/api/drive/oauth/callback" not in paths
    assert "/api/finance/import" not in paths


def test_real_financial_mode_remains_denied_on_private_mfa(monkeypatch,tmp_path):
    keys(monkeypatch)
    monkeypatch.setenv("APP_DATA_MODE","real")
    engine=create_engine("sqlite:///"+str(tmp_path/"notreal.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        with pytest.raises(PrivateOwnerIdentityBlocked):
            enroll_private_owner(db,owner_ref=OWNER,password=PASSWORD,
                totp_secret_base32=SEED,now_epoch=T,
                verified_offline_bootstrap=True)
    engine.dispose()
