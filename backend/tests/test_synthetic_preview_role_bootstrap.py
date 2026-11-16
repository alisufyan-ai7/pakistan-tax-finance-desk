"""G2: irreversible live DDL is prohibited; CI-only bootstrap contract."""
import os
import pytest

from app.synthetic_preview_role_bootstrap import (
    PreviewRoleBootstrapBlocked, provision_synthetic_preview_role,
)


class FakeAdmin:
    def __init__(self, name="synthetic_ci_db", existing=None):
        self.name = name
        self.existing = existing
        self.calls = []
    def execute(self, query, *params):
        code = str(query)
        self.calls.append(code)
        class Row:
            def __init__(self, data):
                self.data = data
            def fetchone(self):
                return (self.data,)
        if code.startswith("SELECT current_database()"):
            return Row(self.name)
        if code.startswith("SELECT to_regrole("):
            return Row(self.existing)
        return Row(None)
    def transaction(self):
        class Tx:
            def __enter__(self):
                return self
            def __exit__(self,*args):
                pass
        return Tx()


def allowed(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("G2_EPHEMERAL_CI_ONLY", "1")


def test_ci_only_role_has_no_table_grants_or_public_temp(monkeypatch):
    allowed(monkeypatch)
    admin = FakeAdmin()
    result = provision_synthetic_preview_role(admin, password="synthetic_ci_password_for_tests_123")
    assert result["live_railway_role_changed"] is False
    commands = " ".join(admin.calls)
    assert "REVOKE TEMPORARY" in commands
    assert "CREATE ROLE" in commands
    assert "GRANT CONNECT" in commands
    assert "GRANT SELECT" not in commands
    assert "GRANT ALL" not in commands
    assert "ALTER SYSTEM" not in commands


@pytest.mark.parametrize("database", ["postgres","production","synthetic_restore_verified","personal_cfo_dev"])
def test_never_touch_other_databases(monkeypatch, database):
    allowed(monkeypatch)
    admin = FakeAdmin(database)
    with pytest.raises(PreviewRoleBootstrapBlocked):
        provision_synthetic_preview_role(admin, password="synthetic_ci_password_for_tests_123")
    assert not any("CREATE ROLE" in str(q) for q in admin.calls)


def test_reject_existing_role_password_error_and_real_mode(monkeypatch):
    allowed(monkeypatch)
    with pytest.raises(PreviewRoleBootstrapBlocked):
        provision_synthetic_preview_role(FakeAdmin(existing="role"), password="synthetic_ci_password_for_tests_123")
    with pytest.raises(PreviewRoleBootstrapBlocked):
        provision_synthetic_preview_role(FakeAdmin(), password="short")
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(PreviewRoleBootstrapBlocked):
        provision_synthetic_preview_role(FakeAdmin(), password="synthetic_ci_password_for_tests_123")
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.delenv("G2_EPHEMERAL_CI_ONLY", raising=False)
    with pytest.raises(PreviewRoleBootstrapBlocked):
        provision_synthetic_preview_role(FakeAdmin(), password="synthetic_ci_password_for_tests_123")


def test_db_failure_sanitized(monkeypatch):
    allowed(monkeypatch)
    class Broken:
        def execute(self, *args, **kwargs):
            raise RuntimeError("synthetic_password_should_not_escape")
    with pytest.raises(PreviewRoleBootstrapBlocked) as exc:
        provision_synthetic_preview_role(Broken(), password="synthetic_ci_password_for_tests_123")
    assert "should_not_escape" not in str(exc.value)
