"""G1-c offline backup-first sealed candidate safety tests; synthetic only."""
import base64
from pathlib import Path

import pytest

from app import g1c_candidate
from app.g1c_candidate import G1CCandidateBlocked, create_verified_sealed_candidate


def _fake_snapshot_keys(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("PG_SNAPSHOT_KEY", base64.urlsafe_b64encode(b"R" * 32).decode())


def test_real_mode_blocked_before_any_legacy_db_access(tmp_path, monkeypatch):
    _fake_snapshot_keys(monkeypatch)
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(G1CCandidateBlocked, match="real"):
        create_verified_sealed_candidate(tmp_path / "unused.tfpg")
    assert not (tmp_path / "unused.tfpg").exists()


def test_guard_requires_specific_source_restore_and_distinct_keys(monkeypatch):
    _fake_snapshot_keys(monkeypatch)
    source = "postgresql://synthetic:fictional@localhost/synthetic_fixture_db"
    target = "postgresql://synthetic:fictional@localhost/synthetic_restore_fixture"
    monkeypatch.setenv("PG_G1C_SOURCE_DSN", source)
    monkeypatch.setenv("PG_SNAPSHOT_SOURCE_DSN", source)
    monkeypatch.setenv("PG_SNAPSHOT_RESTORE_DSN", target)
    assert g1c_candidate._guards() == (source, target)
    monkeypatch.setenv("PG_SNAPSHOT_SOURCE_DSN",
                       "postgresql://synthetic:fictional@localhost/synthetic_wrong")
    with pytest.raises(G1CCandidateBlocked, match="exact preflight"):
        g1c_candidate._guards()
    monkeypatch.setenv("PG_SNAPSHOT_SOURCE_DSN", source)
    monkeypatch.setenv("PRIVATE_EVENT_HMAC_KEY", base64.urlsafe_b64encode(b"R" * 32).decode())
    with pytest.raises(G1CCandidateBlocked, match="independent"):
        g1c_candidate._guards()


def test_blocking_source_graph_never_calls_backup_or_restore(monkeypatch, tmp_path):
    monkeypatch.setattr(g1c_candidate, "_guards", lambda: ("synthetic-source", "synthetic-restore"))
    monkeypatch.setattr(g1c_candidate, "preflight_postgres_source",
                        lambda **kwargs: {"source_graph_consistent": False})
    def forbid(*args, **kwargs):
        raise AssertionError("Backup/restore must never start for inconsistent sources")
    monkeypatch.setattr(g1c_candidate, "create_pg_snapshot", forbid)
    monkeypatch.setattr(g1c_candidate, "restore_pg_snapshot", forbid)
    with pytest.raises(G1CCandidateBlocked, match="blocking source anomalies"):
        create_verified_sealed_candidate(tmp_path / "unused.tfpg")


def test_snapshot_change_prevents_restore_and_candidate_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(g1c_candidate, "_guards", lambda: ("fictional", "fictional-restore"))
    first = {"source_graph_consistent": True,
             "table_counts": {"canonical_source_mirrors": 0},
             "source_integrity_hmac": "initial",
             "year_owner_account_direction_hmac": "initial-year"}
    second = dict(first, source_integrity_hmac="changed")
    responses = iter([first, second])
    monkeypatch.setattr(g1c_candidate, "preflight_postgres_source",
                        lambda **kwargs: next(responses))
    monkeypatch.setattr(g1c_candidate, "create_pg_snapshot",
                        lambda backup_file: {"encrypted": True, "verified_read_snapshot": True})
    def forbid(*args, **kwargs):
        raise AssertionError("Restore/copy not permitted when source HMAC changed")
    monkeypatch.setattr(g1c_candidate, "restore_pg_snapshot", forbid)
    monkeypatch.setattr(g1c_candidate, "_copy_all_as_sealed_candidate", forbid)
    with pytest.raises(G1CCandidateBlocked, match="changed during encrypted backup"):
        create_verified_sealed_candidate(tmp_path / "sealed.tfpg")


def test_only_reviewed_registered_mirror_schema_is_copyable(monkeypatch):
    tables = g1c_candidate._non_mirror_tables()
    assert "transactions" in tables
    assert "loan_allocations" in tables
    assert "historical_filings" in tables
    assert "cash_movement_reversals" in tables
    assert "canonical_source_mirrors" not in tables
    assert len(tables) == 35
