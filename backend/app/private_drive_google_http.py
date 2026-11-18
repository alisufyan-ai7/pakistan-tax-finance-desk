"""P1C restricted Google OAuth code exchange + owner-folder metadata verification.

Uses only fixed Google HTTPS endpoints, bounded response JSON, no redirects and
default-verified TLS. No file media/download endpoints, no write scopes, no
Drive-wide search. An explicitly enabled PRIVATE LOOPBACK host may use this
transport; public Railway, CI and APP_DATA_MODE=real do not.

The external HTTP adapter is injection-friendly for fully synthetic tests,
with no live Google requests in source CI. Do not expose access/refresh tokens,
authorization codes, folder IDs, provider errors or raw names in logs.
"""
from __future__ import annotations

from collections.abc import Callable
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPSHandler, HTTPRedirectHandler, Request, build_opener,
)

from .drive_google_oauth import (
    GOOGLE_METADATA_SCOPE, GOOGLE_TOKEN_URL, DriveOAuthConfig,
    PrivateDriveOAuthBlocked, private_google_configuration,
)
from .private_drive_oauth_vault import (
    PrivateGoogleOAuthVault, PrivateDriveVaultBlocked,
)

GOOGLE_DRIVE_FOLDER_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_LIST_URL = "https://www.googleapis.com/drive/v3/files"
_GOOGLE_ABOUT_URL = "https://www.googleapis.com/drive/v3/about"
_MAX_RESPONSE_BYTES = 32768
_EXPECTED_FOLDER_MIME = "application/vnd.google-apps.folder"
_ID = re.compile(r"^[A-Za-z0-9_-]{10,200}$")


class PrivateGoogleNetworkBlocked(ValueError):
    """Google provider or local connection boundary denied."""


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PrivateGoogleNetworkBlocked("Unexpected Google API redirect refused")


def _guard_network() -> DriveOAuthConfig:
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("P1C_GOOGLE_NETWORK_ENABLED") != "1"
        or os.getenv("P1C_PRIVATE_OWNER_MFA_ACCEPTED") != "1"
        or (
            os.getenv("P1C_LOCAL_OAUTH_VAULT_ENABLED") != "1"
            and not (
                os.getenv("P1AL_CLOUD_METADATA_NETWORK_ONLY") == "1"
                and os.getenv("P1AL_G2_EXACT_OAUTH_REVIEWED") == "1"
                and os.getenv("P1M_PRIVATE_METADATA_CUSTODY_ONLY") == "1"
                and os.getenv("P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED") == "1"
                and os.getenv("P1R_PRIVATE_OAUTH_STATE_ONLY") == "1"
                and os.getenv("P1R_G2_SESSION_OAUTH_REVIEWED") == "1"
                and os.getenv("P1D_RAILWAY_CALLBACK_CONTRACT_ONLY") == "1"
            )
        )):
        raise PrivateGoogleNetworkBlocked("Private Google metadata network not approved")
    try:
        return private_google_configuration()
    except PrivateDriveOAuthBlocked:
        raise PrivateGoogleNetworkBlocked("Private Google metadata network not approved") from None


def _http_google(method: str, url: str, form: dict | None, bearer: str | None) -> dict:
    """Allowlisted non-redirecting TLS: no generic URL/network primitive."""
    _guard_network()
    allowed = {
        GOOGLE_TOKEN_URL, _GOOGLE_ABOUT_URL,
    }
    if not (url in allowed or url.startswith(GOOGLE_DRIVE_FOLDER_URL + "/")
            or url.startswith(GOOGLE_DRIVE_LIST_URL + "?")):
        raise PrivateGoogleNetworkBlocked("Unexpected Google API endpoint")
    if url.startswith(GOOGLE_DRIVE_LIST_URL + "?"):
        # Only approved Drive query is ever built by list_owner_folder_page.
        pass
    if method not in {"GET", "POST"}:
        raise PrivateGoogleNetworkBlocked("Unapproved Google operation")
    if method=="POST" and url!=GOOGLE_TOKEN_URL:
        raise PrivateGoogleNetworkBlocked("Only OAuth token POST permitted")
    if method=="GET" and url==GOOGLE_TOKEN_URL:
        raise PrivateGoogleNetworkBlocked("OAuth token endpoint cannot be queried")
    data=urlencode(form).encode("ascii") if form is not None else None
    headers={"Accept":"application/json","User-Agent":"PersonalCFO-PrivateMetadata/1"}
    if data is not None:
        headers["Content-Type"]="application/x-www-form-urlencoded"
    if bearer is not None:
        if not isinstance(bearer,str) or not 20<=len(bearer)<=8192 or any(
                x in bearer for x in "\r\n\x00"):
            raise PrivateGoogleNetworkBlocked("Invalid private metadata token")
        headers["Authorization"]="Bearer "+bearer
    opener=build_opener(HTTPSHandler(),_NoRedirects())
    request=Request(url,data=data,headers=headers,method=method)
    try:
        with opener.open(request,timeout=8) as response:
            if response.status!=200 or response.headers.get("Content-Type","").split(";")[0].strip()!="application/json":
                raise PrivateGoogleNetworkBlocked("Google API returned an unsupported response")
            raw=response.read(_MAX_RESPONSE_BYTES+1)
    except (HTTPError,URLError,TimeoutError,OSError):
        raise PrivateGoogleNetworkBlocked("Private Google API temporarily unavailable") from None
    if len(raw)>_MAX_RESPONSE_BYTES:
        raise PrivateGoogleNetworkBlocked("Google response exceeded safe limit")
    try:
        parsed=json.loads(raw)
    except (UnicodeError,ValueError):
        raise PrivateGoogleNetworkBlocked("Google response failed validation") from None
    if type(parsed) is not dict:
        raise PrivateGoogleNetworkBlocked("Google response failed validation")
    return parsed


def _client_secret() -> str:
    secret=os.getenv("P1C_GOOGLE_CLIENT_SECRET","")
    if not 20<=len(secret)<=512 or any(c in secret for c in "\r\n\x00"):
        raise PrivateGoogleNetworkBlocked("Private OAuth client secret is not configured")
    return secret


def _token_response(raw: dict, *, requires_refresh: bool) -> tuple[str,str|None]:
    if type(raw) is not dict:
        raise PrivateGoogleNetworkBlocked("Malformed Google OAuth response")
    token=raw.get("access_token")
    refresh=raw.get("refresh_token")
    if (type(token) is not str or not 20<=len(token)<=8192
        or raw.get("token_type")!="Bearer"
        or raw.get("scope")!=GOOGLE_METADATA_SCOPE
        or type(raw.get("expires_in")) is not int
        or not 1<=raw["expires_in"]<=86400
        or (refresh is not None and (type(refresh) is not str
            or not 24<=len(refresh)<=4096))
        or (requires_refresh and not refresh)):
        raise PrivateGoogleNetworkBlocked("Invalid Google OAuth scope, token or expiry")
    return token,refresh


def exchange_google_code(
    *, code: str, verifier: str, config: DriveOAuthConfig,
    transport: Callable[[str,str,dict|None,str|None],dict] = _http_google,
) -> tuple[str,str]:
    _guard_network()
    if (config!=private_google_configuration()
        or not isinstance(code,str) or not re.fullmatch(r"[A-Za-z0-9._~/-]{8,2048}",code)
        or not isinstance(verifier,str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}",verifier)):
        raise PrivateGoogleNetworkBlocked("Invalid private Google exchange state")
    body={
        "client_id":config.client_id,
        "client_secret":_client_secret(),
        "grant_type":"authorization_code",
        "code":code,"code_verifier":verifier,
        "redirect_uri":config.redirect_uri,
    }
    try:
        raw=transport("POST",GOOGLE_TOKEN_URL,body,None)
    except Exception:
        raise PrivateGoogleNetworkBlocked("Private Google authorization could not be exchanged") from None
    access,refresh=_token_response(raw,requires_refresh=True)
    return access,refresh


def refresh_google_access_token(
    *, refresh_token: str, config: DriveOAuthConfig,
    transport: Callable[[str,str,dict|None,str|None],dict] = _http_google,
) -> tuple[str,str|None]:
    _guard_network()
    if (config!=private_google_configuration()
        or not isinstance(refresh_token,str) or not 24<=len(refresh_token)<=4096):
        raise PrivateGoogleNetworkBlocked("Unapproved private Google refresh")
    try:
        raw=transport("POST",GOOGLE_TOKEN_URL,{
            "client_id":config.client_id,
            "client_secret":_client_secret(),
            "grant_type":"refresh_token",
            "refresh_token":refresh_token,
        },None)
    except Exception:
        raise PrivateGoogleNetworkBlocked("Private Google grant unavailable") from None
    return _token_response(raw,requires_refresh=False)


def verify_owner_private_folder(
    *, access_token: str, config: DriveOAuthConfig,
    transport: Callable[[str,str,dict|None,str|None],dict] = _http_google,
) -> None:
    """Owner, folder type, not trashed or shared; never accept other accounts."""
    _guard_network()
    if config!=private_google_configuration():
        raise PrivateGoogleNetworkBlocked("Private folder not authorized")
    url=GOOGLE_DRIVE_FOLDER_URL+"/"+config.folder_id+"?"+urlencode({
        "fields":"id,mimeType,trashed,shared,owners(me)",
        "supportsAllDrives":"false",
    })
    try:
        raw=transport("GET",url,None,access_token)
    except Exception:
        raise PrivateGoogleNetworkBlocked("Approved private Google folder unavailable") from None
    if (type(raw) is not dict or raw.get("id")!=config.folder_id
        or raw.get("mimeType")!=_EXPECTED_FOLDER_MIME
        or raw.get("trashed") is not False
        or raw.get("shared") is not False
        or type(raw.get("owners")) is not list
        or len(raw["owners"])!=1
        or type(raw["owners"][0]) is not dict
        or raw["owners"][0].get("me") is not True):
        raise PrivateGoogleNetworkBlocked("Consent did not identify the owner-only approved folder")


def complete_private_google_oauth(
    vault: PrivateGoogleOAuthVault, *, state: str, code: str,
    transport: Callable[[str,str,dict|None,str|None],dict] = _http_google,
) -> dict:
    """Consume state BEFORE the token exchange, verify folder BEFORE storage.

    Failures require starting a new consent attempt; code and refresh token
    never reach a browser response or financial database.
    """
    config=_guard_network()
    try:
        pending=vault.consume_attempt(state)
    except (PrivateDriveVaultBlocked,PrivateDriveOAuthBlocked):
        raise PrivateGoogleNetworkBlocked("Expired, replayed or mismatched Google consent") from None
    if (pending.client_id!=config.client_id
        or pending.redirect_uri!=config.redirect_uri
        or pending.folder_hmac!=config.folder_hmac):
        raise PrivateGoogleNetworkBlocked("Google authorization bound to another folder")
    access,refresh=exchange_google_code(
        code=code,verifier=pending.pkce_verifier,config=config,transport=transport)
    verify_owner_private_folder(access_token=access,config=config,transport=transport)
    vault.store_grant(
        folder_hmac=config.folder_hmac,client_id=config.client_id,
        refresh_token=refresh,scope=GOOGLE_METADATA_SCOPE)
    return {
        "owner_metadata_consent":"SEALED_LOCAL",
        "approved_private_folder_verified":True,
        "oauth_state_replay_protected":True,
        "content_download_enabled":False,
        "financial_reconciliation_enabled":False,
        "background_app_sync_enabled":False,
    }


def list_private_owner_folder_page(
    *, access_token: str, config: DriveOAuthConfig,
    page_token: str|None=None,
    transport: Callable[[str,str,dict|None,str|None],dict] = _http_google,
) -> dict:
    """Only one pinned folder, never whole-account search or media download."""
    _guard_network()
    if config!=private_google_configuration():
        raise PrivateGoogleNetworkBlocked("Wrong private folder config")
    if page_token is not None and (type(page_token) is not str
        or not 1<=len(page_token)<=1024):
        raise PrivateGoogleNetworkBlocked("Untrusted Drive pagination token")
    params={
        "q":f"'{config.folder_id}' in parents and trashed = false",
        "pageSize":"100","corpora":"user","spaces":"drive",
        "fields":"nextPageToken,incompleteSearch,files(id,name,mimeType,parents,size,modifiedTime,md5Checksum,trashed)",
    }
    if page_token:
        params["pageToken"]=page_token
    url=GOOGLE_DRIVE_LIST_URL+"?"+urlencode(params)
    try:
        result=transport("GET",url,None,access_token)
    except Exception:
        raise PrivateGoogleNetworkBlocked("Owner folder metadata scan unavailable") from None
    if (type(result) is not dict or result.get("incompleteSearch",False) is not False
        or type(result.get("files")) is not list or len(result["files"])>100):
        raise PrivateGoogleNetworkBlocked("Incomplete owner folder metadata page")
    # Provider response may be forged; validate parents in addition to fixed query.
    ids=set()
    for file in result["files"]:
        if (type(file) is not dict or file.get("mimeType")=="application/vnd.google-apps.folder"
            or not isinstance(file.get("id"),str) or not _ID.fullmatch(file["id"])
            or file["id"] in ids or type(file.get("parents")) is not list
            or config.folder_id not in file["parents"]):
            raise PrivateGoogleNetworkBlocked("Folder returned unexpected source metadata")
        ids.add(file["id"])
    return result
