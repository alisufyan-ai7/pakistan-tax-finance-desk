"""G2 one-time recovery codes: replay, owner binding, expiry and real-mode refusal."""
import base64
import pytest

from app.owner_recovery_codes import (
    RecoveryBlocked, issue_recovery_bundle, redeem_recovery_code,
)


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("OWNER_RECOVERY_HMAC_KEY", base64.urlsafe_b64encode(b"Q"*32).decode())


def test_issue_once_and_redeem_exactly_one_code():
    batch, codes = issue_recovery_bundle(owner_ref="owner", mfa_confirmed=True, issued_epoch=10)
    assert len(codes) == 8 and len(set(codes)) == 8
    assert codes[0] not in repr(batch)
    changed = redeem_recovery_code(bundle=batch, owner_ref="owner",
        presented_code=codes[0], password_confirmed=True, now_epoch=11)
    assert len(changed.consumed_hmacs) == 1
    with pytest.raises(RecoveryBlocked, match="already used"):
        redeem_recovery_code(bundle=changed, owner_ref="owner",
            presented_code=codes[0], password_confirmed=True, now_epoch=12)
    second = redeem_recovery_code(bundle=changed, owner_ref="owner",
        presented_code=codes[1], password_confirmed=True, now_epoch=13)
    assert len(second.consumed_hmacs) == 2
    assert len(batch.consumed_hmacs) == 0  # caller MUST persist transition atomically


@pytest.mark.parametrize("mfa,owner", [(False,"owner"),(True,"unknown Owner"),(True,"")])
def test_issuance_requires_existing_mfa(mfa, owner):
    with pytest.raises(RecoveryBlocked):
        issue_recovery_bundle(owner_ref=owner, mfa_confirmed=mfa, issued_epoch=10)


def test_wrong_owner_password_code_and_expiration():
    batch, codes = issue_recovery_bundle(owner_ref="owner", mfa_confirmed=True, issued_epoch=10)
    for kw in [
        {"owner_ref": "other"}, {"password_confirmed": False},
        {"presented_code": "BAD"}, {"now_epoch": 10+366*86400},
    ]:
        opts = dict(bundle=batch, owner_ref="owner", presented_code=codes[0],
                    password_confirmed=True, now_epoch=11)
        opts.update(kw)
        with pytest.raises(RecoveryBlocked):
            redeem_recovery_code(**opts)


def test_missing_keys_key_rotation_and_real_mode_are_blocked(monkeypatch):
    batch, codes = issue_recovery_bundle(owner_ref="owner", mfa_confirmed=True, issued_epoch=10)
    monkeypatch.delenv("OWNER_RECOVERY_HMAC_KEY")
    with pytest.raises(RecoveryBlocked):
        redeem_recovery_code(bundle=batch, owner_ref="owner",
            presented_code=codes[0], password_confirmed=True, now_epoch=11)
    monkeypatch.setenv("OWNER_RECOVERY_HMAC_KEY", base64.urlsafe_b64encode(b"R"*32).decode())
    with pytest.raises(RecoveryBlocked):
        redeem_recovery_code(bundle=batch, owner_ref="owner",
            presented_code=codes[0], password_confirmed=True, now_epoch=11)
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(RecoveryBlocked):
        issue_recovery_bundle(owner_ref="owner", mfa_confirmed=True, issued_epoch=11)
