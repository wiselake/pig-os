"""Feed Engine 순수성 — 소스 스캔 (IMPLEMENTATION_MAP T-X1).

engine/feed/** 는 DB·시계·난수·환경·네트워크를 모른다. 결정론의 전제이자, "같은 입력 → 같은 결과" 가
테스트 몇 개가 아니라 구조로 보장된다는 증거다.
"""
from __future__ import annotations

import re
from pathlib import Path

_PKG = Path(__file__).resolve().parents[2] / "app" / "engine" / "feed"

_FORBIDDEN = [
    r"^\s*(from|import)\s+sqlalchemy",
    r"^\s*from\s+app\.db\b",
    r"^\s*from\s+app\.services\.(?!kpi_status_assembler\b)",   # 상태 조립기(순수 함수)만 허용
    r"^\s*(from|import)\s+(random|secrets|os|sys|time|httpx|requests|asyncio)\b",
    r"datetime\.(now|utcnow|today)\(",
    r"date\.today\(",
    r"os\.environ",
    r"\bsettings\b",
]


def test_feed_engine_has_no_side_effect_imports_or_clock_access():
    hits = []
    for p in sorted(_PKG.glob("*.py")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for pat in _FORBIDDEN:
                if re.search(pat, line):
                    hits.append(f"{p.name}:{i}: {line.strip()}")
    assert not hits, "feed engine must stay pure:\n" + "\n".join(hits)


def test_feed_engine_package_exists_with_expected_modules():
    assert {p.name for p in _PKG.glob("*.py")} >= {"__init__.py", "types.py", "normalize.py", "metrics.py", "variance.py", "status.py"}
