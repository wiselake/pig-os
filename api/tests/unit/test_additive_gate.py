"""Decision D-A (2026-09-23): the deploy gate lets an older code tree run on a database that is ahead of it only through
revisions listed in ops/additive_revisions.txt. This file keeps that list honest:
  - ops/additive_migration.py judges a destructive upgrade() NOT additive (it has to be able to fail)
  - every listed revision exists in the repo, its down_revision matches the listed parent, and it is judged ADDITIVE
  - the real shell entry point (ops/check_migration_drift.sh) refuses when the list is missing or corrupt
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
VERSIONS = ROOT / "api" / "alembic" / "versions"
OPS = ROOT / "ops"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, OPS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


am = _load("additive_migration")
ag = _load("alembic_graph")


def _mig(body: str) -> str:
    lines = "\n".join("    " + ln for ln in body.strip().splitlines())
    return f"import sqlalchemy as sa\nfrom alembic import op\n\n\ndef upgrade() -> None:\n{lines}\n\n\ndef downgrade() -> None:\n    pass\n"


@pytest.mark.parametrize("body,additive", [
    ("op.create_table('t', sa.Column('id', sa.Integer()))\nop.create_index('ix', 't', ['id'], unique=True)", True),
    ("op.create_index('ix', 'farms', ['name'])", True),                                   # non-unique on existing
    ("op.add_column('farms', sa.Column('x', sa.String(), nullable=True))", True),
    ("op.add_column('farms', sa.Column('x', sa.Integer(), nullable=False, server_default='0'))", True),
    ("pass", True),
    ("op.drop_column('farms', 'name')", False),
    ("op.drop_table('farms')", False),
    ("op.alter_column('farms', 'name', nullable=False)", False),
    ("op.rename_table('farms', 'farm')", False),
    ("op.execute('UPDATE farms SET name = 1')", False),
    ("op.add_column('farms', sa.Column('x', sa.Integer(), nullable=False))", False),     # old INSERTs fail
    ("op.add_column('farms', sa.Column('x', sa.Integer()))", False),                     # nullable not proven
    ("op.create_index('ix', 'farms', ['name'], unique=True)", False),
    ("op.create_check_constraint('ck', 'farms', 'x > 0')", False),
    ("op.create_foreign_key('fk', 'farms', 'orgs', ['org_id'], ['id'])", False),
    ("conn = op.get_bind()", False),                                                     # not a plain op call
    ("for t in ['a']:\n    op.create_table(t)", False),
])
def test_checker_judgement(body, additive):
    ok, reasons = am.check(_mig(body))
    assert ok is additive, reasons
    assert (reasons == []) is additive


def test_checker_refuses_unparseable_and_ambiguous():
    assert am.check("def upgrade(:\n")[0] is False
    assert am.check("x = 1\n")[0] is False                                               # no upgrade()
    assert am.check(_mig("pass") + "\n\ndef upgrade() -> None:\n    pass\n")[0] is False  # two upgrade()


def test_review_note_flags_fk_to_existing_table():
    body = "op.create_table('n', sa.Column('farm_id', sa.UUID()), sa.ForeignKeyConstraint(['farm_id'], ['farms.id']))"
    assert am.check(_mig(body))[0] is True
    notes = am.review_notes(_mig(body))
    assert len(notes) == 1 and "farms" in notes[0]


def _allowlist() -> dict[str, str]:
    return ag.load_allowlist(OPS / "additive_revisions.txt")


def test_every_allowlisted_revision_is_real_matching_and_additive():
    files = {}
    for f in VERSIONS.glob("*.py"):
        p = ag.parse(f.read_text(encoding="utf-8"))
        if p:
            files[p[0]] = (f, p[1])
    allow = _allowlist()
    assert allow, "allowlist is empty - a7c9e1f3b5d7 is expected (evidence w1_a7c9_additive.txt)"
    for rev, parent in allow.items():
        assert rev in files, f"allow-listed {rev} has no migration file in the repo"
        f, downs = files[rev]
        assert downs == [parent], f"{rev}: listed parent {parent} != down_revision {downs}"
        ok, reasons = am.check(f.read_text(encoding="utf-8"))
        assert ok, f"{rev} is allow-listed but not additive: {reasons}"


# ── the real shell entry point ──────────────────────────────────────────────────────────────────────────────────────
_CAN_SHELL = sys.platform != "win32" and shutil.which("bash") and shutil.which("python3")


def _gate_dir(tmp_path: Path, allow_text: str | None) -> Path:
    g = tmp_path / "gate"
    g.mkdir()
    for n in ("check_migration_drift.sh", "alembic_graph.py"):
        shutil.copy(OPS / n, g / n)
    if allow_text is not None:
        (g / "additive_revisions.txt").write_text(allow_text, encoding="utf-8")
    return g


def _old_tree(tmp_path: Path) -> Path:
    d = tmp_path / "old_versions"
    d.mkdir()
    for f in VERSIONS.glob("*.py"):
        if not f.name.startswith("a7c9e1f3b5d7"):
            shutil.copy(f, d / f.name)
    return d


@pytest.mark.skipif(not _CAN_SHELL and not os.environ.get("CI"), reason="needs bash + python3 (runs in CI)")
@pytest.mark.parametrize("allow_text,expect", [
    ((OPS / "additive_revisions.txt").read_text(encoding="utf-8"), 0),     # installed list → old tree may run on a7c9
    (None, 3),                                                              # list missing
    ("a7c9e1f3b5d7 f3c6a8d0b2e4\n", 3),                                     # list corrupt (reason missing)
    ("# empty\n", 3),                                                       # a7c9 not listed
])
def test_shell_gate_old_tree_on_a7c9(tmp_path, allow_text, expect):
    assert _CAN_SHELL, "CI must be able to run the shell gate - a skip here would hide it"
    g = _gate_dir(tmp_path, allow_text)
    r = subprocess.run(["bash", str(g / "check_migration_drift.sh"), "a7c9e1f3b5d7", str(_old_tree(tmp_path))],
                       capture_output=True, text=True)
    assert r.returncode == expect, r.stdout + r.stderr
