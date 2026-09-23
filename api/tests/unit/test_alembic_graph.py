"""ops/alembic_graph.py — deploy drift gate (2026-09-23). The real repo graph must stay single-headed, and the gate
must refuse a DB that is ahead of the code, a DB that is behind it, and a code tree with two heads."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("alembic_graph", ROOT / "ops" / "alembic_graph.py")
ag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ag)  # type: ignore[union-attr]
VERSIONS = ROOT / "api" / "alembic" / "versions"


def _write(d: Path, rev: str, down: str | None) -> None:
    down_s = "None" if down is None else f'"{down}"'
    (d / f"{rev}_x.py").write_text(f'revision = "{rev}"\ndown_revision = {down_s}\n', encoding="utf-8")


def test_repo_graph_has_exactly_one_head():
    assert len(ag.heads(ag.from_dir(VERSIONS))) == 1


def test_parse_variants():
    assert ag.parse('revision = "b"\ndown_revision = "a"\n') == ("b", ["a"])
    assert ag.parse("revision: str = 'b'\ndown_revision: str | None = None\n") == ("b", [])
    assert ag.parse('revision = "m"\ndown_revision = ("a", "b")\n') == ("m", ["a", "b"])


@pytest.mark.parametrize("dbrev,code,expect", [
    ("c", "a>b>c", 0),          # equal
    ("b", "a>b>c", 3),          # pending migration
    ("zz", "a>b>c", 3),         # DB ahead of code (today's real case: main vs a7c9e1f3b5d7)
    ("c", "a>b>c|b>d", 3),      # two heads
])
def test_check_db_revision(tmp_path, monkeypatch, capsys, dbrev, code, expect):
    for chain in code.split("|"):
        revs = chain.split(">")
        for i, r in enumerate(revs):
            if not (tmp_path / f"{r}_x.py").exists():
                _write(tmp_path, r, revs[i - 1] if i else None)
    monkeypatch.setattr("sys.argv", ["x", "--dir", str(tmp_path), "--check-db-revision", dbrev])
    assert ag.main() == expect
    out = capsys.readouterr().out
    assert ("OK" in out) == (expect == 0)
