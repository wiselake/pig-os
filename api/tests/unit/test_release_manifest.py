"""Decision D-B (2026-09-23): the server app tree must be tied to one commit. ops/release_manifest.py builds a release
tarball with RELEASE_MANIFEST.json; the deploy gate refuses unless the tree matches it file by file. The gate itself is
installed outside the app tree and checks its own files against GATE_SOURCE.json (decision D-A)."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
OPS = ROOT / "ops"
spec = importlib.util.spec_from_file_location("release_manifest", OPS / "release_manifest.py")
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)  # type: ignore[union-attr]

SHA = "a" * 40
OTHER = "b" * 40
MIG_A = b'revision = "r1"\ndown_revision = None\n'
MIG_B = b'revision = "r2"\ndown_revision = "r1"\n'


def _files() -> dict[str, bytes]:
    return {
        "api/app/main.py": b"print('api')\n",
        "api/alembic/versions/r1_init.py": MIG_A,
        "api/alembic/versions/r2_next.py": MIG_B,
        "src/app/page.tsx": b"export default 1\n",
        "ops/backup_db.sh": b"#!/bin/sh\necho s3\n",
        "nginx/pigos.conf": b"server {}\n",
        "docker-compose.prod.yml": b"services: {}\n",
    }


def _extract(tgz: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tgz) as t:
        t.extractall(dest, filter="data")
    return dest


def _release(tmp_path: Path, files: dict[str, bytes] | None = None, sha: str = SHA,
             execs: frozenset[str] = frozenset({"ops/backup_db.sh"})) -> Path:
    tgz = rm.pack_release(files or _files(), sha, tmp_path / "out", set(execs))
    return _extract(tgz, tmp_path / "pigos")


def test_manifest_records_sha_files_and_alembic_head(tmp_path):
    root = _release(tmp_path)
    m = json.loads((root / rm.MANIFEST).read_text(encoding="utf-8"))
    assert m["sha"] == SHA and m["alembic_heads"] == ["r2"]
    assert set(m["files"]) == set(_files())
    assert m["executables"] == ["ops/backup_db.sh"]


def _mutate(root: Path, case: str) -> str:
    """Apply one change to an extracted release; return the --expect-sha to use."""
    if case == "match":
        return SHA
    if case == "wrong_sha":
        return OTHER
    if case == "short_sha":
        return SHA[:12]
    if case == "modified_file":
        (root / "ops" / "backup_db.sh").write_bytes(b"#!/bin/sh\necho no-s3\n")      # the 2026-08-25 failure mode
    elif case == "missing_file":
        (root / "src" / "app" / "page.tsx").unlink()
    elif case == "extra_file_covered":
        (root / "api" / "app" / "leftover.py").write_text("x = 1\n", encoding="utf-8")
    elif case == "extra_migration":
        (root / "api" / "alembic" / "versions" / "r3_x.py").write_bytes(b'revision = "r3"\ndown_revision = "r2"\n')
    elif case == "manifest_missing":
        (root / rm.MANIFEST).unlink()
    elif case == "manifest_corrupt":
        (root / rm.MANIFEST).write_text("{not json", encoding="utf-8")
    elif case == "manifest_no_executables_key":
        m = json.loads((root / rm.MANIFEST).read_text(encoding="utf-8"))
        del m["executables"]
        (root / rm.MANIFEST).write_text(json.dumps(m), encoding="utf-8")
    elif case == "manifest_wrong_format":
        m = json.loads((root / rm.MANIFEST).read_text(encoding="utf-8"))
        m["format"] = 999
        (root / rm.MANIFEST).write_text(json.dumps(m), encoding="utf-8")
    elif case == "cache_dirs_ok":
        for d in ("api/app/__pycache__", "src/node_modules/x", "src/.next", "api/.mypy_cache"):
            (root / d).mkdir(parents=True, exist_ok=True)
            (root / d / "junk.bin").write_bytes(b"\0")
    elif case == "outside_covered_ok":
        (root / ".env").write_text("SECRET=x\n", encoding="utf-8")
        (root / "api.bak-20260101").mkdir()
        (root / "api.bak-20260101" / "old.py").write_text("x\n", encoding="utf-8")
        (root / "docker-compose.prod.yml.bak").write_text("old\n", encoding="utf-8")
    else:
        raise AssertionError(case)
    return SHA


@pytest.mark.parametrize("case,expect", [
    ("match", 0),
    ("wrong_sha", 3),
    ("short_sha", 3),
    ("modified_file", 3),
    ("missing_file", 3),
    ("extra_file_covered", 3),
    ("extra_migration", 3),
    ("manifest_missing", 3),
    ("manifest_corrupt", 3),
    ("manifest_wrong_format", 3),
    ("manifest_no_executables_key", 3),
    ("cache_dirs_ok", 0),
    ("outside_covered_ok", 0),
])
def test_verify_matrix(tmp_path, case, expect):
    root = _release(tmp_path)
    rc, msgs = rm.verify(root, _mutate(root, case))
    assert rc == expect, (case, msgs)
    assert msgs[0].startswith("OK" if expect == 0 else "REFUSED"), (case, msgs)


_POSIX = os.name == "posix"


@pytest.mark.skipif(not _POSIX and not os.environ.get("CI"), reason="exec bits are POSIX-only (runs in CI)")
def test_verify_refuses_lost_exec_bit(tmp_path):
    """cron runs ~/pigos/ops/backup_db.sh directly; a release that drops its exec bit would silently stop backups."""
    assert _POSIX, "CI must run this on POSIX - a skip here would hide it"
    root = _release(tmp_path)
    assert rm.verify(root, SHA)[0] == 0
    (root / "ops" / "backup_db.sh").chmod(0o644)
    rc, msgs = rm.verify(root, SHA)
    assert rc == 3 and any("not executable ops/backup_db.sh" in x for x in msgs), msgs


def test_build_from_real_repo_head_round_trips(tmp_path):
    """git archive of this commit → tarball → extract → verify == OK; covers every covered path present at HEAD."""
    tgz = rm.build("HEAD", tmp_path / "out")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=ROOT).stdout.strip()
    root = _extract(tgz, tmp_path / "pigos")
    rc, msgs = rm.verify(root, sha)
    assert rc == 0, msgs
    m = json.loads((root / rm.MANIFEST).read_text(encoding="utf-8"))
    assert any(p.startswith("ops/") for p in m["files"]) and any(p.startswith("api/app/") for p in m["files"])
    # git mode 100755 → recorded executable (cron and the gate call these directly)
    assert {"ops/backup_db.sh", "ops/backup_incremental.sh", "ops/deploy.sh", "ops/check_migration_drift.sh"} <= set(m["executables"])
    assert (tmp_path / "out" / f"{tgz.name}.sha256").read_text(encoding="utf-8").split()[0] == rm._sha256(tgz.read_bytes())


# ── gate integrity ─────────────────────────────────────────────────────────────────────────────────────────────────
def _gate(tmp_path: Path) -> Path:
    files = {n: (OPS / n).read_bytes() for n in rm.GATE_FILES}
    return _extract(rm.pack_gate(files, SHA, tmp_path / "gout"), tmp_path / "gate")


def test_gate_verifies_itself(tmp_path):
    g = _gate(tmp_path)
    assert rm.verify_gate(g)[0] == 0


@pytest.mark.parametrize("case", ["modified", "missing", "source_missing", "source_corrupt"])
def test_gate_refuses_when_tampered(tmp_path, case):
    g = _gate(tmp_path)
    if case == "modified":
        (g / "additive_revisions.txt").write_text("zz f3c6a8d0b2e4 sneaked in\n", encoding="utf-8")
    elif case == "missing":
        (g / "alembic_graph.py").unlink()
    elif case == "source_missing":
        (g / rm.GATE_SOURCE).unlink()
    else:
        (g / rm.GATE_SOURCE).write_text("[]", encoding="utf-8")
    rc, msgs = rm.verify_gate(g)
    assert rc == 3 and msgs[0].startswith("REFUSED"), msgs


# ── the real deploy.sh, preflight only (web: no DB step, no docker, no build) ─────────────────────────────────────────
_CAN_SHELL = sys.platform != "win32" and shutil.which("bash") and shutil.which("python3")


@pytest.mark.skipif(not _CAN_SHELL and not os.environ.get("CI"), reason="needs bash + python3 (runs in CI)")
@pytest.mark.parametrize("case,expect", [
    ("pass", 0),
    ("wrong_sha", 3),
    ("tampered_tree", 3),
    ("no_manifest", 3),
    ("tampered_gate", 3),
    ("run_from_app_tree", 3),
    ("no_expect_sha", 2),
])
def test_deploy_sh_preflight(tmp_path, case, expect):
    assert _CAN_SHELL, "CI must be able to run deploy.sh preflight - a skip here would hide it"
    files = _files()
    files.update({f"ops/{n}": (OPS / n).read_bytes() for n in rm.GATE_FILES})    # the release carries ops/ too
    root = _release(tmp_path, files, execs=frozenset({"ops/backup_db.sh", "ops/deploy.sh", "ops/check_migration_drift.sh"}))
    gate = _gate(tmp_path)
    script = gate / "deploy.sh"
    args = ["web", "--expect-sha", SHA, "--preflight-only"]
    if case == "wrong_sha":
        args[2] = OTHER
    elif case == "tampered_tree":
        (root / "ops" / "backup_db.sh").write_bytes(b"#!/bin/sh\necho no-s3\n")
    elif case == "no_manifest":
        (root / rm.MANIFEST).unlink()
    elif case == "tampered_gate":
        (gate / "additive_revisions.txt").write_text("zz f3c6a8d0b2e4 sneaked in\n", encoding="utf-8")
    elif case == "run_from_app_tree":
        script = root / "ops" / "deploy.sh"
    elif case == "no_expect_sha":
        args = ["web", "--preflight-only"]
    r = subprocess.run(["bash", str(script), *args], capture_output=True, text=True,
                       env={**os.environ, "PIGOS_ROOT": str(root)})
    assert r.returncode == expect, r.stdout + r.stderr
