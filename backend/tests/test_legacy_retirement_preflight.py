"""G1 A8 retirement preflight must refuse every non-restored/private database."""
import pytest
from sqlalchemy import create_engine

from app.legacy_retirement_preflight import (
    inspect_restored_legacy_schema, LegacyRetirementBlocked,
)


def test_local_sqlite_cannot_be_mistaken_for_verified_retirement(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    engine=create_engine(f"sqlite:///{tmp_path / 'fake.db'}")
    with pytest.raises(LegacyRetirementBlocked,match="Only independent"):
        inspect_restored_legacy_schema(engine)


def test_real_data_mode_blocks_retirement_even_if_report_only(tmp_path,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","real")
    engine=create_engine(f"sqlite:///{tmp_path / 'fake.db'}")
    with pytest.raises(LegacyRetirementBlocked,match="Real-data"):
        inspect_restored_legacy_schema(engine)


@pytest.mark.parametrize("database", [
    "synthetic_ci_db", "production", "synthetic_source",
    "postgres", "synthetic_restore_X", "synthetic_restore_",
])
def test_database_name_firewall_denies_wrong_clone(database,monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    from sqlalchemy import create_engine
    engine=create_engine(f"postgresql+psycopg://fake:fake@localhost:5432/{database}")
    # Validation occurs BEFORE any connection attempt; no network needed.
    with pytest.raises(LegacyRetirementBlocked,match="independent"):
        inspect_restored_legacy_schema(engine)


def test_only_scoped_offline_status_is_reported():
    from app.g1c_preflight import LEGACY_FINANCE_TABLES
    assert "transactions" in LEGACY_FINANCE_TABLES
    assert "historical_filings" in LEGACY_FINANCE_TABLES
    assert "loan_accounts" in LEGACY_FINANCE_TABLES
    assert "cash_movements" in LEGACY_FINANCE_TABLES
    assert "asset_snapshots" in LEGACY_FINANCE_TABLES
