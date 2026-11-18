"""Chat04 issue #110/#114/#115 integration: independent synthetic gates stay closed."""
from pathlib import Path
import base64
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.drive_inbox_planner import _index,DriveInboxBlocked
from app.drive_scan_lease import acquire_fake_scan_lease
from app.owner_login_http_candidate import create_fake_owner_login_http
from app.drive_cloud_owner_gateway import ORIGIN
from app.preview_api import create_preview_app

FOLDER="SYNTHETIC_CHAT04_INTEGRATION_FOLDER_2026"


def test_new_owner_login_and_scan_lease_both_denied_by_real_mode(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    monkeypatch.setenv("P1G_FAKE_LOGIN_HTTP_CONTRACT_ONLY","1")
    monkeypatch.setenv("P1J_FAKE_SCAN_LEASE_ONLY","1")
    monkeypatch.setenv("DRIVE_FAKE_TRANSPORT_ONLY","1")
    monkeypatch.setenv("P1J_SQLITE_TEST_ONLY","1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
                       base64.urlsafe_b64encode(b"D"*32).decode())
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC",_index("folder",FOLDER))
    engine=create_engine("sqlite:///"+str(tmp_path/"integration.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        with pytest.raises(DriveInboxBlocked):
            acquire_fake_scan_lease(db,folder_id=FOLDER,now_epoch=1800000000)
    with TestClient(create_fake_owner_login_http(lambda:Session(engine)),
                    base_url=ORIGIN) as client:
        assert client.post("/internal/drive/auth/login",
                           json={"username":"synthetic-owner","password":"fictional",
                                 "totp_code":"123456"},
                           headers={"Origin":ORIGIN}).status_code==503
        assert client.get("/internal/drive/auth/session").status_code==503
    assert {"owner_login_throttles","drive_scan_leases"} <= set(Base.metadata.tables)
    engine.dispose()


def test_combined_private_and_public_route_firewalls_hold():
    paths={r.path for r in create_preview_app().routes}
    for path in [
        "/api/drive/oauth/callback","/api/drive/oauth/start",
        "/internal/drive/auth/login","/internal/drive/auth/rotate",
        "/internal/drive/sync/run","/api/drive/scheduler/run",
    ]:
        assert path not in paths
    nginx=(Path(__file__).parents[2]/"frontend/nginx.railway.conf").read_text()
    assert "location = /api/preview/status" in nginx
    assert "location /api/" not in nginx
    assert "location = /api/drive/oauth/callback" not in nginx
    assert "location = /api/owner/login" in nginx
    assert 'if ($p1ak_owner_ingress != "1") { return 404; }' in nginx
    app=(Path(__file__).parents[1]/"app/preview_api.py").read_text()
    assert "owner_login_http_candidate" not in app
    assert "drive_scan_lease" not in app
