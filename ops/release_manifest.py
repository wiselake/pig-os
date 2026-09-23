"""Release manifest — say, with a SHA, what source is on the server (decision D-B, 2026-09-23).

Why: the server tree ~/pigos was never a git checkout. On 2026-08-25 a tree without the S3 backup commits was
unpacked over it and nothing noticed for four weeks (docs/feed/runs/goal_20260923/evidence/r1_forensics.txt).

    # workstation: build the release tarball for one commit (RELEASE_MANIFEST.json is inside the tarball, at its root)
    python ops/release_manifest.py build --ref <40-hex sha> --out <dir>
    # server (deploy gate, before anything else): the tree must be exactly that commit
    python3 release_manifest.py verify --root ~/pigos --expect-sha <40-hex sha>

verify refuses (exit 3) when: the manifest is missing or unreadable · its sha != --expect-sha · any listed file is
missing or its sha256 differs · a file exists under a covered directory but is not listed (caches excepted) ·
the tree's alembic head != the manifest's. Files outside the covered paths (.env, backups, other trees) are ignored.
No switch turns a refusal into a pass.

The deploy gate itself lives OUTSIDE the app tree (decision D-A: on a rollback the app tree is older than the DB):
    python ops/release_manifest.py gate-build --ref <sha> --out <dir>     # pigos-gate-<sha12>.tar.gz with GATE_SOURCE.json
    python3 release_manifest.py verify-gate --dir ~/pigos-gate           # deploy.sh checks itself with this first
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

FORMAT = 1
MANIFEST = "RELEASE_MANIFEST.json"
GATE_SOURCE = "GATE_SOURCE.json"
GATE_FILES = ("deploy.sh", "check_migration_drift.sh", "alembic_graph.py", "additive_revisions.txt", "release_manifest.py")
COVERED_DIRS = ("api", "src", "ops", "nginx")
COVERED_FILES = ("docker-compose.prod.yml", "docker-compose.deploy.yml")
CACHE_DIRS = {"__pycache__", "node_modules", ".next", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv"}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
REV = re.compile(r'^revision\s*(?::\s*str\s*)?=\s*["\']([0-9a-zA-Z_]+)["\']', re.M)
DOWN = re.compile(r'^down_revision\s*(?::[^=]*)?=\s*(None|["\']([0-9a-zA-Z_]+)["\']|\(([^)]*)\))', re.M)


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def alembic_head(files: dict[str, bytes]) -> list[str]:
    """Heads of the alembic graph among api/alembic/versions/*.py in a {path: content} map (same rule as alembic_graph)."""
    graph: dict[str, list[str]] = {}
    for p, b in files.items():
        if p.startswith("api/alembic/versions/") and p.endswith(".py") and p.count("/") == 3:
            t = b.decode("utf-8", errors="replace")
            r, d = REV.search(t), DOWN.search(t)
            if r and d:
                graph[r.group(1)] = [] if d.group(1) == "None" else ([d.group(2)] if d.group(2) else re.findall(r'["\']([0-9a-zA-Z_]+)["\']', d.group(3) or ""))
    parents = {x for ds in graph.values() for x in ds}
    return sorted(set(graph) - parents)


def covered(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in CACHE_DIRS for p in parts):
        return False
    return rel in COVERED_FILES or parts[0] in COVERED_DIRS


def manifest_for(files: dict[str, bytes], sha: str) -> dict:
    listed = {p: _sha256(b) for p, b in sorted(files.items()) if covered(p)}
    return {"format": FORMAT, "sha": sha, "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "covered_dirs": list(COVERED_DIRS), "covered_files": list(COVERED_FILES),
            "alembic_heads": alembic_head(files), "files": listed}


def _tree_files(root: Path) -> dict[str, bytes]:
    out = {}
    for p in root.rglob("*"):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if covered(rel):
                out[rel] = p.read_bytes()
    return out


def verify(root: Path, expect_sha: str) -> tuple[int, list[str]]:
    if not FULL_SHA.match(expect_sha or ""):
        return 3, ["REFUSED: --expect-sha must be a full 40-hex commit sha"]
    mp = root / MANIFEST
    try:
        m = json.loads(mp.read_text(encoding="utf-8"))
        files, msha = m["files"], m["sha"]
        if m.get("format") != FORMAT or not isinstance(files, dict):
            raise ValueError("format")
    except FileNotFoundError:
        return 3, [f"REFUSED: {MANIFEST} not found in {root} - the server tree cannot be tied to a commit"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        return 3, [f"REFUSED: {MANIFEST} unreadable ({e.__class__.__name__})"]
    if msha != expect_sha:
        return 3, [f"REFUSED: server tree is {msha}, deploy target is {expect_sha}"]
    tree = _tree_files(root)
    bad = []
    for p, h in files.items():
        b = tree.get(p)
        if b is None:
            bad.append(f"missing {p}")
        elif _sha256(b) != h:
            bad.append(f"modified {p}")
    bad += [f"not in release {p}" for p in sorted(set(tree) - set(files))]
    if bad:
        return 3, [f"REFUSED: server tree differs from release {msha} in {len(bad)} file(s)"] + [f"  {x}" for x in bad[:50]]
    heads = alembic_head(tree)
    if heads != m.get("alembic_heads"):
        return 3, [f"REFUSED: alembic heads {heads} != manifest {m.get('alembic_heads')}"]
    return 0, [f"OK: server tree == release {msha} ({len(files)} files, alembic head {heads})"]


def build(ref: str, out: Path) -> Path:
    sha = _commit(ref)
    paths = [p for p in (*COVERED_DIRS, *COVERED_FILES) if _git("cat-file", "-e", f"{sha}:{p}").returncode == 0]
    r = _git("archive", "--format=tar", sha, "--", *paths)
    r.check_returncode()
    raw = r.stdout
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as t:
        for mem in t.getmembers():
            if mem.isfile():
                files[mem.name] = t.extractfile(mem).read()
    return pack_release(files, sha, out)


def pack_release(files: dict[str, bytes], sha: str, out: Path) -> Path:
    m = manifest_for(files, sha)
    out.mkdir(parents=True, exist_ok=True)
    tgz = out / f"pigos-release-{sha[:12]}.tar.gz"
    _write_tgz(tgz, {**files, MANIFEST: json.dumps(m, indent=1, sort_keys=True).encode()})
    return tgz


def _write_tgz(tgz: Path, files: dict[str, bytes], modes: dict[str, int] | None = None) -> None:
    with tarfile.open(tgz, "w:gz") as t:
        for p, b in sorted(files.items()):
            ti = tarfile.TarInfo(p)
            ti.size, ti.mode = len(b), (modes or {}).get(p, 0o644)
            t.addfile(ti, io.BytesIO(b))
    (tgz.parent / f"{tgz.name}.sha256").write_text(f"{_sha256(tgz.read_bytes())}  {tgz.name}\n", encoding="utf-8")


def _git(*args: str, text: bool = False) -> subprocess.CompletedProcess:
    """git in the repository top level — pathspecs must not depend on the caller's cwd."""
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    return subprocess.run(["git", *args], capture_output=True, text=text, check=False, cwd=top)


def _commit(ref: str) -> str:
    r = _git("rev-parse", "--verify", f"{ref}^{{commit}}", text=True)
    r.check_returncode()
    return r.stdout.strip()


def gate_build(ref: str, out: Path) -> Path:
    sha = _commit(ref)
    files = {}
    for n in GATE_FILES:
        r = _git("show", f"{sha}:ops/{n}")
        r.check_returncode()
        files[n] = r.stdout
    return pack_gate(files, sha, out)


def pack_gate(files: dict[str, bytes], sha: str, out: Path) -> Path:
    files = dict(files)
    src = {"format": FORMAT, "sha": sha, "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "files": {n: _sha256(b) for n, b in files.items()}}
    files[GATE_SOURCE] = json.dumps(src, indent=1, sort_keys=True).encode()
    out.mkdir(parents=True, exist_ok=True)
    tgz = out / f"pigos-gate-{sha[:12]}.tar.gz"
    _write_tgz(tgz, files, {n: 0o755 for n in GATE_FILES if n != "additive_revisions.txt"})
    return tgz


def verify_gate(d: Path) -> tuple[int, list[str]]:
    try:
        src = json.loads((d / GATE_SOURCE).read_text(encoding="utf-8"))
        want = src["files"]
        if not isinstance(want, dict):
            raise TypeError("files")
    except (OSError, ValueError, KeyError, TypeError) as e:
        return 3, [f"REFUSED: {GATE_SOURCE} missing or unreadable in {d} ({e.__class__.__name__}) - the gate cannot vouch for itself"]
    bad = []
    for n in GATE_FILES:
        f = d / n
        if n not in want:
            bad.append(f"not recorded {n}")
        elif not f.is_file():
            bad.append(f"missing {n}")
        elif _sha256(f.read_bytes()) != want[n]:
            bad.append(f"modified {n}")
    if bad:
        return 3, [f"REFUSED: gate files differ from gate source {src.get('sha')}"] + [f"  {x}" for x in bad]
    return 0, [f"OK: gate == source {src.get('sha')}"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--ref", required=True)
    b.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--root", type=Path, required=True)
    v.add_argument("--expect-sha", required=True)
    gb = sub.add_parser("gate-build")
    gb.add_argument("--ref", required=True)
    gb.add_argument("--out", type=Path, required=True)
    gv = sub.add_parser("verify-gate")
    gv.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        print(build(a.ref, a.out))
        return 0
    if a.cmd == "gate-build":
        print(gate_build(a.ref, a.out))
        return 0
    rc, msgs = verify(a.root, a.expect_sha) if a.cmd == "verify" else verify_gate(a.dir)
    print("\n".join(msgs))
    return rc


if __name__ == "__main__":
    sys.exit(main())
