"""D-15a guard (2026-09-23): the CUSTOMER_VISIBLE path exists in code, but nothing in the repo ever sets it — no migration,
seed or script writes the visibility flag, and the decision never infers visibility from a farm's country/jurisdiction."""
from __future__ import annotations

import ast
import re
from pathlib import Path

API = Path(__file__).resolve().parents[2]
SERVICE = API / "app" / "services" / "feed_visibility.py"
KEY = "FEED_DELIVERY_VISIBILITY"


STATE_RE = re.compile(r"FEED_DELIVERY_VISIBILITY|REFERENCE_VISIBLE|CUSTOMER_VISIBLE")


def _py_files(*dirs: str) -> list[Path]:
    return [p for d in dirs for p in (API / d).rglob("*.py") if "__pycache__" not in p.parts]


def _code_strings(src: str) -> list[str]:
    """String constants that are code, not documentation: docstrings excluded (comments are not in the AST)."""
    tree = ast.parse(src)
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


def test_flag_and_states_are_code_only_in_the_service():
    """Anywhere else in app/, alembic/ or scripts/ a string constant naming the flag or a state would be a second
    decision point or a writer — the CUSTOMER_VISIBLE path must exist only as the service constant."""
    offenders = [str(p.relative_to(API)) for p in _py_files("app", "alembic", "scripts")
                 if p != SERVICE and any(STATE_RE.search(v) for v in _code_strings(p.read_text(encoding="utf-8-sig")))]
    sql = [str(p.relative_to(API)) for p in API.rglob("*.sql") if STATE_RE.search(p.read_text(encoding="utf-8", errors="replace"))]
    assert offenders == [] and sql == []


def test_scanner_is_not_vacuous():
    nl = "\n"
    assert _code_strings('"""doc CUSTOMER_VISIBLE"""' + nl + "x = 1  # REFERENCE_VISIBLE" + nl) == []
    assert any(STATE_RE.search(v) for v in _code_strings('x = "CUSTOMER_VISIBLE"' + nl))


def test_decision_does_not_infer_from_country():
    tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not ({"country", "country_code", "jurisdiction", "market", "region"} & names), names


def test_default_is_hidden_and_only_three_states():
    from app.services import feed_visibility as fv
    assert fv.STATES == ("HIDDEN", "REFERENCE_VISIBLE", "CUSTOMER_VISIBLE")
    assert not fv.is_visible("HIDDEN") and not fv.is_visible("") and not fv.is_visible("reference_visible")
    assert fv.is_visible("REFERENCE_VISIBLE") and fv.is_visible("CUSTOMER_VISIBLE")
