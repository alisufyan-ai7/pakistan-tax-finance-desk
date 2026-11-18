"""P1AT: fictional-only read-only post-enrollment readiness checks.

No Railway, real owner, auth password/TOTP or Google network in CI.
"""
from contextlib import contextmanager
import base64

import pytest

from app import private_owner_post_enrollment_readiness as readiness
from app.drive_inbox_planner import _index
from app.drive_google_oauth import PERSONAL_CFO_RAILWAY_CALLBACK


FOLDER = "SYNTHETIC_TEST_PRIVATE_P1AT_FOLDER_2026"
CLIENT = "000000000000-fakefixture.apps.googleusercontent.com"
OWNER = "SYNTHETIC_TEST_P1AT_OWNER_2026"


def key(n):
    return base64.urlsafe_b64encode(bytes([n]) * 32).decode("ascii")


class FakeEngine:
    def __init__(self):
        self.closed = 0
        self.connected = 0

    @contextmanager
    def connect(self):
        self.connected += 1
        yield "FAKE_STRICT_READ_ONLY_SQL_CONNECTION"

    def dispose(self):
        self.closed += 1


@pytest.fixture
def approved(monkeypatch):
    env = {
        "APP_DATA_MODE": "synthetic",
        "PERSONAL_CFO_PRIVATE_PREVIEW": "enabled",
        "RAILWAY_PROJECT_NAME": "personal-cfo-dev-sandbox",
        "RAILWAY_ENVIRONMENT_NAME": "development",
        "RAILWAY_SERVICE_NAME": "personal-cfo-api-preview",
        "P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT": "1",
        "P1N_OWNER_ENCRYPTION_KEY": key(1),
        "P1N_OWNER_IDENTITY_HMAC_KEY": key(2),
        "P1N_OWNER_SESSION_HMAC_KEY": key(3),
        "P1P_OWNER_RECOVERY_ENCRYPTION_KEY": key(4),
        "P1P_OWNER_RECOVERY_HMAC_KEY": key(5),
        "P1Q_OPERATOR_PUBLIC_KEY": key(6),
        "P1W_OWNER_REF": OWNER,
        "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN": "G"*90,
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY": "1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY": "1",
        "P1B_GOOGLE_CLIENT_ID": CLIENT,
        "P1B_GOOGLE_REDIRECT_URI": PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_FOLDER_ID": FOLDER,
        "P1R_OAUTH_STATE_ENCRYPTION_KEY": key(7),
        "P1R_OAUTH_STATE_HMAC_KEY": key(8),
        "P1M_METADATA_ENCRYPTION_KEYS_JSON": (
            '{"cfo-google-key-v1":"' + key(9) +
            '","cfo-google-key-v2":"' + key(10) + '"}'
        ),
        "P1M_METADATA_ACTIVE_KEY_ID": "cfo-google-key-v1",
        "P1M_METADATA_ROW_HMAC_KEY": key(11),
        "DRIVE_INDEX_HMAC_KEY": key(12),
    }
    for n,v in env.items():
        monkeypatch.setenv(n,v)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    for name in readiness._ACTIVATION:
        monkeypatch.delenv(name, raising=False)
    engine=FakeEngine()
    monkeypatch.setattr(readiness, "_new_engine", lambda: engine)
    called=[]
    monkeypatch.setattr(
        readiness, "_attest_enrolled_owner",
        lambda conn: called.append(conn),
    )
    return monkeypatch, engine, called


def test_complete_read_only_attestation_is_not_full_g2_acceptance(approved):
    _, engine, called = approved
    report = readiness.check_read_only()
    assert report["result"] == "PASS"
    assert report["stage"] == "complete"
    assert report["owner_and_recovery_state_present"] is True
    assert report["private_connector_key_domains_validated"] is True
    assert report["isolated_tls_postgres_least_privilege_attested"] is True
    assert report["one_folder_contract_verified_without_google_network"] is True
    assert report["public_g2_release_authorized"] is False
    assert report["railway_platform_request_target_logging_independently_accepted"] is False
    assert report["gateway_value_equality_between_services_independently_verified"] is False
    assert report["new_connector_keys_off_device_restore_tested"] is False
    assert report["sensitive_values_included"] is False
    assert report["database_modified"] is False
    assert called == ["FAKE_STRICT_READ_ONLY_SQL_CONNECTION"]
    assert engine.connected == engine.closed == 1
    assert CLIENT not in str(report)
    assert OWNER not in str(report)
    assert FOLDER not in str(report)


@pytest.mark.parametrize("name,value", [
    ("APP_DATA_MODE","real"),
    ("PERSONAL_CFO_PRIVATE_PREVIEW","0"),
    ("RAILWAY_PROJECT_NAME","other"),
    ("RAILWAY_ENVIRONMENT_NAME","production"),
    ("RAILWAY_SERVICE_NAME","other"),
    ("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT","0"),
    ("P1AJ_OWNER_LOGIN_RUNTIME","1"),
    ("P1AN_GOOGLE_METADATA_RUNTIME","1"),
    ("P1C_GOOGLE_NETWORK_ENABLED","1"),
])
def test_scope_and_active_g2_flags_refused_before_sql(approved,name,value):
    monkeypatch,engine,called=approved
    monkeypatch.setenv(name,value)
    report=readiness.check_read_only()
    assert report["result"]=="BLOCKED"
    assert report["stage"]=="runtime_scope"
    assert engine.connected==engine.closed==0
    assert not called


@pytest.mark.parametrize("name,value", [
    ("P1R_OAUTH_STATE_ENCRYPTION_KEY","not-base64"),
    ("P1R_OAUTH_STATE_HMAC_KEY",key(1)),
    ("P1M_METADATA_ROW_HMAC_KEY",key(9)),
    ("P1M_METADATA_ACTIVE_KEY_ID","cfo-google-key-v99"),
    ("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN","short"),
    ("DRIVE_INDEX_HMAC_KEY",""),
    ("P1B_PRIVATE_OAUTH_CONTRACT_ONLY","0"),
])
def test_connector_key_invalid_or_reused_never_contacts_sql(approved,name,value):
    monkeypatch,engine,called=approved
    monkeypatch.setenv(name,value)
    report=readiness.check_read_only()
    assert report["result"]=="BLOCKED"
    assert report["stage"]=="connector_key_custody"
    assert engine.connected==0
    assert not called


@pytest.mark.parametrize("name,value", [
    ("P1B_GOOGLE_REDIRECT_URI","https://attacker.invalid/callback"),
    ("P1B_GOOGLE_FOLDER_ID","wrong"),
    ("DRIVE_ALLOWED_FOLDER_HMAC","f"*64),
])
def test_unpinned_google_client_and_folder_refused_without_network(approved,name,value):
    monkeypatch,engine,called=approved
    monkeypatch.setenv(name,value)
    report=readiness.check_read_only()
    assert report["stage"]=="approved_folder_contract"
    assert engine.connected==0
    assert not called


def test_sql_attestation_failure_is_scrubbed_and_engine_closed(approved,capsys):
    monkeypatch,engine,_=approved
    secret="SYNTHETIC_FAKE_PG_DSN_PASSWORD_MUST_NOT_LOG"
    def denied(connection):
        raise RuntimeError(secret)
    monkeypatch.setattr(readiness,"_attest_enrolled_owner",denied)
    assert readiness.main() == 1
    output=capsys.readouterr().out
    assert secret not in output
    assert FOLDER not in output
    assert CLIENT not in output
    assert OWNER not in output
    assert '"stage": "private_tls_role_and_one_owner"' in output
    assert '"result": "BLOCKED"' in output
    assert '"public_g2_release_authorized": false' in output
    assert engine.connected==engine.closed==1
