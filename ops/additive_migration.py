"""Is an Alembic migration's upgrade() additive-only? — static (AST) check, no app import, no DB.

"Additive" here means: code written before this revision keeps working on the schema after it, so the deploy gate may
let an OLDER code tree run on a database that is AHEAD of it (ops/additive_revisions.txt, decision D-A 2026-09-23).

Allowed in upgrade():
  op.create_table(...)                                   new table — old code never touches it
  op.create_index(...) on a table created in this upgrade (any), or non-unique on an existing table
  op.add_column(t, sa.Column(..., nullable=True))        or with server_default — old INSERTs still succeed
Everything else is refused, including: drop_* · alter_column · rename_table · execute · bulk_insert ·
create_unique_constraint / create_check_constraint / create_foreign_key / create_primary_key on existing tables ·
unique index on an existing table · add_column NOT NULL without server_default · any non-`op.` statement with side effects.

This does not replace review. It stops the obvious mistake of allow-listing a destructive revision.
REVIEW notes (not failures): a new table with a FOREIGN KEY to an EXISTING table makes old-code hard DELETEs of the
referenced rows fail while rows point at them — a reviewer must confirm the old code never hard-deletes those rows.

    python ops/additive_migration.py api/alembic/versions/a7c9e1f3b5d7_*.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

_CONSTRAINT_OPS = {"create_unique_constraint", "create_check_constraint", "create_foreign_key", "create_primary_key"}


def _kw(call: ast.Call, name: str) -> ast.expr | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def _const(node: ast.expr | None):
    return node.value if isinstance(node, ast.Constant) else None


def _first_str(call: ast.Call, pos: int, kw: str) -> str | None:
    if len(call.args) > pos and isinstance(call.args[pos], ast.Constant):
        return call.args[pos].value
    return _const(_kw(call, kw))


def check(text: str) -> tuple[bool, list[str]]:
    """(additive?, reasons). reasons lists every violation (empty when additive) or why it could not be judged."""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return False, [f"unparseable: {e.msg}"]
    ups = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade"]
    if len(ups) != 1:
        return False, [f"expected exactly one upgrade(), found {len(ups)}"]
    created: set[str] = set()
    reasons: list[str] = []
    for stmt in ups[0].body:
        if isinstance(stmt, ast.Pass) or (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)):
            continue                                               # pass / docstring
        call = stmt.value if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) else None
        fn = call.func if call else None
        if not (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id == "op"):
            reasons.append(f"line {stmt.lineno}: statement is not a plain op.<call>(...) - cannot prove it additive")
            continue
        name = fn.attr
        if name == "create_table":
            t = _first_str(call, 0, "table_name")
            if t is None:
                reasons.append(f"line {stmt.lineno}: create_table with non-literal name")
            else:
                created.add(t)
        elif name == "create_index":
            t = _first_str(call, 1, "table_name")
            unique = _const(_kw(call, "unique")) is True
            if t is None:
                reasons.append(f"line {stmt.lineno}: create_index with non-literal table")
            elif unique and t not in created:
                reasons.append(f"line {stmt.lineno}: unique index on existing table {t} - old writes may start failing")
        elif name == "add_column":
            col = call.args[1] if len(call.args) > 1 else None
            ok = False
            if isinstance(col, ast.Call):
                nullable = _const(_kw(col, "nullable"))
                ok = nullable is True or _kw(col, "server_default") is not None
            t = _first_str(call, 0, "table_name")
            if not ok and t not in created:
                reasons.append(f"line {stmt.lineno}: add_column on {t} is NOT NULL without server_default - old INSERTs fail")
        elif name in _CONSTRAINT_OPS:
            t = _first_str(call, 1, "table_name") if name != "create_foreign_key" else _first_str(call, 1, "source_table")
            if t not in created:
                reasons.append(f"line {stmt.lineno}: {name} on existing table {t}")
        else:
            reasons.append(f"line {stmt.lineno}: op.{name} is not additive")
    return (not reasons), reasons


def review_notes(text: str) -> list[str]:
    """FKs from tables created in upgrade() to tables that already existed. Empty when unparseable (check() reports that)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    ups = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade"]
    if len(ups) != 1:
        return []
    created: dict[str, ast.Call] = {}
    for stmt in ups[0].body:
        c = stmt.value if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) else None
        if c and isinstance(c.func, ast.Attribute) and c.func.attr == "create_table":
            t = _first_str(c, 0, "table_name")
            if t:
                created[t] = c
    notes = []
    for t, c in created.items():
        for node in ast.walk(c):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"ForeignKeyConstraint", "ForeignKey"}:
                targets = node.args[1] if node.func.attr == "ForeignKeyConstraint" and len(node.args) > 1 else (node.args[0] if node.args else None)
                refs = [e.value for e in getattr(targets, "elts", [targets]) if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                for r in refs:
                    ref_table = r.split(".")[0]
                    if ref_table not in created:
                        notes.append(f"new table {t} references existing table {ref_table} (FK {r}) - "
                                     f"confirm old code never hard-deletes {ref_table} rows")
    return notes


def main(argv: list[str]) -> int:
    rc = 0
    for p in argv:
        ok, reasons = check(Path(p).read_text(encoding="utf-8"))
        print(f"{'ADDITIVE' if ok else 'NOT_ADDITIVE'} {Path(p).name}")
        for r in reasons:
            print(f"  - {r}")
        for n in review_notes(Path(p).read_text(encoding="utf-8")):
            print(f"  REVIEW: {n}")
        rc |= 0 if ok else 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
