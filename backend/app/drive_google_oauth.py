"""Priority 1B: private, owner-consented Google Drive metadata OAuth contract.

No browser-facing public endpoint, credentials, or network calls live here.
Only an explicitly permitted synthetic private client may prepare an OAuth
authorization URL. The connecting owner must consent through Google, and
the app must independently certify private MFA, OAuth custody and Google
restricted-scope policy before enabling genuine source synchronization.

The exact owner folder is supplied ONLY by private configuration; never
a file in public GitHub. The Google Drive API scope is account-wide at the
OAuth layer; our client only ever lists direct children of this folder.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
import hmac
import os
import re
import secrets
from urllib.parse import urlencode, urlsplit, quote

from .drive_inbox_planner import DRIVE_ID, DriveInboxBlocked, _index

GOOGLE_METADATA_SCOPE = "https://www.googleapis.com/auth/drive.metadata.readonly"
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
# The owner registered this EXACT public Railway frontend redirect for the
# existing Personal CFO Web OAuth client. This is an allowed *contract*, not a
# running/approved callback or a newly exposed API service. Only the single
# fixed URL is permitted; arbitrary Railway and user-supplied hosts are denied.
PERSONAL_CFO_RAILWAY_CALLBACK = (
    "https://personal-cfo-frontend-preview-development.up.railway.app"
    "/api/drive/oauth/callback"
)
_CLIENT_ID = re.compile(r"^[A-Za-z0-9._-]{12,220}\.apps\.googleusercontent\.com$")
_CODE = re.compile(r"^[A-Za-z0-9._~\/-]{8,2048}$")
_STATE = re.compile(r"^[A-Za-z0-9_-]{40,128}$")


class PrivateDriveOAuthBlocked(ValueError):
    """Private Google connection has missing/mismatched consent or security."""


@dataclass(frozen=True)
class DriveOAuthConfig:
    client_id: str
    redirect_uri: str
    folder_id: str
    folder_hmac: str


def _guard() -> None:
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("P1B_PRIVATE_OAUTH_CONTRACT_ONLY") != "1"):
        raise PrivateDriveOAuthBlocked("Private Google OAuth not accepted or enabled")


def private_google_configuration() -> DriveOAuthConfig:
    """Owner-only runtime configuration; never a public/preview endpoint."""
    _guard()
    client_id = os.getenv("P1B_GOOGLE_CLIENT_ID", "")
    redirect_uri = os.getenv("P1B_GOOGLE_REDIRECT_URI", "")
    folder_id = os.getenv("P1B_GOOGLE_FOLDER_ID", "")
    folder_hmac = os.getenv("DRIVE_ALLOWED_FOLDER_HMAC", "")
    if not _CLIENT_ID.fullmatch(client_id):
        raise PrivateDriveOAuthBlocked("Google app client registration missing")
    url = urlsplit(redirect_uri)
    railway_contract = (redirect_uri == PERSONAL_CFO_RAILWAY_CALLBACK
        and os.getenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY") == "1")
    loopback_contract = (
        url.scheme == "https" and url.hostname in ("localhost", "127.0.0.1")
        and url.username is None and url.password is None
        and not url.query and not url.fragment
        and url.path == "/api/drive/oauth/callback"
        and url.port in (443, 8443, 9443)
    )
    if not (railway_contract or loopback_contract):
        raise PrivateDriveOAuthBlocked(
            "Google callback must be the explicitly approved HTTPS origin"
        )
    if (not isinstance(folder_id, str) or not DRIVE_ID.fullmatch(folder_id)
        or not re.fullmatch("[0-9a-f]{64}", folder_hmac)
        or not hmac.compare_digest(folder_hmac, _index("folder", folder_id))):
        raise PrivateDriveOAuthBlocked("Approved owner folder integrity not configured")
    return DriveOAuthConfig(client_id, redirect_uri, folder_id, folder_hmac)


@dataclass(frozen=True)
class PendingGoogleConsent:
    authorization_url: str
    state: str
    pkce_verifier: str
    folder_hmac: str


def begin_google_metadata_consent(config: DriveOAuthConfig) -> PendingGoogleConsent:
    """One-time state/PKCE: only server-side encrypted pending storage allowed."""
    _guard()
    if not isinstance(config, DriveOAuthConfig) or config != private_google_configuration():
        raise PrivateDriveOAuthBlocked("Unverified private OAuth configuration")
    # Never accept caller-supplied state or code challenge.
    state = secrets.token_urlsafe(36)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    params = {
        "client_id": config.client_id, "redirect_uri": config.redirect_uri,
        "response_type": "code", "scope": GOOGLE_METADATA_SCOPE,
        "access_type": "offline", "prompt": "consent",
        "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return PendingGoogleConsent(
        GOOGLE_AUTHORIZE_URL+"?"+urlencode(params),
        state, verifier, config.folder_hmac
    )


def validate_google_callback(
    *, state: str, expected_state: str, code: str,
    granted_scope: str, refresh_token: str,
) -> dict:
    """Validate *injected* token-exchange result; no actual tokens in response.

    Google callback must be tied to a single-use encrypted state record that
    is atomically consumed by the private session handler. Google token POST,
    TLS and identity checks are separate implementation/release gates.
    """
    _guard()
    if (not isinstance(state, str) or not isinstance(expected_state, str)
        or not _STATE.fullmatch(state) or not hmac.compare_digest(state, expected_state)
        or not isinstance(code, str) or not _CODE.fullmatch(code)
        or not isinstance(granted_scope, str) or
        set(granted_scope.split()) != {GOOGLE_METADATA_SCOPE}
        or not isinstance(refresh_token, str) or not 24 <= len(refresh_token) <= 4096
        or any(ch in refresh_token for ch in "\r\n\x00")):
        raise PrivateDriveOAuthBlocked("Consent state, offline grant or scope invalid")
    return {
        "private_consent_contract_valid": True,
        "scope": "DRIVE_METADATA_ONLY",
        "owner_folder_restricted_in_application": True,
        "refresh_token_persisted_or_used": False,
        "actual_google_connection_established": False,
        "original_bytes_accessible": False,
        "real_finance_authorized": False,
    }


def redact_private_connection_status(*, oauth_configured: bool,
                                      token_vault_approved: bool) -> dict:
    """Safe owner UI state, never claim connected because client ID exists."""
    return {
        "connection": "AWAITING_PRIVATE_SETUP",
        "oauth_client_configured": bool(oauth_configured),
        "encrypted_token_vault_accepted": bool(token_vault_approved),
        "last_successful_app_sync": None,
        "google_drive_app_connected": False,
        "real_document_import_enabled": False,
        "financial_reconciliation_completed": False,
    }
