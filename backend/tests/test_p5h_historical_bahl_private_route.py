"""P5H exact owner-only historical report wiring. Synthetic routes only."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import private_runtime_entrypoint as runtime
from app import private_owner_login_service as login
from app import private_owner_real_google_http as google
from app import private_owner_http_gateway as gateway


@pytest.mark.parametrize("value",["1","true","maybe"])
def test_historical_bahl_runtime_fails_closed_without_original_ingestion(monkeypatch,value):
    for k,v in {
       "P1AJ_OWNER_LOGIN_RUNTIME":"1",
       "P1AJ_G2_EXACT_INGRESS_REVIEWED":"1",
       "P1AJ_NO_SENSITIVE_ACCESS_LOG_ACCEPTED":"1",
       "APP_DATA_MODE":"synthetic",
       "P1AN_GOOGLE_METADATA_RUNTIME":"0",
       "P4C_CONTENT_OAUTH_RUNTIME":"0",
       "P5A_PRIVATE_SOURCE_PREFLIGHT_RUNTIME":"0",
       "P5H_OWNER_HISTORICAL_BAHL_RUNTIME":value,
       "P1C_GOOGLE_NETWORK_ENABLED":"0",
    }.items():
        monkeypatch.setenv(k,v)
    with pytest.raises(runtime.PrivateRuntimeSwitchBlocked):
        runtime.create_private_runtime_entrypoint()


def test_unmounted_bank_route_never_reachable_in_composite():
    preview=FastAPI()
    owner=FastAPI()
    @owner.post("/internal/finance/historical/bahl")
    def test_private_route():
        return {"fake":True}
    no_report=runtime._PrivatePreviewComposite(preview,owner)
    with TestClient(no_report) as c:
        assert c.post("/internal/finance/historical/bahl").status_code==404
        assert c.post("/api/finance/historical/bahl").status_code==404
    yes_report=runtime._PrivatePreviewComposite(
        preview,owner,historical_bahl=True)
    with TestClient(yes_report) as c:
        assert c.post("/internal/finance/historical/bahl").json()=={"fake":True}
        assert c.get("/internal/finance/historical/bahl").status_code==405
        assert c.post("/api/finance/historical/bahl").status_code==404
        assert c.get("/internal/finance/ledger").status_code==404


def test_owner_gateway_allowlist_only_explicit_historical_path():
    assert ("POST","/internal/finance/historical/bahl") in gateway._PATHS
    assert ("GET","/internal/finance/historical/bahl") not in gateway._PATHS
    for forbidden in (
      ("POST","/internal/finance/historical"),
      ("POST","/internal/finance/bahl/status"),
      ("POST","/internal/finance/bahl/analyze"),
      ("GET","/internal/finance/historical/bahl?password=SECRET"),
      ("POST","/internal/finance/ledger"),
    ):
        assert forbidden not in gateway._PATHS


def test_source_and_google_consent_required_before_historical_route(monkeypatch):
    monkeypatch.setattr(google,"_reviewed_content_http",lambda:None)
    # Existing private owner gateway factory still needs approved session,
    # simulated by the pre-existing owner HTTP gateway returned app.
    monkeypatch.setattr(google,"create_private_owner_http_gateway",
                        lambda *a,**kw:FastAPI())
    with pytest.raises(google.PrivateOwnerGoogleHttpBlocked):
        google.create_review_only_private_google_http_gateway(
            lambda:None,enable_historical_bahl=True,enable_source_preflight=False,
            enable_content_oauth=True)
    with pytest.raises(login.PrivateOwnerLoginServiceBlocked):
        login.create_review_only_private_owner_login_service(
            google_metadata=True,google_content=True,
            source_preflight=False,historical_bahl=True)
