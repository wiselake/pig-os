"""Alembic revision graph from a git ref (or a directory) — without importing the app or connecting to a DB.

    python ops/alembic_graph.py --ref origin/main            # heads + children of each revision
    python ops/alembic_graph.py --dir api/alembic/versions --check-db-revision a7c9e1f3b5d7         --additive-allowlist ops/additive_revisions.txt

Used by ops/deploy.sh preflight and for merge-safety checks (two revisions with the same down_revision → multiple heads).

Gate rule (fail closed):
  code must have exactly one head
  DB revision == code head                                   → OK
  DB revision in the code but not the head                   → REFUSED (pending migration)
  DB revision NOT in the code (DB ahead of the code):
      walk DB revision → parent → … using the additive allowlist; every revision walked must be listed and the walk must
      land on the code head                                  → OK ("ahead by additive revisions …")
      otherwise                                              → REFUSED
  allowlist missing / unreadable / malformed / duplicate     → REFUSED, whatever the revisions are
The allowlist is read from the gate installation (next to check_migration_drift.sh), never from the tree being deployed:
on a rollback the deployed tree is OLDER than the database and cannot know about the newer revisions (decision D-A).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ALLOW_LINE = re.compile(r"^([0-9a-zA-Z_]+)[ \t]+([0-9a-zA-Z_]+)[ \t]+(\S.*)$")


class AllowlistError(Exception):
    pass


def load_allowlist(path: Path) -> dict[str, str]:
    """revision -> parent. Comments (#) and blank lines ignored; anything else must be `<rev> <parent> <reason>`."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise AllowlistError(f"cannot read allowlist {path}: {e.__class__.__name__}") from e
    out: dict[str, str] = {}
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = ALLOW_LINE.match(s)
        if not m:
            raise AllowlistError(f"allowlist line {n} malformed (want '<revision> <parent> <reason>')")
        if m.group(1) in out:
            raise AllowlistError(f"allowlist line {n}: duplicate revision {m.group(1)}")
        out[m.group(1)] = m.group(2)
    return out


def check_db_revision(graph: dict[str, list[str]], dbrev: str, allow: dict[str, str]) -> tuple[int, str]:
    hs = heads(graph)
    if len(hs) != 1:
        return 3, f"REFUSED: code has {len(hs)} alembic heads {hs}"
    head = hs[0]
    if not dbrev or dbrev == "None":
        return 3, "REFUSED: DB revision could not be read"
    if dbrev in graph:
        if dbrev == head:
            return 0, f"OK: DB revision == code head {head}"
        return 3, (f"REFUSED: DB revision {dbrev} != code head {head} - pending migration(s); "
                   "apply them through the approved path first")
    chain: list[str] = []
    cur = dbrev
    while True:
        if cur in chain:
            return 3, f"REFUSED: allowlist parent chain loops at {cur}"
        if cur not in allow:
            return 3, (f"REFUSED: DB revision {dbrev} is ahead of the code (head {head}) and {cur} is not in the "
                       "additive allowlist - the database is ahead of the code being deployed")
        chain.append(cur)
        parent = allow[cur]
        if parent == head:
            return 0, f"OK: DB is ahead of code head {head} by additive revision(s) {chain} (allowlisted)"
        if parent in graph:
            return 3, (f"REFUSED: allowlisted {cur} sits on {parent}, which is not the code head {head} - "
                       "the code has migrations the database lacks")
        cur = parent


REV = re.compile(r'^revision\s*(?::\s*str\s*)?=\s*["\']([0-9a-zA-Z_]+)["\']', re.M)
DOWN = re.compile(r'^down_revision\s*(?::[^=]*)?=\s*(None|["\']([0-9a-zA-Z_]+)["\']|\(([^)]*)\))', re.M)


def parse(text: str) -> tuple[str, list[str]] | None:
    r = REV.search(text)
    d = DOWN.search(text)
    if not r or not d:
        return None
    if d.group(1) == "None":
        downs: list[str] = []
    elif d.group(2):
        downs = [d.group(2)]
    else:
        downs = re.findall(r'["\']([0-9a-zA-Z_]+)["\']', d.group(3) or "")
    return r.group(1), downs


def from_ref(ref: str) -> dict[str, list[str]]:
    names = subprocess.run(["git", "ls-tree", "--name-only", f"{ref}:api/alembic/versions"],
                           capture_output=True, text=True, check=True).stdout.split()
    graph = {}
    for n in names:
        if not n.endswith(".py"):
            continue
        text = subprocess.run(["git", "show", f"{ref}:api/alembic/versions/{n}"], capture_output=True, text=True,
                              encoding="utf-8", check=True).stdout
        p = parse(text)
        if p:
            graph[p[0]] = p[1]
    return graph


def from_dir(d: Path) -> dict[str, list[str]]:
    graph = {}
    for f in d.glob("*.py"):
        p = parse(f.read_text(encoding="utf-8"))
        if p:
            graph[p[0]] = p[1]
    return graph


def heads(graph: dict[str, list[str]]) -> list[str]:
    parents = {x for ds in graph.values() for x in ds}
    return sorted(set(graph) - parents)


def children_of(graph: dict[str, list[str]], rev: str) -> list[str]:
    return sorted(r for r, ds in graph.items() if rev in ds)


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ref")
    g.add_argument("--dir", type=Path)
    ap.add_argument("--children-of")
    ap.add_argument("--check-db-revision", help="gate: exit 3 unless the rule in the module docstring passes")
    ap.add_argument("--additive-allowlist", type=Path, help="required with --check-db-revision (fail closed)")
    a = ap.parse_args()
    graph = from_ref(a.ref) if a.ref else from_dir(a.dir)
    hs = heads(graph)
    print(f"revisions={len(graph)} heads={hs}")
    if a.children_of:
        print(f"children_of[{a.children_of}]={children_of(graph, a.children_of)}")
    if a.check_db_revision is not None:
        if a.additive_allowlist is None:
            print("REFUSED: --additive-allowlist not given (the gate fails closed)")
            return 3
        try:
            allow = load_allowlist(a.additive_allowlist)
        except AllowlistError as e:
            print(f"REFUSED: {e}")
            return 3
        rc, msg = check_db_revision(graph, a.check_db_revision, allow)
        print(msg)
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
