"""P1Z synthetic-only local escrow security and fail-closed tests."""
import json
import os
import stat
from types import SimpleNamespace

import pytest

from app import private_owner_key_custody as custody


@pytest.fixture(autouse=True)
def terminal(monkeypatch):
    monkeypatch.setattr(custody.sys,"stdin",SimpleNamespace(isatty=lambda:True))
    monkeypatch.setattr(custody.sys,"stdout",SimpleNamespace(isatty=lambda:True))
    answers=iter(["SYNTHETIC owner escrow long offline passphrase 2026"]*20)
    monkeypatch.setattr(custody.getpass,"getpass",lambda prompt="":next(answers))


def test_encrypted_owner_keys_are_distinct_256_bit_and_never_written_plain(tmp_path):
    path=tmp_path/"owner-keys.enc"
    report=custody.create(str(path))
    assert report["encrypted_file_created"]
    assert report["distinct_owner_runtime_keys"]==5
    assert not report["railway_variables_configured"]
    assert stat.S_IMODE(path.stat().st_mode)==0o600
    raw=path.read_bytes()
    data=json.loads(raw)
    assert set(data)=={"format","salt","nonce","ciphertext"}
    assert b"P1N_OWNER_ENCRYPTION_KEY" not in raw
    assert b"P1W_OWNER_REF" not in raw
    assert custody.verify(str(path))["authenticated_decryption"]
    retrieved={
        name:custody.reveal(str(path),name) for name in
        (*custody._SECRET_NAMES,custody._OWNER_NAME)
    }
    assert len(set(retrieved.values()))==6
    for name in custody._SECRET_NAMES:
        assert len(custody._decode(retrieved[name]))==32
        assert retrieved[name].encode() not in raw
    assert len(retrieved[custody._OWNER_NAME])>=16
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create(str(path))


def test_wrong_passphrase_detected_without_leaking_ciphertext(tmp_path,monkeypatch):
    path=tmp_path/"owner-keys.enc"
    custody.create(str(path))
    monkeypatch.setattr(custody.getpass,"getpass",lambda prompt="":"WRONG PASSCODE never use")
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked) as error:
        custody.verify(str(path))
    assert "WRONG PASSCODE" not in str(error.value)


def test_tampered_ciphertext_rejected(tmp_path):
    path=tmp_path/"owner-keys.enc"
    custody.create(str(path))
    obj=json.loads(path.read_text())
    obj["ciphertext"]=obj["ciphertext"][:-4]+"AAAA"
    path.write_text(json.dumps(obj))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.reveal(str(path),"P1N_OWNER_ENCRYPTION_KEY")


def test_paths_are_absolute_and_never_inside_source_tree(tmp_path):
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create("relative-file.enc")
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create(str(tmp_path/"backend"/"secret.enc"))
    (tmp_path/"backend").mkdir()
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create(str(tmp_path/"backend"/"secret.enc"))


def test_invalid_key_name_denied_before_passphrase(tmp_path):
    path=tmp_path/"owner-keys.enc"
    custody.create(str(path))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.reveal(str(path),"POSTGRES_PASSWORD")
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.reveal(str(path),"P1C_GOOGLE_CLIENT_SECRET")


def test_requires_private_attended_tty(monkeypatch,tmp_path):
    monkeypatch.setattr(custody.sys,"stdin",SimpleNamespace(isatty=lambda:False))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.create(str(tmp_path/"keys.enc"))
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody.verify(str(tmp_path/"keys.enc"))


def test_payload_wrong_key_size_or_duplicate_domains_denied():
    from base64 import urlsafe_b64encode
    v={name:urlsafe_b64encode(bytes([i])*32).decode()
       for i,name in enumerate(custody._SECRET_NAMES)}
    v[custody._OWNER_NAME]="SYNTHETIC_ONE_OWNER_REFERENCE"
    assert custody._validate(v)
    v[custody._SECRET_NAMES[0]]=v[custody._SECRET_NAMES[1]]
    with pytest.raises(custody.LocalOwnerKeyCustodyBlocked):
        custody._validate(v)
