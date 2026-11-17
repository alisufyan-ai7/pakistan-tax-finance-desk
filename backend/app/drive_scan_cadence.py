"""P1H: deterministic one-folder *synthetic-only* scan cadence/health contract.

No scheduler, timers, background process, Google HTTP, credentials or source
download is started by importing/calling this module. The private runner may
eventually consume this policy after G2 owner consent and a separate deployment
decision. Until then, only fictional injected timestamps and scan outcomes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import os
from typing import Literal

from .drive_inbox_planner import DriveInboxBlocked

_SCAN_INTERVAL = timedelta(hours=24)
_RETRY_DELAYS = (timedelta(minutes=5), timedelta(minutes=15),
                 timedelta(minutes=45), timedelta(hours=2))
_STALE_AFTER = timedelta(hours=36)
_UTC = timezone.utc
_MAX_CLOCK_SKEW = timedelta(minutes=2)


@dataclass(frozen=True)
class SyntheticScanHealth:
    # status is only synthetic test-fixture state, never a live integration claim
    last_success_at: datetime | None
    last_attempt_at: datetime | None
    consecutive_failures: int
    last_outcome: Literal["never", "success", "retryable", "denied"]
    provider_permission: Literal["fictional_authorized", "fictional_revoked"]


def _stamp(value: datetime | None, *, now: datetime) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise DriveInboxBlocked("Synthetic scan timing needs UTC-aware timestamps")
    instant = value.astimezone(_UTC)
    if instant > now + _MAX_CLOCK_SKEW:
        raise DriveInboxBlocked("Future synthetic scan event rejected")
    return instant


def _guard(state: SyntheticScanHealth, now: datetime):
    if (os.getenv("APP_DATA_MODE", "synthetic") != "synthetic"
        or os.getenv("DRIVE_FAKE_TRANSPORT_ONLY") != "1"
        or os.getenv("P1H_FAKE_SCAN_CADENCE_ONLY") != "1"
        or not isinstance(state, SyntheticScanHealth)
        or not isinstance(now, datetime) or now.tzinfo is None
        or type(state.consecutive_failures) is not int
        or not 0 <= state.consecutive_failures <= 100
        or state.last_outcome not in {"never", "success", "retryable", "denied"}
        or state.provider_permission not in {"fictional_authorized", "fictional_revoked"}):
        raise DriveInboxBlocked("No authenticated synthetic scan schedule")
    clock = now.astimezone(_UTC)
    success = _stamp(state.last_success_at, now=clock)
    attempt = _stamp(state.last_attempt_at, now=clock)
    if ((state.last_outcome == "never") != (attempt is None)
        or (state.last_outcome == "success" and (
            attempt is None or success is None or attempt != success
            or state.consecutive_failures != 0))
        or (state.last_outcome == "retryable" and (
            attempt is None or state.consecutive_failures < 1))
        or (state.last_outcome == "denied" and attempt is None)
        or (attempt is not None and success is not None and success > attempt)):
        raise DriveInboxBlocked("Synthetic scan receipt sequence inconsistent")
    return clock, success, attempt


def evaluate_fake_scan_health(*, state: SyntheticScanHealth, now: datetime) -> dict:
    """Tell a future scheduler WHEN it could run; NEVER start it.

    An incomplete or failed page never overwrites last success. Denied
    permissions require owner reauthorization rather than unlimited retries.
    Expose only age and reason, no owner folder IDs, filenames or tokens.
    """
    clock, success, attempt = _guard(state, now)
    permission_lost = state.provider_permission == "fictional_revoked" or (
        state.last_outcome == "denied"
    )
    stale = success is None or clock - success > _STALE_AFTER
    if permission_lost:
        due_at = None
        reason = "REAUTHORIZATION_REQUIRED"
    elif state.last_outcome == "retryable":
        delay = _RETRY_DELAYS[min(state.consecutive_failures - 1, len(_RETRY_DELAYS) - 1)]
        due_at = attempt + delay
        reason = "RETRY_SCHEDULED"
    elif success is None:
        due_at = clock
        reason = "INITIAL_SCAN_PENDING"
    else:
        due_at = success + _SCAN_INTERVAL
        reason = "NORMAL_CADENCE"
    return {
        "contract": "personal_cfo_fake_drive_scan_cadence_v1",
        "synthetic_only": True,
        "one_folder_policy": True,
        "permission_state": "REAUTHORIZATION_REQUIRED" if permission_lost else "FICTIONAL_TEST_ONLY",
        "last_success_at": success.isoformat() if success else None,
        "next_due_at": due_at.isoformat() if due_at else None,
        "scan_due": bool(due_at is not None and due_at <= clock),
        "stale_or_never_scanned": stale,
        "reason": reason,
        "consecutive_failures": state.consecutive_failures,
        "heartbeat_is_real": False,
        "background_job_started": False,
        "google_drive_app_connected": False,
        "files_downloaded": False,
        "real_data_authorized": False,
    }


def record_fake_scan_outcome(
    *, state: SyntheticScanHealth, now: datetime,
    outcome: Literal["success", "retryable", "denied"],
) -> SyntheticScanHealth:
    """Pure state change; no persistent writes. Preserve success on failure."""
    clock, success, attempt = _guard(state, now)
    if outcome not in {"success", "retryable", "denied"}:
        raise DriveInboxBlocked("Unapproved synthetic scan result")
    if attempt is not None and clock < attempt:
        raise DriveInboxBlocked("Non-monotonic synthetic scan result")
    if state.provider_permission == "fictional_revoked" and outcome == "success":
        raise DriveInboxBlocked("Revoked provider cannot report scan success")
    if outcome == "success":
        return SyntheticScanHealth(
            last_success_at=clock, last_attempt_at=clock,
            consecutive_failures=0, last_outcome="success",
            provider_permission="fictional_authorized")
    return SyntheticScanHealth(
        last_success_at=success, last_attempt_at=clock,
        consecutive_failures=min(100, state.consecutive_failures + 1),
        last_outcome=outcome,
        provider_permission="fictional_revoked" if outcome == "denied"
            else state.provider_permission,
    )


def initial_fake_scan_health() -> SyntheticScanHealth:
    return SyntheticScanHealth(None, None, 0, "never", "fictional_authorized")
