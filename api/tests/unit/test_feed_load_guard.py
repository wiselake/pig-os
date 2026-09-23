"""Initial-load 가드 — 기본은 거부, 기대가 하나라도 어긋나면 거부 (APPROVAL GATE §5).

여기서 통과하는 조합은 단 하나: --apply + 다섯 기대값이 전부 실제와 일치.
"""
from __future__ import annotations

import pytest

from app.harvest import feed_load_guard as g

LOCAL = "postgresql+asyncpg://u:p@localhost:5432/pigos"
PROD = "postgresql+asyncpg://u:p@172.18.0.1:5434/pigos"
FULL = g.Expectations(environment="production", code_sha="x" * 64, migration="a7c9e1f3b5d7",
                      source_scope_hash="s" * 64, source_rows=5461)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)


class TestEnvironmentDetection:
    def test_local_is_local_and_prod_env_var_wins(self, monkeypatch):
        assert g.detect_environment(LOCAL) == "local"
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert g.detect_environment(LOCAL) == "production"      # 로컬 호스트라도 환경변수가 production 이면 production
        assert g.detect_environment(PROD) == "production"

    def test_unknown_when_nothing_says_where_we_are(self):
        assert g.detect_environment(PROD) == "unknown"          # 사설 IP + 환경변수 없음 → 모름
        assert g.detect_environment("postgresql://u:p@db.example.rds.amazonaws.com/x") == "production"


class TestModes:
    def test_dry_run_never_writes_and_needs_nothing(self):
        assert g.check_write_allowed("dry-run", PROD, g.Expectations())["writes"] == "none"

    def test_target_local_refuses_non_local(self, monkeypatch):
        assert g.check_write_allowed("target-local", LOCAL, g.Expectations())["writes"] == "local"
        with pytest.raises(g.RefusedError, match="local/ephemeral"):
            g.check_write_allowed("target-local", PROD, g.Expectations())
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(g.RefusedError, match="local/ephemeral"):
            g.check_write_allowed("target-local", LOCAL, g.Expectations())   # 프로덕션 환경변수면 로컬 호스트여도 거부

    def test_unknown_mode_refused(self):
        with pytest.raises(g.RefusedError):
            g.check_write_allowed("yolo", LOCAL, g.Expectations())


class TestApply:
    def test_apply_without_expectations_is_refused(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(g.RefusedError, match="missing: --expect-environment, --expect-code-sha"):
            g.check_write_allowed("apply", PROD, g.Expectations())

    @pytest.mark.parametrize("field", ["environment", "code_sha", "migration", "source_scope_hash", "source_rows"])
    def test_each_missing_expectation_is_refused(self, monkeypatch, field):
        monkeypatch.setenv("ENVIRONMENT", "production")
        kw = {**FULL.__dict__, field: None}
        with pytest.raises(g.RefusedError, match="missing"):
            g.check_write_allowed("apply", PROD, g.Expectations(**kw))

    def test_environment_mismatch_refused(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(g.RefusedError, match="environment mismatch"):
            g.check_write_allowed("apply", PROD, g.Expectations(**{**FULL.__dict__, "environment": "staging"}))

    def test_unknown_environment_refused(self):
        with pytest.raises(g.RefusedError, match="could not be determined"):
            g.check_write_allowed("apply", PROD, FULL)               # ENVIRONMENT 없음 → unknown

    def test_code_fingerprint_mismatch_refused(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(g.RefusedError, match="code fingerprint mismatch"):
            g.check_write_allowed("apply", PROD, FULL)

    def test_apply_passes_only_with_the_real_fingerprint(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        ok = g.check_write_allowed("apply", PROD, g.Expectations(**{**FULL.__dict__, "code_sha": g.code_fingerprint()}))
        assert ok["mode"] == "apply" and ok["environment"] == "production" and ok["writes"] == "target"

    def test_fingerprint_changes_when_load_code_changes(self, tmp_path):
        root = tmp_path / "api"
        for rel in g.FINGERPRINT_FILES:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")
        first = g.code_fingerprint(root)
        (root / g.FINGERPRINT_FILES[0]).write_text("x2", encoding="utf-8")
        assert g.code_fingerprint(root) != first
        assert g.code_fingerprint(root) == g.code_fingerprint(root)          # 결정론
        (root / g.FINGERPRINT_FILES[0]).unlink()
        with pytest.raises(g.RefusedError, match="fingerprint source missing"):
            g.code_fingerprint(root)


class TestMigrationAndScope:
    def test_migration_checks(self):
        g.check_migration("a7c9e1f3b5d7", "a7c9e1f3b5d7", ["a7c9e1f3b5d7"])
        with pytest.raises(g.RefusedError, match="exactly one head"):
            g.check_migration("a7c9e1f3b5d7", "a7c9e1f3b5d7", ["a7c9e1f3b5d7", "other"])
        with pytest.raises(g.RefusedError, match="!= approved migration"):
            g.check_migration("a7c9e1f3b5d7", "a7c9e1f3b5d7", ["zzz"])
        with pytest.raises(g.RefusedError, match="apply the migration first"):
            g.check_migration("a7c9e1f3b5d7", "f3c6a8d0b2e4", ["a7c9e1f3b5d7"])

    def test_scope_checks(self):
        g.check_scope("h" * 64, "h" * 64, 5461, 5461, unmapped_farms=0)
        with pytest.raises(g.RefusedError, match="scope hash mismatch"):
            g.check_scope("h" * 64, "z" * 64, 5461, 5461, unmapped_farms=0)
        with pytest.raises(g.RefusedError, match="no PigOS mapping"):
            g.check_scope("h" * 64, "h" * 64, 5461, 5461, unmapped_farms=3)
        with pytest.raises(g.RefusedError, match="row count changed since preflight"):
            g.check_scope("h" * 64, "h" * 64, 5461, 5470, unmapped_farms=0)
