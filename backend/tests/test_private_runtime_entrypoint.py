"""P1AJ: existing private preview stays default-off; no wildcard owner ingress."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import private_owner_login_service
from app import private_runtime_entrypoint as runtime
from app.preview_api import create_preview_app


def test_unchanged_default_private_preview_has_no_owner_or_google_routes(monkeypatch):
    monkeypatch.delenv("P1AJ_OWNER_LOGIN_RUNTIME", raising=False)
    app = runtime.create_private_runtime_entrypoint()
    assert isinstance(app, FastAPI)
    paths = {route.path for route in app.routes}
    assert paths == {route.path for route in create_preview_app().routes}
    assert not paths & runtime._OWNER_ROUTES
    assert not any(path.startswith("/internal/drive/") for path in paths)


@pytest.mark.parametrize("mode", ["0", "true", "on", "1"])
def test_gated_runtime_denies_missing_independent_review(monkeypatch, mode):
    monkeypatch.setenv("P1AJ_OWNER_LOGIN_RUNTIME", mode)
    monkeypatch.delenv("P1AJ_G2_EXACT_INGRESS_REVIEWED", raising=False)
    monkeypatch.delenv("P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED", raising=False)
    with pytest.raises(runtime.PrivateRuntimeSwitchBlocked):
        runtime.create_private_runtime_entrypoint()


@pytest.mark.parametrize("key,value", (
    ("P1AJ_G2_EXACT_INGRESS_REVIEWED", "0"),
    ("P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED", "0"),
    ("APP_DATA_MODE", "real"),
    ("P1C_GOOGLE_NETWORK_ENABLED", "1"),
))
def test_private_runtime_denies_incomplete_release_flags(monkeypatch, key, value):
    monkeypatch.setenv("P1AJ_OWNER_LOGIN_RUNTIME", "1")
    monkeypatch.setenv("P1AJ_G2_EXACT_INGRESS_REVIEWED", "1")
    monkeypatch.setenv("P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED", "1")
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("P1C_GOOGLE_NETWORK_ENABLED", "0")
    monkeypatch.setenv(key, value)
    with pytest.raises(runtime.PrivateRuntimeSwitchBlocked):
        runtime.create_private_runtime_entrypoint()


def test_exact_three_owner_paths_composed_without_google_or_finance(monkeypatch):
    monkeypatch.setenv("P1AJ_OWNER_LOGIN_RUNTIME", "1")
    monkeypatch.setenv("P1AJ_G2_EXACT_INGRESS_REVIEWED", "1")
    monkeypatch.setenv("P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED", "1")
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("P1C_GOOGLE_NETWORK_ENABLED", "0")
    monkeypatch.setattr(
        private_owner_login_service, "_reviewed_private_configuration",
        lambda: None,
    )
    entered = []
    preview = FastAPI()
    owner = FastAPI()

    @asynccontextmanager
    async def preview_lifespan(_app):
        entered.append("preview enter")
        yield
        entered.append("preview exit")

    @asynccontextmanager
    async def owner_lifespan(_app):
        entered.append("owner enter")
        yield
        entered.append("owner exit")

    preview.router.lifespan_context = preview_lifespan
    owner.router.lifespan_context = owner_lifespan

    @preview.get("/healthz")
    def health():
        return {"preview": True}

    @preview.get("/internal/preview/status")
    def status():
        return {"synthetic": True}

    @owner.get("/internal/drive/auth/session")
    def session():
        return {"fake_only": True}

    monkeypatch.setattr(runtime, "create_preview_app", lambda: preview)
    monkeypatch.setattr(
        private_owner_login_service,
        "create_review_only_private_owner_login_service",
        lambda: owner,
    )
    app = runtime.create_private_runtime_entrypoint()
    assert isinstance(app, runtime._PrivatePreviewComposite)
    with TestClient(app) as client:
        assert entered == ["preview enter", "owner enter"]
        assert client.get("/healthz").json() == {"preview": True}
        assert client.get("/internal/preview/status").json() == {
            "synthetic": True
        }
        assert client.get("/internal/drive/auth/session").json() == {
            "fake_only": True
        }
        assert client.post("/internal/drive/auth/session").status_code == 405
        assert client.get("/internal/drive/oauth/callback?code=SECRET").status_code == 404
        assert client.post("/internal/drive/oauth/start").status_code == 404
        assert client.get("/api/owner/session").status_code == 404
        assert client.get("/internal/finance/ledger").status_code == 404
        assert client.get("/internal/drive/auth/session/").status_code == 404
    assert entered == [
        "preview enter", "owner enter", "owner exit", "preview exit"
    ]


def test_private_runtime_source_never_enables_public_proxy_or_google():
    root = Path(__file__).parents[2]
    docker = (root / "backend/Dockerfile.preview").read_text()
    frontend = (root / "frontend/nginx.railway.conf").read_text()
    assert "app.private_runtime_entrypoint:app" in docker
    for flag in ("--no-access-log", "--no-server-header",
                 "--no-proxy-headers", "--workers", '"1"'):
        assert flag in docker
    assert "P1AJ_OWNER_LOGIN_RUNTIME" not in docker
    assert "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN" not in docker
    for route in ("/api/owner/login", "/api/owner/session", "/api/owner/logout"):
        assert f"location = {route}" in frontend
    assert 'if ($p1ak_owner_ingress != "1") { return 404; }' in frontend
    for route in ("/api/drive/oauth/callback", "/api/drive/oauth/start"):
        assert f"location = {route}" not in frontend
    assert "location /api/" not in frontend
