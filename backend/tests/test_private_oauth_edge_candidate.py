"""P1O: exact nondeployed Railway OAuth path and logging acceptance checks.

Source tests only; runtime edge access/error logging, TLS, proxy behavior,
rate-limit and authenticated one-time owner PKCE must be accepted independently.
"""
from pathlib import Path
import re

ROOT=Path(__file__).parents[2]
LIVE=ROOT/"frontend/nginx.railway.conf"
CANDIDATE=ROOT/"ops/nginx.personal-cfo-oauth.candidate.conf"
ROUTES={
    "/api/owner/login":("POST","/internal/drive/auth/login"),
    "/api/owner/session":("GET","/internal/drive/auth/session"),
    "/api/owner/logout":("POST","/internal/drive/auth/logout"),
    "/api/drive/oauth/start":("POST","/internal/drive/oauth/start"),
    "/api/drive/oauth/callback":("GET","/internal/drive/oauth/callback"),
    "/api/drive/oauth/status":("GET","/internal/drive/oauth/status"),
}
HOST="personal-cfo-frontend-preview-development.up.railway.app"
UPSTREAM="personal-cfo-api-preview.railway.internal:8000"


def locations(config):
    pattern=r"location = (?P<path>[^ ]+) \{(?P<body>.*?)\n    \}"
    return {m["path"]:m["body"] for m in re.finditer(pattern,config,re.S)}


def test_live_frontend_did_not_gain_auth_login_or_google_callback():
    current=LIVE.read_text()
    paths=set(locations(current))
    assert paths & ROUTES.keys()==set()
    assert "/api/preview/status" in paths
    assert "location /api/" not in current
    assert "proxy_pass http://$private_preview_upstream/internal/preview/status" in current
    assert not CANDIDATE.is_symlink()
    assert CANDIDATE!=LIVE


def test_non_deployed_candidate_has_exact_boundaries_only():
    config=CANDIDATE.read_text()
    assert config.startswith("# REVIEW CANDIDATE ONLY.")
    paths=locations(config)
    assert set(ROUTES)<=set(paths)
    assert "/api/preview/status" in paths
    assert not re.search(r"location\s+(?:~\*?|\^~)?\s*/api/",config)
    assert not re.search(r"location\s+=\s+/internal/",config)
    for path,(method,internal) in ROUTES.items():
        b=paths[path]
        assert f'if ($host != "{HOST}") {{ return 403; }}' in b
        assert f'if ($request_method != "{method}") {{ return 405; }}' in b
        assert "access_log off;" in b
        assert "error_log /dev/null crit;" in b
        assert 'add_header Cache-Control "no-store" always;' in b
        assert 'add_header Referrer-Policy "no-referrer" always;' in b
        assert f'set $private_oauth_upstream "{UPSTREAM}";' in b
        suffix="$is_args$args" if path=="/api/drive/oauth/callback" else ""
        assert f"proxy_pass http://$private_oauth_upstream{internal}{suffix};" in b
        for unsafe in ("$request_uri","proxy_pass http://$host","proxy_pass https://",
                       "proxy_set_header X-Real-IP $remote_addr",
                       "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for"):
            assert unsafe not in b
        assert 'proxy_set_header X-Forwarded-Host "";' in b
        assert 'proxy_set_header X-Forwarded-For "";' in b
        assert 'proxy_set_header X-Real-IP "";' in b
        assert "proxy_hide_header Server;" in b


def test_callback_keeps_code_internal_never_browser_navigation():
    callback=locations(CANDIDATE.read_text())["/api/drive/oauth/callback"]
    assert "proxy_pass http://$private_oauth_upstream/internal/drive/oauth/callback$is_args$args;" in callback
    assert "access_log off;" in callback
    assert "error_log /dev/null crit;" in callback
    assert "return 301" not in callback
    assert "return 302" not in callback
    assert "rewrite" not in callback
    assert "try_files" not in callback


def test_provider_scope_cannot_be_enlarged_by_edge_candidate():
    source=CANDIDATE.read_text()
    assert "drive.readonly" not in source
    assert "drive.file" not in source
    assert "redirect_uri=" not in source
    assert "client_secret" not in source
    assert "P1C_GOOGLE_CLIENT_SECRET" not in source
    assert 'proxy_set_header Host personal-cfo-api-preview.railway.internal;' in source
    assert 'proxy_set_header X-Forwarded-Proto https;' in source
    assert "limit_req zone" not in source  # shared http{} policy not yet approved


def test_no_gateway_activated_through_current_private_api():
    from app.preview_api import create_preview_app
    paths={r.path for r in create_preview_app().routes}
    assert not paths & ROUTES.keys()
    assert not any(path.startswith("/internal/drive/oauth/") for path in paths)
    assert not any(path.startswith("/internal/drive/auth/") for path in paths)



def test_exact_public_candidate_route_parity_with_actual_private_asgi():
    """Never publish an endpoint the private ASGI candidate cannot serve."""
    from app.private_owner_oauth_http_gateway import (
        create_synthetic_private_owner_oauth_gateway,
    )
    candidate = locations(CANDIDATE.read_text())
    api_paths = {path for path in candidate if path.startswith("/api/")}
    assert api_paths == set(ROUTES) | {"/api/preview/status"}
    assert "/api/drive/oauth/disconnect" not in candidate

    private = create_synthetic_private_owner_oauth_gateway(lambda: None)
    actual = {
        (method, route.path)
        for route in private.routes
        if route.path.startswith("/internal/drive/")
        for method in route.methods
    }
    expected = {(method, path) for method, path in ROUTES.values()}
    assert actual == expected
    for public, (method, path) in ROUTES.items():
        assert f'if ($request_method != "{method}")' in candidate[public]
        assert f"proxy_pass http://$private_oauth_upstream{path}" in candidate[public]
    # No actual owner or Google credentials and no public runtime wiring.
    from app.preview_api import create_preview_app
    assert not any(
        route.path.startswith("/internal/drive/")
        for route in create_preview_app().routes
    )
