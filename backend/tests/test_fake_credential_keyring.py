"""P1K: fake-only custody encryption/rotation/restore + owner MFA recovery veto."""
import base64
from copy import deepcopy
import pytest
from app.fake_credential_keyring import (
    FakeKeyCustodyBlocked, make_fake_keyring, seal_fake_grant,
    open_fake_grant, rotate_fake_grant, inspect_fake_recovery_controls,
)

OWNER="a"*64
FOLDER="b"*64
TOKEN="SYNTHETIC_FAKE_REFRESH_"+("X"*48)
ENC=lambda b:base64.urlsafe_b64encode(b*32).decode("ascii")

@pytest.fixture(autouse=True)
def mode(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1K_FAKE_KEY_CUSTODY_ONLY","1")


def ring(active="fixture-key-v1"):
    return make_fake_keyring(active_id=active,encoded_keys={
        "fixture-key-v1":ENC(b"A"),"fixture-key-v2":ENC(b"B")
    })


def test_envelope_random_aad_authenticated_and_never_plaintext():
    initial=ring()
    a=seal_fake_grant(ring=initial,owner_hmac=OWNER,folder_hmac=FOLDER,fictional_token=TOKEN)
    b=seal_fake_grant(ring=initial,owner_hmac=OWNER,folder_hmac=FOLDER,fictional_token=TOKEN)
    assert a!=b
    assert TOKEN not in a and OWNER not in a and FOLDER not in a
    assert open_fake_grant(ring=initial,owner_hmac=OWNER,folder_hmac=FOLDER,sealed=a)==TOKEN
    with pytest.raises(FakeKeyCustodyBlocked):
        open_fake_grant(ring=initial,owner_hmac="c"*64,folder_hmac=FOLDER,sealed=a)
    with pytest.raises(FakeKeyCustodyBlocked):
        open_fake_grant(ring=initial,owner_hmac=OWNER,folder_hmac="c"*64,sealed=a)
    with pytest.raises(FakeKeyCustodyBlocked):
        open_fake_grant(ring=initial,owner_hmac=OWNER,folder_hmac=FOLDER,sealed=a[:-1]+"A")


def test_rotation_rewrap_and_restore_without_old_key():
    initial=ring()
    old=seal_fake_grant(ring=initial,owner_hmac=OWNER,folder_hmac=FOLDER,fictional_token=TOKEN)
    future=make_fake_keyring(active_id="fixture-key-v2",encoded_keys={
        "fixture-key-v2":ENC(b"B"),"fixture-key-v3":ENC(b"C")})
    result=rotate_fake_grant(old_ring=initial,new_ring=future,
                             owner_hmac=OWNER,folder_hmac=FOLDER,sealed=old)
    assert result["synthetic_only"] is True
    assert result["old_grant_revoked_in_store"] is False
    assert result["real_google_access_enabled"] is False
    assert result["independent_restore_test_required"]
    assert TOKEN not in repr(result)
    assert open_fake_grant(ring=future,owner_hmac=OWNER,folder_hmac=FOLDER,
                           sealed=result["wrapped_grant"])==TOKEN
    with pytest.raises(FakeKeyCustodyBlocked):
        open_fake_grant(ring=future,owner_hmac=OWNER,folder_hmac=FOLDER,sealed=old)
    # A restored generation requires the active new key: an unrelated key fails.
    wrong=make_fake_keyring(active_id="fixture-key-v2",encoded_keys={
        "fixture-key-v2":ENC(b"Q"),"fixture-key-v3":ENC(b"R")})
    with pytest.raises(FakeKeyCustodyBlocked):
        open_fake_grant(ring=wrong,owner_hmac=OWNER,folder_hmac=FOLDER,
                        sealed=result["wrapped_grant"])
    with pytest.raises(FakeKeyCustodyBlocked):
        rotate_fake_grant(old_ring=initial,new_ring=initial,
                          owner_hmac=OWNER,folder_hmac=FOLDER,sealed=old)


@pytest.mark.parametrize("value",[
    "YA29.authentic.refresh-token","SYNTHETIC_FAKE_REFRESH_short",
    "SYNTHETIC_FAKE_REFRESH_"+"X"*160, "",42
])
def test_real_or_unapproved_grants_blocked(value):
    with pytest.raises(FakeKeyCustodyBlocked):
        seal_fake_grant(ring=ring(),owner_hmac=OWNER,folder_hmac=FOLDER,
                        fictional_token=value)


def test_invalid_key_lifecycle_denied():
    for keys in [
        {"fixture-key-v1":ENC(b"A")},
        {"fixture-key-v1":ENC(b"A"),"fixture-key-v2":ENC(b"A")},
        {"fixture-key-v1":ENC(b"A"),"fixture-key-v2":"notbase64"},
        {"fixture-key-v1":ENC(b"A"),"wrong":ENC(b"B")},
    ]:
        with pytest.raises(FakeKeyCustodyBlocked):
            make_fake_keyring(active_id="fixture-key-v1",encoded_keys=keys)
    with pytest.raises(FakeKeyCustodyBlocked):
        make_fake_keyring(active_id="fixture-key-v4",encoded_keys={
            "fixture-key-v1":ENC(b"A"),"fixture-key-v2":ENC(b"B")})


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("P1K_FAKE_KEY_CUSTODY_ONLY","0"),
])
def test_real_mode_and_missing_feature_gates(monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    with pytest.raises(FakeKeyCustodyBlocked):
        ring()
    with pytest.raises(FakeKeyCustodyBlocked):
        inspect_fake_recovery_controls(audit={},password_reverified=False,
                                       enrolled_mfa_present=False)


def test_recovery_requires_exact_chained_state_and_cannot_reset_mfa():
    valid={"synthetic_only":True,"audit_revision":3,"active_code_count":4,
           "audit_chain_verified":True,"encrypted_state":True,
           "prod_owner_recovery_certified":False}
    result=inspect_fake_recovery_controls(audit=valid,password_reverified=True,
                                           enrolled_mfa_present=False)
    assert result["recovery_codes_available"]
    assert result["persisted_code_redemption_separately_required"]
    assert result["any_live_session_created"] is False
    assert result["real_mfa_reset_allowed"] is False
    assert result["owner_recovery_independently_approved"] is False
    for changed in [
        {"audit_chain_verified":False},{"prod_owner_recovery_certified":True},
        {"audit_revision":0},{"active_code_count":-1},{"owner_verified":True}
    ]:
        bad={**valid,**changed}
        with pytest.raises(FakeKeyCustodyBlocked):
            inspect_fake_recovery_controls(audit=bad,password_reverified=True,
                                           enrolled_mfa_present=True)


def test_no_public_key_custody_import_or_google_access():
    from app.preview_api import create_preview_app
    routes={r.path for r in create_preview_app().routes}
    assert "/api/owner/recover" not in routes
    assert "/api/drive/oauth/callback" not in routes
    import inspect
    import app.fake_credential_keyring as candidate
    source=inspect.getsource(candidate)
    assert "requests." not in source and "googleapiclient" not in source


def test_rotation_refuses_same_key_material_disguised_under_new_id():
    old_ring=ring()
    old=seal_fake_grant(ring=old_ring,owner_hmac=OWNER,folder_hmac=FOLDER,fictional_token=TOKEN)
    masquerade=make_fake_keyring(active_id="fixture-key-v3",encoded_keys={
        "fixture-key-v3":ENC(b"A"),  # retired v1 material under different label
        "fixture-key-v4":ENC(b"C"),
    })
    with pytest.raises(FakeKeyCustodyBlocked,match="retire"):
        rotate_fake_grant(old_ring=old_ring,new_ring=masquerade,
                          owner_hmac=OWNER,folder_hmac=FOLDER,sealed=old)
