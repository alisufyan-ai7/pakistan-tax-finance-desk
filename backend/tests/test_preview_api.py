"""Railway preview API security and DB connectivity contract, no actual records."""
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import preview_api


def config(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("PERSONAL_CFO_PRIVATE_PREVIEW", "enabled")
    monkeypatch.setenv("DATABASE_URL", "postgresql://preview:fiction@postgres.railway.internal:5432/synthetic")
    monkeypatch.setenv("PREVIEW_INTERNAL_TOKEN", "X"*48)
    monkeypatch.setenv("PREVIEW_DB_TLS", "require")
    monkeypatch.delenv("PREVIEW_TEST_ONLY", raising=False)


class FakeEngine:
    def dispose(self):
        pass


@pytest.fixture
def api(monkeypatch):
    config(monkeypatch)
    monkeypatch.setattr(preview_api, "_engine", lambda url, tls: FakeEngine())
    monkeypatch.setattr(preview_api, "_check_database", lambda engine: True)
    with TestClient(preview_api.create_preview_app()) as c:
        yield c


def test_public_health_checks_only_private_database_connection(api):
    r=api.get("/healthz")
    assert r.status_code==200 and r.json()=={"ok":True}
    assert r.headers["cache-control"]=="no-store"
    assert api.get("/api/accounts").status_code==404
    assert api.get("/api/owner/workspace/status").status_code==404
    assert api.get("/docs").status_code==404
    assert api.get("/openapi.json").status_code==404


def test_private_token_required_and_year_coverage_has_no_money(api):
    assert api.get("/internal/preview/status").status_code==401
    assert api.get("/internal/preview/status",headers={"X-Personal-CFO-Preview-Key":"wrong"}).status_code==401
    r=api.get("/internal/preview/status?tax_year=2027",
            headers={"X-Personal-CFO-Preview-Key":"X"*48})
    assert r.status_code==200,r.text
    data=r.json()
    assert data["contract"]=="personal_cfo_private_preview_status_v1"
    assert data["postgresql"]=="private_connected"
    assert data["canonical_finance_schema"]=="NOT_CERTIFIED"
    assert data["owner_workspace"]["coverage"]["state"]=="UNAVAILABLE"
    assert all(x is None for x in data["owner_workspace"]["financial_facts"].values())
    assert data["real_data_authorized"] is False
    assert r.headers["cache-control"]=="no-store"
    assert "postgres.railway.internal" not in r.text
    assert "fiction" not in r.text


def test_invalid_year_and_methods_refuse(api):
    hdr={"X-Personal-CFO-Preview-Key":"X"*48}
    assert api.get("/internal/preview/status?tax_year=2028",headers=hdr).status_code==422
    assert api.post("/internal/preview/status",headers=hdr,json={"data":"secret"}).status_code==405
    assert api.post("/api/accounts",json={"account":"test"}).status_code==404


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),("PERSONAL_CFO_PRIVATE_PREVIEW","disabled"),
    ("PREVIEW_INTERNAL_TOKEN","too-short"),
    ("DATABASE_URL","sqlite:///tmp/test.db"),
    ("DATABASE_URL","postgresql://user:pass@public.example.org:5432/test"),
    ("PREVIEW_DB_TLS","disable_for_ci")
])
def test_unsupported_or_unsafe_deployment_refuses_startup(monkeypatch,variable,value):
    config(monkeypatch)
    monkeypatch.setenv(variable,value)
    with pytest.raises(preview_api.PreviewConfigurationError):
        preview_api._configuration()


def test_database_failure_yields_503_without_credentials(api,monkeypatch):
    monkeypatch.setattr(preview_api,"_check_database",lambda eng:False)
    r=api.get("/internal/preview/status",headers={"X-Personal-CFO-Preview-Key":"X"*48})
    assert r.status_code==503
    assert "fiction" not in r.text
    assert api.get("/healthz").status_code==503


def test_read_only_connection_options(monkeypatch):
    config(monkeypatch)
    url,token,tls=preview_api._configuration()
    assert url.startswith("postgresql+psycopg://")
    assert tls is True
    assert token=="X"*48
