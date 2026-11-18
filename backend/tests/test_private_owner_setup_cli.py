"""P1W: offline owner-key generation and terminal-only enrollment guard tests."""
import base64
import os
import stat

import pytest
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app import private_owner_setup_cli as cli


class PrivateTTY:
    def isatty(self):
        return True


def test_offline_signing_key_is_encrypted_0600_never_overwritten(monkeypatch,tmp_path):
    monkeypatch.setattr(cli.sys,"stdin",PrivateTTY())
    monkeypatch.setattr(cli.sys,"stdout",PrivateTTY())
    answers=iter(["SYNTHETIC_offline_very_long_passphrase_2026"]*2)
    monkeypatch.setattr(cli.getpass,"getpass",lambda prompt="":next(answers))
    path=tmp_path/"private-do-not-upload.pem"
    pub=cli.create_offline_recovery_signing_key(str(path))
    assert len(base64.urlsafe_b64decode(pub))==32
    assert path.exists()
    assert stat.S_IMODE(path.stat().st_mode)==0o600
    encrypted=path.read_bytes()
    assert b"ENCRYPTED PRIVATE KEY" in encrypted
    assert b"BEGIN PRIVATE KEY" not in encrypted
    assert load_pem_private_key(
        encrypted,password=b"SYNTHETIC_offline_very_long_passphrase_2026")
    with pytest.raises(cli.PrivateOwnerSetupBlocked):
        cli.create_offline_recovery_signing_key(str(path))


def test_rejects_nonprivate_terminal_and_browser_source_path(monkeypatch,tmp_path):
    class NonTTY:
        def isatty(self):
            return False
    monkeypatch.setattr(cli.sys,"stdin",NonTTY())
    monkeypatch.setattr(cli.sys,"stdout",NonTTY())
    with pytest.raises(cli.PrivateOwnerSetupBlocked):
        cli.create_offline_recovery_signing_key(str(tmp_path/"offline.pem"))
    with pytest.raises(cli.PrivateOwnerSetupBlocked):
        cli.bootstrap_with_private_terminal()


def test_operator_private_database_must_be_independently_restricted(monkeypatch):
    monkeypatch.delenv("P1W_OWNER_CREDENTIAL_DATABASE_URL",raising=False)
    with pytest.raises(cli.PrivateOwnerSetupBlocked):
        cli._operator_database_url()
    monkeypatch.setenv("DATABASE_URL","postgresql://synthetic:fake@localhost/db")
    monkeypatch.setenv("P1W_OWNER_CREDENTIAL_DATABASE_URL",
                       "postgresql://synthetic:fake@localhost/db")
    with pytest.raises(cli.PrivateOwnerSetupBlocked):
        cli._operator_database_url()
    monkeypatch.setenv("P1W_OWNER_CREDENTIAL_DATABASE_URL",
                       "sqlite:///tmp/fake.db")
    with pytest.raises(cli.PrivateOwnerSetupBlocked):
        cli._operator_database_url()


def test_no_public_setup_or_oauth_route_mounting():
    from app.preview_api import create_preview_app
    paths={r.path for r in create_preview_app().routes}
    assert "/api/owner/setup" not in paths
    assert "/api/owner/enroll" not in paths
    assert "/internal/drive/auth/enroll" not in paths
    assert "/api/drive/oauth/callback" not in paths


def test_operator_url_requires_isolated_restricted_tls_role(monkeypatch):
    url = ("postgresql+psycopg://personal_cfo_owner_credentials:"
           "SYNTHETIC_ONLY_fake_encoded_password%402026"
           "@postgres.railway.internal:5432/personal_cfo_owner_auth?sslmode=require")
    monkeypatch.setenv("P1W_OWNER_CREDENTIAL_DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_URL","postgresql+psycopg://finance:fake@other.railway.internal/finance")
    assert cli._operator_database_url() == url


@pytest.mark.parametrize("wrong", [
    "postgresql+psycopg://postgres:fake@postgres.railway.internal:5432/personal_cfo_owner_auth?sslmode=require",
    "postgresql+psycopg://personal_cfo_owner_credentials:fake@postgres.railway.internal:5432/finance?sslmode=require",
    "postgresql+psycopg://personal_cfo_owner_credentials:fake@localhost:5432/personal_cfo_owner_auth?sslmode=require",
    "postgresql+psycopg://personal_cfo_owner_credentials:fake@postgres.railway.internal:5432/personal_cfo_owner_auth",
    "postgresql+psycopg://personal_cfo_owner_credentials:fake@postgres.railway.internal:5432/personal_cfo_owner_auth?sslmode=disable",
    "postgresql+psycopg://personal_cfo_owner_credentials:fake@postgres.railway.internal:5432/personal_cfo_owner_auth?sslmode=require&options=-c",
])
def test_operator_url_refuses_admin_finance_public_hosts_or_cleartext(monkeypatch,wrong):
    monkeypatch.setenv("P1W_OWNER_CREDENTIAL_DATABASE_URL",wrong)
    monkeypatch.setenv("DATABASE_URL","postgresql://synthetic:fake@other.railway.internal/finance")
    with pytest.raises(cli.PrivateOwnerSetupBlocked):
        cli._operator_database_url()
