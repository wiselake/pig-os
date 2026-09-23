"""The execution record's numbers block must be exactly what the run files produce (review ③, 2026-09-23).

A hand-typed or hand-edited number in the generated block fails here — the fix is to change the run files (evidence)
or rerun `scripts/feed_load_report.py --write`, never to edit the block.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "docs" / "feed" / "runs" / "prod_20260923"
DOC = ROOT / "docs" / "feed" / "releases" / "FEED_INITIAL_LOAD_EXECUTION_20260923.md"

spec = importlib.util.spec_from_file_location("feed_load_report", ROOT / "api" / "scripts" / "feed_load_report.py")
flr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flr)  # type: ignore[union-attr]


def _block(doc: str) -> str:
    return doc[doc.index(flr.BEGIN):doc.index(flr.END) + len(flr.END)]


def test_committed_block_equals_generated():
    doc = DOC.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert _block(doc) == flr.render(RUN)


def test_hand_edit_is_detected():
    doc = DOC.read_text(encoding="utf-8").replace("\r\n", "\n")
    tampered = _block(doc).replace("5461 · 5202 · 259", "5461 · 5203 · 258", 1)
    assert tampered != _block(doc), "fixture assumption: the pre-count row must be present"
    assert tampered != flr.render(RUN)


def test_every_row_declares_a_provenance_grade():
    rows = [ln for ln in flr.render(RUN).splitlines() if ln.startswith("| ") and not ln.startswith("| 단계")]
    assert rows and all(ln.rstrip(" |").split("|")[-1].strip().split()[0] in {"MACHINE", "CAPTURED", "TRANSCRIBED"} for ln in rows)
