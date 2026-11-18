"""P1AR: prepare all default-off Google metadata/G2 gateway keys in one Mac command.

STRICTLY PRIVATE ATTENDED OWNER PREPARATION. No OAuth grant, restored owner DB,
public login, source media or financial data is accessed. All fresh cryptographic
material is generated locally; passed to existing named Railway services ONLY
through subprocess stdin with --skip-deploys; never printed, stored in a file,
put on argv, placed in GitHub or returned to ChatGPT.

Do not execute after any G2 owner/Google/runtime route has been activated.
Preparation replaces connector-only keys, so never use it to rotate an
already-issued real Google refresh grant. Always use the separate reviewed
key-rotation process after first consent.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import hmac
import json
import re
import secrets
import shutil
import subprocess
import sys

PROJECT = "7021b227-f704-43d6-bcff-debdb7255b81"
ENV = "development"
BACKEND = "personal-cfo-api-preview"
FRONTEND = "personal-cfo-frontend-preview"
APPROVAL = "PREPARE PERSONAL CFO GOOGLE METADATA KEYS ONLY"
_FOLDER = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
_CLIENT = re.compile(r"^[A-Za-z0-9._-]{12,220}\.apps\.googleusercontent\.com$")
_CALLBACK = (
    "https://personal-cfo-frontend-preview-development.up.railway.app"
    "/api/drive/oauth/callback"
)
_ACTIVE_FLAGS = (
    "P1AJ_OWNER_LOGIN_RUNTIME", "P1AK_OWNER_INGRESS_ENABLED",
    "P1AO_GOOGLE_INGRESS_ENABLED", "P1AN_GOOGLE_METADATA_RUNTIME",
    "P1C_GOOGLE_NETWORK_ENABLED", "P1AP_OWNER_FOLDER_METADATA_REVIEW_ONLY",
)
_KEY_NAMES = (
    "P1R_OAUTH_STATE_ENCRYPTION_KEY", "P1R_OAUTH_STATE_HMAC_KEY",
    "P1M_METADATA_ENCRYPTION_KEYS_JSON", "P1M_METADATA_ROW_HMAC_KEY",
    "DRIVE_INDEX_HMAC_KEY",
    "DRIVE_ALLOWED_FOLDER_HMAC",
)


class PrivateGoogleKeyPreparationBlocked(ValueError):
    """A secure owner-only connector key preparation cannot proceed."""


def _command(service: str) -> list[str]:
    if service not in (BACKEND, FRONTEND):
        raise PrivateGoogleKeyPreparationBlocked("Unapproved Railway service")
    return [
        "--project", PROJECT, "--environment", ENV,
        "--service", service,
    ]


def _run_service_vars(service: str) -> dict[str, str]:
    try:
        result = subprocess.run(
            ["railway", "variable", "list", "--kv", *_command(service)],
            capture_output=True, text=True, timeout=45, check=False,
        )
        if result.returncode != 0 or len(result.stdout) > 150_000:
            raise ValueError()
        result_dict = {}
        for line in result.stdout.splitlines():
            if "=" not in line:
                continue
            name, value = line.split("=", 1)
            if re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", name):
                result_dict[name] = value
        if not result_dict:
            raise ValueError()
        return result_dict
    except Exception:
        # No values, folder, database URL or CLI stderr ever reach output.
        raise PrivateGoogleKeyPreparationBlocked(
            "Approved Railway service configuration unavailable"
        ) from None


def _set_stdin(service: str, name: str, value: str) -> None:
    if (
        service not in (BACKEND, FRONTEND)
        or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", name)
        or not isinstance(value, str)
        or not 1 <= len(value) <= 1500
        or any(c in value for c in "\r\n\0")
    ):
        raise PrivateGoogleKeyPreparationBlocked("Private key write denied")
    try:
        result = subprocess.run(
            ["railway", "variable", "set", name, "--stdin",
             *_command(service), "--skip-deploys"],
            input=value, text=True, capture_output=True, timeout=60,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError()
    except Exception:
        raise PrivateGoogleKeyPreparationBlocked(
            "Private key preparation incomplete; release remains disabled"
        ) from None


def _new_key() -> bytes:
    return secrets.token_bytes(32)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _folder_tag(key: bytes, folder_id: str) -> str:
    return hmac.new(
        key,
        ("personal-cfo:drive-inbox:v1:folder:" + folder_id).encode("utf-8"),
        sha256,
    ).hexdigest()


def prepare() -> dict:
    if (
        sys.platform != "darwin"
        or not sys.stdin.isatty()
        or not sys.stdout.isatty()
        or shutil.which("railway") is None
    ):
        raise PrivateGoogleKeyPreparationBlocked(
            "Attended authenticated Mac and Railway CLI required"
        )
    print("Prepare private Personal CFO Google metadata + owner gateway keys.")
    print("Nothing will be deployed or publicly enabled. No secrets are displayed.")
    if input("Type the exact approval phrase: ").strip() != APPROVAL:
        raise PrivateGoogleKeyPreparationBlocked(
            "Owner has not approved connector preparation"
        )
    backend = _run_service_vars(BACKEND)
    frontend = _run_service_vars(FRONTEND)
    # Protect any already-active real grant/session: never overwrite source
    # protection keys while a live owner/Google HTTP entrypoint is enabled.
    if any(scope.get(k, "") == "1"
           for scope in (backend, frontend) for k in _ACTIVE_FLAGS):
        raise PrivateGoogleKeyPreparationBlocked(
            "Active owner or Google runtime must use reviewed key rotation"
        )
    folder = backend.get("P1B_GOOGLE_FOLDER_ID", "")
    client = backend.get("P1B_GOOGLE_CLIENT_ID", "")
    callback = backend.get("P1B_GOOGLE_REDIRECT_URI", "")
    if (
        _FOLDER.fullmatch(folder) is None
        or _CLIENT.fullmatch(client) is None
        or callback != _CALLBACK
    ):
        raise PrivateGoogleKeyPreparationBlocked(
            "Existing approved Google client/callback/folder not configured"
        )
    # Six independent keys; the front end gets only the separate gateway
    # proof, never any Google encryption or source-key material.
    p1r_enc, p1r_mac, p1m_v1, p1m_v2, p1m_mac, index_key = (
        _new_key() for _ in range(6)
    )
    if len({p1r_enc, p1r_mac, p1m_v1, p1m_v2, p1m_mac, index_key}) != 6:
        raise PrivateGoogleKeyPreparationBlocked(
            "Cryptographic key separation failed"
        )
    backend_vars = {
        "P1R_OAUTH_STATE_ENCRYPTION_KEY": _encode(p1r_enc),
        "P1R_OAUTH_STATE_HMAC_KEY": _encode(p1r_mac),
        "P1M_METADATA_ENCRYPTION_KEYS_JSON": json.dumps({
            "cfo-google-key-v1": _encode(p1m_v1),
            "cfo-google-key-v2": _encode(p1m_v2),
        }, separators=(",", ":")),
        "P1M_METADATA_ACTIVE_KEY_ID": "cfo-google-key-v1",
        "P1M_METADATA_ROW_HMAC_KEY": _encode(p1m_mac),
        "DRIVE_INDEX_HMAC_KEY": _encode(index_key),
        "DRIVE_ALLOWED_FOLDER_HMAC": _folder_tag(index_key, folder),
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY": "1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY": "1",
    }
    # Backend-only secrets are independent of existing five escrowed owner
    # identity/recovery keys and the staged Google OAuth client secret.
    for name, value in backend_vars.items():
        _set_stdin(BACKEND, name, value)

    old_b = backend.get("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", "")
    old_f = frontend.get("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", "")
    if (old_b and old_f and hmac.compare_digest(old_b, old_f)
        and re.fullmatch(r"[A-Za-z0-9_-]{48,256}", old_b)):
        gateway_prepared = True
    else:
        # Generate one single value for both existing services, without
        # shell argv, user copy/paste or an additional resource/secret file.
        gateway = secrets.token_urlsafe(64)
        if re.fullmatch(r"[A-Za-z0-9_-]{48,256}", gateway) is None:
            raise PrivateGoogleKeyPreparationBlocked(
                "New private gateway proof invalid"
            )
        _set_stdin(BACKEND, "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", gateway)
        _set_stdin(FRONTEND, "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN", gateway)
        gateway_prepared = True
    return {
        "approved_existing_railway_services_only": True,
        "new_private_key_domains_prepared": 6,
        "approved_folder_hmac_prepared_without_printing_id": True,
        "gateway_proof_prepared_for_both_services": gateway_prepared,
        "private_secret_values_printed": False,
        "owner_identity_and_recovery_keys_unchanged": True,
        "railway_deployments_triggered": False,
        "google_client_secret_staged_patch_applied": False,
        "public_owner_or_google_routes_activated": False,
        "real_google_grant_created": False,
        "original_document_bytes_accessed": False,
        "real_financial_mode_enabled": False,
    }


def main() -> int:
    try:
        print(json.dumps(prepare(), sort_keys=True))
        return 0
    except PrivateGoogleKeyPreparationBlocked:
        print(
            "Private connector key preparation denied or incomplete; "
            "public login and Google consent remain disabled.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
