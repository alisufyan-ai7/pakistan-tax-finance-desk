"""P1L: nondeployable exact-route OAuth ingress and log-redaction threat rehearsal.

Returns redacted allow/deny decisions, NOT a reverse proxy or authorization.
Actual Railway TLS/trusted headers, access-log code scrubbing and G2 review
must be verified independently before any Nginx route is added.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from urllib.parse import parse_qsl

from .drive_cloud_owner_gateway import HOST, ORIGIN

_PUBLIC = {
    ("POST", "/api/drive/oauth/start"): "/internal/drive/oauth/start",
    ("GET", "/api/drive/oauth/callback"): "/internal/drive/oauth/callback",
    ("GET", "/api/drive/oauth/status"): "/internal/drive/oauth/status",
    ("POST", "/api/drive/oauth/disconnect"): "/internal/drive/oauth/disconnect",
}
_STATE = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
_FAKE_CODE = re.compile(r"^SYNTHETIC_GOOGLE_CODE_[A-Za-z0-9_-]{12,120}$")


class FakeOAuthIngressBlocked(ValueError):
    """A route/header/logging or permission acceptance boundary was not met."""


@dataclass(frozen=True)
class FakeIngressRequest:
    method: str
    path: str
    scheme: str
    host: str
    origin: str | None
    query: str
    owner_session_present: bool
    csrf_verified: bool
    forwarded_headers_present: bool = False


def plan_fake_exact_oauth_ingress(req: FakeIngressRequest) -> dict:
    """Approve only a *fictional* route for offline protocol tests.

    Opaque OAuth secrets, cookies, codes and query strings never enter the
    returned plan; a future proxy must disable request-target access logs.
    This intentionally cannot verify an actual browser session or state.
    """
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("P1L_FAKE_OAUTH_INGRESS_REVIEW_ONLY") != "1"
        or type(req) is not FakeIngressRequest):
        raise FakeOAuthIngressBlocked("OAuth ingress review unavailable")
    if (type(req.method) is not str or type(req.path) is not str
        or type(req.scheme) is not str or type(req.host) is not str
        or type(req.query) is not str or type(req.owner_session_present) is not bool
        or type(req.csrf_verified) is not bool
        or type(req.forwarded_headers_present) is not bool
        or (req.origin is not None and type(req.origin) is not str)):
        raise FakeOAuthIngressBlocked("Malformed ingress request")
    internal = _PUBLIC.get((req.method,req.path))
    if (internal is None or req.scheme!="https" or req.host!=HOST
        or req.forwarded_headers_present
        or len(req.query)>320):
        raise FakeOAuthIngressBlocked("Untrusted OAuth authority or route")
    if not req.owner_session_present:
        raise FakeOAuthIngressBlocked("Missing owner session")
    is_callback = req.path=="/api/drive/oauth/callback"
    if is_callback:
        # Cross-site top-level GET redirect must work with SameSite=Lax; no
        # Origin or CSRF request header requirement for this external GET.
        if req.method!="GET" or req.origin is not None:
            raise FakeOAuthIngressBlocked("Unsupported OAuth callback")
        try:
            pairs=parse_qsl(req.query,keep_blank_values=True,strict_parsing=True)
        except ValueError:
            raise FakeOAuthIngressBlocked("Malformed callback query") from None
        if (len(pairs)!=2 or {k for k,_ in pairs}!={"code","state"}
            or len({k for k,_ in pairs})!=2):
            raise FakeOAuthIngressBlocked("OAuth callback must have exact query fields")
        values=dict(pairs)
        if _STATE.fullmatch(values["state"]) is None or _FAKE_CODE.fullmatch(values["code"]) is None:
            raise FakeOAuthIngressBlocked("Only fictional, bound OAuth callback is testable")
    else:
        if req.query or req.origin!=ORIGIN and req.method=="POST":
            raise FakeOAuthIngressBlocked("Untrusted mutation or query")
        if req.method=="POST" and not req.csrf_verified:
            raise FakeOAuthIngressBlocked("Owner CSRF absent")
        if req.method=="GET" and req.origin not in (None,ORIGIN):
            raise FakeOAuthIngressBlocked("Untrusted GET Origin")
    return {
        "synthetic_only":True,
        "candidate_public_path":req.path,
        "candidate_private_path":internal,
        "allowed_method":req.method,
        "request_target_log_allowed":False,
        "cookie_or_code_logged":False,
        "proxy_must_strip_client_forwarded_headers":True,
        "server_must_strip_or_avoid_query_logging":True,
        "provider_code_exchanged":False,
        "session_and_state_binding_independently_tested":False,
        "owner_mfa_production_approved":False,
        "real_google_redirect_routed":False,
        "real_data_authorized":False,
    }


def audit_current_public_nginx(*, nginx_source: str) -> dict:
    """Source-only check for exact disabled owner+Google routes.

    All six paths can be deployed in a source image while independent
    Railway approval flags remain OFF. This cannot independently attest
    the actual Railway edge, platform logs or owner MFA availability.
    """
    if type(nginx_source) is not str or len(nginx_source) > 100_000:
        raise FakeOAuthIngressBlocked("Unsupported proxy configuration")
    if ("location = /api/preview/status" not in nginx_source
        or "location /api/" in nginx_source
        or "location = /api/drive/oauth/disconnect" in nginx_source
        or "location = /api/finance" in nginx_source):
        raise FakeOAuthIngressBlocked("Public ingress unexpectedly broadened")
    owner_routes = {
        "/api/owner/login": ("POST", "/internal/drive/auth/login"),
        "/api/owner/session": ("GET", "/internal/drive/auth/session"),
        "/api/owner/logout": ("POST", "/internal/drive/auth/logout"),
    }
    google_routes = {
        "/api/drive/oauth/start": ("POST", "/internal/drive/oauth/start"),
        "/api/drive/oauth/callback": ("GET", "/internal/drive/oauth/callback"),
        "/api/drive/oauth/status": ("GET", "/internal/drive/oauth/status"),
    }
    for path, (method, internal) in {**owner_routes, **google_routes}.items():
        if nginx_source.count("location = " + path + " {") != 1:
            raise FakeOAuthIngressBlocked("Exact private ingress count unsafe")
        match = re.search(
            r"location = " + re.escape(path) + r" \{(.*?)\n    \}",
            nginx_source, re.S,
        )
        if match is None:
            raise FakeOAuthIngressBlocked("Exact private ingress incomplete")
        body = match.group(1)
        google = path in google_routes
        requirements = [
            'if ($p1ak_owner_ingress != "1") { return 404; }',
            'if ($p1ak_gateway_token = "") { return 503; }',
            'if ($request_method != "' + method + '") { return 405; }',
            'proxy_set_header X-Personal-CFO-Private-Gateway $p1ak_gateway_token;',
            'proxy_set_header Forwarded "";',
            'proxy_set_header X-Forwarded-Host "";',
            'access_log off;',
            'error_log /dev/null crit;',
        ]
        if google:
            requirements.extend([
                'if ($p1ao_google_ingress != "1") { return 404; }',
                'proxy_pass http://$private_google_upstream' + internal
                + ('$is_args$args' if path.endswith('/callback') else '') + ';',
            ])
        else:
            requirements.append(
                'proxy_pass http://$private_auth_upstream' + internal + ';'
            )
        if any(item not in body for item in requirements):
            raise FakeOAuthIngressBlocked(
                "Private owner/Google fail-closed controls absent"
            )
    return {
        "synthetic_only": True,
        "public_google_oauth_route_active": False,
        "google_routes_default_off_in_source": True,
        "owner_login_routes_default_off_in_source": True,
        "current_preview_route_only": False,
        "actual_owner_login_activation_independently_verified": False,
        "g2_exact_proxy_release_accepted": False,
    }
