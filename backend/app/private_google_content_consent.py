"""P4: independent Google drive.readonly consent/exchange contract.

The existing one-owner Google metadata-only OAuth grant MUST remain intact.
This code is intentionally UNMOUNTED until its caller is the independently
authenticated, one-time session PKCE controller and its distinct encrypted
content-token custody is reviewed. Merely declaring a scope in Google Cloud
does not grant that scope to Personal CFO.

Only a real provider authorization response granting exactly drive.readonly
can release an access/refresh token to a PRIVATE caller. Never put either
token or the OAuth URL in logs, exceptions, GitHub, HTTP cache, or finance rows.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from hashlib import sha256
import os
import re
import secrets
from collections.abc import Callable
from urllib.parse import urlencode

from .drive_google_oauth import (
    DriveOAuthConfig, GOOGLE_AUTHORIZE_URL, GOOGLE_TOKEN_URL,
    PERSONAL_CFO_RAILWAY_CALLBACK, private_google_configuration,
)
from .private_drive_google_http import _http_google, _client_secret

GOOGLE_CONTENT_READ_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
_STATE = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
_CODE = re.compile(r"^[A-Za-z0-9._~/-]{8,2048}$")
_VERIFIER = re.compile(r"^[A-Za-z0-9_-]{43,128}$")


class PrivateContentConsentBlocked(ValueError):
    """The owner has not completed an independently accepted content grant."""


@dataclass(frozen=True)
class PendingContentConsent:
    authorization_url: str = field(repr=False)
    state: str = field(repr=False)
    pkce_verifier: str = field(repr=False)
    folder_hmac: str


def _gate(config: DriveOAuthConfig) -> None:
    if (
        os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P4_CONTENT_OAUTH_CONTRACT_ONLY") != "1"
        or os.getenv("P4_G2_OWNER_SESSION_CONTENT_REVIEWED") != "1"
        or os.getenv("P4_G3_RESTRICTED_SCOPE_ACCEPTED") != "1"
    ):
        raise PrivateContentConsentBlocked("Google content read authorization disabled")
    try:
        if (type(config) is not DriveOAuthConfig
            or config != private_google_configuration()
            or config.redirect_uri != PERSONAL_CFO_RAILWAY_CALLBACK):
            raise ValueError()
    except Exception:
        raise PrivateContentConsentBlocked("Unapproved Google content client/folder") from None


def begin_google_content_read_consent(
    *, config: DriveOAuthConfig,
) -> PendingContentConsent:
    """Generate unguessable, exact-scope content OAuth request.

    Caller MUST bind state/verifier to owner session, folder and client in a
    one-time encrypted PostgreSQL row before returning this URL to an already
    signed-in owner. The returned object cannot certify that this occurred.
    """
    _gate(config)
    state = secrets.token_urlsafe(36)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    url = GOOGLE_AUTHORIZE_URL + "?" + urlencode({
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_CONTENT_READ_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "false",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return PendingContentConsent(url, state, verifier, config.folder_hmac)


def _token(raw: object, *, needs_refresh: bool) -> tuple[str, str | None]:
    if type(raw) is not dict:
        raise PrivateContentConsentBlocked("Untrusted Google content consent result")
    access = raw.get("access_token")
    refresh = raw.get("refresh_token")
    if (type(access) is not str or not 20 <= len(access) <= 8192
        or any(ord(c) < 33 or ord(c) > 126 for c in access)
        or raw.get("token_type") != "Bearer"
        or raw.get("scope") != GOOGLE_CONTENT_READ_SCOPE
        or type(raw.get("expires_in")) is not int
        or not 1 <= raw["expires_in"] <= 86400
        or (refresh is not None
            and (type(refresh) is not str or not 24 <= len(refresh) <= 4096
                 or any(ord(c) < 33 or ord(c) > 126 for c in refresh)))
        or (needs_refresh and not refresh)):
        raise PrivateContentConsentBlocked("Google did not grant exact read-only content permission")
    return access, refresh


def exchange_google_content_code(
    *, code: str, verifier: str, config: DriveOAuthConfig,
    transport: Callable = _http_google,
) -> tuple[str, str]:
    """After ONE-USE session state claim, exchange only the exact OAuth code.

    A refresh token MUST be sealed in a DIFFERENT scoped vault from the
    metadata-only grant. This function cannot store it and is not a callback.
    """
    _gate(config)
    if (type(code) is not str or _CODE.fullmatch(code) is None
        or type(verifier) is not str or _VERIFIER.fullmatch(verifier) is None
        or not callable(transport)):
        raise PrivateContentConsentBlocked("Missing authenticated content PKCE claim")
    try:
        raw = transport("POST", GOOGLE_TOKEN_URL, {
            "client_id": config.client_id,
            "client_secret": _client_secret(),
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": config.redirect_uri,
        }, None)
        access, refresh = _token(raw, needs_refresh=True)
        if refresh is None:
            raise ValueError()
        return access, refresh
    except Exception:
        raise PrivateContentConsentBlocked(
            "Google content permission exchange was not accepted"
        ) from None


def refresh_google_content_token(
    *, refresh_token: str, config: DriveOAuthConfig,
    transport: Callable = _http_google,
) -> tuple[str, str | None]:
    """Use ONLY a previously authenticated CONTENT vault refresh token."""
    _gate(config)
    if (type(refresh_token) is not str or not 24 <= len(refresh_token) <= 4096
        or any(ord(c) < 33 or ord(c) > 126 for c in refresh_token)
        or not callable(transport)):
        raise PrivateContentConsentBlocked("Invalid sealed content grant")
    try:
        raw = transport("POST", GOOGLE_TOKEN_URL, {
            "client_id": config.client_id,
            "client_secret": _client_secret(),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }, None)
        return _token(raw, needs_refresh=False)
    except Exception:
        raise PrivateContentConsentBlocked(
            "Google content permission refresh rejected; owner may need to re-authorize"
        ) from None
