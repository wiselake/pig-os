"""B-2 / D-15b (2026-09-23): the feed read API never computes or returns FCR-family metrics. The router is read as an AST
(comments and docstrings that *mention* FCR do not count); any code path that reaches a cohort/efficiency metric fails."""
from __future__ import annotations

import ast
from pathlib import Path

ROUTER = Path(__file__).resolve().parents[2] / "app" / "routers" / "base" / "feed_summary.py"
EFFICIENCY = {"FCR", "FEED_COST_PER_KG_GAIN", "FEED_QTY_PER_HEAD", "FEED_COST_PER_PIG", "ADG"}
EFFICIENCY_FUNCS = {"fcr", "feed_cost_per_kg_gain", "feed_qty_per_head", "feed_cost_per_pig", "adg"}


def violations(src: str) -> list[str]:
    out = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Attribute) and node.attr in EFFICIENCY | EFFICIENCY_FUNCS:
            out.append(f"line {node.lineno}: .{node.attr}")
        elif isinstance(node, ast.Name) and node.id in EFFICIENCY | EFFICIENCY_FUNCS:
            out.append(f"line {node.lineno}: {node.id}")
        elif isinstance(node, ast.Constant) and node.value in EFFICIENCY:
            out.append(f"line {node.lineno}: '{node.value}'")
        elif isinstance(node, ast.keyword) and node.arg == "with_cohort" and not (
                isinstance(node.value, ast.Constant) and node.value.value is False):
            out.append(f"line {node.value.lineno}: with_cohort is not literally False")
    return out


def test_router_has_no_efficiency_metric_path():
    assert violations(ROUTER.read_text(encoding="utf-8")) == []


def test_every_manual_load_is_explicitly_cohort_free():
    tree = ast.parse(ROUTER.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "load_feed_input"]
    assert calls, "expected load_feed_input calls"
    for c in calls:
        kw = {k.arg: k.value for k in c.keywords}
        assert isinstance(kw.get("with_cohort"), ast.Constant) and kw["with_cohort"].value is False, ast.dump(c)


def test_checker_is_not_vacuous():
    bad = "def f(m):\n    x = m.FCR\n    y = fcr(inp)\n    z = load_feed_input(db, farm, s, e, with_cohort=True)\n    return {'FCR': 1}\n"
    v = violations(bad)
    assert len(v) >= 4, v
