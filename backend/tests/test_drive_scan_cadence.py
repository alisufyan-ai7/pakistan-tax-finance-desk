"""P1H cadence, bounded retries, stale state, denied permission and real-mode refusal."""
from datetime import datetime, timedelta, timezone

import pytest

from app.drive_scan_cadence import (
    initial_fake_scan_health, evaluate_fake_scan_health,
    record_fake_scan_outcome, SyntheticScanHealth,
)
from app.drive_inbox_planner import DriveInboxBlocked


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("DRIVE_FAKE_TRANSPORT_ONLY", "1")
    monkeypatch.setenv("P1H_FAKE_SCAN_CADENCE_ONLY", "1")


NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def test_initial_scan_never_claims_real_connection_or_heartbeat():
    first = evaluate_fake_scan_health(state=initial_fake_scan_health(), now=NOW)
    assert first["reason"] == "INITIAL_SCAN_PENDING"
    assert first["scan_due"] is True
    assert first["stale_or_never_scanned"] is True
    assert first["next_due_at"] == NOW.isoformat()
    assert first["last_success_at"] is None
    assert first["heartbeat_is_real"] is False
    assert first["background_job_started"] is False
    assert first["google_drive_app_connected"] is False
    assert first["real_data_authorized"] is False
    assert "folder_id" not in str(first) and "refresh_token" not in str(first)


def test_success_24_hour_cadence_preserves_recent_health():
    success = record_fake_scan_outcome(
        state=initial_fake_scan_health(), now=NOW, outcome="success"
    )
    at23 = evaluate_fake_scan_health(state=success, now=NOW + timedelta(hours=23))
    assert at23["scan_due"] is False
    assert at23["stale_or_never_scanned"] is False
    assert at23["next_due_at"] == (NOW + timedelta(hours=24)).isoformat()
    at24 = evaluate_fake_scan_health(state=success, now=NOW + timedelta(hours=24))
    assert at24["scan_due"] is True
    assert at24["reason"] == "NORMAL_CADENCE"
    at37 = evaluate_fake_scan_health(state=success, now=NOW + timedelta(hours=37))
    assert at37["stale_or_never_scanned"] is True
    assert at37["last_success_at"] == NOW.isoformat()


def test_failures_preserve_last_verified_success_and_bounded_retry_delay():
    original = record_fake_scan_outcome(
        state=initial_fake_scan_health(), now=NOW, outcome="success"
    )
    for n, delay in enumerate((5, 15, 45, 120, 120), start=1):
        when = NOW + timedelta(hours=24, minutes=n)
        original = record_fake_scan_outcome(
            state=original, now=when, outcome="retryable")
        expected = when + timedelta(minutes=delay)
        receipt = evaluate_fake_scan_health(state=original, now=when)
        assert receipt["next_due_at"] == expected.isoformat()
        assert receipt["consecutive_failures"] == n
        assert receipt["last_success_at"] == NOW.isoformat()
        assert receipt["scan_due"] is False
        due = evaluate_fake_scan_health(state=original, now=expected)
        assert due["scan_due"] is True


def test_denied_permission_suspends_work_until_explicit_owner_reauthorization():
    success = record_fake_scan_outcome(state=initial_fake_scan_health(),
                                       now=NOW, outcome="success")
    denied = record_fake_scan_outcome(
        state=success, now=NOW + timedelta(days=2), outcome="denied"
    )
    report = evaluate_fake_scan_health(state=denied, now=NOW+timedelta(days=30))
    assert report["permission_state"] == "REAUTHORIZATION_REQUIRED"
    assert report["next_due_at"] is None
    assert report["scan_due"] is False
    assert report["stale_or_never_scanned"]
    assert report["last_success_at"] == NOW.isoformat()
    with pytest.raises(DriveInboxBlocked):
        record_fake_scan_outcome(
            state=denied, now=NOW + timedelta(days=31), outcome="success")


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("DRIVE_FAKE_TRANSPORT_ONLY","0"),
    ("P1H_FAKE_SCAN_CADENCE_ONLY","0"),
])
def test_no_real_mode_or_unapproved_scheduler(monkeypatch, variable, value):
    monkeypatch.setenv(variable,value)
    with pytest.raises(DriveInboxBlocked):
        evaluate_fake_scan_health(state=initial_fake_scan_health(), now=NOW)
    with pytest.raises(DriveInboxBlocked):
        record_fake_scan_outcome(
            state=initial_fake_scan_health(), now=NOW, outcome="success")


def test_non_monotonic_or_naive_provider_timestamps_are_denied():
    state = record_fake_scan_outcome(
        state=initial_fake_scan_health(), now=NOW, outcome="success"
    )
    with pytest.raises(DriveInboxBlocked):
        record_fake_scan_outcome(
            state=state, now=NOW - timedelta(days=1), outcome="retryable")
    with pytest.raises(DriveInboxBlocked):
        evaluate_fake_scan_health(state=state, now=NOW-timedelta(minutes=3))
    with pytest.raises(DriveInboxBlocked):
        evaluate_fake_scan_health(state=state, now=NOW.replace(tzinfo=None))


def test_fake_inconsistent_state_rejected():
    states = [
        SyntheticScanHealth(NOW,None,0,"never","fictional_authorized"),
        SyntheticScanHealth(NOW,NOW,1,"success","fictional_authorized"),
        SyntheticScanHealth(NOW,NOW,0,"retryable","fictional_authorized"),
        SyntheticScanHealth(NOW,None,0,"denied","fictional_authorized"),
        SyntheticScanHealth(NOW,NOW,True,"success","fictional_authorized"),
        SyntheticScanHealth(NOW,NOW,0,"success","actual_google_connected"),
    ]
    for state in states:
        with pytest.raises(DriveInboxBlocked):
            evaluate_fake_scan_health(state=state, now=NOW)


def test_timezone_normalization_and_unchanged_state_on_refusal():
    east = timezone(timedelta(hours=5))
    t = datetime(2026,11,17,17,0,tzinfo=east)
    state = record_fake_scan_outcome(
        state=initial_fake_scan_health(), now=t, outcome="success")
    assert state.last_success_at == NOW
    expected = NOW + timedelta(days=1)
    assert evaluate_fake_scan_health(state=state,now=expected)["scan_due"]
    with pytest.raises(DriveInboxBlocked):
        record_fake_scan_outcome(state=state,now=expected,outcome="unexpected")
    assert state.last_success_at == NOW
