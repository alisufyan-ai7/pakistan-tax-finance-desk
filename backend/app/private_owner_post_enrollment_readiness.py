"""P1AT: default-off, one-off READ-ONLY post-enrollment G2 SQL acceptance probe.

This is an attended Railway *private service shell* command, not an HTTP
route, scheduled worker, migration, login or Google network adapter. It
validates live read-only restricted SQL role + exact one-owner/recovery
existence and the independent connector key contracts without ever exposing
the owner, folder, tokens, passwords, DSN, SQL rows or exception details.

Even a PASS never means Railway platform/edge logs, browser MFA/CSRF,
new-key recovery, OAuth consent or a real financial release was accepted.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys

from .drive_google_oauth import private_google_configuration
from .private_owner_login_service import (
    _attest_enrolled_owner, _new_engine,
)
from .private_owner_runtime_preflight import _inventory, _read_key
from .private_owner_http_gateway import _GATEWAY_RE

_STAGE = frozenset({
    "runtime_scope", "connector_key_custody", "approved_folder_contract",
    "private_tls_role_and_one_owner", "complete", "unexpected_failure",
})
_ACTIVATION = (
    "P1AJ_OWNER_LOGIN_RUNTIME",
    "P1AK_OWNER_INGRESS_ENABLED",
    "P1AO_GOOGLE_INGRESS_ENABLED",
    "P1AN_GOOGLE_METADATA_RUNTIME",
    "P1C_GOOGLE_NETWORK_ENABLED",
    "P1AP_OWNER_FOLDER_METADATA_REVIEW_ONLY",
)
_KEYRING_VERSIONS = frozenset({"cfo-google-key-v1", "cfo-google-key-v2"})


class PrivatePostEnrollmentReadinessBlocked(ValueError):
    """Only fixed, scrubbed acceptance stages may be exposed."""


def _report(stage: str) -> dict:
    if stage not in _STAGE:
        stage = "unexpected_failure"
    accepted = stage == "complete"
    return {
        "contract": "personal_cfo_private_post_enrollment_g2_sql_readiness_v1",
        "result": "PASS" if accepted else "BLOCKED",
        "stage": stage,
        "read_only": True,
        "owner_and_recovery_state_present": accepted,
        "isolated_tls_postgres_least_privilege_attested": accepted,
        "private_connector_key_domains_validated": accepted,
        "one_folder_contract_verified_without_google_network": accepted,
        "gateway_value_equality_between_services_independently_verified": False,
        "railway_platform_request_target_logging_independently_accepted": False,
        "new_connector_keys_off_device_restore_tested": False,
        "public_g2_release_authorized": False,
        "google_client_secret_staged_patch_applied": False,
        "google_consent_activated": False,
        "original_document_bytes_accessed": False,
        "real_financial_data_enabled": False,
        "sensitive_values_included": False,
        "database_modified": False,
    }


def _runtime_scope() -> None:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("PERSONAL_CFO_PRIVATE_PREVIEW") != "enabled"
        or tuple(os.getenv(name) for name in (
            "RAILWAY_PROJECT_NAME",
            "RAILWAY_ENVIRONMENT_NAME",
            "RAILWAY_SERVICE_NAME",
        )) != (
            "personal-cfo-dev-sandbox",
            "development",
            "personal-cfo-api-preview",
        )
        or os.getenv("P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT") != "1"
        or any(os.getenv(name, "") == "1" for name in _ACTIVATION)
    ):
        raise PrivatePostEnrollmentReadinessBlocked(
            "Private read-only scope not accepted"
        )


def _independent_connector_keys() -> None:
    # Existing original five-key private owner inventory remains validated
    # separately by P1AA/P1N; this must NOT re-enroll/reset it.
    _inventory()
    existing = {
        _read_key(os.getenv(name, ""))
        for name in (
            "P1N_OWNER_ENCRYPTION_KEY",
            "P1N_OWNER_IDENTITY_HMAC_KEY",
            "P1N_OWNER_SESSION_HMAC_KEY",
            "P1P_OWNER_RECOVERY_ENCRYPTION_KEY",
            "P1P_OWNER_RECOVERY_HMAC_KEY",
        )
    }
    if (
        not _GATEWAY_RE.fullmatch(
            os.getenv("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", "")
        )
        or os.getenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY") != "1"
        or os.getenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY") != "1"
    ):
        raise PrivatePostEnrollmentReadinessBlocked(
            "Private connector proof/configuration missing"
        )
    try:
        keyring = json.loads(
            os.getenv("P1M_METADATA_ENCRYPTION_KEYS_JSON", "")
        )
        if (
            type(keyring) is not dict
            or set(keyring) != _KEYRING_VERSIONS
            or os.getenv("P1M_METADATA_ACTIVE_KEY_ID")
            not in _KEYRING_VERSIONS
        ):
            raise ValueError()
        new_values = [
            _read_key(os.getenv("P1R_OAUTH_STATE_ENCRYPTION_KEY", "")),
            _read_key(os.getenv("P1R_OAUTH_STATE_HMAC_KEY", "")),
            _read_key(keyring["cfo-google-key-v1"]),
            _read_key(keyring["cfo-google-key-v2"]),
            _read_key(os.getenv("P1M_METADATA_ROW_HMAC_KEY", "")),
            _read_key(os.getenv("DRIVE_INDEX_HMAC_KEY", "")),
        ]
        if len(set(new_values) | existing) != len(new_values) + len(existing):
            raise ValueError()
    except Exception:
        raise PrivatePostEnrollmentReadinessBlocked(
            "Distinct private connector keys unavailable"
        ) from None


def check_read_only() -> dict:
    try:
        _runtime_scope()
    except Exception:
        return _report("runtime_scope")
    try:
        _independent_connector_keys()
    except Exception:
        return _report("connector_key_custody")
    try:
        # This consumes only pinned private env/client/HMAC configuration,
        # never Google/Drive provider HTTP or source files.
        private_google_configuration()
    except Exception:
        return _report("approved_folder_contract")
    engine = None
    try:
        # _new_engine rejects financial/superuser/non-private/non-TLS DSN.
        engine = _new_engine()
        with engine.connect() as db:
            # Existing P1AI independently checks exact TLS private owner DB,
            # restricted effective role, and exactly one enrolled owner and
            # one recoverable state. Begins a READ ONLY transaction first.
            _attest_enrolled_owner(db)
    except Exception:
        return _report("private_tls_role_and_one_owner")
    finally:
        if engine is not None:
            engine.dispose()
    return _report("complete")


def main() -> int:
    try:
        result = check_read_only()
    except Exception:
        result = _report("unexpected_failure")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
