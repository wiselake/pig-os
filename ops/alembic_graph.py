"""Alembic revision graph from a git ref (or a directory) — without importing the app or connecting to a DB.

    python ops/alembic_graph.py --ref origin/main            # heads + children of each revision
    python ops/alembic_graph.py --dir api/alembic/versions --check-db-revision a7c9e1f3b5d7

Used by ops/deploy.sh preflight (deploy refuses if the DB revision is not a head of the code being deployed)
and for merge-safety checks (two revisions with the same down_revision → multiple heads).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

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
    ap.add_argument("--check-db-revision", help="exit 3 unless this revision is the single head of the code")
    a = ap.parse_args()
    graph = from_ref(a.ref) if a.ref else from_dir(a.dir)
    hs = heads(graph)
    print(f"revisions={len(graph)} heads={hs}")
    if a.children_of:
        print(f"children_of[{a.children_of}]={children_of(graph, a.children_of)}")
    if a.check_db_revision:
        if len(hs) != 1:
            print(f"REFUSED: code has {len(hs)} alembic heads {hs}")
            return 3
        if a.check_db_revision not in graph:
            print(f"REFUSED: DB revision {a.check_db_revision} does not exist in this code (code head {hs[0]}) - "
                  "the database is ahead of the code being deployed")
            return 3
        if a.check_db_revision != hs[0]:
            print(f"REFUSED: DB revision {a.check_db_revision} != code head {hs[0]} - pending migration(s); "
                  "apply them through the approved path first")
            return 3
        print(f"OK: DB revision == code head {hs[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
