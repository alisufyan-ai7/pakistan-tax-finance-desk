"""P1U: nondeployed Railway edge private gateway proof header rehearsal.

The actual Railway edge, TLS, ingress logs, IP handling, CSRF, rate zones,
secret substitution and production credential custody remain G2 blockers.
"""
from pathlib import Path
import re

ROOT = Path(__file__).parents[2]
CANDIDATE = ROOT / "ops/nginx.personal-cfo-oauth.candidate.conf"
LIVE = ROOT / "frontend/nginx.railway.conf"
DOCKERFILE = ROOT / "frontend/Dockerfile"

EXACT = {
    "/api/owner/login",
    "/api/owner/session",
    "/api/owner/logout",
    "/api/drive/oauth/start",
    "/api/drive/oauth/callback",
    "/api/drive/oauth/status",
}


def locations(source):
    pattern = r"location = (?P<path>[^ ]+) \{(?P<body>.*?)\n    \}"
    return {m["path"]: m["body"] for m in re.finditer(pattern, source, re.S)}


def test_review_candidate_replaces_browser_auth_headers_and_scrubs_forwarded():
    content = CANDIDATE.read_text()
    assert content.startswith("# REVIEW CANDIDATE ONLY.")
    blocks = locations(content)
    assert EXACT <= set(blocks)
    expected = ('proxy_set_header X-Personal-CFO-Private-Gateway '
                '"${P1Q_PRIVATE_GATEWAY_SHARED_TOKEN}";')
    assert content.count(expected) == len(EXACT)
    for route in EXACT:
        body = blocks[route]
        assert expected in body
        assert 'proxy_set_header Forwarded "";' in body
        for header in ("X-Original-URI", "X-Original-URL",
                       "X-Rewrite-URL", "X-Forwarded-Prefix"):
            assert f'proxy_set_header {header} "";' in body
        assert 'proxy_set_header X-Forwarded-Host "";' in body
        assert 'proxy_set_header X-Forwarded-For "";' in body
        assert 'proxy_set_header X-Real-IP "";' in body
        assert 'proxy_set_header X-Forwarded-Proto https;' in body
        assert "access_log off;" in body
        assert "error_log /dev/null crit;" in body
        assert 'proxy_set_header X-Personal-CFO-Preview-Key "";' in body
        # An incoming caller-supplied credential must NEVER be used.
        assert "$http_x_personal_cfo_private_gateway" not in body
        assert 'proxy_set_header X-Personal-CFO-Private-Gateway "";' not in body
    assert "/api/drive/oauth/disconnect" not in blocks
    assert "P1C_GOOGLE_CLIENT_SECRET" not in content


def test_live_frontend_does_not_enable_google_or_unapproved_owner_login():
    live = LIVE.read_text()
    docker = DOCKERFILE.read_text()
    assert 'COPY nginx.railway.conf /etc/nginx/templates/default.conf.template' in docker
    assert "nginx.personal-cfo-oauth.candidate.conf" not in docker
    assert 'P1AK_OWNER_INGRESS_ENABLED' in docker
    assert 'ENV P1AK_OWNER_INGRESS_ENABLED=1' not in docker
    assert "P1AK_OWNER_INGRESS_ENABLED" in live
    blocks = locations(live)
    assert set(blocks) & EXACT == {
        "/api/owner/login", "/api/owner/session", "/api/owner/logout"
    }
    for route in EXACT:
        if route.startswith("/api/drive/"):
            assert route not in blocks
    for route in set(blocks) & EXACT:
        body = blocks[route]
        assert 'if ($p1ak_owner_ingress != "1") { return 404; }' in body
        assert 'if ($p1ak_gateway_token = "") { return 503; }' in body
        assert 'proxy_set_header X-Personal-CFO-Private-Gateway $p1ak_gateway_token;' in body
        assert 'proxy_set_header Forwarded "";' in body
        assert "access_log off;" in body
        assert "error_log /dev/null crit;" in body
    assert "location /api/" not in live


def test_exact_callback_remains_internal_with_no_rewrite_or_sensitive_referrer():
    callback = locations(CANDIDATE.read_text())["/api/drive/oauth/callback"]
    assert ("proxy_pass http://$private_oauth_upstream"
            "/internal/drive/oauth/callback$is_args$args;") in callback
    assert 'add_header Referrer-Policy "no-referrer" always;' in callback
    assert 'add_header Cache-Control "no-store" always;' in callback
    assert "rewrite" not in callback and "return 302" not in callback
    assert "proxy_pass https://" not in callback
    assert "limit_req zone" not in CANDIDATE.read_text()


def test_private_gateway_not_mounted_by_public_preview():
    from app.preview_api import create_preview_app
    paths = {r.path for r in create_preview_app().routes}
    assert not any(x.startswith("/internal/drive/auth/") for x in paths)
    assert not any(x.startswith("/internal/drive/oauth/") for x in paths)
