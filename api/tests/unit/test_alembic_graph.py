"""ops/alembic_graph.py — deploy drift gate (2026-09-23). The real repo graph must stay single-headed, and the gate
must refuse a DB that is behind the code, a code tree with two heads, and a DB that is ahead of the code — unless every
revision it is ahead by is in the additive allowlist and chains back to the code head (decision D-A). Fail closed."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("alembic_graph", ROOT / "ops" / "alembic_graph.py")
ag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ag)  # type: ignore[union-attr]
VERSIONS = ROOT / "api" / "alembic" / "versions"
NL = "\n"


def _write(d: Path, rev: str, down: str | None) -> None:
    down_s = "None" if down is None else f'"{down}"'
    (d / f"{rev}_x.py").write_text(f'revision = "{rev}"\ndown_revision = {down_s}\n', encoding="utf-8")


def _build(tmp_path: Path, code: str) -> Path:
    d = tmp_path / "versions"
    d.mkdir()
    for chain in code.split("|"):
        revs = chain.split(">")
        for i, r in enumerate(revs):
            if not (d / f"{r}_x.py").exists():
                _write(d, r, revs[i - 1] if i else None)
    return d


def _run(monkeypatch, capsys, versions: Path, dbrev: str, allow: Path | None) -> tuple[int, str]:
    argv = ["x", "--dir", str(versions), "--check-db-revision", dbrev]
    if allow is not None:
        argv += ["--additive-allowlist", str(allow)]
    monkeypatch.setattr("sys.argv", argv)
    rc = ag.main()
    return rc, capsys.readouterr().out


def test_repo_graph_has_exactly_one_head():
    assert len(ag.heads(ag.from_dir(VERSIONS))) == 1


def test_parse_variants():
    assert ag.parse('revision = "b"\ndown_revision = "a"\n') == ("b", ["a"])
    assert ag.parse("revision: str = 'b'\ndown_revision: str | None = None\n") == ("b", [])
    assert ag.parse('revision = "m"\ndown_revision = ("a", "b")\n') == ("m", ["a", "b"])


# code a>b>c (head c). allow = allowlist lines joined by newline.
@pytest.mark.parametrize("case,dbrev,code,allow,expect", [
    ("equal", "c", "a>b>c", [], 0),
    ("pending", "b", "a>b>c", [], 3),
    ("ahead_not_listed", "zz", "a>b>c", [], 3),                       # the 2026-09-23 case before D-A
    ("ahead_listed", "d", "a>b>c", ["d c create_table only"], 0),
    ("ahead_two_listed", "e", "a>b>c", ["d c r", "e d r"], 0),
    ("ahead_chain_gap", "e", "a>b>c", ["e d r"], 3),                  # d is not listed
    ("ahead_listed_off_nonhead", "d", "a>b>c", ["d b r"], 3),         # code has c, the DB lacks it
    ("ahead_loop", "d", "a>b>c", ["d e r", "e d r"], 3),
    ("two_heads", "c", "a>b>c|b>x", [], 3),
    ("db_unreadable_empty", "", "a>b>c", [], 3),
    ("db_unreadable_none", "None", "a>b>c", [], 3),
    ("list_malformed", "c", "a>b>c", ["d c"], 3),                     # reason missing -> whole list rejected
    ("list_duplicate", "d", "a>b>c", ["d c r", "d c r2"], 3),
    ("comments_blank_ok", "d", "a>b>c", ["# header", "", "   ", "d c r"], 0),
])
def test_gate_matrix(tmp_path, monkeypatch, capsys, case, dbrev, code, allow, expect):
    versions = _build(tmp_path, code)
    allow_file = tmp_path / "additive_revisions.txt"
    allow_file.write_text(NL.join(allow) + NL, encoding="utf-8")
    rc, out = _run(monkeypatch, capsys, versions, dbrev, allow_file)
    assert rc == expect, (case, out)
    assert ("OK" in out) == (expect == 0), (case, out)


def test_gate_refuses_without_allowlist_argument(tmp_path, monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, _build(tmp_path, "a>b>c"), "c", None)
    assert rc == 3 and "fails closed" in out


def test_gate_refuses_when_allowlist_file_missing(tmp_path, monkeypatch, capsys):
    rc, out = _run(monkeypatch, capsys, _build(tmp_path, "a>b>c"), "c", tmp_path / "nope.txt")
    assert rc == 3 and "cannot read allowlist" in out


def test_real_repo_gate_today():
    """The repo's own graph + allowlist: DB == main head passes; the pre-PR#8 tree (head f3c6) against DB a7c9 passes
    only because a7c9 is allow-listed; the same without the list is refused; an unknown revision is refused."""
    allow = ag.load_allowlist(ROOT / "ops" / "additive_revisions.txt")
    g = ag.from_dir(VERSIONS)
    head = ag.heads(g)[0]
    assert ag.check_db_revision(g, head, allow)[0] == 0
    old = {r: ds for r, ds in g.items() if r != "a7c9e1f3b5d7"}          # the tree before PR #8
    assert ag.heads(old) == ["f3c6a8d0b2e4"]
    assert ag.check_db_revision(old, "a7c9e1f3b5d7", allow)[0] == 0
    assert ag.check_db_revision(old, "a7c9e1f3b5d7", {})[0] == 3
    assert ag.check_db_revision(g, "ffffffffffff", allow)[0] == 3
