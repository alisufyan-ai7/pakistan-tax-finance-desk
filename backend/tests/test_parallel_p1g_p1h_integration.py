"""Chat 04: integration contract for independent P1G/P1H engineering lanes.

No real owner, OAuth secret, live Railway mutation or background job.
"""
from datetime import datetime, timezone

import base64
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base
from app.drive_scan_cadence import (
    evaluate_fake_scan_health, record_fake_scan_outcome,
    initial_fake_scan_health,
)
from app.drive_inbox_planner import DriveInboxBlocked, _index
from app.drive_google_oauth import PERSONAL_CFO_RAILWAY_CALLBACK
from app.owner_login_throttle import (
    fake_throttle_health, issue_throttled_fake_owner_session,
    OwnerThrottleBlocked,
)
from app.preview_api import create_preview_app

FOLDER = "SYNTHETIC_INTEGRATED_NO_REAL_DRIVE_2026"
NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)


def test_parallel_owner_security_and_scan_health_are_isolated(tmp_path, monkeypatch):
    conf = {
        "APP_DATA_MODE":"synthetic",
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY":"1",
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY":"1",
        "P1E_SYNTHETIC_CLOUD_CUSTODY_ONLY":"1",
        "P1E_SQLITE_TEST_ONLY":"1",
        "P1F_SYNTHETIC_OWNER_GATEWAY_ONLY":"1",
        "P1G_FAKE_LOGIN_THROTTLE_ONLY":"1",
        "P1G_SQLITE_TEST_ONLY":"1",
        "P1H_FAKE_SCAN_CADENCE_ONLY":"1",
        "DRIVE_FAKE_TRANSPORT_ONLY":"1",
        "P1B_GOOGLE_REDIRECT_URI":PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_CLIENT_ID":"000000000000-syntheticdev.apps.googleusercontent.com",
        "P1B_GOOGLE_FOLDER_ID":FOLDER,
        "DRIVE_INDEX_HMAC_KEY":base64.urlsafe_b64encode(b"D"*32).decode(),
        "P1E_FAKE_CLOUD_VAULT_KEY":base64.urlsafe_b64encode(b"E"*32).decode(),
        "P1E_FAKE_CLOUD_INDEX_KEY":base64.urlsafe_b64encode(b"J"*32).decode(),
        "P1G_FAKE_THROTTLE_KEY":base64.urlsafe_b64encode(b"T"*32).decode(),
    }
    for k,v in conf.items():
        monkeypatch.setenv(k,v)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    db_engine = create_engine("sqlite:///" + str(tmp_path/"integrated-safe.db"))
    Base.metadata.create_all(db_engine)
    try:
        with Session(db_engine) as db:
            throttle = fake_throttle_health(db)
            assert throttle["durable_multiworker_contract"] is True
            assert throttle["hosted_owner_login_enabled"] is False
            assert throttle["real_data_authorized"] is False

        state = initial_fake_scan_health()
        due = evaluate_fake_scan_health(state=state, now=NOW)
        assert due["scan_due"] and not due["heartbeat_is_real"]
        state = record_fake_scan_outcome(state=state, now=NOW, outcome="denied")
        denied = evaluate_fake_scan_health(state=state, now=NOW)
        assert denied["permission_state"] == "REAUTHORIZATION_REQUIRED"
        assert not denied["scan_due"] and not denied["background_job_started"]
        assert denied["google_drive_app_connected"] is False

        # Both independently developed lanes must fail closed together in real mode.
        monkeypatch.setenv("APP_DATA_MODE","real")
        with Session(db_engine) as db:
            with pytest.raises(OwnerThrottleBlocked):
                issue_throttled_fake_owner_session(
                    db,username="synthetic-owner",password="fictional-password",
                    totp_code="123456",now_epoch=1800000000)
        with pytest.raises(DriveInboxBlocked):
            evaluate_fake_scan_health(state=initial_fake_scan_health(), now=NOW)
    finally:
        db_engine.dispose()


def test_combined_lanes_do_not_expose_public_owner_login_or_google_callback():
    routes = {route.path for route in create_preview_app().routes}
    assert "/internal/drive/oauth/callback" not in routes
    assert "/api/drive/oauth/callback" not in routes
    assert "/api/owner/login" not in routes
    assert "/api/drive/scheduler/run" not in routes
    from pathlib import Path
    nginx = (Path(__file__).parents[2] / "frontend/nginx.railway.conf").read_text()
    assert "location = /api/preview/status" in nginx
    assert "location /api/" not in nginx
    assert "location = /api/drive/oauth/callback" in nginx
    assert 'if ($p1ao_google_ingress != "1") { return 404; }' in nginx
